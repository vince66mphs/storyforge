import logging
import uuid
from collections.abc import AsyncIterator

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.models.node import Node
from app.models.story import Story
from app.services.context_service import ContextService
from app.services.ollama_service import OllamaService

logger = logging.getLogger(__name__)

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
    """Generates story scenes using Ollama with narrative DAG context."""

    def __init__(self):
        self.ollama = OllamaService()
        self.context_svc = ContextService()
        settings = get_settings()
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

    async def get_story_context(
        self,
        session: AsyncSession,
        node_id: uuid.UUID,
        depth: int = 3,
    ) -> str:
        """Walk up the ancestor chain to build narrative context.

        Args:
            session: Active database session.
            node_id: The node to start from (walks toward root).
            depth: Maximum number of ancestor nodes to include.

        Returns:
            Concatenated text of ancestor nodes (oldest first).
        """
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

        # Reverse so oldest ancestor comes first (chronological order)
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

        Builds context from ancestor nodes, sends to Ollama, embeds the
        result, and saves a new Node to the database.

        Args:
            session: Active database session.
            story_id: The story this node belongs to.
            parent_node_id: The parent node to continue from.
            user_prompt: The reader's direction for this scene.

        Returns:
            The newly created Node with generated content.
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
        prompt = self._build_prompt(context, user_prompt)

        writer_model = self._get_writer_model(content_mode)
        system_prompt = self._get_system_prompt(content_mode)

        logger.info(
            "Generating scene for story=%s, parent=%s, mode=%s, model=%s, context_len=%d",
            story_id, parent_node_id, content_mode, writer_model, len(context),
        )

        # Generate scene text
        content = await self.ollama.generate(
            prompt=prompt,
            system=system_prompt,
            model=writer_model,
        )

        # Generate embedding for the new content
        embedding = await self.ollama.create_embedding(content)

        # Create and persist the new node
        new_node = Node(
            story_id=story_id,
            parent_id=parent_node_id,
            content=content,
            embedding=embedding,
            node_type="scene",
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

        logger.info("Created scene node=%s (%d chars)", new_node.id, len(content))
        return new_node

    def _build_prompt(self, context: str, user_prompt: str) -> str:
        return f"Story so far:\n{context}\n\nReader's direction: {user_prompt}\n\nContinue the story:"

    async def generate_scene_stream(
        self,
        session: AsyncSession,
        story_id: uuid.UUID,
        parent_node_id: uuid.UUID,
        user_prompt: str,
    ) -> AsyncIterator[str | Node]:
        """Stream scene generation, yielding text chunks then the saved Node.

        Yields text chunks as they arrive from Ollama, then saves the
        completed scene and yields the final Node object as the last item.

        Usage:
            async for chunk in svc.generate_scene_stream(...):
                if isinstance(chunk, str):
                    print(chunk, end="", flush=True)
                else:
                    node = chunk  # final Node
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
        prompt = self._build_prompt(context, user_prompt)

        writer_model = self._get_writer_model(content_mode)
        system_prompt = self._get_system_prompt(content_mode)

        logger.info(
            "Streaming scene for story=%s, parent=%s, mode=%s, model=%s, context_len=%d",
            story_id, parent_node_id, content_mode, writer_model, len(context),
        )

        # Stream and collect the full text
        chunks: list[str] = []
        async for chunk in self.ollama.generate_stream(
            prompt=prompt, system=system_prompt, model=writer_model
        ):
            chunks.append(chunk)
            yield chunk

        content = "".join(chunks)

        # Embed and save
        embedding = await self.ollama.create_embedding(content)

        new_node = Node(
            story_id=story_id,
            parent_id=parent_node_id,
            content=content,
            embedding=embedding,
            node_type="scene",
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

        logger.info("Created scene node=%s (%d chars)", new_node.id, len(content))
        yield new_node

    async def _generate_summary(self, session: AsyncSession, node: Node) -> None:
        """Generate a 1-2 sentence summary for a node using phi4.

        Summaries are used by RAG for efficient context retrieval.
        Failures are logged but don't block scene creation.
        """
        try:
            summary = await self.ollama.generate(
                prompt=node.content,
                system=SUMMARY_SYSTEM_PROMPT,
                model="phi4:latest",
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
        """Create an alternative branch from the same parent as the given node.

        This generates a sibling scene — an alternative continuation from
        the same point in the story.

        Args:
            session: Active database session.
            node_id: An existing node whose parent will be the branch point.
            user_prompt: The reader's alternative direction.

        Returns:
            The newly created branch Node.
        """
        # Load the reference node to find its parent and story
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
