"""Scene illustration service with IP-Adapter support for visual consistency."""

import asyncio
import json
import logging
import uuid
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm.attributes import flag_modified

from app.core.config import get_settings
from app.core.exceptions import GenerationError, ServiceTimeoutError, ServiceUnavailableError
from app.models.node import Node
from app.models.story import Story
from app.models.world_bible import WorldBibleEntity
from app.services.comfyui_service import ComfyUIService

logger = logging.getLogger(__name__)

# Semaphore to prevent concurrent ComfyUI illustration requests
illustration_lock = asyncio.Semaphore(1)


class IllustrationService:
    """Generates scene illustrations, optionally using IP-Adapter for character consistency."""

    def __init__(self):
        self.comfyui = ComfyUIService()
        self.settings = get_settings()
        # Pre-load workflow templates (small JSON files, read once at startup)
        workflow_dir = Path(self.settings.workflow_dir)
        with open(workflow_dir / "scene_ipadapter.json") as f:
            self._ipadapter_template = json.load(f)
        with open(workflow_dir / "scene_basic.json") as f:
            self._basic_template = json.load(f)

    async def illustrate_scene(
        self,
        session: AsyncSession,
        node: Node,
        story: Story,
    ) -> str | None:
        """Generate an illustration for a scene node.

        Uses IP-Adapter with a character reference image when available,
        falls back to plain txt2img otherwise.

        Args:
            session: Active database session.
            node: The scene node to illustrate.
            story: The parent story.

        Returns:
            The illustration filename, or None on failure.
        """
        async with illustration_lock:
            try:
                prompt = self._build_image_prompt(node)
                if not prompt:
                    logger.warning("No image prompt for node=%s", node.id)
                    return None

                ref_image_path = await self._find_reference_image(
                    session, node, story.id
                )

                if ref_image_path and self.settings.ipadapter_enabled:
                    filename = await self._generate_ipadapter(
                        prompt, ref_image_path
                    )
                else:
                    filename = await self._generate_basic(prompt)

                # Store illustration path in node metadata
                if filename:
                    if node.metadata_ is None:
                        node.metadata_ = {}
                    node.metadata_["illustration_path"] = filename
                    flag_modified(node, "metadata_")
                    await session.commit()
                    await session.refresh(node)
                    logger.info(
                        "Illustration saved for node=%s: %s", node.id, filename
                    )

                return filename

            except (ServiceUnavailableError, ServiceTimeoutError, GenerationError) as e:
                logger.error("Illustration failed for node=%s: %s", node.id, e)
                return None

    def _build_image_prompt(self, node: Node) -> str | None:
        """Build an image generation prompt from the node's beat or content.

        Extracts setting, characters, first event, and tone from the planner
        beat. Falls back to the first 200 characters of content.
        """
        beat = node.beat
        if beat:
            parts = []
            if beat.get("setting"):
                parts.append(beat["setting"])
            chars = beat.get("characters_present", [])
            if chars:
                parts.append(", ".join(chars))
            events = beat.get("key_events", [])
            if events:
                parts.append(events[0])
            tone = beat.get("emotional_tone")
            if tone:
                parts.append(f"{tone} atmosphere")
            if parts:
                base = ", ".join(parts)
                return f"{base}, cinematic scene, detailed illustration, high quality"

        # Fallback: use scene content
        content = (node.content or "").strip()
        if content:
            snippet = content[:200].rsplit(" ", 1)[0] if len(content) > 200 else content
            return f"{snippet}, cinematic scene, detailed illustration, high quality"

        return None

    async def _find_reference_image(
        self,
        session: AsyncSession,
        node: Node,
        story_id: uuid.UUID,
    ) -> str | None:
        """Find a reference image from entities mentioned in this scene's beat.

        Prioritizes characters over locations. Returns the absolute path
        to the first entity with a reference image, or None.
        """
        beat = node.beat
        if not beat:
            return None

        characters = beat.get("characters_present", [])
        if not characters:
            return None

        # Look up entities by name
        from sqlalchemy import func as sa_func

        result = await session.execute(
            select(WorldBibleEntity).where(
                WorldBibleEntity.story_id == story_id,
                sa_func.lower(WorldBibleEntity.name).in_(
                    [n.lower() for n in characters]
                ),
                WorldBibleEntity.reference_image_path.isnot(None),
            )
        )
        entities = list(result.scalars().all())

        # Prefer characters, then locations
        images_dir = Path(self.settings.static_dir) / "images"
        for entity in sorted(
            entities, key=lambda e: 0 if e.entity_type == "character" else 1
        ):
            if entity.reference_image_path:
                # Sanitize: use only the filename to prevent path traversal
                clean_name = Path(entity.reference_image_path).name
                img_path = images_dir / clean_name
                if not img_path.resolve().is_relative_to(images_dir.resolve()):
                    logger.warning(
                        "Skipping entity %s: path escapes static dir", entity.name
                    )
                    continue
                if img_path.exists():
                    logger.info(
                        "Using reference image from %s: %s",
                        entity.name,
                        clean_name,
                    )
                    return str(img_path)

        return None

    async def _generate_ipadapter(self, prompt: str, ref_image_path: str) -> str:
        """Generate a scene illustration using the IP-Adapter workflow."""
        workflow = json.loads(json.dumps(self._ipadapter_template))

        # Upload reference image to ComfyUI
        ref_filename = await self.comfyui.upload_image(ref_image_path)

        # Configure workflow
        workflow["6"]["inputs"]["text"] = prompt
        workflow["5"]["inputs"]["width"] = self.settings.scene_image_width
        workflow["5"]["inputs"]["height"] = self.settings.scene_image_height
        workflow["12"]["inputs"]["image"] = ref_filename
        workflow["13"]["inputs"]["weight"] = self.settings.ipadapter_weight
        workflow["3"]["inputs"]["seed"] = _random_seed()

        prompt_id = await self.comfyui.queue_workflow(workflow)
        logger.info("Queued IP-Adapter workflow prompt_id=%s", prompt_id)

        output = await self.comfyui._wait_for_completion(prompt_id)
        filename = await self.comfyui._save_output_image(prompt_id, output)
        return filename

    async def _generate_basic(self, prompt: str) -> str:
        """Generate a scene illustration using plain txt2img."""
        workflow = json.loads(json.dumps(self._basic_template))

        workflow["6"]["inputs"]["text"] = prompt
        workflow["5"]["inputs"]["width"] = self.settings.scene_image_width
        workflow["5"]["inputs"]["height"] = self.settings.scene_image_height
        workflow["3"]["inputs"]["seed"] = _random_seed()

        prompt_id = await self.comfyui.queue_workflow(workflow)
        logger.info("Queued basic scene workflow prompt_id=%s", prompt_id)

        output = await self.comfyui._wait_for_completion(prompt_id)
        filename = await self.comfyui._save_output_image(prompt_id, output)
        return filename


def _random_seed() -> int:
    import random
    return random.randint(0, 2**32 - 1)
