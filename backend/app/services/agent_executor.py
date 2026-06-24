"""Agent execution service — runs an AgentRun against the configured LLM provider."""
import logging
from datetime import datetime, timezone
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.agent import Agent, AgentRun, AgentRunEvent, AgentRunStatus, AgentVersion
from app.models.audit import AuditEventType
from app.providers.base import Message
from app.providers.registry import get_registry
from app.services.audit import log_event

logger = logging.getLogger(__name__)


async def _execute_media_run(run: AgentRun, agent: Agent, version: AgentVersion | None, db: AsyncSession) -> AgentRun:
    """Execute a media generation agent run via HuggingFace Inference API."""
    from app.config import settings
    from app.providers.huggingface_media import HuggingFaceMediaProvider

    if not settings.huggingface_api_token:
        run.status = AgentRunStatus.FAILED
        run.error = "HuggingFace API token not configured. Add HUGGINGFACE_API_TOKEN to your .env file."
        run.finished_at = datetime.now(timezone.utc)
        await db.commit()
        await db.refresh(run)
        return run

    run.status = AgentRunStatus.RUNNING
    run.started_at = datetime.now(timezone.utc)
    run.model_provider = "huggingface_media"
    await db.commit()

    prompt = ""
    if run.input:
        prompt = run.input.get("goal") or run.input.get("task") or run.input.get("prompt") or str(run.input)

    media_type = "image"
    if version and version.config:
        media_type = version.config.get("media_type", "image")

    provider = HuggingFaceMediaProvider(settings.huggingface_api_token)
    try:
        if media_type == "audio":
            result = await provider.generate_audio(prompt)
        elif media_type == "video":
            result = await provider.generate_video(prompt)
        elif media_type == "upscale":
            result = await provider.upscale_image(prompt)
        else:
            result = await provider.generate_image(prompt)

        run.status = AgentRunStatus.COMPLETED
        run.output = result
        run.finished_at = datetime.now(timezone.utc)

        db.add(AgentRunEvent(run_id=run.id, event_type="completion", data={"status": "completed", "media_type": media_type}))
        await log_event(db, AuditEventType.AGENT_RUN, resource_type="agent_run", resource_id=str(run.id), detail={"status": "completed", "agent_id": agent.id})
    except Exception as exc:
        run.status = AgentRunStatus.FAILED
        run.error = str(exc)
        run.finished_at = datetime.now(timezone.utc)
        db.add(AgentRunEvent(run_id=run.id, event_type="error", data={"error": str(exc)}))

    await db.commit()
    await db.refresh(run)
    return run


async def execute_agent_run(run_id: int, db: AsyncSession) -> AgentRun:
    """Load a pending AgentRun, call the LLM (with agentic tool loop if workspace present), and persist the result."""
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

    # Media agents take a dedicated path
    provider_name = run.model_provider or (version.model_provider if version else None)
    if provider_name == "huggingface_media":
        return await _execute_media_run(run, agent, version, db)

    # Resolve provider and model
    model_id = run.model_id or (version.model_id if version else None)
    system_prompt = version.system_prompt if version else None

    registry = get_registry()
    provider = None

    if provider_name:
        provider = registry.get(provider_name)

    if provider is None:
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

    # Merge skills from version config + Chief auto-resolved _skills
    skill_slugs: list[str] = []
    if version and version.config:
        skill_slugs = list(version.config.get("skills", []))
    if run.input and run.input.get("_skills"):
        for s in run.input["_skills"]:
            if s not in skill_slugs:
                skill_slugs.append(s)
    if skill_slugs:
        from app.services.skill_loader import load_skills_content
        skill_context = await load_skills_content(skill_slugs)
        if skill_context:
            system_prompt = skill_context + "\n\n---\n\n" + (system_prompt or "")

    # Workspace / agentic tool loop
    workspace_path: Path | None = None
    use_tools = False
    if run.input and run.input.get("_workspace"):
        workspace_path = Path(run.input["_workspace"])
        workspace_path.mkdir(parents=True, exist_ok=True)
        if hasattr(provider, "complete_with_tools"):
            use_tools = True

    if use_tools and workspace_path is not None:
        from app.services.agent_tools import AGENT_TOOLS, OLLAMA_TOOLS, get_tools_system_addendum, make_tool_executor
        from app.services.workspace import ws_list_as_dicts

        tool_addendum = get_tools_system_addendum()
        system_prompt = (system_prompt or "") + "\n\n" + tool_addendum

        # Inject shared project context from Chief (all agents share same blueprint)
        shared_context = (run.input or {}).get("_shared_context", "")
        if shared_context:
            system_prompt = f"## Project Blueprint\n{shared_context}\n\n---\n\n" + system_prompt

        # Inject current workspace manifest so agents see what's already been built
        existing_files = ws_list_as_dicts(workspace_path)
        if existing_files:
            manifest_lines = "\n".join(f"  {f['path']} ({f['size']} B)" for f in existing_files)
            system_prompt += (
                f"\n\n## Files already in workspace:\n{manifest_lines}\n"
                "Use read_file to inspect any of these before writing new content."
            )

        # Choose correct tool format per provider
        tools = OLLAMA_TOOLS if provider.name == "ollama" else AGENT_TOOLS
        tool_exec = make_tool_executor(workspace_path)

        messages: list[Message] = []
        if system_prompt:
            messages.append(Message(role="system", content=system_prompt))

        user_content = ""
        if run.input:
            goal = run.input.get("goal") or run.input.get("task") or str(run.input)
            user_content = goal
        if not user_content:
            user_content = "Complete your assigned task."
        messages.append(Message(role="user", content=user_content))

        try:
            result = await provider.complete_with_tools(messages, model_id, tools, tool_exec)  # type: ignore[attr-defined]
            run.status = AgentRunStatus.COMPLETED
            run.output = {"content": result.content, "model": result.model, "provider": result.provider, "used_tools": True}
            if result.input_tokens is not None:
                run.output["input_tokens"] = result.input_tokens
            if result.output_tokens is not None:
                run.output["output_tokens"] = result.output_tokens
            run.finished_at = datetime.now(timezone.utc)
            db.add(AgentRunEvent(run_id=run.id, event_type="completion", data={"status": "completed", "provider": provider.name, "model": model_id, "used_tools": True}))
            await log_event(db, AuditEventType.AGENT_RUN, resource_type="agent_run", resource_id=str(run.id), detail={"status": "completed", "agent_id": agent.id})
        except Exception as exc:
            run.status = AgentRunStatus.FAILED
            run.error = str(exc)
            run.finished_at = datetime.now(timezone.utc)
            db.add(AgentRunEvent(run_id=run.id, event_type="error", data={"error": str(exc)}))

        await db.commit()
        await db.refresh(run)
        return run

    # Standard (non-agentic) path
    messages = []
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
