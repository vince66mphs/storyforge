import json
import logging
import os
import random
import uuid
from collections.abc import AsyncIterator
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.models.world_bible import WorldBibleEntity
from app.services.comfyui_service import ComfyUIService
from app.services.ollama_service import OllamaService

logger = logging.getLogger(__name__)

ENTITY_DETECTION_SYSTEM = (
    "You are an entity extractor for interactive fiction. "
    "Given a scene of text, identify all named characters, locations, and notable props/objects. "
    "Return ONLY a JSON array of objects with these fields:\n"
    '  - "name": the entity name\n'
    '  - "entity_type": one of "character", "location", or "prop"\n'
    '  - "description": a brief physical description (1-2 sentences)\n'
    '  - "base_prompt": an image generation prompt describing the entity visually '
    "(detailed, suitable for text-to-image AI)\n\n"
    "If no entities are found, return an empty array: []\n"
    "Return ONLY valid JSON, no markdown fences or explanation."
)


class AssetService:
    """Manages world bible entities — detection, creation, and image generation."""

    def __init__(self):
        self.ollama = OllamaService()
        self.comfyui = ComfyUIService()

    async def detect_entities(self, text: str) -> list[dict]:
        """Extract characters, locations, and props from scene text.

        Uses phi4 (logical planner) to analyze text and return structured
        entity data.

        Args:
            text: The scene text to analyze.

        Returns:
            A list of dicts with keys: name, entity_type, description, base_prompt.
        """
        logger.info("Detecting entities in %d chars of text", len(text))

        raw = await self.ollama.generate(
            prompt=text,
            system=ENTITY_DETECTION_SYSTEM,
            model="phi4:latest",
        )

        # Parse JSON — strip any markdown fences the model might add
        cleaned = raw.strip()
        if cleaned.startswith("```"):
            # Remove ```json ... ``` wrapping
            lines = cleaned.split("\n")
            lines = [l for l in lines if not l.strip().startswith("```")]
            cleaned = "\n".join(lines)

        try:
            entities = json.loads(cleaned)
        except json.JSONDecodeError:
            logger.warning("Failed to parse entity JSON: %s", cleaned[:200])
            return []

        if not isinstance(entities, list):
            logger.warning("Entity detection returned non-list: %s", type(entities))
            return []

        # Validate each entity has required fields
        valid = []
        required = {"name", "entity_type", "description", "base_prompt"}
        for entity in entities:
            if isinstance(entity, dict) and required.issubset(entity.keys()):
                valid.append(entity)
            else:
                logger.warning("Skipping invalid entity: %s", entity)

        logger.info("Detected %d valid entities", len(valid))
        return valid

    async def create_entity(
        self,
        session: AsyncSession,
        story_id: uuid.UUID,
        entity_data: dict,
    ) -> WorldBibleEntity:
        """Create a new world bible entity with embedding.

        Args:
            session: Active database session.
            story_id: The story this entity belongs to.
            entity_data: Dict with name, entity_type, description, base_prompt.

        Returns:
            The persisted WorldBibleEntity.
        """
        # Generate embedding from description
        embed_text = f"{entity_data['name']}: {entity_data['description']}"
        embedding = await self.ollama.create_embedding(embed_text)

        entity = WorldBibleEntity(
            story_id=story_id,
            entity_type=entity_data["entity_type"],
            name=entity_data["name"],
            description=entity_data["description"],
            base_prompt=entity_data["base_prompt"],
            embedding=embedding,
        )
        session.add(entity)
        await session.commit()
        await session.refresh(entity)

        logger.info("Created entity: %s (%s) id=%s", entity.name, entity.entity_type, entity.id)
        return entity

    async def get_entity_references(
        self,
        session: AsyncSession,
        story_id: uuid.UUID,
        entity_names: list[str],
    ) -> list[WorldBibleEntity]:
        """Look up world bible entities by name for a story.

        Args:
            session: Active database session.
            story_id: The story to search within.
            entity_names: List of entity names to find (case-insensitive).

        Returns:
            List of matching WorldBibleEntity objects.
        """
        from sqlalchemy import func as sa_func

        result = await session.execute(
            select(WorldBibleEntity).where(
                WorldBibleEntity.story_id == story_id,
                sa_func.lower(WorldBibleEntity.name).in_(
                    [n.lower() for n in entity_names]
                ),
            )
        )
        entities = list(result.scalars().all())
        logger.info(
            "Found %d/%d entity references for story=%s",
            len(entities), len(entity_names), story_id,
        )
        return entities

    async def generate_entity_image(
        self,
        session: AsyncSession,
        entity: WorldBibleEntity,
        seed: int | None = None,
    ) -> str:
        """Generate a reference image for an entity via ComfyUI.

        Uses the entity's base_prompt. Saves the image path and seed
        back to the entity for consistency on regeneration.

        Args:
            session: Active database session.
            entity: The entity to generate an image for.
            seed: Optional fixed seed for reproducibility.

        Returns:
            The filename of the saved image.
        """
        logger.info("Generating image for entity=%s (%s)", entity.name, entity.id)

        image_filename = await self.comfyui.generate_image(
            prompt=entity.base_prompt,
            seed=seed,
        )

        # Update entity with image reference
        entity.reference_image_path = image_filename
        if seed is not None:
            entity.image_seed = seed
        await session.commit()
        await session.refresh(entity)

        logger.info("Image saved for entity %s: %s", entity.name, image_filename)
        return image_filename

    async def generate_entity_images(
        self,
        entity: WorldBibleEntity,
        count: int = 4,
    ) -> AsyncIterator[dict]:
        """Generate multiple candidate images for an entity with different seeds.

        Yields dicts as each image completes:
            {"index": 0, "filename": "xxx.png", "seed": 12345}

        Args:
            entity: The entity to generate images for.
            count: Number of candidate images to generate.
        """
        logger.info(
            "Generating %d candidate images for entity=%s (%s)",
            count, entity.name, entity.id,
        )

        for i in range(count):
            seed = random.randint(0, 2**32 - 1)
            image_filename = await self.comfyui.generate_image(
                prompt=entity.base_prompt,
                seed=seed,
            )
            logger.info("Candidate %d/%d for %s: %s (seed=%d)", i + 1, count, entity.name, image_filename, seed)
            yield {"index": i, "filename": image_filename, "seed": seed}

    async def select_entity_image(
        self,
        session: AsyncSession,
        entity: WorldBibleEntity,
        filename: str,
        seed: int,
        reject_filenames: list[str] | None = None,
    ) -> None:
        """Set the selected image as the entity's reference and clean up rejected ones.

        Args:
            session: Active database session.
            entity: The entity to update.
            filename: The selected image filename.
            seed: The seed used to generate the selected image.
            reject_filenames: Filenames of rejected candidates to delete.
        """
        entity.reference_image_path = filename
        entity.image_seed = seed
        await session.commit()
        await session.refresh(entity)

        # Clean up rejected images
        if reject_filenames:
            static_dir = Path(get_settings().static_dir) / "images"
            for reject in reject_filenames:
                path = static_dir / reject
                try:
                    if path.exists():
                        os.remove(path)
                        logger.info("Deleted rejected candidate: %s", reject)
                except OSError as e:
                    logger.warning("Failed to delete %s: %s", reject, e)

        logger.info(
            "Selected image for entity %s: %s (seed=%d)",
            entity.name, filename, seed,
        )

    async def describe_entity_from_image(
        self,
        session: AsyncSession,
        entity: WorldBibleEntity,
    ) -> str:
        """Generate a description for an entity using its reference image via vision model.

        Uses gemma2:9b vision capabilities to analyze the entity's reference image
        and produce a detailed description.

        Args:
            session: Active database session.
            entity: The entity with a reference image.

        Returns:
            The generated description text.
        """
        if not entity.reference_image_path:
            raise ValueError("Entity has no reference image")

        image_path = str(Path(get_settings().static_dir) / "images" / entity.reference_image_path)

        prompt = (
            f"This image depicts a {entity.entity_type} named '{entity.name}' "
            f"from an interactive fiction story. "
            f"Provide a detailed physical description of what you see. "
            f"Focus on appearance, distinguishing features, and visual details. "
            f"Write 2-3 sentences."
        )

        description = await self.ollama.generate_vision(
            prompt=prompt,
            image_path=image_path,
            model="gemma2:9b",
        )

        # Update entity description
        entity.description = description.strip()
        entity.version += 1

        # Re-embed with new description
        try:
            embed_text = f"{entity.name} ({entity.entity_type}): {entity.description}"
            entity.embedding = await self.ollama.create_embedding(embed_text)
        except Exception:
            pass  # Embedding failure shouldn't block

        await session.commit()
        await session.refresh(entity)

        logger.info("Generated vision description for %s: %d chars", entity.name, len(description))
        return description
