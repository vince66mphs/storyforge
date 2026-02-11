import logging
import uuid
from collections.abc import AsyncIterator

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.models.node import Node
from app.models.story import Story
from app.models.world_bible import WorldBibleEntity
from app.services.context_service import ContextService
from app.services.model_manager import ModelManager
from app.services.ollama_service import OllamaService
from app.services.planner_service import PlannerService
from app.services.writer_service import WriterService
_clean_output = WriterService._clean_output

logger = logging.getLogger(__name__)

# Fallback system prompts for single-model mode (MOA_ENABLED=false)
SYSTEM_PROMPT_UNRESTRICTED = (
    "You are a creative fiction writer collaborating with a reader on an interactive story. "
    "Continue the narrative based on the story so far and the reader's direction. "
    "Write in vivid, engaging prose. Keep each scene to 2-4 paragraphs. "
    "End scenes at moments that invite the reader to choose what happens next. "
    "Do not break the fourth wall or mention that you are an AI. "
    "You have full creative freedom — explore any themes, emotions, or situations "
    "the story demands without restriction."
)

SYSTEM_PROMPT_SAFE = (
    "You are a creative fiction writer collaborating with a reader on an interactive story. "
    "Continue the narrative based on the story so far and the reader's direction. "
    "Write in vivid, engaging prose. Keep each scene to 2-4 paragraphs. "
    "End scenes at moments that invite the reader to choose what happens next. "
    "Do not break the fourth wall or mention that you are an AI. "
    "Keep content appropriate for a general audience — avoid graphic violence, "
    "explicit sexual content, and excessive profanity."
)

SUMMARY_SYSTEM_PROMPT = (
    "Summarize the following story scene in 1-2 sentences. "
    "Focus on key plot events, character actions, and important details. "
    "Be concise and factual."
)


class StoryGenerationService:
    """Generates story scenes using Ollama with narrative DAG context.

    Supports two modes:
    - MoA (moa_enabled=True): Two-pass pipeline — planner generates a beat,
      writer expands it into prose.
    - Single-model (moa_enabled=False): Direct generation as before.
    """

    def __init__(self):
        self.ollama = OllamaService()
        self.context_svc = ContextService()
        self.planner = PlannerService()
        self.writer = WriterService()
        self.model_manager = ModelManager()
        settings = get_settings()
        self._moa_enabled = settings.moa_enabled
        self._planner_model = settings.planner_model
        self._writer_models = {
            "unrestricted": settings.writer_model_unrestricted,
            "safe": settings.writer_model_safe,
        }

    def _get_writer_model(self, content_mode: str) -> str:
        return self._writer_models.get(content_mode, self._writer_models["unrestricted"])

    def _get_system_prompt(self, content_mode: str) -> str:
        if content_mode == "safe":
            return SYSTEM_PROMPT_SAFE
        return SYSTEM_PROMPT_UNRESTRICTED

    async def _get_world_bible_entities(
        self, session: AsyncSession, story_id: uuid.UUID
    ) -> list[dict]:
        """Fetch world bible entities as simple dicts for the planner."""
        result = await session.execute(
            select(WorldBibleEntity).where(WorldBibleEntity.story_id == story_id)
        )
        entities = result.scalars().all()
        return [
            {
                "name": e.name,
                "type": e.entity_type,
                "description": e.description,
            }
            for e in entities
        ]

    async def get_story_context(
        self,
        session: AsyncSession,
        node_id: uuid.UUID,
        depth: int = 3,
    ) -> str:
        """Walk up the ancestor chain to build narrative context."""
        ancestors: list[str] = []
        current_id = node_id

        for _ in range(depth):
            result = await session.execute(
                select(Node).where(Node.id == current_id)
            )
            node = result.scalar_one_or_none()
            if node is None:
                break
            ancestors.append(node.content)
            if node.parent_id is None:
                break
            current_id = node.parent_id

        ancestors.reverse()
        return "\n\n---\n\n".join(ancestors)

    async def generate_scene(
        self,
        session: AsyncSession,
        story_id: uuid.UUID,
        parent_node_id: uuid.UUID,
        user_prompt: str,
    ) -> Node:
        """Generate a new scene node as a child of the given parent.

        When MoA is enabled, runs planner → writer pipeline under the
        generation lock. Falls back to single-model when disabled.
        """
        # Load story for content mode and settings
        story_result = await session.execute(
            select(Story).where(Story.id == story_id)
        )
        story_obj = story_result.scalar_one()
        content_mode = story_obj.content_mode

        # Build RAG context
        context = await self.context_svc.build_context(
            session=session,
            story_id=story_id,
            parent_node_id=parent_node_id,
            user_prompt=user_prompt,
            ancestor_depth=story_obj.context_depth,
        )

        beat = None
        metadata = {}

        async with self.model_manager.generation_lock:
            if self._moa_enabled:
                # Phase 1: Plan
                wb_entities = await self._get_world_bible_entities(session, story_id)
                beat = await self.planner.plan_beat(context, user_prompt, wb_entities)
                metadata["beat"] = beat
                if beat.get("continuity_warnings"):
                    metadata["continuity_warnings"] = beat["continuity_warnings"]

                # Phase 2: Write
                content = await self.writer.write_scene(beat, context, content_mode)
            else:
                # Single-model fallback
                prompt = self._build_prompt(context, user_prompt)
                writer_model = self._get_writer_model(content_mode)
                system_prompt = self._get_system_prompt(content_mode)

                logger.info(
                    "Generating scene (single-model) for story=%s, parent=%s, mode=%s",
                    story_id, parent_node_id, content_mode,
                )
                content = await self.ollama.generate(
                    prompt=prompt, system=system_prompt, model=writer_model,
                )

        # Clean leaked model artifacts before storage
        content = _clean_output(content)

        # Generate embedding for the new content
        embedding = await self.ollama.create_embedding(content)

        # Create and persist the new node
        new_node = Node(
            story_id=story_id,
            parent_id=parent_node_id,
            content=content,
            embedding=embedding,
            node_type="scene",
            metadata_=metadata or None,
        )
        session.add(new_node)

        # Update story's current leaf pointer (re-fetch to ensure clean state)
        result = await session.execute(
            select(Story).where(Story.id == story_id)
        )
        story = result.scalar_one()
        story.current_leaf_id = new_node.id

        await session.commit()
        await session.refresh(new_node)

        # Generate summary (non-blocking — failure doesn't affect scene)
        await self._generate_summary(session, new_node)

        logger.info("Created scene node=%s (%d chars, moa=%s)", new_node.id, len(content), self._moa_enabled)
        return new_node

    def _build_prompt(self, context: str, user_prompt: str) -> str:
        return f"Story so far:\n{context}\n\nReader's direction: {user_prompt}\n\nContinue the story:"

    async def generate_scene_stream(
        self,
        session: AsyncSession,
        story_id: uuid.UUID,
        parent_node_id: uuid.UUID,
        user_prompt: str,
    ) -> AsyncIterator[str | dict | Node]:
        """Stream scene generation, yielding phase signals, text chunks, then the saved Node.

        When MoA is enabled, yields:
        1. {"phase": "planning"} — planner is working
        2. {"phase": "writing"} — writer is streaming
        3. str chunks — prose tokens
        4. Node — the final saved node

        When MoA is disabled, yields str chunks then Node (no phase signals).
        """
        # Load story for content mode and settings
        story_result = await session.execute(
            select(Story).where(Story.id == story_id)
        )
        story_obj = story_result.scalar_one()
        content_mode = story_obj.content_mode

        # Build RAG context
        context = await self.context_svc.build_context(
            session=session,
            story_id=story_id,
            parent_node_id=parent_node_id,
            user_prompt=user_prompt,
            ancestor_depth=story_obj.context_depth,
        )

        beat = None
        metadata = {}

        async with self.model_manager.generation_lock:
            if self._moa_enabled:
                # Phase 1: Plan
                yield {"phase": "planning"}
                wb_entities = await self._get_world_bible_entities(session, story_id)
                beat = await self.planner.plan_beat(context, user_prompt, wb_entities)
                metadata["beat"] = beat
                if beat.get("continuity_warnings"):
                    metadata["continuity_warnings"] = beat["continuity_warnings"]

                # Phase 2: Write (streaming)
                yield {"phase": "writing"}
                chunks: list[str] = []
                async for chunk in self.writer.write_scene_stream(beat, context, content_mode):
                    chunks.append(chunk)
                    yield chunk

                content = "".join(chunks)
            else:
                # Single-model fallback
                prompt = self._build_prompt(context, user_prompt)
                writer_model = self._get_writer_model(content_mode)
                system_prompt = self._get_system_prompt(content_mode)

                logger.info(
                    "Streaming scene (single-model) for story=%s, parent=%s, mode=%s",
                    story_id, parent_node_id, content_mode,
                )

                chunks: list[str] = []
                async for chunk in self.ollama.generate_stream(
                    prompt=prompt, system=system_prompt, model=writer_model
                ):
                    chunks.append(chunk)
                    yield chunk

                content = "".join(chunks)

        # Clean leaked model artifacts before storage (streamed text is already
        # delivered to the client, but stored/embedded content gets cleaned)
        content = _clean_output(content)

        # Embed and save
        embedding = await self.ollama.create_embedding(content)

        new_node = Node(
            story_id=story_id,
            parent_id=parent_node_id,
            content=content,
            embedding=embedding,
            node_type="scene",
            metadata_=metadata or None,
        )
        session.add(new_node)

        # Update story's current leaf pointer (re-fetch to ensure clean state)
        result = await session.execute(
            select(Story).where(Story.id == story_id)
        )
        story = result.scalar_one()
        story.current_leaf_id = new_node.id

        await session.commit()
        await session.refresh(new_node)

        # Generate summary (non-blocking — failure doesn't affect scene)
        await self._generate_summary(session, new_node)

        logger.info("Created scene node=%s (%d chars, moa=%s)", new_node.id, len(content), self._moa_enabled)
        yield new_node

    async def _generate_summary(self, session: AsyncSession, node: Node) -> None:
        """Generate a 1-2 sentence summary for a node.

        Uses the planner model for summaries. Failures are logged but
        don't block scene creation.
        """
        try:
            summary = await self.ollama.generate(
                prompt=node.content,
                system=SUMMARY_SYSTEM_PROMPT,
                model=self._planner_model,
            )
            node.summary = summary.strip()
            await session.commit()
            logger.info("Generated summary for node=%s (%d chars)", node.id, len(node.summary))
        except Exception as e:
            logger.warning("Summary generation failed for node=%s: %s", node.id, e)

    async def create_branch(
        self,
        session: AsyncSession,
        node_id: uuid.UUID,
        user_prompt: str,
    ) -> Node:
        """Create an alternative branch from the same parent as the given node."""
        result = await session.execute(
            select(Node).where(Node.id == node_id)
        )
        node = result.scalar_one()

        if node.parent_id is None:
            raise ValueError("Cannot branch from the root node — it has no parent")

        logger.info("Branching from parent=%s (sibling of node=%s)", node.parent_id, node_id)

        return await self.generate_scene(
            session=session,
            story_id=node.story_id,
            parent_node_id=node.parent_id,
            user_prompt=user_prompt,
        )
