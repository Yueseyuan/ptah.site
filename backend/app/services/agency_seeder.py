"""Seed The Agency's 232 specialist agents into APEX AI.

Downloads the public repo zip, parses every agent markdown file,
and creates Agent + AgentVersion + AgentCapability records.
"""
import io
import zipfile

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.agent import Agent, AgentCapability, AgentCapabilityType, AgentVersion

REPO_ZIP = "https://github.com/msitarzewski/agency-agents/archive/refs/heads/main.zip"
KNOWN_TOTAL = 232

DIVISION_CAPABILITY: dict[str, AgentCapabilityType] = {
    "engineering": AgentCapabilityType.CODE,
    "design": AgentCapabilityType.WEBSITE,
    "marketing": AgentCapabilityType.BUSINESS,
    "sales": AgentCapabilityType.BUSINESS,
    "product": AgentCapabilityType.BUSINESS,
    "project-management": AgentCapabilityType.AUTOMATION,
    "testing": AgentCapabilityType.REVIEW,
    "security": AgentCapabilityType.RISK_REVIEW,
    "support": AgentCapabilityType.KNOWLEDGE,
    "finance": AgentCapabilityType.BUSINESS,
    "specialized": AgentCapabilityType.KNOWLEDGE,
    "game-development": AgentCapabilityType.CODE,
    "academic": AgentCapabilityType.RESEARCH,
    "gis": AgentCapabilityType.RESEARCH,
    "paid-media": AgentCapabilityType.BUSINESS,
    "spatial-computing": AgentCapabilityType.CODE,
}


def _parse_agent(content: str, zip_path: str) -> dict | None:
    """Extract name, description, division, and system prompt from an agent file."""
    parts = zip_path.split("/")
    if len(parts) < 3:
        return None

    division = parts[1]
    lines = content.strip().splitlines()

    name: str | None = None
    description: str | None = None

    for line in lines:
        stripped = line.strip()
        if stripped.startswith("# ") and name is None:
            name = stripped[2:].strip()
        elif stripped.startswith("> ") and description is None:
            description = stripped[2:].strip()
        if name and description:
            break

    if not name:
        return None

    return {
        "name": name,
        "description": description or f"{name} — {division} specialist",
        "division": division,
        "system_prompt": content,
        "capability": DIVISION_CAPABILITY.get(division, AgentCapabilityType.KNOWLEDGE),
    }


async def _fetch_zip() -> bytes:
    async with httpx.AsyncClient(timeout=120.0, follow_redirects=True) as client:
        r = await client.get(REPO_ZIP)
        r.raise_for_status()
        return r.content


def _extract_agents(zip_bytes: bytes) -> list[dict]:
    agents: list[dict] = []
    with zipfile.ZipFile(io.BytesIO(zip_bytes)) as zf:
        for name in zf.namelist():
            if not name.endswith(".md"):
                continue
            parts = name.split("/")
            if len(parts) < 3:
                continue
            division = parts[1]
            if division not in DIVISION_CAPABILITY:
                continue
            content = zf.read(name).decode("utf-8", errors="ignore")
            parsed = _parse_agent(content, name)
            if parsed:
                agents.append(parsed)
    return agents


async def seed_agency_agents(db: AsyncSession, user_id: int) -> dict:
    zip_bytes = await _fetch_zip()
    agent_specs = _extract_agents(zip_bytes)

    existing_names: set[str] = set(
        (await db.execute(select(Agent.name))).scalars().all()
    )

    seeded = 0
    skipped = 0
    agent_names: list[str] = []

    for spec in agent_specs:
        if spec["name"] in existing_names:
            skipped += 1
            continue

        agent = Agent(
            name=spec["name"],
            description=spec["description"],
            is_active=True,
            created_by_id=user_id,
        )
        db.add(agent)
        await db.flush()

        version = AgentVersion(
            agent_id=agent.id,
            version="1.0.0",
            system_prompt=spec["system_prompt"],
            model_provider="ollama",
            model_id="llama3.1",
            config={"division": spec["division"]},
            is_current=True,
            published_by_id=user_id,
        )
        db.add(version)

        capability = AgentCapability(
            agent_id=agent.id,
            capability_type=spec["capability"],
        )
        db.add(capability)

        seeded += 1
        agent_names.append(spec["name"])

    await db.commit()
    return {
        "seeded": seeded,
        "skipped": skipped,
        "total_found": len(agent_specs),
        "agents": agent_names,
    }


async def get_agency_status(db: AsyncSession) -> dict:
    from sqlalchemy import func

    result = await db.execute(
        select(func.count(Agent.id))
        .join(AgentVersion, AgentVersion.agent_id == Agent.id)
        .where(AgentVersion.config["division"].isnot(None))
    )
    installed_count = result.scalar() or 0
    return {"available": KNOWN_TOTAL, "installed": min(installed_count, KNOWN_TOTAL)}
