"""Seed APEX with CL4R1T4S pre-built agent templates."""
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.agent import Agent, AgentCapability, AgentCapabilityType, AgentVersion

_DATA_DIR = Path(__file__).parent.parent / "data" / "claritas"

AGENT_NAMES = [
    "Devin",
    "Cursor",
    "Perplexity Research",
    "Manus",
    "v0 UI Builder",
    "Claude Code",
]

_AGENTS = [
    {
        "name": "Devin",
        "description": (
            "AI software engineer. Writes, tests, and ships production code. "
            "Handles git, CI/CD, and full dev workflows."
        ),
        "model_id": "llama3.1",
        "prompt_file": "devin.txt",
        "capabilities": [
            AgentCapabilityType.CODE,
            AgentCapabilityType.REVIEW,
            AgentCapabilityType.AUTOMATION,
        ],
    },
    {
        "name": "Cursor",
        "description": (
            "Expert pair programmer. Code review, refactoring, debugging, and precise file edits."
        ),
        "model_id": "llama3.1",
        "prompt_file": "cursor.txt",
        "capabilities": [
            AgentCapabilityType.CODE,
            AgentCapabilityType.REVIEW,
        ],
    },
    {
        "name": "Perplexity Research",
        "description": (
            "Deep research agent. Produces exhaustive 10,000-word cited academic reports on any topic."
        ),
        "model_id": "llama3.1",
        "prompt_file": "perplexity.txt",
        "capabilities": [
            AgentCapabilityType.RESEARCH,
            AgentCapabilityType.KNOWLEDGE,
        ],
    },
    {
        "name": "Manus",
        "description": (
            "General-purpose AI agent. Research, writing, data processing, "
            "web automation, and app creation."
        ),
        "model_id": "llama3.1",
        "prompt_file": "manus.txt",
        "capabilities": [
            AgentCapabilityType.RESEARCH,
            AgentCapabilityType.CODE,
            AgentCapabilityType.DOCUMENT,
            AgentCapabilityType.AUTOMATION,
        ],
    },
    {
        "name": "v0 UI Builder",
        "description": (
            "Vercel v0 UI agent. Generates production-ready React/Next.js components "
            "with Tailwind and shadcn/ui."
        ),
        "model_id": "llama3.1",
        "prompt_file": "v0.txt",
        "capabilities": [
            AgentCapabilityType.CODE,
            AgentCapabilityType.WEBSITE,
        ],
    },
    {
        "name": "Claude Code",
        "description": (
            "CLI coding agent. Bash automation, file operations, migrations, "
            "tests, and codebase navigation."
        ),
        "model_id": "llama3.1",
        "prompt_file": "claudecode.txt",
        "capabilities": [
            AgentCapabilityType.CODE,
            AgentCapabilityType.AUTOMATION,
            AgentCapabilityType.DOCUMENT,
        ],
    },
]


async def seed_claritas_agents(
    db: AsyncSession,
    user_id: int,
) -> dict:
    """Create CL4R1T4S agent templates if they do not already exist.

    Returns a dict with keys: seeded, skipped, agents.
    """
    seeded: list[str] = []
    skipped: list[str] = []

    for spec in _AGENTS:
        name: str = spec["name"]

        existing = (
            await db.execute(select(Agent).where(Agent.name == name))
        ).scalar_one_or_none()

        if existing is not None:
            skipped.append(name)
            continue

        prompt_path = _DATA_DIR / spec["prompt_file"]
        system_prompt = prompt_path.read_text(encoding="utf-8")

        agent = Agent(
            name=name,
            description=spec["description"],
            is_active=True,
            created_by_id=user_id,
        )
        db.add(agent)
        await db.flush()  # populate agent.id

        version = AgentVersion(
            agent_id=agent.id,
            version="1",
            system_prompt=system_prompt,
            model_provider="ollama",
            model_id=spec["model_id"],
            is_current=True,
            published_by_id=user_id,
        )
        db.add(version)

        for cap_type in spec["capabilities"]:
            cap = AgentCapability(
                agent_id=agent.id,
                capability_type=cap_type,
            )
            db.add(cap)

        seeded.append(name)

    await db.commit()

    return {
        "seeded": len(seeded),
        "skipped": len(skipped),
        "agents": seeded,
    }
