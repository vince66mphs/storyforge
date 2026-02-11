import json
import logging
import secrets
import uuid
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, UploadFile
from fastapi.responses import StreamingResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings

from app.api.schemas import (
    EntityCreate,
    EntityUpdate,
    EntityResponse,
    ImageSelectRequest,
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


@router.post("/api/entities/{entity_id}/images/generate")
async def generate_entity_images(
    entity_id: uuid.UUID,
    session: AsyncSession = Depends(get_session),
):
    """Generate 4 candidate images for an entity, streaming results via SSE."""
    result = await session.execute(
        select(WorldBibleEntity).where(WorldBibleEntity.id == entity_id)
    )
    entity = result.scalar_one_or_none()
    if entity is None:
        raise HTTPException(status_code=404, detail="Entity not found")

    async def event_stream():
        try:
            async for candidate in asset_svc.generate_entity_images(entity):
                data = json.dumps(candidate)
                yield f"data: {data}\n\n"
            yield "data: {\"done\": true}\n\n"
        except (ServiceUnavailableError, ServiceTimeoutError, GenerationError) as e:
            error_data = json.dumps({"error": str(e), "error_type": type(e).__name__})
            yield f"data: {error_data}\n\n"

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@router.post("/api/entities/{entity_id}/images/select", response_model=EntityResponse)
async def select_entity_image(
    entity_id: uuid.UUID,
    body: ImageSelectRequest,
    session: AsyncSession = Depends(get_session),
):
    """Select one candidate image as the entity's reference, delete the rest."""
    result = await session.execute(
        select(WorldBibleEntity).where(WorldBibleEntity.id == entity_id)
    )
    entity = result.scalar_one_or_none()
    if entity is None:
        raise HTTPException(status_code=404, detail="Entity not found")

    await asset_svc.select_entity_image(
        session=session,
        entity=entity,
        filename=body.filename,
        seed=body.seed,
        reject_filenames=body.reject_filenames,
    )
    return entity


@router.post("/api/entities/{entity_id}/describe", response_model=EntityResponse)
async def describe_entity_from_image(
    entity_id: uuid.UUID,
    session: AsyncSession = Depends(get_session),
):
    """Generate a description for an entity from its reference image using vision AI."""
    result = await session.execute(
        select(WorldBibleEntity).where(WorldBibleEntity.id == entity_id)
    )
    entity = result.scalar_one_or_none()
    if entity is None:
        raise HTTPException(status_code=404, detail="Entity not found")

    if not entity.reference_image_path:
        raise HTTPException(status_code=400, detail="Entity has no reference image")

    await asset_svc.describe_entity_from_image(session=session, entity=entity)
    return entity


ALLOWED_IMAGE_TYPES = {
    "image/png": ".png",
    "image/jpeg": ".jpg",
    "image/webp": ".webp",
}
MAX_UPLOAD_SIZE = 10 * 1024 * 1024  # 10 MB


@router.post("/api/entities/{entity_id}/image/upload", response_model=EntityResponse)
async def upload_entity_image(
    entity_id: uuid.UUID,
    file: UploadFile,
    session: AsyncSession = Depends(get_session),
):
    """Upload a reference image for an entity."""
    result = await session.execute(
        select(WorldBibleEntity).where(WorldBibleEntity.id == entity_id)
    )
    entity = result.scalar_one_or_none()
    if entity is None:
        raise HTTPException(status_code=404, detail="Entity not found")

    # Validate content type
    if file.content_type not in ALLOWED_IMAGE_TYPES:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid file type: {file.content_type}. Allowed: PNG, JPG, WebP",
        )

    # Read and validate size
    data = await file.read()
    if len(data) > MAX_UPLOAD_SIZE:
        raise HTTPException(status_code=400, detail="File too large (max 10 MB)")

    # Save file
    ext = ALLOWED_IMAGE_TYPES[file.content_type]
    random_suffix = secrets.token_hex(4)
    filename = f"upload_{entity_id}_{random_suffix}{ext}"
    settings = get_settings()
    image_dir = Path(settings.static_dir) / "images"
    image_dir.mkdir(parents=True, exist_ok=True)
    (image_dir / filename).write_bytes(data)

    # Update entity
    entity.reference_image_path = filename
    entity.image_seed = None
    await session.commit()
    await session.refresh(entity)
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
