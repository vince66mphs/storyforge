"""RAG-based context assembly for story generation.

Builds rich context from multiple sources:
1. Ancestor chain (recent narrative flow)
2. Semantic search over past nodes (relevant history)
3. World bible entity lookup (characters, locations, props)
"""

import logging
import uuid

from sqlalchemy import select, and_, not_
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.node import Node
from app.models.world_bible import WorldBibleEntity
from app.services.ollama_service import OllamaService

logger = logging.getLogger(__name__)

# Approximate chars-per-token ratio for budget estimation
CHARS_PER_TOKEN = 4
DEFAULT_TOKEN_BUDGET = 3000


class ContextService:
    """Assembles RAG context for scene generation."""

    def __init__(self):
        self.ollama = OllamaService()

    async def build_context(
        self,
        session: AsyncSession,
        story_id: uuid.UUID,
        parent_node_id: uuid.UUID,
        user_prompt: str,
        ancestor_depth: int = 3,
        semantic_top_k: int = 5,
        entity_top_k: int = 5,
        token_budget: int = DEFAULT_TOKEN_BUDGET,
    ) -> str:
        """Assemble rich context from multiple sources.

        Args:
            session: Active database session.
            story_id: The story being generated for.
            parent_node_id: Current node (walk ancestors from here).
            user_prompt: The reader's prompt (used for semantic search).
            ancestor_depth: Number of ancestor nodes to include.
            semantic_top_k: Max semantically similar nodes to retrieve.
            entity_top_k: Max world bible entities to retrieve.
            token_budget: Approximate token limit for total context.

        Returns:
            Structured context string with labeled sections.
        """
        # 1. Get ancestor chain (always included, highest priority)
        ancestors, ancestor_ids = await self._get_ancestors(
            session, parent_node_id, ancestor_depth
        )

        # 2. Embed user prompt for semantic search
        prompt_embedding = await self.ollama.create_embedding(user_prompt)

        # 3. Semantic search over past nodes (excluding ancestors)
        similar_nodes = await self._semantic_node_search(
            session, story_id, prompt_embedding, ancestor_ids, semantic_top_k
        )

        # 4. World bible entity retrieval
        entities_by_vector = await self._semantic_entity_search(
            session, story_id, prompt_embedding, entity_top_k
        )
        entities_by_name = await self._name_match_entities(
            session, story_id, user_prompt
        )
        # Merge and deduplicate entities (name match takes priority)
        all_entities = {e.id: e for e in entities_by_vector}
        all_entities.update({e.id: e for e in entities_by_name})
        entities = list(all_entities.values())

        # 5. Assemble with budget
        return self._assemble(ancestors, similar_nodes, entities, token_budget)

    async def _get_ancestors(
        self,
        session: AsyncSession,
        node_id: uuid.UUID,
        depth: int,
    ) -> tuple[list[Node], set[uuid.UUID]]:
        """Walk ancestor chain and return nodes + their IDs."""
        ancestors: list[Node] = []
        ancestor_ids: set[uuid.UUID] = set()
        current_id = node_id

        for _ in range(depth):
            result = await session.execute(
                select(Node).where(Node.id == current_id)
            )
            node = result.scalar_one_or_none()
            if node is None:
                break
            ancestors.append(node)
            ancestor_ids.add(node.id)
            if node.parent_id is None:
                break
            current_id = node.parent_id

        ancestors.reverse()  # oldest first
        return ancestors, ancestor_ids

    async def _semantic_node_search(
        self,
        session: AsyncSession,
        story_id: uuid.UUID,
        prompt_embedding: list[float],
        exclude_ids: set[uuid.UUID],
        top_k: int,
    ) -> list[Node]:
        """Find semantically similar past nodes via pgvector cosine distance."""
        if not exclude_ids:
            exclude_ids = set()

        query = (
            select(Node)
            .where(
                and_(
                    Node.story_id == story_id,
                    Node.embedding.isnot(None),
                    Node.node_type != "root",
                    not_(Node.id.in_(exclude_ids)) if exclude_ids else True,
                )
            )
            .order_by(Node.embedding.cosine_distance(prompt_embedding))
            .limit(top_k)
        )

        result = await session.execute(query)
        return list(result.scalars().all())

    async def _semantic_entity_search(
        self,
        session: AsyncSession,
        story_id: uuid.UUID,
        prompt_embedding: list[float],
        top_k: int,
    ) -> list[WorldBibleEntity]:
        """Find semantically similar world bible entities."""
        query = (
            select(WorldBibleEntity)
            .where(
                and_(
                    WorldBibleEntity.story_id == story_id,
                    WorldBibleEntity.embedding.isnot(None),
                )
            )
            .order_by(WorldBibleEntity.embedding.cosine_distance(prompt_embedding))
            .limit(top_k)
        )

        result = await session.execute(query)
        return list(result.scalars().all())

    async def _name_match_entities(
        self,
        session: AsyncSession,
        story_id: uuid.UUID,
        user_prompt: str,
    ) -> list[WorldBibleEntity]:
        """Find entities whose names appear in the user prompt."""
        # Get all entity names for this story
        result = await session.execute(
            select(WorldBibleEntity).where(
                WorldBibleEntity.story_id == story_id
            )
        )
        all_entities = list(result.scalars().all())

        prompt_lower = user_prompt.lower()
        return [e for e in all_entities if e.name.lower() in prompt_lower]

    def _assemble(
        self,
        ancestors: list[Node],
        similar_nodes: list[Node],
        entities: list[WorldBibleEntity],
        token_budget: int,
    ) -> str:
        """Assemble structured context string within token budget.

        Priority: ancestors > entities > semantic history.
        """
        char_budget = token_budget * CHARS_PER_TOKEN
        sections: list[str] = []
        used = 0

        # Section 1: Recent scenes (ancestors) — full content, highest priority
        if ancestors:
            ancestor_texts = []
            for node in ancestors:
                text = node.content
                if used + len(text) > char_budget:
                    break
                ancestor_texts.append(text)
                used += len(text)

            if ancestor_texts:
                section = "[RECENT SCENES]\n" + "\n\n---\n\n".join(ancestor_texts)
                sections.append(section)

        # Section 2: World bible entities — descriptions
        if entities and used < char_budget:
            entity_texts = []
            for entity in entities:
                entry = f"- {entity.name} ({entity.entity_type}): {entity.description}"
                if used + len(entry) > char_budget:
                    break
                entity_texts.append(entry)
                used += len(entry)

            if entity_texts:
                section = "[WORLD BIBLE]\n" + "\n".join(entity_texts)
                sections.append(section)

        # Section 3: Relevant history — summaries preferred, fall back to truncated content
        if similar_nodes and used < char_budget:
            history_texts = []
            for node in similar_nodes:
                text = node.summary if node.summary else node.content[:300] + "..."
                if used + len(text) > char_budget:
                    break
                history_texts.append(text)
                used += len(text)

            if history_texts:
                section = "[RELEVANT HISTORY]\n" + "\n\n".join(history_texts)
                sections.append(section)

        context = "\n\n".join(sections)
        logger.info(
            "Context assembled: %d ancestors, %d entities, %d history nodes, %d chars",
            len(ancestors),
            len(entities),
            len(similar_nodes),
            len(context),
        )
        return context
