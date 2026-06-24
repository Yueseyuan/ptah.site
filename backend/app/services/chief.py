"""Chief orchestrator — decomposes a goal into subtasks, assigns agents, executes in parallel, merges results."""
import asyncio
import json
import logging
from datetime import datetime, timezone
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.agent import Agent, AgentCapability, AgentRun, AgentRunStatus
from app.models.audit import AuditEventType
from app.models.orchestrator import OrchestratorRun, OrchestratorRunStatus, OrchestratorTask, TaskStatus
from app.providers.base import Message
from app.providers.registry import get_registry
from app.services.agent_executor import execute_agent_run
from app.services.audit import log_event
from app.services.workspace import create_workspace, ws_list_as_dicts, ws_read_file

logger = logging.getLogger(__name__)

MAX_ROUNDS = 3

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
    "email": [],
    "social": [],
    "scrape": [],
    "content": [],
    "marketing": [],
}

_DECOMPOSE_SYSTEM = (
    "You are the Chief of an AI company. Your job is to:\n"
    "1. Create a shared project context (file structure, data models, API contracts, naming conventions, tech stack)\n"
    "2. Decompose the goal into 2-6 parallel subtasks for specialist agents\n\n"
    "Return ONLY valid JSON — no markdown, no explanation:\n"
    '{"shared_context": "...", "subtasks": [{"title": "...", "description": "...", "required_capability": "..."}]}\n\n'
    "shared_context should be a detailed technical blueprint all agents will follow. "
    "Include: folder structure, key file names, class/function names, data schemas, import conventions. "
    "Be specific enough that two agents writing different parts produce consistent, compatible code.\n\n"
    "required_capability must be one of: research, code, website, automation, document, knowledge, "
    "business, review, risk_review, email, social, scrape, content, marketing."
)

_MERGE_SYSTEM = (
    "You are the Chief of an AI company. Multiple specialist agents have completed subtasks. "
    "Synthesize their outputs into a concise, coherent final answer that addresses the original goal. "
    "Be direct and useful. No need to repeat the subtask titles verbatim."
)

_REVIEW_SYSTEM = (
    "You are the Chief of an AI company doing a quality review after agents built a project. "
    "Review what was built against the original goal and decide if it's complete and correct.\n\n"
    "Return ONLY valid JSON — no markdown, no explanation:\n"
    '{"is_complete": true, "summary": "...", "fix_tasks": [{"title": "...", "description": "...", "required_capability": "..."}]}\n\n'
    "is_complete: true if the core goal is achieved (minor gaps are OK). "
    "fix_tasks: specific, actionable tasks to fill genuine gaps or fix errors. "
    "Each fix_task description must name the exact files to modify and what to change."
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


async def _decompose_goal(goal: str, registry) -> tuple[list[dict], str]:
    """Use LLM to decompose the goal. Returns (subtasks, shared_context)."""
    provider, model_id = await _get_provider_and_model(registry)
    if provider is None:
        return [{"title": goal, "description": goal, "required_capability": "research"}], ""

    messages = [
        Message(role="system", content=_DECOMPOSE_SYSTEM),
        Message(role="user", content=f"Goal: {goal}"),
    ]
    try:
        result = await provider.complete(messages, model=model_id)
        data = json.loads(result.content)
        subtasks = data.get("subtasks", [])
        shared_context = data.get("shared_context", "")
        if subtasks and isinstance(subtasks, list):
            return subtasks, shared_context
    except (json.JSONDecodeError, KeyError, Exception) as exc:
        logger.warning("Chief decompose failed, falling back to single subtask: %s", exc)

    return [{"title": goal, "description": goal, "required_capability": "research"}], ""


async def _review_workspace(
    goal: str,
    workspace: Path,
    completed_subtasks: list[dict],
    registry,
) -> dict:
    """Review the workspace and decide if more work is needed."""
    provider, model_id = await _get_provider_and_model(registry)
    if provider is None:
        return {"is_complete": True, "summary": "No provider.", "fix_tasks": []}

    files = ws_list_as_dicts(workspace)
    if not files:
        return {
            "is_complete": False,
            "summary": "No files were produced.",
            "fix_tasks": [{"title": "Build the project", "description": goal, "required_capability": "code"}],
        }

    file_manifest = "\n".join(f"  {f['path']} ({f['size']} B)" for f in files)

    # Sample small files for context (up to 3 files, max 1500 chars each)
    samples = []
    for f in sorted(files, key=lambda x: x["size"])[:5]:
        if f["size"] < 4000:
            try:
                content = ws_read_file(workspace, f["path"])
                samples.append(f"### {f['path']}\n```\n{content[:1500]}\n```")
            except Exception:
                pass
    samples_text = "\n\n".join(samples[:3])

    subtasks_summary = "\n".join(
        f"- {m['title']}: {(m.get('output') or 'no output')[:300]}"
        for m in completed_subtasks
    )

    messages = [
        Message(role="system", content=_REVIEW_SYSTEM),
        Message(
            role="user",
            content=(
                f"Original goal: {goal}\n\n"
                f"Files built:\n{file_manifest}\n\n"
                f"Agent outputs:\n{subtasks_summary}\n\n"
                f"Sample files:\n{samples_text}\n\n"
                "Is the goal achieved? What's missing or broken?"
            ),
        ),
    ]
    try:
        result = await provider.complete(messages, model=model_id)
        data = json.loads(result.content)
        return {
            "is_complete": bool(data.get("is_complete", True)),
            "summary": data.get("summary", ""),
            "fix_tasks": data.get("fix_tasks", []),
        }
    except Exception as exc:
        logger.warning("Chief review failed: %s", exc)
        return {"is_complete": True, "summary": "Review skipped.", "fix_tasks": []}


async def _merge_results(goal: str, subtask_results: list[dict], registry) -> str:
    """Use LLM to merge all subtask outputs into a final summary."""
    provider, model_id = await _get_provider_and_model(registry)
    if provider is None:
        parts = [f"### {sr['title']}\n{sr.get('output', 'No output.')}" for sr in subtask_results]
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
        logger.warning("Chief merge failed: %s", exc)
        parts = [f"### {sr['title']}\n{sr.get('output', 'No output.')}" for sr in subtask_results]
        return "\n\n".join(parts)


def _match_agent(subtask: dict, agents: list[Agent], capabilities_map: dict[int, list[str]]) -> Agent | None:
    """Find the best agent for a subtask by capability, or return any active agent."""
    required = (subtask.get("required_capability") or "").lower()
    if required:
        for agent in agents:
            caps = capabilities_map.get(agent.id, [])
            if required in caps:
                return agent
    return agents[0] if agents else None


async def _create_and_run_agents(
    subtask_defs: list[dict],
    shared_context: str,
    workspace: Path,
    agents: list[Agent],
    capabilities_map: dict[int, list[str]],
    triggered_by_id: int,
    db: AsyncSession,
) -> list[dict]:
    """Create AgentRuns for each subtask, execute in parallel, return result dicts."""
    agent_run_ids: list[int] = []
    subtask_meta: list[dict] = []

    for subtask_def in subtask_defs:
        title = subtask_def.get("title", "Subtask")
        description = subtask_def.get("description", title)
        required_cap = subtask_def.get("required_capability", "")

        matched_agent = _match_agent(subtask_def, agents, capabilities_map)
        if matched_agent is None:
            subtask_meta.append({
                "title": title,
                "description": description,
                "agent_name": "none",
                "agent_run_id": None,
                "output": "No agents are configured. Please create agents in the Agents section.",
            })
            continue

        auto_skills = _CAPABILITY_SKILLS.get(required_cap, [])
        agent_run = AgentRun(
            agent_id=matched_agent.id,
            triggered_by_id=triggered_by_id,
            status=AgentRunStatus.PENDING,
            input={
                "goal": description,
                "_skills": auto_skills,
                "_workspace": str(workspace),
                "_shared_context": shared_context,
            },
        )
        db.add(agent_run)
        await db.flush()

        agent_run_ids.append(agent_run.id)
        subtask_meta.append({
            "title": title,
            "description": description,
            "agent_name": matched_agent.name,
            "agent_run_id": agent_run.id,
            "output": None,
        })

    await db.commit()

    if agent_run_ids:
        from app.database import AsyncSessionLocal

        async def _run_one(run_id: int) -> AgentRun:
            async with AsyncSessionLocal() as session:
                return await execute_agent_run(run_id, session)

        completed_runs: list[AgentRun] = list(
            await asyncio.gather(*[_run_one(rid) for rid in agent_run_ids])
        )

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

    return subtask_meta


async def run_chief(goal: str, db: AsyncSession, triggered_by_id: int) -> dict:
    """
    Execute the Chief orchestration loop:
    1. Decompose goal into subtasks + shared project context
    2. Execute all agents in parallel (round 1)
    3. Review workspace — if gaps found, run fix agents (rounds 2-3)
    4. Merge all results
    """
    registry = get_registry()

    provider, _ = await _get_provider_and_model(registry)
    if provider is None:
        return {
            "run_id": None,
            "error": "No model provider available. Configure one in Settings.",
            "subtasks": [],
            "merged_output": None,
            "workspace_files": [],
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
        # 0. Workspace
        workspace = await create_workspace(orch_run.id)

        # 1. Decompose — returns subtasks AND shared project blueprint
        subtask_defs, shared_context = await _decompose_goal(goal, registry)

        # 2. Load agents + capabilities
        agents: list[Agent] = list(
            (await db.execute(select(Agent).where(Agent.is_active.is_(True)).order_by(Agent.id))).scalars().all()
        )
        capabilities_rows = list((await db.execute(select(AgentCapability))).scalars().all())
        capabilities_map: dict[int, list[str]] = {}
        for cap in capabilities_rows:
            capabilities_map.setdefault(cap.agent_id, []).append(cap.capability_type.value)

        orch_run.status = OrchestratorRunStatus.RUNNING
        await db.commit()

        # 3. Round 1 — full build
        all_subtask_meta: list[dict] = await _create_and_run_agents(
            subtask_defs, shared_context, workspace, agents, capabilities_map, triggered_by_id, db
        )

        # 4. Review + fix rounds (up to MAX_ROUNDS - 1 additional rounds)
        for round_num in range(2, MAX_ROUNDS + 1):
            review = await _review_workspace(goal, workspace, all_subtask_meta, registry)
            logger.info("Chief review round %d: is_complete=%s, fixes=%d",
                        round_num, review["is_complete"], len(review.get("fix_tasks", [])))

            if review["is_complete"] or not review.get("fix_tasks"):
                break

            fix_meta = await _create_and_run_agents(
                review["fix_tasks"], shared_context, workspace, agents, capabilities_map, triggered_by_id, db
            )
            all_subtask_meta.extend(fix_meta)

        # 5. Merge all results into final output
        merged_output = await _merge_results(goal, all_subtask_meta, registry)

        # 6. Collect workspace files
        workspace_files = ws_list_as_dicts(workspace)

        # 7. Persist
        orch_run.status = OrchestratorRunStatus.COMPLETED
        orch_run.output = {
            "merged_output": merged_output,
            "workspace_files": workspace_files,
            "shared_context": shared_context,
            "subtasks": [
                {
                    "title": m["title"],
                    "description": m["description"],
                    "agent_name": m["agent_name"],
                    "agent_run_id": m["agent_run_id"],
                    "output": m["output"],
                }
                for m in all_subtask_meta
            ],
        }
        orch_run.finished_at = datetime.now(timezone.utc)
        await db.commit()

        return {
            "run_id": orch_run.id,
            "subtasks": all_subtask_meta,
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
            "workspace_files": [],
        }
