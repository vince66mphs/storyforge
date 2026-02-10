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
    EntityCreate,
    EntityUpdate,
    EntityResponse,
    DetectEntitiesRequest,
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
