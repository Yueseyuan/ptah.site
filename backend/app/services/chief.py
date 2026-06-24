"""Chief orchestrator — decomposes a goal into subtasks, assigns agents, executes in parallel, merges results."""
import asyncio
import json
import logging
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.agent import Agent, AgentCapability, AgentRun, AgentRunStatus
from app.models.audit import AuditEventType
from app.models.orchestrator import OrchestratorRun, OrchestratorRunStatus, OrchestratorTask, TaskStatus
from app.providers.base import Message
from app.providers.registry import get_registry
from app.services.agent_executor import execute_agent_run
from app.services.audit import log_event
from app.services.workspace import create_workspace, ws_list_as_dicts

logger = logging.getLogger(__name__)

# Maps subtask capability → skills.sh slugs to auto-inject
_CAPABILITY_SKILLS: dict[str, list[str]] = {
    "code": ["python-patterns", "typescript-patterns"],
    "website": ["react-patterns", "nextjs-patterns"],
    "automation": ["python-patterns", "docker-patterns"],
    "review": ["security-patterns", "testing-patterns"],
    "risk_review": ["security-patterns"],
    "research": [],
    "document": [],
    "knowledge": [],
    "business": [],
}

_DECOMPOSE_SYSTEM = (
    "You are the Chief of an AI company. Your job is to decompose a high-level goal into "
    "parallel subtasks that specialized agents can execute independently. "
    "Return ONLY valid JSON in this exact format: "
    '{\"subtasks\": [{\"title\": \"...\", \"description\": \"...\", \"required_capability\": \"...\"}]}. '
    "Use one of these capability values: research, code, website, automation, document, knowledge, business, review, risk_review. "
    "Create 2-5 subtasks that together address the full goal."
)

_MERGE_SYSTEM = (
    "You are the Chief of an AI company. Multiple specialist agents have completed subtasks. "
    "Synthesize their outputs into a concise, coherent final answer that addresses the original goal. "
    "Be direct and useful. No need to repeat the subtask titles verbatim."
)


async def _get_provider_and_model(registry):
    """Return the first healthy (provider, model_id) pair or (None, None)."""
    for provider in registry.all():
        try:
            if not await provider.health():
                continue
            models = await provider.list_models()
            if models:
                return provider, models[0].id
        except Exception:
            continue
    return None, None


async def _decompose_goal(goal: str, registry) -> list[dict]:
    """Use LLM to decompose the goal. Falls back to a single subtask on error."""
    provider, model_id = await _get_provider_and_model(registry)
    if provider is None:
        return [{"title": goal, "description": goal, "required_capability": "research"}]

    messages = [
        Message(role="system", content=_DECOMPOSE_SYSTEM),
        Message(role="user", content=f"Goal: {goal}"),
    ]
    try:
        result = await provider.complete(messages, model=model_id)
        data = json.loads(result.content)
        subtasks = data.get("subtasks", [])
        if subtasks and isinstance(subtasks, list):
            return subtasks
    except (json.JSONDecodeError, KeyError, Exception) as exc:
        logger.warning("Chief decompose failed, falling back to single subtask: %s", exc)

    return [{"title": goal, "description": goal, "required_capability": "research"}]


async def _merge_results(goal: str, subtask_results: list[dict], registry) -> str:
    """Use LLM to merge all subtask outputs into a final summary."""
    provider, model_id = await _get_provider_and_model(registry)
    if provider is None:
        # No provider — concatenate outputs manually
        parts = []
        for sr in subtask_results:
            parts.append(f"### {sr['title']}\n{sr.get('output', 'No output.')}")
        return "\n\n".join(parts)

    outputs_text = "\n\n".join(
        f"Task: {sr['title']}\nResult: {sr.get('output', 'No output.')}"
        for sr in subtask_results
    )
    messages = [
        Message(role="system", content=_MERGE_SYSTEM),
        Message(
            role="user",
            content=f"Original goal: {goal}\n\nSubtask results:\n{outputs_text}\n\nSynthesize a final answer:",
        ),
    ]
    try:
        result = await provider.complete(messages, model=model_id)
        return result.content
    except Exception as exc:
        logger.warning("Chief merge failed, falling back to concatenation: %s", exc)
        parts = []
        for sr in subtask_results:
            parts.append(f"### {sr['title']}\n{sr.get('output', 'No output.')}")
        return "\n\n".join(parts)


def _match_agent(subtask: dict, agents: list[Agent], capabilities_map: dict[int, list[str]]) -> Agent | None:
    """Find the best agent for a subtask by capability, or return any active agent."""
    required = (subtask.get("required_capability") or "").lower()
    # Try capability match first
    if required:
        for agent in agents:
            caps = capabilities_map.get(agent.id, [])
            if required in caps:
                return agent
    # Fallback: any agent
    return agents[0] if agents else None


async def run_chief(goal: str, db: AsyncSession, triggered_by_id: int) -> dict:
    """
    Execute the Chief orchestration loop:
    1. Decompose goal into subtasks
    2. Match subtasks to agents
    3. Execute all AgentRuns in parallel
    4. Merge results
    5. Persist OrchestratorRun
    """
    registry = get_registry()

    # Quick provider check
    provider, _ = await _get_provider_and_model(registry)
    if provider is None:
        return {
            "run_id": None,
            "error": "No model provider available. Configure one in Settings.",
            "subtasks": [],
            "merged_output": None,
        }

    # Create OrchestratorRun
    orch_run = OrchestratorRun(
        name=f"Chief: {goal[:100]}",
        status=OrchestratorRunStatus.PLANNING,
        input={"goal": goal},
        triggered_by_id=triggered_by_id,
        started_at=datetime.now(timezone.utc),
    )
    db.add(orch_run)
    await db.commit()
    await db.refresh(orch_run)

    await log_event(
        db,
        AuditEventType.WORKFLOW_RUN,
        user_id=triggered_by_id,
        resource_type="orchestrator_run",
        resource_id=str(orch_run.id),
        detail={"goal": goal[:200]},
    )

    try:
        # 0. Create workspace for this run (agents write files here)
        workspace = await create_workspace(orch_run.id)

        # 1. Decompose
        subtask_defs = await _decompose_goal(goal, registry)

        # 2. Load agents + capabilities
        agents: list[Agent] = list(
            (await db.execute(select(Agent).where(Agent.is_active.is_(True)).order_by(Agent.id))).scalars().all()
        )
        capabilities_rows = list(
            (await db.execute(select(AgentCapability))).scalars().all()
        )
        capabilities_map: dict[int, list[str]] = {}
        for cap in capabilities_rows:
            capabilities_map.setdefault(cap.agent_id, []).append(cap.capability_type.value)

        # 3. Create OrchestratorTasks and AgentRuns
        orch_run.status = OrchestratorRunStatus.RUNNING
        await db.commit()

        task_records: list[OrchestratorTask] = []
        agent_run_ids: list[int] = []
        subtask_meta: list[dict] = []  # tracks {title, description, agent_name, agent_run_id}

        for subtask_def in subtask_defs:
            title = subtask_def.get("title", "Subtask")
            description = subtask_def.get("description", title)
            required_cap = subtask_def.get("required_capability", "")

            orch_task = OrchestratorTask(
                title=title,
                description=description,
                task_type=required_cap or "general",
                status=TaskStatus.ASSIGNED,
                input={"goal": description},
                required_capabilities=[required_cap] if required_cap else [],
                created_by_id=triggered_by_id,
                started_at=datetime.now(timezone.utc),
            )
            db.add(orch_task)
            await db.flush()  # get orch_task.id
            task_records.append(orch_task)

            matched_agent = _match_agent(subtask_def, agents, capabilities_map)

            if matched_agent is None:
                subtask_meta.append({
                    "title": title,
                    "description": description,
                    "agent_name": "none",
                    "agent_run_id": None,
                    "output": "No agents are configured. Please create agents in the Agents section.",
                })
                orch_task.status = TaskStatus.FAILED
                orch_task.error = "No agents available"
                orch_task.finished_at = datetime.now(timezone.utc)
                continue

            auto_skills = _CAPABILITY_SKILLS.get(required_cap, [])
            agent_run = AgentRun(
                agent_id=matched_agent.id,
                triggered_by_id=triggered_by_id,
                status=AgentRunStatus.PENDING,
                input={"goal": description, "_skills": auto_skills, "_workspace": str(workspace)},
            )
            db.add(agent_run)
            await db.flush()  # get agent_run.id

            agent_run_ids.append(agent_run.id)
            subtask_meta.append({
                "title": title,
                "description": description,
                "agent_name": matched_agent.name,
                "agent_run_id": agent_run.id,
                "output": None,  # will be filled after execution
            })

        await db.commit()

        # 4. Execute all AgentRuns in parallel
        if agent_run_ids:
            # Each coroutine gets its own session so concurrent execution is safe.
            from app.database import AsyncSessionLocal

            async def _run_one(run_id: int) -> AgentRun:
                async with AsyncSessionLocal() as session:
                    return await execute_agent_run(run_id, session)

            completed_runs: list[AgentRun] = list(
                await asyncio.gather(*[_run_one(rid) for rid in agent_run_ids])
            )

            # Map results back to subtask_meta
            run_map = {r.id: r for r in completed_runs}
            for meta in subtask_meta:
                rid = meta.get("agent_run_id")
                if rid is not None and rid in run_map:
                    run = run_map[rid]
                    if run.output and isinstance(run.output, dict):
                        meta["output"] = run.output.get("content", str(run.output))
                    elif run.error:
                        meta["output"] = f"Error: {run.error}"
                    else:
                        meta["output"] = "No output produced."

        # 5. Merge results
        merged_output = await _merge_results(goal, subtask_meta, registry)

        # 6. Collect workspace files
        workspace_files = ws_list_as_dicts(workspace)

        # 7. Update OrchestratorRun
        orch_run.status = OrchestratorRunStatus.COMPLETED
        orch_run.output = {
            "merged_output": merged_output,
            "workspace_files": workspace_files,
            "subtasks": [
                {
                    "title": m["title"],
                    "description": m["description"],
                    "agent_name": m["agent_name"],
                    "agent_run_id": m["agent_run_id"],
                    "output": m["output"],
                }
                for m in subtask_meta
            ],
        }
        orch_run.finished_at = datetime.now(timezone.utc)
        await db.commit()

        return {
            "run_id": orch_run.id,
            "subtasks": subtask_meta,
            "merged_output": merged_output,
            "workspace_files": workspace_files,
        }

    except Exception as exc:
        logger.exception("Chief run failed: %s", exc)
        orch_run.status = OrchestratorRunStatus.FAILED
        orch_run.error = str(exc)
        orch_run.finished_at = datetime.now(timezone.utc)
        await db.commit()
        return {
            "run_id": orch_run.id,
            "error": str(exc),
            "subtasks": [],
            "merged_output": None,
        }
