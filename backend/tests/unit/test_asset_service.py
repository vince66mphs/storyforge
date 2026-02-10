"""Tests for AssetService — mocked OllamaService, ComfyUI, and DB."""

import json
import uuid
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.models.world_bible import WorldBibleEntity
from app.services.asset_service import AssetService


@pytest.fixture
def svc():
    service = AssetService()
    service.ollama = AsyncMock()
    service.comfyui = AsyncMock()
    service.ollama.create_embedding.return_value = [0.1] * 768
    return service


class TestDetectEntities:
    async def test_valid_detection(self, svc):
        svc.ollama.generate.return_value = json.dumps([
            {
                "name": "Alice",
                "entity_type": "character",
                "description": "A brave hero",
                "base_prompt": "woman, adventurer",
            }
        ])
        result = await svc.detect_entities("Alice walked into the forest.")
        assert len(result) == 1
        assert result[0]["name"] == "Alice"

    async def test_markdown_fenced_json(self, svc):
        svc.ollama.generate.return_value = '```json\n[{"name": "Bob", "entity_type": "character", "description": "knight", "base_prompt": "knight"}]\n```'
        result = await svc.detect_entities("Bob fought bravely.")
        assert len(result) == 1

    async def test_invalid_json_returns_empty(self, svc):
        svc.ollama.generate.return_value = "This is not JSON"
        result = await svc.detect_entities("Some text")
        assert result == []

    async def test_non_list_returns_empty(self, svc):
        svc.ollama.generate.return_value = json.dumps({"name": "Alice"})
        result = await svc.detect_entities("Alice")
        assert result == []

    async def test_missing_fields_skipped(self, svc):
        svc.ollama.generate.return_value = json.dumps([
            {"name": "Alice"},  # missing required fields
            {"name": "Bob", "entity_type": "character", "description": "d", "base_prompt": "p"},
        ])
        result = await svc.detect_entities("Alice and Bob")
        assert len(result) == 1
        assert result[0]["name"] == "Bob"

    async def test_empty_array(self, svc):
        svc.ollama.generate.return_value = "[]"
        result = await svc.detect_entities("Nothing here")
        assert result == []


class TestCreateEntity:
    async def test_creates_entity(self, svc):
        session = AsyncMock()
        session.add = MagicMock()
        story_id = uuid.uuid4()

        entity_data = {
            "name": "Alice",
            "entity_type": "character",
            "description": "A brave hero",
            "base_prompt": "woman, adventurer",
        }

        result = await svc.create_entity(session, story_id, entity_data)
        assert isinstance(result, WorldBibleEntity)
        assert result.name == "Alice"
        session.add.assert_called_once()
        session.commit.assert_called_once()
        svc.ollama.create_embedding.assert_called_once()


class TestGenerateEntityImage:
    async def test_generates_and_saves(self, svc):
        session = AsyncMock()
        entity = WorldBibleEntity(
            story_id=uuid.uuid4(),
            name="Alice",
            entity_type="character",
            description="Hero",
            base_prompt="woman, hero",
        )
        entity.id = uuid.uuid4()

        svc.comfyui.generate_image.return_value = "alice_img.png"

        result = await svc.generate_entity_image(session, entity, seed=42)
        assert result == "alice_img.png"
        assert entity.reference_image_path == "alice_img.png"
        assert entity.image_seed == 42
        session.commit.assert_called_once()

    async def test_without_seed(self, svc):
        session = AsyncMock()
        entity = WorldBibleEntity(
            story_id=uuid.uuid4(),
            name="Bob",
            entity_type="character",
            description="Knight",
            base_prompt="knight, armor",
        )
        entity.id = uuid.uuid4()

        svc.comfyui.generate_image.return_value = "bob_img.png"

        result = await svc.generate_entity_image(session, entity)
        assert result == "bob_img.png"
        assert entity.reference_image_path == "bob_img.png"
        assert entity.image_seed is None
