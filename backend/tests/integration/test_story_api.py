"""Integration tests for Story API endpoints — real DB."""

import uuid

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.story import Story


class TestCreateStory:
    async def test_create_minimal(self, client: AsyncClient):
        resp = await client.post("/api/stories", json={"title": "My Story"})
        assert resp.status_code == 201
        data = resp.json()
        assert data["title"] == "My Story"
        assert data["content_mode"] == "unrestricted"
        assert data["current_leaf_id"] is not None  # Root node created

    async def test_create_with_genre_and_mode(self, client: AsyncClient):
        resp = await client.post(
            "/api/stories",
            json={"title": "Safe Tale", "genre": "sci-fi", "content_mode": "safe"},
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["genre"] == "sci-fi"
        assert data["content_mode"] == "safe"

    async def test_create_empty_title_rejected(self, client: AsyncClient):
        resp = await client.post("/api/stories", json={"title": ""})
        assert resp.status_code == 422

    async def test_create_invalid_mode_rejected(self, client: AsyncClient):
        resp = await client.post(
            "/api/stories", json={"title": "X", "content_mode": "adult"}
        )
        assert resp.status_code == 422


class TestListStories:
    async def test_list_empty(self, client: AsyncClient):
        resp = await client.get("/api/stories")
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)

    async def test_list_returns_created(self, client: AsyncClient):
        await client.post("/api/stories", json={"title": "Story A"})
        await client.post("/api/stories", json={"title": "Story B"})
        resp = await client.get("/api/stories")
        assert resp.status_code == 200
        titles = [s["title"] for s in resp.json()]
        assert "Story A" in titles
        assert "Story B" in titles


class TestGetStory:
    async def test_get_existing(self, client: AsyncClient):
        create_resp = await client.post("/api/stories", json={"title": "Get Me"})
        story_id = create_resp.json()["id"]

        resp = await client.get(f"/api/stories/{story_id}")
        assert resp.status_code == 200
        assert resp.json()["title"] == "Get Me"

    async def test_get_nonexistent(self, client: AsyncClient):
        fake_id = str(uuid.uuid4())
        resp = await client.get(f"/api/stories/{fake_id}")
        assert resp.status_code == 404


class TestUpdateStory:
    async def test_update_content_mode(self, client: AsyncClient):
        create_resp = await client.post("/api/stories", json={"title": "Update Me"})
        story_id = create_resp.json()["id"]

        resp = await client.patch(
            f"/api/stories/{story_id}", json={"content_mode": "safe"}
        )
        assert resp.status_code == 200
        assert resp.json()["content_mode"] == "safe"

    async def test_update_auto_illustrate(self, client: AsyncClient):
        create_resp = await client.post("/api/stories", json={"title": "Illustrate"})
        story_id = create_resp.json()["id"]

        resp = await client.patch(
            f"/api/stories/{story_id}", json={"auto_illustrate": True}
        )
        assert resp.status_code == 200
        assert resp.json()["auto_illustrate"] is True

    async def test_update_nonexistent(self, client: AsyncClient):
        fake_id = str(uuid.uuid4())
        resp = await client.patch(
            f"/api/stories/{fake_id}", json={"content_mode": "safe"}
        )
        assert resp.status_code == 404


class TestDeleteStory:
    async def test_delete_existing(self, client: AsyncClient):
        create_resp = await client.post("/api/stories", json={"title": "Delete Me"})
        story_id = create_resp.json()["id"]

        resp = await client.delete(f"/api/stories/{story_id}")
        assert resp.status_code == 204

        # Verify it's gone
        resp = await client.get(f"/api/stories/{story_id}")
        assert resp.status_code == 404

    async def test_delete_nonexistent(self, client: AsyncClient):
        fake_id = str(uuid.uuid4())
        resp = await client.delete(f"/api/stories/{fake_id}")
        assert resp.status_code == 404


class TestStoryTree:
    async def test_get_tree(self, client: AsyncClient):
        create_resp = await client.post("/api/stories", json={"title": "Tree Test"})
        story_id = create_resp.json()["id"]

        resp = await client.get(f"/api/stories/{story_id}/tree")
        assert resp.status_code == 200
        nodes = resp.json()
        assert len(nodes) >= 1  # At least the root node
        assert nodes[0]["node_type"] == "root"

    async def test_tree_nonexistent_story(self, client: AsyncClient):
        fake_id = str(uuid.uuid4())
        resp = await client.get(f"/api/stories/{fake_id}/tree")
        assert resp.status_code == 404


class TestExportMarkdown:
    async def test_export(self, client: AsyncClient):
        # Create story (has root node with current_leaf_id set)
        create_resp = await client.post(
            "/api/stories", json={"title": "Export Test", "genre": "fantasy"}
        )
        story_id = create_resp.json()["id"]

        resp = await client.get(f"/api/stories/{story_id}/export/markdown")
        assert resp.status_code == 200
        assert resp.headers["content-type"].startswith("text/markdown")
        assert "Export Test" in resp.text

    async def test_export_nonexistent(self, client: AsyncClient):
        fake_id = str(uuid.uuid4())
        resp = await client.get(f"/api/stories/{fake_id}/export/markdown")
        assert resp.status_code == 404
