"""Tests for Pydantic schemas and exception classes."""

import uuid
from datetime import datetime, timezone

import pytest
from pydantic import ValidationError

from app.core.exceptions import GenerationError, ModelNotFoundError
from app.api.schemas import (
    StoryCreate,
    StoryUpdate,
    StoryResponse,
    GenerateSceneRequest,
    BranchRequest,
    NodeUpdate,
    NodeResponse,
    UnknownCharacter,
    EntityCreate,
    EntityUpdate,
    EntityResponse,
    DetectEntitiesRequest,
    ImageSelectRequest,
)


# ── StoryCreate ───────────────────────────────────────────────────────

class TestStoryCreate:
    def test_valid_minimal(self):
        s = StoryCreate(title="My Story")
        assert s.title == "My Story"
        assert s.genre is None
        assert s.content_mode == "unrestricted"

    def test_valid_full(self):
        s = StoryCreate(title="Epic", genre="fantasy", content_mode="safe")
        assert s.genre == "fantasy"
        assert s.content_mode == "safe"

    def test_empty_title_rejected(self):
        with pytest.raises(ValidationError):
            StoryCreate(title="")

    def test_invalid_content_mode_rejected(self):
        with pytest.raises(ValidationError):
            StoryCreate(title="X", content_mode="adult")

    def test_title_too_long_rejected(self):
        with pytest.raises(ValidationError):
            StoryCreate(title="x" * 256)


# ── StoryUpdate ───────────────────────────────────────────────────────

class TestStoryUpdate:
    def test_all_none(self):
        s = StoryUpdate()
        assert s.content_mode is None
        assert s.auto_illustrate is None
        assert s.context_depth is None

    def test_partial_update(self):
        s = StoryUpdate(content_mode="safe", context_depth=10)
        assert s.content_mode == "safe"
        assert s.context_depth == 10

    def test_context_depth_bounds(self):
        with pytest.raises(ValidationError):
            StoryUpdate(context_depth=0)
        with pytest.raises(ValidationError):
            StoryUpdate(context_depth=21)


# ── GenerateSceneRequest / BranchRequest ──────────────────────────────

class TestSceneRequests:
    def test_generate_scene_valid(self):
        r = GenerateSceneRequest(user_prompt="Go north")
        assert r.user_prompt == "Go north"

    def test_generate_scene_empty_rejected(self):
        with pytest.raises(ValidationError):
            GenerateSceneRequest(user_prompt="")

    def test_branch_valid(self):
        r = BranchRequest(user_prompt="Try something else")
        assert r.user_prompt == "Try something else"

    def test_node_update_valid(self):
        r = NodeUpdate(content="Edited content")
        assert r.content == "Edited content"

    def test_node_update_empty_rejected(self):
        with pytest.raises(ValidationError):
            NodeUpdate(content="")


# ── EntityCreate ──────────────────────────────────────────────────────

class TestEntityCreate:
    def test_valid(self):
        e = EntityCreate(
            entity_type="character",
            name="Alice",
            description="A brave hero",
            base_prompt="woman, adventurer",
        )
        assert e.entity_type == "character"

    def test_invalid_entity_type(self):
        with pytest.raises(ValidationError):
            EntityCreate(
                entity_type="animal",
                name="Cat",
                description="A cat",
                base_prompt="cat",
            )

    def test_valid_entity_types(self):
        for t in ("character", "location", "prop"):
            e = EntityCreate(entity_type=t, name="X", description="d", base_prompt="p")
            assert e.entity_type == t


# ── DetectEntitiesRequest ─────────────────────────────────────────────

class TestDetectEntitiesRequest:
    def test_valid(self):
        r = DetectEntitiesRequest(text="Alice walked into the forest.")
        assert "Alice" in r.text

    def test_empty_rejected(self):
        with pytest.raises(ValidationError):
            DetectEntitiesRequest(text="")


# ── ModelNotFoundError ──────────────────────────────────────────────

class TestModelNotFoundError:
    def test_attributes(self):
        err = ModelNotFoundError("phi4:latest")
        assert err.model_name == "phi4:latest"
        assert err.service == "Ollama"
        assert "phi4:latest" in str(err)
        assert "ollama pull" in str(err)

    def test_is_subclass_of_generation_error(self):
        err = ModelNotFoundError("test-model")
        assert isinstance(err, GenerationError)

    def test_custom_detail(self):
        err = ModelNotFoundError("foo", detail="custom message")
        assert "custom message" in str(err)


# ── ImageSelectRequest ───────────────────────────────────────────────

class TestImageSelectRequest:
    def test_valid(self):
        r = ImageSelectRequest(filename="alice_001.png", seed=12345)
        assert r.filename == "alice_001.png"
        assert r.seed == 12345
        assert r.reject_filenames == []

    def test_empty_filename_rejected(self):
        with pytest.raises(ValidationError):
            ImageSelectRequest(filename="", seed=42)

    def test_with_reject_list(self):
        r = ImageSelectRequest(
            filename="selected.png",
            seed=99,
            reject_filenames=["reject1.png", "reject2.png", "reject3.png"],
        )
        assert len(r.reject_filenames) == 3
        assert "reject2.png" in r.reject_filenames


# ── UnknownCharacter ────────────────────────────────────────────────

class TestUnknownCharacter:
    def test_valid(self):
        c = UnknownCharacter(name="Bob", description="A stranger", base_prompt="portrait of Bob")
        assert c.name == "Bob"
        assert c.entity_type == "character"

    def test_defaults(self):
        c = UnknownCharacter(name="Eve")
        assert c.entity_type == "character"
        assert c.description == ""
        assert c.base_prompt == ""


# ── NodeResponse with unknown_characters ─────────────────────────────

class TestNodeResponseUnknownCharacters:
    def test_empty_by_default(self):
        n = NodeResponse(
            id=uuid.uuid4(),
            story_id=uuid.uuid4(),
            parent_id=None,
            content="Test",
            summary=None,
            node_type="scene",
            created_at=datetime.now(timezone.utc),
        )
        assert n.unknown_characters == []

    def test_with_unknown_characters(self):
        chars = [{"name": "Bob", "entity_type": "character", "description": "A stranger", "base_prompt": "portrait"}]
        n = NodeResponse(
            id=uuid.uuid4(),
            story_id=uuid.uuid4(),
            parent_id=None,
            content="Test",
            summary=None,
            node_type="scene",
            created_at=datetime.now(timezone.utc),
            unknown_characters=chars,
        )
        assert len(n.unknown_characters) == 1
        assert n.unknown_characters[0].name == "Bob"
