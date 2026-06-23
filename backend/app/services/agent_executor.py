"""Agent execution service — runs an AgentRun against the configured LLM provider."""
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.agent import Agent, AgentRun, AgentRunEvent, AgentRunStatus, AgentVersion
from app.models.audit import AuditEventType
from app.providers.base import Message
from app.providers.registry import get_registry
from app.services.audit import log_event


async def execute_agent_run(run_id: int, db: AsyncSession) -> AgentRun:
    """Load a pending AgentRun, call the LLM, and persist the result."""
    run = (await db.execute(select(AgentRun).where(AgentRun.id == run_id))).scalar_one_or_none()
    if run is None:
        raise ValueError(f"AgentRun {run_id} not found")

    agent = (await db.execute(select(Agent).where(Agent.id == run.agent_id))).scalar_one_or_none()
    if agent is None:
        raise ValueError(f"Agent {run.agent_id} not found")

    # Load current version for system prompt / model config
    version: AgentVersion | None = None
    if run.version_id:
        version = (await db.execute(
            select(AgentVersion).where(AgentVersion.id == run.version_id)
        )).scalar_one_or_none()
    else:
        version = (await db.execute(
            select(AgentVersion).where(
                AgentVersion.agent_id == agent.id,
                AgentVersion.is_current.is_(True),
            )
        )).scalar_one_or_none()

    # Resolve provider and model
    provider_name = run.model_provider or (version.model_provider if version else None)
    model_id = run.model_id or (version.model_id if version else None)
    system_prompt = version.system_prompt if version else None

    registry = get_registry()
    provider = None

    if provider_name:
        provider = registry.get(provider_name)

    if provider is None:
        # Pick the first healthy provider
        for p in registry.all():
            try:
                if await p.health():
                    provider = p
                    break
            except Exception:
                continue

    if provider is None:
        run.status = AgentRunStatus.FAILED
        run.error = "No model provider available. Configure one in Settings."
        run.finished_at = datetime.now(timezone.utc)
        await db.commit()
        await db.refresh(run)
        return run

    # If we found a provider but no model_id, pick any available model
    if not model_id:
        try:
            models = await provider.list_models()
            if models:
                model_id = models[0].id
        except Exception:
            pass

    if not model_id:
        run.status = AgentRunStatus.FAILED
        run.error = f"No model available on provider '{provider.name}'. Add a model in Settings."
        run.finished_at = datetime.now(timezone.utc)
        await db.commit()
        await db.refresh(run)
        return run

    # Mark running
    run.status = AgentRunStatus.RUNNING
    run.started_at = datetime.now(timezone.utc)
    run.model_provider = provider.name
    run.model_id = model_id
    await db.commit()

    # Build messages
    messages: list[Message] = []
    if system_prompt:
        messages.append(Message(role="system", content=system_prompt))

    user_content = ""
    if run.input:
        goal = run.input.get("goal") or run.input.get("task") or str(run.input)
        user_content = goal
    if not user_content:
        user_content = "Please complete your assigned task."

    messages.append(Message(role="user", content=user_content))

    try:
        result = await provider.complete(messages, model=model_id)
        run.status = AgentRunStatus.COMPLETED
        run.output = {"content": result.content, "model": result.model, "provider": result.provider}
        if result.input_tokens is not None:
            run.output["input_tokens"] = result.input_tokens
        if result.output_tokens is not None:
            run.output["output_tokens"] = result.output_tokens
        run.finished_at = datetime.now(timezone.utc)

        event = AgentRunEvent(
            run_id=run.id,
            event_type="completion",
            data={"status": "completed", "provider": provider.name, "model": model_id},
        )
        db.add(event)
        await log_event(
            db,
            AuditEventType.AGENT_RUN,
            resource_type="agent_run",
            resource_id=str(run.id),
            detail={"status": "completed", "agent_id": agent.id},
        )
    except Exception as exc:
        run.status = AgentRunStatus.FAILED
        run.error = str(exc)
        run.finished_at = datetime.now(timezone.utc)

        event = AgentRunEvent(
            run_id=run.id,
            event_type="error",
            data={"error": str(exc)},
        )
        db.add(event)

    await db.commit()
    await db.refresh(run)
    return run
