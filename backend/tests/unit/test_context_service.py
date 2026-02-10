"""Tests for ContextService — mocked DB and OllamaService."""

import uuid
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.models.node import Node
from app.models.world_bible import WorldBibleEntity
from app.services.context_service import CHARS_PER_TOKEN, ContextService


@pytest.fixture
def svc():
    service = ContextService()
    service.ollama = AsyncMock()
    service.ollama.create_embedding.return_value = [0.1] * 768
    return service


class TestAssemble:
    def test_ancestors_only(self, svc):
        sid = uuid.uuid4()
        ancestors = [
            Node(story_id=sid, content="Scene 1", node_type="scene"),
            Node(story_id=sid, content="Scene 2", node_type="scene"),
        ]
        result = svc._assemble(ancestors, [], [], token_budget=3000)
        assert "[RECENT SCENES]" in result
        assert "Scene 1" in result
        assert "Scene 2" in result

    def test_entities_section(self, svc):
        sid = uuid.uuid4()
        entities = [
            WorldBibleEntity(
                story_id=sid, name="Alice", entity_type="character",
                description="Brave hero", base_prompt="hero"
            ),
        ]
        result = svc._assemble([], [], entities, token_budget=3000)
        assert "[WORLD BIBLE]" in result
        assert "Alice" in result

    def test_history_section(self, svc):
        sid = uuid.uuid4()
        nodes = [
            Node(story_id=sid, content="Old scene content", node_type="scene", summary="Old summary"),
        ]
        result = svc._assemble([], nodes, [], token_budget=3000)
        assert "[RELEVANT HISTORY]" in result
        assert "Old summary" in result

    def test_history_uses_truncated_content_when_no_summary(self, svc):
        sid = uuid.uuid4()
        nodes = [
            Node(story_id=sid, content="x" * 500, node_type="scene", summary=None),
        ]
        result = svc._assemble([], nodes, [], token_budget=3000)
        assert "..." in result

    def test_budget_limits_content(self, svc):
        sid = uuid.uuid4()
        # Each ancestor is 100 chars. With budget of 50 tokens = 200 chars,
        # only 2 should fit.
        ancestors = [
            Node(story_id=sid, content="A" * 100, node_type="scene"),
            Node(story_id=sid, content="B" * 100, node_type="scene"),
            Node(story_id=sid, content="C" * 100, node_type="scene"),
        ]
        result = svc._assemble(ancestors, [], [], token_budget=50)
        # Budget is 200 chars, two ancestors = 200, third wouldn't fit
        assert "A" * 100 in result
        assert "B" * 100 in result

    def test_priority_order(self, svc):
        """Ancestors should appear before entities, entities before history."""
        sid = uuid.uuid4()
        ancestors = [Node(story_id=sid, content="Ancestor", node_type="scene")]
        entities = [
            WorldBibleEntity(
                story_id=sid, name="Bob", entity_type="character",
                description="Knight", base_prompt="knight"
            ),
        ]
        history = [
            Node(story_id=sid, content="History", node_type="scene", summary="Old stuff"),
        ]
        result = svc._assemble(ancestors, history, entities, token_budget=3000)
        # Verify order
        ancestor_pos = result.index("[RECENT SCENES]")
        entity_pos = result.index("[WORLD BIBLE]")
        history_pos = result.index("[RELEVANT HISTORY]")
        assert ancestor_pos < entity_pos < history_pos

    def test_empty_inputs(self, svc):
        result = svc._assemble([], [], [], token_budget=3000)
        assert result == ""
