"""Integration tests for Node API endpoints — real DB, mocked services."""

import uuid
from unittest.mock import AsyncMock, patch

import pytest
from httpx import AsyncClient

from app.models.node import Node
from app.models.story import Story


class TestGenerateScene:
    async def test_generate_scene(self, client: AsyncClient):
        # Create a story first
        create_resp = await client.post("/api/stories", json={"title": "Gen Test"})
        story_id = create_resp.json()["id"]

        # Mock the story service
        mock_node = Node(
            story_id=uuid.UUID(story_id),
            parent_id=uuid.UUID(create_resp.json()["current_leaf_id"]),
            content="The hero ventured forth.",
            node_type="scene",
        )
        mock_node.id = uuid.uuid4()
        from datetime import datetime, timezone
        mock_node.created_at = datetime.now(timezone.utc)

        with patch.object(
            __import__("app.api.nodes", fromlist=["story_svc"]).story_svc,
            "generate_scene",
            new_callable=AsyncMock,
            return_value=mock_node,
        ):
            resp = await client.post(
                f"/api/stories/{story_id}/nodes",
                json={"user_prompt": "Go north"},
            )
            assert resp.status_code == 201
            assert resp.json()["content"] == "The hero ventured forth."

    async def test_generate_story_not_found(self, client: AsyncClient):
        fake_id = str(uuid.uuid4())
        resp = await client.post(
            f"/api/stories/{fake_id}/nodes",
            json={"user_prompt": "Go north"},
        )
        assert resp.status_code == 404

    async def test_generate_empty_prompt_rejected(self, client: AsyncClient):
        create_resp = await client.post("/api/stories", json={"title": "Empty"})
        story_id = create_resp.json()["id"]
        resp = await client.post(
            f"/api/stories/{story_id}/nodes",
            json={"user_prompt": ""},
        )
        assert resp.status_code == 422


class TestBranch:
    async def test_branch_node_not_found(self, client: AsyncClient):
        fake_id = str(uuid.uuid4())
        resp = await client.post(
            f"/api/nodes/{fake_id}/branch",
            json={"user_prompt": "Try again"},
        )
        assert resp.status_code == 404


class TestGetNode:
    async def test_get_existing_node(self, client: AsyncClient):
        # Create story → root node
        create_resp = await client.post("/api/stories", json={"title": "Node Get"})
        leaf_id = create_resp.json()["current_leaf_id"]

        resp = await client.get(f"/api/nodes/{leaf_id}")
        assert resp.status_code == 200
        assert resp.json()["node_type"] == "root"

    async def test_get_nonexistent(self, client: AsyncClient):
        fake_id = str(uuid.uuid4())
        resp = await client.get(f"/api/nodes/{fake_id}")
        assert resp.status_code == 404


class TestGetNodePath:
    async def test_root_path(self, client: AsyncClient):
        create_resp = await client.post("/api/stories", json={"title": "Path Test"})
        leaf_id = create_resp.json()["current_leaf_id"]

        resp = await client.get(f"/api/nodes/{leaf_id}/path")
        assert resp.status_code == 200
        path = resp.json()
        assert len(path) >= 1
        assert path[0]["node_type"] == "root"


class TestUpdateNode:
    async def test_update_content(self, client: AsyncClient):
        create_resp = await client.post("/api/stories", json={"title": "Edit Test"})
        leaf_id = create_resp.json()["current_leaf_id"]

        with patch.object(
            __import__("app.api.nodes", fromlist=["ollama_svc"]).ollama_svc,
            "create_embedding",
            new_callable=AsyncMock,
            return_value=[0.1] * 768,
        ):
            resp = await client.patch(
                f"/api/nodes/{leaf_id}",
                json={"content": "Edited content here"},
            )
            assert resp.status_code == 200
            assert resp.json()["content"] == "Edited content here"

    async def test_update_nonexistent(self, client: AsyncClient):
        fake_id = str(uuid.uuid4())
        resp = await client.patch(
            f"/api/nodes/{fake_id}",
            json={"content": "Doesn't matter"},
        )
        assert resp.status_code == 404


class TestIllustrateNode:
    async def test_illustrate_root_rejected(self, client: AsyncClient):
        create_resp = await client.post("/api/stories", json={"title": "Illust Test"})
        leaf_id = create_resp.json()["current_leaf_id"]

        resp = await client.post(f"/api/nodes/{leaf_id}/illustrate")
        assert resp.status_code == 400
        assert "root" in resp.json()["detail"].lower()

    async def test_illustrate_nonexistent(self, client: AsyncClient):
        fake_id = str(uuid.uuid4())
        resp = await client.post(f"/api/nodes/{fake_id}/illustrate")
        assert resp.status_code == 404
