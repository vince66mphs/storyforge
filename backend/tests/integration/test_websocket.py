"""Integration tests for WebSocket generation endpoint."""

import json
import uuid
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime, timezone

import pytest

from app.core.exceptions import ModelNotFoundError
from app.main import app
from app.models.node import Node


class TestWebSocketGenerate:
    def test_invalid_json(self):
        """WebSocket should handle invalid JSON gracefully."""
        from starlette.testclient import TestClient

        with TestClient(app) as tc:
            with tc.websocket_connect("/ws/generate") as ws:
                ws.send_text("not json")
                msg = ws.receive_json()
                assert msg["type"] == "error"
                assert msg["error_type"] == "parse_error"

    def test_unknown_action(self):
        from starlette.testclient import TestClient

        with TestClient(app) as tc:
            with tc.websocket_connect("/ws/generate") as ws:
                ws.send_json({"action": "unknown"})
                msg = ws.receive_json()
                assert msg["type"] == "error"
                assert msg["error_type"] == "invalid_action"

    def test_generate_stream(self, client):
        """Test streaming generation via WebSocket with mocked service."""
        from starlette.testclient import TestClient

        story_id = str(uuid.uuid4())
        parent_id = str(uuid.uuid4())

        # Build a mock node for the final result
        final_node = Node(
            story_id=uuid.UUID(story_id),
            parent_id=uuid.UUID(parent_id),
            content="Streamed content",
            node_type="scene",
        )
        final_node.id = uuid.uuid4()
        final_node.created_at = datetime.now(timezone.utc)
        final_node.summary = None
        final_node.metadata_ = None

        # Mock Story lookup inside _handle_generate
        mock_story = MagicMock()
        mock_story.id = uuid.UUID(story_id)
        mock_story.current_leaf_id = uuid.UUID(parent_id)
        mock_story.auto_illustrate = False

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_story

        async def mock_stream(*args, **kwargs):
            yield {"phase": "planning"}
            yield {"phase": "writing"}
            yield "Hello "
            yield "world"
            yield final_node

        ws_module = __import__("app.api.websocket", fromlist=["story_svc"])

        with patch.object(
            ws_module.story_svc, "generate_scene_stream", side_effect=mock_stream
        ), patch("app.api.websocket.async_session") as mock_session_maker:
            # Mock the async session context manager
            mock_session = AsyncMock()
            mock_session.execute.return_value = mock_result
            mock_session.__aenter__ = AsyncMock(return_value=mock_session)
            mock_session.__aexit__ = AsyncMock(return_value=False)
            mock_session_maker.return_value = mock_session

            with TestClient(app) as tc:
                with tc.websocket_connect("/ws/generate") as ws:
                    ws.send_json({
                        "action": "generate",
                        "story_id": story_id,
                        "prompt": "Go north",
                        "parent_node_id": parent_id,
                    })
                    messages = []
                    for _ in range(5):  # planning, writing, 2 tokens, complete
                        msg = ws.receive_json()
                        messages.append(msg)

                    types = [m["type"] for m in messages]
                    assert "phase" in types
                    assert "token" in types
                    assert "complete" in types

    def test_generate_story_not_found(self):
        """WebSocket should return error for missing story."""
        from starlette.testclient import TestClient

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None

        with patch("app.api.websocket.async_session") as mock_session_maker:
            mock_session = AsyncMock()
            mock_session.execute.return_value = mock_result
            mock_session.__aenter__ = AsyncMock(return_value=mock_session)
            mock_session.__aexit__ = AsyncMock(return_value=False)
            mock_session_maker.return_value = mock_session

            with TestClient(app) as tc:
                with tc.websocket_connect("/ws/generate") as ws:
                    ws.send_json({
                        "action": "generate",
                        "story_id": str(uuid.uuid4()),
                        "prompt": "Go north",
                    })
                    msg = ws.receive_json()
                    assert msg["type"] == "error"
                    assert msg["error_type"] == "not_found"

    def test_model_not_found_ws_error(self):
        """WebSocket should send model_not_found error type."""
        from starlette.testclient import TestClient

        story_id = str(uuid.uuid4())
        parent_id = str(uuid.uuid4())

        mock_story = MagicMock()
        mock_story.id = uuid.UUID(story_id)
        mock_story.current_leaf_id = uuid.UUID(parent_id)

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_story

        ws_module = __import__("app.api.websocket", fromlist=["story_svc"])

        with patch.object(
            ws_module.story_svc,
            "generate_scene_stream",
            side_effect=ModelNotFoundError("bogus-model:latest"),
        ), patch("app.api.websocket.async_session") as mock_session_maker:
            mock_session = AsyncMock()
            mock_session.execute.return_value = mock_result
            mock_session.__aenter__ = AsyncMock(return_value=mock_session)
            mock_session.__aexit__ = AsyncMock(return_value=False)
            mock_session_maker.return_value = mock_session

            with TestClient(app) as tc:
                with tc.websocket_connect("/ws/generate") as ws:
                    ws.send_json({
                        "action": "generate",
                        "story_id": story_id,
                        "prompt": "Go north",
                        "parent_node_id": parent_id,
                    })
                    msg = ws.receive_json()
                    assert msg["type"] == "error"
                    assert msg["error_type"] == "model_not_found"
                    assert "bogus-model" in msg["message"]

    def test_branch_node_not_found(self):
        from starlette.testclient import TestClient

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None

        with patch("app.api.websocket.async_session") as mock_session_maker:
            mock_session = AsyncMock()
            mock_session.execute.return_value = mock_result
            mock_session.__aenter__ = AsyncMock(return_value=mock_session)
            mock_session.__aexit__ = AsyncMock(return_value=False)
            mock_session_maker.return_value = mock_session

            with TestClient(app) as tc:
                with tc.websocket_connect("/ws/generate") as ws:
                    ws.send_json({
                        "action": "branch",
                        "story_id": str(uuid.uuid4()),
                        "node_id": str(uuid.uuid4()),
                        "prompt": "Try again",
                    })
                    msg = ws.receive_json()
                    assert msg["type"] == "error"
                    assert msg["error_type"] == "not_found"
