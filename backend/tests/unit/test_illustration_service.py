"""Tests for IllustrationService — mocked ComfyUI and DB."""

import json
import uuid
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.models.node import Node
from app.models.story import Story
from app.services.illustration_service import IllustrationService
from tests.factories import make_beat


@pytest.fixture
def svc(tmp_path):
    """Create IllustrationService with mocked ComfyUI."""
    with patch.object(IllustrationService, "__init__", lambda self: None):
        service = IllustrationService()
        service.comfyui = AsyncMock()
        service.settings = MagicMock()
        service.settings.ipadapter_enabled = True
        service.settings.ipadapter_weight = 0.7
        service.settings.scene_image_width = 1024
        service.settings.scene_image_height = 576
        service.settings.static_dir = str(tmp_path)
        service._ipadapter_template = {"6": {"inputs": {"text": ""}}, "5": {"inputs": {}}, "12": {"inputs": {}}, "13": {"inputs": {}}, "3": {"inputs": {}}}
        service._basic_template = {"6": {"inputs": {"text": ""}}, "5": {"inputs": {}}, "3": {"inputs": {}}}
        return service


def _make_scene_node(story_id, beat=None, content="A dark forest scene."):
    metadata = {}
    if beat:
        metadata["beat"] = beat
    node = Node(
        story_id=story_id,
        content=content,
        node_type="scene",
        metadata_=metadata or None,
    )
    node.id = uuid.uuid4()
    return node


class TestBuildImagePrompt:
    def test_from_beat(self, svc):
        beat = make_beat(setting="castle", characters=["Alice"], events=["Enter gate"], tone="dramatic")
        node = _make_scene_node(uuid.uuid4(), beat=beat)
        prompt = svc._build_image_prompt(node)
        assert "castle" in prompt
        assert "Alice" in prompt
        assert "Enter gate" in prompt
        assert "dramatic atmosphere" in prompt
        assert "cinematic scene" in prompt

    def test_from_content_fallback(self, svc):
        node = _make_scene_node(uuid.uuid4(), beat=None, content="The wizard cast a spell.")
        prompt = svc._build_image_prompt(node)
        assert "wizard" in prompt
        assert "cinematic scene" in prompt

    def test_empty_content_returns_none(self, svc):
        node = _make_scene_node(uuid.uuid4(), beat=None, content="")
        prompt = svc._build_image_prompt(node)
        assert prompt is None

    def test_long_content_truncated(self, svc):
        node = _make_scene_node(uuid.uuid4(), beat=None, content="word " * 100)
        prompt = svc._build_image_prompt(node)
        # Content should be truncated at ~200 chars + suffix
        assert len(prompt) < 400


class TestIllustrateScene:
    async def test_basic_workflow_when_no_ref_image(self, svc):
        story_id = uuid.uuid4()
        story = Story(title="Test")
        story.id = story_id
        node = _make_scene_node(story_id, beat=make_beat())

        session = AsyncMock()
        session.execute.return_value = MagicMock(
            scalars=MagicMock(return_value=MagicMock(all=MagicMock(return_value=[])))
        )

        svc.comfyui.queue_workflow.return_value = "prompt_123"
        svc.comfyui._wait_for_completion.return_value = {
            "outputs": {"9": {"images": [{"filename": "out.png"}]}}
        }
        svc.comfyui._save_output_image.return_value = "saved_out.png"

        result = await svc.illustrate_scene(session, node, story)
        assert result == "saved_out.png"
        svc.comfyui.queue_workflow.assert_called_once()

    async def test_ipadapter_workflow_when_ref_exists(self, svc, tmp_path):
        story_id = uuid.uuid4()
        story = Story(title="Test")
        story.id = story_id
        node = _make_scene_node(story_id, beat=make_beat(characters=["Alice"]))

        # Create a fake reference image
        images_dir = tmp_path / "images"
        images_dir.mkdir(exist_ok=True)
        ref_img = images_dir / "alice_ref.png"
        ref_img.write_bytes(b"fake_png")

        # Mock entity lookup returning an entity with reference image
        from app.models.world_bible import WorldBibleEntity
        entity = WorldBibleEntity(
            story_id=story_id, name="Alice", entity_type="character",
            description="Hero", base_prompt="hero",
            reference_image_path="alice_ref.png",
        )
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [entity]
        session = AsyncMock()
        session.execute.return_value = mock_result

        svc.comfyui.upload_image.return_value = "alice_ref.png"
        svc.comfyui.queue_workflow.return_value = "prompt_456"
        svc.comfyui._wait_for_completion.return_value = {
            "outputs": {"9": {"images": [{"filename": "out.png"}]}}
        }
        svc.comfyui._save_output_image.return_value = "ipadapter_out.png"

        result = await svc.illustrate_scene(session, node, story)
        assert result == "ipadapter_out.png"
        svc.comfyui.upload_image.assert_called_once()

    async def test_returns_none_on_comfyui_error(self, svc):
        from app.core.exceptions import ServiceUnavailableError

        story_id = uuid.uuid4()
        story = Story(title="Test")
        story.id = story_id
        node = _make_scene_node(story_id, beat=make_beat())

        session = AsyncMock()
        session.execute.return_value = MagicMock(
            scalars=MagicMock(return_value=MagicMock(all=MagicMock(return_value=[])))
        )
        svc.comfyui.queue_workflow.side_effect = ServiceUnavailableError("ComfyUI")

        result = await svc.illustrate_scene(session, node, story)
        assert result is None

    async def test_stores_path_in_metadata(self, svc):
        story_id = uuid.uuid4()
        story = Story(title="Test")
        story.id = story_id
        node = _make_scene_node(story_id, beat=make_beat())
        node.metadata_ = {}

        session = AsyncMock()
        session.execute.return_value = MagicMock(
            scalars=MagicMock(return_value=MagicMock(all=MagicMock(return_value=[])))
        )
        svc.comfyui.queue_workflow.return_value = "p1"
        svc.comfyui._wait_for_completion.return_value = {
            "outputs": {"9": {"images": [{"filename": "out.png"}]}}
        }
        svc.comfyui._save_output_image.return_value = "stored.png"

        await svc.illustrate_scene(session, node, story)
        assert node.metadata_["illustration_path"] == "stored.png"
        session.commit.assert_called()
