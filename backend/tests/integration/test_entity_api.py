"""Integration tests for Entity API endpoints — real DB, mocked services."""

import json
import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, patch

import pytest
from httpx import AsyncClient

from app.models.world_bible import WorldBibleEntity


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


class TestGenerateEntityImages:
    async def test_sse_returns_event_stream(self, client: AsyncClient, db_session):
        # Create story in DB
        create_resp = await client.post("/api/stories", json={"title": "SSE Test"})
        story_id = create_resp.json()["id"]

        # Insert entity directly into DB so subsequent lookups find it
        entity = WorldBibleEntity(
            story_id=uuid.UUID(story_id),
            name="Alice",
            entity_type="character",
            description="Hero",
            base_prompt="woman, hero",
            version=1,
        )
        db_session.add(entity)
        await db_session.flush()
        entity_id = str(entity.id)

        async def mock_generate_images(ent, count=4):
            for i in range(count):
                yield {"index": i, "filename": f"candidate_{i}.png", "seed": 1000 + i}

        with patch.object(
            __import__("app.api.entities", fromlist=["asset_svc"]).asset_svc,
            "generate_entity_images",
            side_effect=mock_generate_images,
        ):
            resp = await client.post(f"/api/entities/{entity_id}/images/generate")
            assert resp.status_code == 200
            assert resp.headers["content-type"].startswith("text/event-stream")

            # Parse SSE events from response body
            body = resp.text
            events = [
                line.removeprefix("data: ")
                for line in body.strip().split("\n")
                if line.startswith("data: ")
            ]
            assert len(events) == 5  # 4 candidates + 1 done marker

            # Verify candidate events
            for i in range(4):
                data = json.loads(events[i])
                assert data["index"] == i
                assert data["filename"] == f"candidate_{i}.png"
                assert data["seed"] == 1000 + i

            # Verify done marker
            done = json.loads(events[4])
            assert done["done"] is True

    async def test_nonexistent_entity_returns_404(self, client: AsyncClient):
        fake_id = str(uuid.uuid4())
        resp = await client.post(f"/api/entities/{fake_id}/images/generate")
        assert resp.status_code == 404


class TestSelectEntityImage:
    async def test_select_image(self, client: AsyncClient, db_session):
        # Create story in DB
        create_resp = await client.post("/api/stories", json={"title": "Select Test"})
        story_id = create_resp.json()["id"]

        # Insert entity directly into DB
        entity = WorldBibleEntity(
            story_id=uuid.UUID(story_id),
            name="Bob",
            entity_type="character",
            description="Knight",
            base_prompt="knight, armor",
            version=1,
        )
        db_session.add(entity)
        await db_session.flush()
        entity_id = str(entity.id)

        with patch.object(
            __import__("app.api.entities", fromlist=["asset_svc"]).asset_svc,
            "select_entity_image",
            new_callable=AsyncMock,
        ) as mock_select:
            resp = await client.post(
                f"/api/entities/{entity_id}/images/select",
                json={
                    "filename": "selected.png",
                    "seed": 42,
                    "reject_filenames": ["reject1.png", "reject2.png"],
                },
            )
            assert resp.status_code == 200
            mock_select.assert_called_once()
            call_kwargs = mock_select.call_args
            assert call_kwargs.kwargs["filename"] == "selected.png"
            assert call_kwargs.kwargs["seed"] == 42
            assert call_kwargs.kwargs["reject_filenames"] == ["reject1.png", "reject2.png"]

    async def test_select_nonexistent_entity_returns_404(self, client: AsyncClient):
        fake_id = str(uuid.uuid4())
        resp = await client.post(
            f"/api/entities/{fake_id}/images/select",
            json={"filename": "img.png", "seed": 1},
        )
        assert resp.status_code == 404


class TestDescribeEntity:
    async def test_describe_entity(self, client: AsyncClient, db_session):
        # Create story in DB
        create_resp = await client.post("/api/stories", json={"title": "Describe Test"})
        story_id = create_resp.json()["id"]

        # Insert entity with reference image directly into DB
        entity = WorldBibleEntity(
            story_id=uuid.UUID(story_id),
            name="Alice",
            entity_type="character",
            description="Hero",
            base_prompt="woman, hero",
            reference_image_path="alice_ref.png",
            image_seed=42,
            version=1,
        )
        db_session.add(entity)
        await db_session.flush()
        entity_id = str(entity.id)

        with patch.object(
            __import__("app.api.entities", fromlist=["asset_svc"]).asset_svc,
            "describe_entity_from_image",
            new_callable=AsyncMock,
            return_value="A tall woman with flowing red hair.",
        ) as mock_describe:
            resp = await client.post(f"/api/entities/{entity_id}/describe")
            assert resp.status_code == 200
            mock_describe.assert_called_once()

    async def test_describe_returns_400_when_no_image(self, client: AsyncClient, db_session):
        # Create story in DB
        create_resp = await client.post("/api/stories", json={"title": "No Img"})
        story_id = create_resp.json()["id"]

        # Insert entity WITHOUT reference image
        entity = WorldBibleEntity(
            story_id=uuid.UUID(story_id),
            name="Orphan",
            entity_type="character",
            description="No image",
            base_prompt="plain character",
            reference_image_path=None,
            version=1,
        )
        db_session.add(entity)
        await db_session.flush()
        entity_id = str(entity.id)

        resp = await client.post(f"/api/entities/{entity_id}/describe")
        assert resp.status_code == 400
        assert "no reference image" in resp.json()["detail"].lower()


class TestUploadEntityImage:
    async def test_upload_image(self, client: AsyncClient, db_session):
        # Create story in DB
        create_resp = await client.post("/api/stories", json={"title": "Upload Test"})
        story_id = create_resp.json()["id"]

        # Insert entity directly into DB
        entity = WorldBibleEntity(
            story_id=uuid.UUID(story_id),
            name="UploadChar",
            entity_type="character",
            description="Test",
            base_prompt="test prompt",
            image_seed=42,
            version=1,
        )
        db_session.add(entity)
        await db_session.flush()
        entity_id = str(entity.id)

        # Upload a small PNG (1x1 pixel)
        import io
        png_data = (
            b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01'
            b'\x00\x00\x00\x01\x08\x02\x00\x00\x00\x90wS\xde\x00'
            b'\x00\x00\x0cIDATx\x9cc\xf8\x0f\x00\x00\x01\x01\x00'
            b'\x05\x18\xd8N\x00\x00\x00\x00IEND\xaeB`\x82'
        )

        resp = await client.post(
            f"/api/entities/{entity_id}/image/upload",
            files={"file": ("test.png", io.BytesIO(png_data), "image/png")},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["reference_image_path"].startswith("upload_")
        assert data["reference_image_path"].endswith(".png")
        assert data["image_seed"] is None

    async def test_upload_invalid_type(self, client: AsyncClient, db_session):
        # Create story in DB
        create_resp = await client.post("/api/stories", json={"title": "Bad Upload"})
        story_id = create_resp.json()["id"]

        # Insert entity
        entity = WorldBibleEntity(
            story_id=uuid.UUID(story_id),
            name="GifChar",
            entity_type="character",
            description="Test",
            base_prompt="test prompt",
            version=1,
        )
        db_session.add(entity)
        await db_session.flush()
        entity_id = str(entity.id)

        import io
        resp = await client.post(
            f"/api/entities/{entity_id}/image/upload",
            files={"file": ("test.gif", io.BytesIO(b"GIF89a"), "image/gif")},
        )
        assert resp.status_code == 400
        assert "Invalid file type" in resp.json()["detail"]

    async def test_upload_nonexistent_entity(self, client: AsyncClient):
        import io
        fake_id = str(uuid.uuid4())
        resp = await client.post(
            f"/api/entities/{fake_id}/image/upload",
            files={"file": ("test.png", io.BytesIO(b"data"), "image/png")},
        )
        assert resp.status_code == 404


class TestUpdateEntity:
    async def test_update_nonexistent(self, client: AsyncClient):
        fake_id = str(uuid.uuid4())
        resp = await client.patch(
            f"/api/entities/{fake_id}",
            json={"description": "Updated"},
        )
        assert resp.status_code == 404
