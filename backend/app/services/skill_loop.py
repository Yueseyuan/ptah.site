"""Self-improving skill loop — extract reusable playbooks from successful Chief runs
and inject them into future runs as context."""
import json
import logging
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.skill import Skill, SkillVersion
from app.providers.base import Message

logger = logging.getLogger(__name__)

_EXTRACT_SYSTEM = (
    "You are an AI that identifies reusable playbooks from successful task completions. "
    "Given a goal and the steps that successfully achieved it, extract a concise reusable skill.\n\n"
    "Return ONLY valid JSON — no markdown, no explanation:\n"
    '{"should_save": true, "name": "...", "description": "...", "playbook": "..."}\n\n'
    "should_save: true only if this is a genuinely reusable pattern across different goals (not a one-off).\n"
    "name: short unique skill name (e.g. 'Market Research Report', 'Python FastAPI CRUD Generator')\n"
    "description: one sentence describing when to use this skill\n"
    "playbook: step-by-step reusable approach as numbered steps (3-8 steps)"
)


async def extract_skill_from_run(
    goal: str,
    subtasks: list[dict],
    merged_output: str,
    triggered_by_id: int,
    db: AsyncSession,
    registry: Any,
) -> Skill | None:
    """Ask the LLM if this run produced a reusable skill; if so, save or update it."""
    from app.services.chief import _get_provider_and_model

    provider, model_id = await _get_provider_and_model(registry)
    if provider is None:
        return None

    steps_summary = "\n".join(
        f"- {s['title']}: {(s.get('output') or '')[:300]}" for s in subtasks
    )

    messages = [
        Message(role="system", content=_EXTRACT_SYSTEM),
        Message(
            role="user",
            content=(
                f"Goal: {goal}\n\n"
                f"Steps taken:\n{steps_summary}\n\n"
                f"Final result: {merged_output[:500]}\n\n"
                "Extract a reusable skill if this represents a repeatable pattern."
            ),
        ),
    ]

    try:
        result = await provider.complete(messages, model=model_id)
        data = json.loads(result.content)
        if not data.get("should_save"):
            return None

        name = (data.get("name") or "").strip()[:255]
        description = (data.get("description") or "").strip()
        playbook = (data.get("playbook") or "").strip()

        if not name or not playbook:
            return None

        existing = (await db.execute(select(Skill).where(Skill.name == name))).scalar_one_or_none()
        if existing:
            for old_ver in (await db.execute(
                select(SkillVersion).where(
                    SkillVersion.skill_id == existing.id,
                    SkillVersion.is_current.is_(True),
                )
            )).scalars().all():
                old_ver.is_current = False
            db.add(SkillVersion(
                skill_id=existing.id,
                version="auto",
                code_config={"playbook": playbook, "source_goal": goal[:200]},
                is_current=True,
                published_by_id=triggered_by_id,
            ))
            await db.commit()
            logger.info("Updated skill '%s' from Chief run", name)
            return existing

        skill = Skill(
            name=name,
            description=description,
            is_active=True,
            created_by_id=triggered_by_id,
        )
        db.add(skill)
        await db.flush()
        db.add(SkillVersion(
            skill_id=skill.id,
            version="1.0",
            code_config={"playbook": playbook, "source_goal": goal[:200]},
            is_current=True,
            published_by_id=triggered_by_id,
        ))
        await db.commit()
        await db.refresh(skill)
        logger.info("Created new skill '%s' from Chief run", name)
        return skill

    except Exception as exc:
        logger.warning("Skill extraction failed: %s", exc)
        return None


async def get_relevant_skills(goal: str, db: AsyncSession, limit: int = 3) -> list[dict]:
    """Return the top matching skills for a goal using keyword overlap scoring."""
    rows = list((await db.execute(
        select(Skill, SkillVersion)
        .join(SkillVersion, (SkillVersion.skill_id == Skill.id) & SkillVersion.is_current.is_(True))
        .where(Skill.is_active.is_(True))
    )).all())

    if not rows:
        return []

    goal_words = {w for w in goal.lower().split() if len(w) > 3}

    def _score(skill: Skill) -> int:
        text = f"{skill.name} {skill.description or ''}".lower()
        return sum(1 for w in goal_words if w in text)

    ranked = sorted(rows, key=lambda x: _score(x[0]), reverse=True)
    results = []
    for skill, ver in ranked[:limit]:
        playbook = (ver.code_config or {}).get("playbook", "")
        if playbook:
            results.append({
                "name": skill.name,
                "description": skill.description or "",
                "playbook": playbook,
            })
    return results


def format_skills_for_prompt(skills: list[dict]) -> str:
    if not skills:
        return ""
    lines = ["\n\n## Learned Skills from Past Runs\nUse these playbooks if relevant to the current goal:\n"]
    for s in skills:
        lines.append(f"**{s['name']}** — {s['description']}\n{s['playbook']}\n")
    return "\n".join(lines)
