"""Integration tests for Entity API endpoints — real DB, mocked services."""

import uuid
from unittest.mock import AsyncMock, patch

import pytest
from httpx import AsyncClient


class TestCreateEntity:
    async def test_create_entity(self, client: AsyncClient):
        # Create story first
        create_resp = await client.post("/api/stories", json={"title": "Entity Test"})
        story_id = create_resp.json()["id"]

        with patch.object(
            __import__("app.api.entities", fromlist=["asset_svc"]).asset_svc,
            "create_entity",
            new_callable=AsyncMock,
        ) as mock_create:
            from app.models.world_bible import WorldBibleEntity
            from datetime import datetime, timezone

            entity = WorldBibleEntity(
                story_id=uuid.UUID(story_id),
                name="Alice",
                entity_type="character",
                description="Hero",
                base_prompt="woman, hero",
            )
            entity.id = uuid.uuid4()
            entity.version = 1
            entity.created_at = datetime.now(timezone.utc)
            mock_create.return_value = entity

            resp = await client.post(
                f"/api/stories/{story_id}/entities",
                json={
                    "entity_type": "character",
                    "name": "Alice",
                    "description": "Hero",
                    "base_prompt": "woman, hero",
                },
            )
            assert resp.status_code == 201
            assert resp.json()["name"] == "Alice"

    async def test_create_story_not_found(self, client: AsyncClient):
        fake_id = str(uuid.uuid4())
        resp = await client.post(
            f"/api/stories/{fake_id}/entities",
            json={
                "entity_type": "character",
                "name": "Alice",
                "description": "Hero",
                "base_prompt": "woman, hero",
            },
        )
        assert resp.status_code == 404

    async def test_create_invalid_type(self, client: AsyncClient):
        create_resp = await client.post("/api/stories", json={"title": "Bad Type"})
        story_id = create_resp.json()["id"]
        resp = await client.post(
            f"/api/stories/{story_id}/entities",
            json={
                "entity_type": "animal",
                "name": "Cat",
                "description": "A cat",
                "base_prompt": "cat",
            },
        )
        assert resp.status_code == 422


class TestListEntities:
    async def test_list_empty(self, client: AsyncClient):
        create_resp = await client.post("/api/stories", json={"title": "List Ent"})
        story_id = create_resp.json()["id"]

        resp = await client.get(f"/api/stories/{story_id}/entities")
        assert resp.status_code == 200
        assert resp.json() == []

    async def test_list_story_not_found(self, client: AsyncClient):
        fake_id = str(uuid.uuid4())
        resp = await client.get(f"/api/stories/{fake_id}/entities")
        assert resp.status_code == 404


class TestDetectEntities:
    async def test_detect_and_create(self, client: AsyncClient):
        create_resp = await client.post("/api/stories", json={"title": "Detect"})
        story_id = create_resp.json()["id"]

        with patch.object(
            __import__("app.api.entities", fromlist=["asset_svc"]).asset_svc,
            "detect_entities",
            new_callable=AsyncMock,
            return_value=[],
        ):
            resp = await client.post(
                f"/api/stories/{story_id}/entities/detect",
                json={"text": "Alice walked into the forest."},
            )
            assert resp.status_code == 201
            assert resp.json() == []


class TestGetEntity:
    async def test_get_nonexistent(self, client: AsyncClient):
        fake_id = str(uuid.uuid4())
        resp = await client.get(f"/api/entities/{fake_id}")
        assert resp.status_code == 404


class TestGenerateEntityImage:
    async def test_nonexistent_entity(self, client: AsyncClient):
        fake_id = str(uuid.uuid4())
        resp = await client.post(f"/api/entities/{fake_id}/image")
        assert resp.status_code == 404


class TestUpdateEntity:
    async def test_update_nonexistent(self, client: AsyncClient):
        fake_id = str(uuid.uuid4())
        resp = await client.patch(
            f"/api/entities/{fake_id}",
            json={"description": "Updated"},
        )
        assert resp.status_code == 404
