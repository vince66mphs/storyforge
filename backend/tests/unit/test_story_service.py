"""Tests for StoryGenerationService — mocked sub-services and DB."""

import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.node import Node
from app.models.story import Story
from app.services.story_service import StoryGenerationService
from tests.factories import make_beat


@pytest.fixture
def svc():
    service = StoryGenerationService()
    service.ollama = AsyncMock()
    service.context_svc = AsyncMock()
    service.planner = AsyncMock()
    service.writer = AsyncMock()
    service.model_manager = MagicMock()
    service.model_manager.generation_lock = AsyncMock()
    # Make the lock context manager work
    service.model_manager.generation_lock.__aenter__ = AsyncMock()
    service.model_manager.generation_lock.__aexit__ = AsyncMock(return_value=False)

    # Defaults
    service.context_svc.build_context.return_value = "Story context text"
    service.planner.plan_beat.return_value = make_beat()
    service.writer.write_scene.return_value = "The hero walked into the forest."
    service.ollama.create_embedding.return_value = [0.1] * 768
    service.ollama.generate.return_value = "Generated summary"

    return service


def _mock_session_for_generate(story_id, leaf_id):
    """Build a mock session that returns a Story with given leaf, then works for add/commit."""
    session = AsyncMock(spec=AsyncSession)

    story = Story(title="Test", content_mode="unrestricted", context_depth=5)
    story.id = story_id
    story.current_leaf_id = leaf_id

    # session.execute returns different results on successive calls
    mock_result = MagicMock()
    mock_result.scalar_one.return_value = story
    mock_result.scalars.return_value.all.return_value = []
    session.execute.return_value = mock_result
    session.add = MagicMock()

    async def fake_refresh(obj):
        if isinstance(obj, Node):
            obj.id = obj.id or uuid.uuid4()
            from datetime import datetime, timezone
            obj.created_at = datetime.now(timezone.utc)

    session.refresh = AsyncMock(side_effect=fake_refresh)

    return session


class TestMoAPipeline:
    async def test_generate_scene_moa(self, svc):
        story_id = uuid.uuid4()
        parent_id = uuid.uuid4()
        session = _mock_session_for_generate(story_id, parent_id)

        node = await svc.generate_scene(session, story_id, parent_id, "Go north")

        assert isinstance(node, Node)
        assert node.content == "The hero walked into the forest."
        svc.planner.plan_beat.assert_called_once()
        svc.writer.write_scene.assert_called_once()
        svc.context_svc.build_context.assert_called_once()
        svc.ollama.create_embedding.assert_called()

    async def test_beat_stored_in_metadata(self, svc):
        story_id = uuid.uuid4()
        parent_id = uuid.uuid4()
        session = _mock_session_for_generate(story_id, parent_id)
        beat = make_beat(setting="cave")
        svc.planner.plan_beat.return_value = beat

        node = await svc.generate_scene(session, story_id, parent_id, "Explore")

        assert node.metadata_ is not None
        assert node.metadata_["beat"]["setting"] == "cave"


class TestSingleModelFallback:
    async def test_generate_scene_single_model(self, svc):
        svc._moa_enabled = False
        svc.ollama.generate.return_value = "Direct generation result"

        story_id = uuid.uuid4()
        parent_id = uuid.uuid4()
        session = _mock_session_for_generate(story_id, parent_id)

        node = await svc.generate_scene(session, story_id, parent_id, "Go east")

        assert node.content == "Direct generation result"
        svc.planner.plan_beat.assert_not_called()
        svc.writer.write_scene.assert_not_called()


class TestBuildPrompt:
    def test_prompt_format(self, svc):
        result = svc._build_prompt("context here", "go north")
        assert "context here" in result
        assert "go north" in result
        assert "Continue the story:" in result


class TestSystemPromptSelection:
    def test_unrestricted(self, svc):
        prompt = svc._get_system_prompt("unrestricted")
        assert "full creative freedom" in prompt

    def test_safe(self, svc):
        prompt = svc._get_system_prompt("safe")
        assert "general audience" in prompt


class TestCreateBranch:
    async def test_branch_calls_generate(self, svc):
        node_id = uuid.uuid4()
        parent_id = uuid.uuid4()
        story_id = uuid.uuid4()

        # First call returns the reference node
        ref_node = Node(story_id=story_id, parent_id=parent_id, content="ref", node_type="scene")
        ref_node.id = node_id

        session = AsyncMock(spec=AsyncSession)
        mock_result = MagicMock()
        mock_result.scalar_one.return_value = ref_node
        session.execute.return_value = mock_result

        # Mock generate_scene
        generated = Node(story_id=story_id, parent_id=parent_id, content="branch", node_type="scene")
        svc.generate_scene = AsyncMock(return_value=generated)

        result = await svc.create_branch(session, node_id, "Try something else")
        assert result.content == "branch"
        svc.generate_scene.assert_called_once_with(
            session=session,
            story_id=story_id,
            parent_node_id=parent_id,
            user_prompt="Try something else",
        )

    async def test_branch_from_root_raises(self, svc):
        node_id = uuid.uuid4()
        root = Node(story_id=uuid.uuid4(), parent_id=None, content="root", node_type="root")
        root.id = node_id

        session = AsyncMock(spec=AsyncSession)
        mock_result = MagicMock()
        mock_result.scalar_one.return_value = root
        session.execute.return_value = mock_result

        with pytest.raises(ValueError, match="root"):
            await svc.create_branch(session, node_id, "branch")
