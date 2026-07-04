"""Seed pre-built media generation agents powered by HuggingFace Inference API."""
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.agent import Agent, AgentCapability, AgentCapabilityType, AgentVersion

MEDIA_AGENTS = [
    {
        "name": "Image Creator",
        "description": "Generates images from text prompts using FLUX.1-schnell via HuggingFace.",
        "capability": AgentCapabilityType.IMAGE_GEN,
        "media_type": "image",
        "system_prompt": (
            "You are an expert image generation specialist. When given a description or goal, "
            "extract the core visual concept and create a detailed, vivid image generation prompt. "
            "Focus on style, lighting, composition, and subject details."
        ),
    },
    {
        "name": "Audio Producer",
        "description": "Generates music and audio from text descriptions using MusicGen via HuggingFace.",
        "capability": AgentCapabilityType.AUDIO_GEN,
        "media_type": "audio",
        "system_prompt": (
            "You are an expert audio and music producer. When given a request, "
            "translate it into a clear music generation prompt specifying genre, tempo, instruments, and mood."
        ),
    },
    {
        "name": "Video Creator",
        "description": "Generates short video clips from text prompts via HuggingFace.",
        "capability": AgentCapabilityType.VIDEO_GEN,
        "media_type": "video",
        "system_prompt": (
            "You are an expert video director. When given a concept, "
            "describe a short, vivid scene with camera movement, subject, and setting."
        ),
    },
    {
        "name": "3D Modeler",
        "description": "Generates 3D-style imagery from text prompts via HuggingFace.",
        "capability": AgentCapabilityType.MODEL_3D,
        "media_type": "3d",
        "system_prompt": (
            "You are a 3D modeling expert. When given an object or scene description, "
            "create a detailed prompt for generating a photorealistic 3D rendered image."
        ),
    },
    {
        "name": "Image Enhancer",
        "description": "Generates high-resolution, ultra-detailed images via HuggingFace FLUX.",
        "capability": AgentCapabilityType.IMAGE_GEN,
        "media_type": "upscale",
        "system_prompt": (
            "You are an image enhancement expert. When given a description, "
            "generate a high-resolution, highly detailed version with superior quality."
        ),
    },
]


async def seed_media_agents(db: AsyncSession, user_id: int) -> dict:
    existing_names = set(
        (await db.execute(select(Agent.name))).scalars().all()
    )

    seeded = 0
    skipped = 0
    agent_names: list[str] = []

    for spec in MEDIA_AGENTS:
        if spec["name"] in existing_names:
            skipped += 1
            continue

        agent = Agent(name=spec["name"], description=spec["description"], is_active=True, created_by_id=user_id)
        db.add(agent)
        await db.flush()

        version = AgentVersion(
            agent_id=agent.id,
            version="1.0.0",
            system_prompt=spec["system_prompt"],
            model_provider="huggingface_media",
            model_id="huggingface_media",
            config={"media_type": spec["media_type"]},
            is_current=True,
            published_by_id=user_id,
        )
        db.add(version)

        capability = AgentCapability(agent_id=agent.id, capability_type=spec["capability"])
        db.add(capability)

        seeded += 1
        agent_names.append(spec["name"])

    await db.commit()
    return {"seeded": seeded, "skipped": skipped, "agents": agent_names}


async def get_media_status(db: AsyncSession) -> dict:
    installed_names = set(
        (await db.execute(select(Agent.name).where(Agent.name.in_([s["name"] for s in MEDIA_AGENTS])))).scalars().all()
    )
    return {"available": len(MEDIA_AGENTS), "installed": len(installed_names)}
