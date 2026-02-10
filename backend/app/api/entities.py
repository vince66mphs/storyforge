import logging
import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.schemas import (
    EntityCreate,
    EntityUpdate,
    EntityResponse,
    DetectEntitiesRequest,
)
from app.core.database import get_session
from app.core.exceptions import ServiceUnavailableError, ServiceTimeoutError, GenerationError
from app.models.story import Story
from app.models.world_bible import WorldBibleEntity
from app.services.asset_service import AssetService
from app.services.ollama_service import OllamaService

logger = logging.getLogger(__name__)

router = APIRouter(tags=["entities"])

asset_svc = AssetService()
ollama_svc = OllamaService()


@router.post(
    "/api/stories/{story_id}/entities",
    response_model=EntityResponse,
    status_code=201,
)
async def create_entity(
    story_id: uuid.UUID,
    body: EntityCreate,
    session: AsyncSession = Depends(get_session),
):
    """Manually add an entity to a story's world bible."""
    result = await session.execute(select(Story).where(Story.id == story_id))
    if result.scalar_one_or_none() is None:
        raise HTTPException(status_code=404, detail="Story not found")

    entity = await asset_svc.create_entity(
        session=session,
        story_id=story_id,
        entity_data=body.model_dump(),
    )
    return entity


@router.get(
    "/api/stories/{story_id}/entities",
    response_model=list[EntityResponse],
)
async def list_entities(
    story_id: uuid.UUID,
    session: AsyncSession = Depends(get_session),
):
    """List all entities for a story."""
    result = await session.execute(select(Story).where(Story.id == story_id))
    if result.scalar_one_or_none() is None:
        raise HTTPException(status_code=404, detail="Story not found")

    result = await session.execute(
        select(WorldBibleEntity)
        .where(WorldBibleEntity.story_id == story_id)
        .order_by(WorldBibleEntity.entity_type, WorldBibleEntity.name)
    )
    return result.scalars().all()


@router.post(
    "/api/stories/{story_id}/entities/detect",
    response_model=list[EntityResponse],
    status_code=201,
)
async def detect_and_create_entities(
    story_id: uuid.UUID,
    body: DetectEntitiesRequest,
    session: AsyncSession = Depends(get_session),
):
    """Detect entities in text and add new ones to the world bible."""
    result = await session.execute(select(Story).where(Story.id == story_id))
    if result.scalar_one_or_none() is None:
        raise HTTPException(status_code=404, detail="Story not found")

    try:
        detected = await asset_svc.detect_entities(body.text)
    except (ServiceUnavailableError, ServiceTimeoutError) as e:
        logger.warning("Entity detection skipped — %s", e)
        raise
    except GenerationError as e:
        logger.warning("Entity detection failed — %s", e)
        return []

    if not detected:
        return []

    # Check which names already exist to avoid duplicates
    existing = await asset_svc.get_entity_references(
        session, story_id, [e["name"] for e in detected]
    )
    existing_names = {e.name.lower() for e in existing}

    created = []
    for entity_data in detected:
        if entity_data["name"].lower() in existing_names:
            continue
        entity = await asset_svc.create_entity(session, story_id, entity_data)
        created.append(entity)
        existing_names.add(entity_data["name"].lower())

    return created


@router.get("/api/entities/{entity_id}", response_model=EntityResponse)
async def get_entity(
    entity_id: uuid.UUID,
    session: AsyncSession = Depends(get_session),
):
    """Get entity details."""
    result = await session.execute(
        select(WorldBibleEntity).where(WorldBibleEntity.id == entity_id)
    )
    entity = result.scalar_one_or_none()
    if entity is None:
        raise HTTPException(status_code=404, detail="Entity not found")
    return entity


@router.post(
    "/api/entities/{entity_id}/image",
    response_model=EntityResponse,
)
async def generate_entity_image(
    entity_id: uuid.UUID,
    session: AsyncSession = Depends(get_session),
):
    """Generate or regenerate a reference image for an entity."""
    result = await session.execute(
        select(WorldBibleEntity).where(WorldBibleEntity.id == entity_id)
    )
    entity = result.scalar_one_or_none()
    if entity is None:
        raise HTTPException(status_code=404, detail="Entity not found")

    await asset_svc.generate_entity_image(
        session=session,
        entity=entity,
        seed=entity.image_seed,  # Reuse seed if regenerating for consistency
    )
    return entity


@router.patch("/api/entities/{entity_id}", response_model=EntityResponse)
async def update_entity(
    entity_id: uuid.UUID,
    body: EntityUpdate,
    session: AsyncSession = Depends(get_session),
):
    """Update entity details (bumps version)."""
    result = await session.execute(
        select(WorldBibleEntity).where(WorldBibleEntity.id == entity_id)
    )
    entity = result.scalar_one_or_none()
    if entity is None:
        raise HTTPException(status_code=404, detail="Entity not found")

    if body.description is not None:
        entity.description = body.description
    if body.base_prompt is not None:
        entity.base_prompt = body.base_prompt
    entity.version += 1

    # Re-embed if description changed for RAG accuracy
    if body.description is not None:
        try:
            embed_text = f"{entity.name} ({entity.entity_type}): {entity.description}"
            entity.embedding = await ollama_svc.create_embedding(embed_text)
        except Exception:
            pass  # Embedding failure shouldn't block update

    await session.commit()
    await session.refresh(entity)
    return entity
