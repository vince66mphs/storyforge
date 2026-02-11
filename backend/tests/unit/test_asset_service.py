"""Tests for AssetService — mocked OllamaService, ComfyUI, and DB."""

import json
import os
import uuid
from unittest.mock import AsyncMock, MagicMock, patch

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


class TestGenerateEntityImages:
    async def test_yields_4_candidates_with_different_seeds(self, svc):
        filenames = [f"candidate_{i}.png" for i in range(4)]
        svc.comfyui.generate_image.side_effect = filenames

        entity = WorldBibleEntity(
            story_id=uuid.uuid4(),
            name="Alice",
            entity_type="character",
            description="Hero",
            base_prompt="woman, hero",
        )
        entity.id = uuid.uuid4()

        results = []
        async for candidate in svc.generate_entity_images(entity):
            results.append(candidate)

        assert len(results) == 4
        assert svc.comfyui.generate_image.call_count == 4

        # Each candidate should have index, filename, and seed
        for i, r in enumerate(results):
            assert r["index"] == i
            assert r["filename"] == filenames[i]
            assert isinstance(r["seed"], int)

        # Seeds should all be different (random)
        seeds = [r["seed"] for r in results]
        assert len(set(seeds)) == 4


class TestSelectEntityImage:
    async def test_sets_reference_image_and_seed(self, svc):
        session = AsyncMock()
        entity = WorldBibleEntity(
            story_id=uuid.uuid4(),
            name="Alice",
            entity_type="character",
            description="Hero",
            base_prompt="woman, hero",
        )
        entity.id = uuid.uuid4()

        await svc.select_entity_image(
            session=session,
            entity=entity,
            filename="selected.png",
            seed=12345,
        )

        assert entity.reference_image_path == "selected.png"
        assert entity.image_seed == 12345
        session.commit.assert_called_once()

    async def test_cleans_up_rejected_files(self, svc, tmp_path):
        session = AsyncMock()
        entity = WorldBibleEntity(
            story_id=uuid.uuid4(),
            name="Alice",
            entity_type="character",
            description="Hero",
            base_prompt="woman, hero",
        )
        entity.id = uuid.uuid4()

        # Create fake image files in a temp images dir
        images_dir = tmp_path / "images"
        images_dir.mkdir()
        reject1 = images_dir / "reject1.png"
        reject2 = images_dir / "reject2.png"
        reject1.write_text("fake image data")
        reject2.write_text("fake image data")

        with patch("app.services.asset_service.get_settings") as mock_settings:
            mock_settings.return_value.static_dir = str(tmp_path)

            await svc.select_entity_image(
                session=session,
                entity=entity,
                filename="selected.png",
                seed=99,
                reject_filenames=["reject1.png", "reject2.png"],
            )

        assert not reject1.exists()
        assert not reject2.exists()


class TestDescribeEntityFromImage:
    async def test_generates_description_and_updates_entity(self, svc):
        session = AsyncMock()
        entity = WorldBibleEntity(
            story_id=uuid.uuid4(),
            name="Alice",
            entity_type="character",
            description="Original description",
            base_prompt="woman, hero",
            reference_image_path="alice_ref.png",
        )
        entity.id = uuid.uuid4()
        entity.version = 1

        svc.ollama.generate_vision = AsyncMock(
            return_value="  A tall woman with flowing red hair.  "
        )
        svc.ollama.create_embedding.return_value = [0.1] * 768

        with patch("app.services.asset_service.get_settings") as mock_settings:
            mock_settings.return_value.static_dir = "/tmp/storyforge_static"

            result = await svc.describe_entity_from_image(session, entity)

        assert result == "  A tall woman with flowing red hair.  "
        assert entity.description == "A tall woman with flowing red hair."
        assert entity.version == 2
        session.commit.assert_called_once()
        svc.ollama.generate_vision.assert_called_once()
        # Verify vision was called with correct image path
        call_kwargs = svc.ollama.generate_vision.call_args
        assert "alice_ref.png" in call_kwargs.kwargs["image_path"]
        assert call_kwargs.kwargs["model"] == "gemma2:9b"

    async def test_raises_value_error_when_no_image(self, svc):
        session = AsyncMock()
        entity = WorldBibleEntity(
            story_id=uuid.uuid4(),
            name="Alice",
            entity_type="character",
            description="Hero",
            base_prompt="woman, hero",
            reference_image_path=None,
        )
        entity.id = uuid.uuid4()

        with pytest.raises(ValueError, match="no reference image"):
            await svc.describe_entity_from_image(session, entity)
