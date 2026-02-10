"""WebSocket endpoint for streaming story generation."""

import asyncio
import json
import logging
import uuid

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from sqlalchemy import select

from app.core.database import async_session
from app.core.exceptions import (
    GenerationError,
    ServiceTimeoutError,
    ServiceUnavailableError,
)
from app.models.node import Node
from app.models.story import Story
from app.services.illustration_service import IllustrationService
from app.services.story_service import StoryGenerationService

logger = logging.getLogger(__name__)

router = APIRouter()

story_svc = StoryGenerationService()
illustration_svc = IllustrationService()


def _node_to_dict(node: Node) -> dict:
    """Convert a Node to a JSON-serializable dict matching NodeResponse."""
    d = {
        "id": str(node.id),
        "story_id": str(node.story_id),
        "parent_id": str(node.parent_id) if node.parent_id else None,
        "content": node.content,
        "summary": node.summary,
        "node_type": node.node_type,
        "created_at": node.created_at.isoformat(),
        "beat": node.beat,
        "continuity_warnings": node.continuity_warnings,
        "illustration_path": node.illustration_path,
    }
    return d


def _error_msg(message: str, error_type: str = "error", service: str | None = None) -> dict:
    """Build a structured error message for WebSocket clients."""
    msg = {"type": "error", "message": message, "error_type": error_type}
    if service:
        msg["service"] = service
    return msg


@router.websocket("/ws/generate")
async def websocket_generate(ws: WebSocket):
    await ws.accept()
    logger.info("WebSocket client connected")

    try:
        while True:
            raw = await ws.receive_text()
            try:
                msg = json.loads(raw)
            except json.JSONDecodeError:
                await ws.send_json(_error_msg("Invalid JSON", "parse_error"))
                continue

            action = msg.get("action")
            if action not in ("generate", "branch"):
                await ws.send_json(_error_msg(f"Unknown action: {action}", "invalid_action"))
                continue

            try:
                if action == "generate":
                    await _handle_generate(ws, msg)
                elif action == "branch":
                    await _handle_branch(ws, msg)
            except ServiceUnavailableError as e:
                logger.error("Service unavailable during WS %s: %s", action, e)
                await ws.send_json(_error_msg(str(e), "service_unavailable", e.service))
            except ServiceTimeoutError as e:
                logger.error("Service timeout during WS %s: %s", action, e)
                await ws.send_json(_error_msg(str(e), "service_timeout", e.service))
            except GenerationError as e:
                logger.error("Generation error during WS %s: %s", action, e)
                await ws.send_json(_error_msg(str(e), "generation_error", e.service))
            except Exception as e:
                logger.exception("Unexpected error handling WebSocket action=%s", action)
                await ws.send_json(_error_msg(f"Internal error: {e}", "internal_error"))

    except WebSocketDisconnect:
        logger.info("WebSocket client disconnected")


async def _handle_generate(ws: WebSocket, msg: dict):
    story_id = uuid.UUID(msg["story_id"])
    prompt = msg["prompt"]
    parent_node_id = msg.get("parent_node_id")

    async with async_session() as session:
        # Resolve parent node
        if parent_node_id:
            parent_id = uuid.UUID(parent_node_id)
        else:
            result = await session.execute(
                select(Story).where(Story.id == story_id)
            )
            story = result.scalar_one_or_none()
            if story is None:
                await ws.send_json(_error_msg("Story not found", "not_found"))
                return
            if story.current_leaf_id is None:
                await ws.send_json(_error_msg("Story has no current leaf", "invalid_state"))
                return
            parent_id = story.current_leaf_id

        # Stream generation
        completed_node = None
        async for chunk in story_svc.generate_scene_stream(
            session=session,
            story_id=story_id,
            parent_node_id=parent_id,
            user_prompt=prompt,
        ):
            if isinstance(chunk, dict):
                await ws.send_json({"type": "phase", "phase": chunk["phase"]})
            elif isinstance(chunk, str):
                await ws.send_json({"type": "token", "content": chunk})
            else:
                completed_node = chunk
                await ws.send_json({"type": "complete", "node": _node_to_dict(chunk)})

        # Auto-illustrate if enabled
        if completed_node:
            result = await session.execute(
                select(Story).where(Story.id == story_id)
            )
            story = result.scalar_one_or_none()
            if story and story.auto_illustrate:
                asyncio.create_task(
                    _auto_illustrate_and_notify(ws, completed_node.id, story_id)
                )


async def _handle_branch(ws: WebSocket, msg: dict):
    story_id = uuid.UUID(msg["story_id"])
    node_id = uuid.UUID(msg["node_id"])
    prompt = msg["prompt"]

    async with async_session() as session:
        # Find the reference node's parent
        result = await session.execute(
            select(Node).where(Node.id == node_id)
        )
        ref_node = result.scalar_one_or_none()
        if ref_node is None:
            await ws.send_json(_error_msg("Node not found", "not_found"))
            return
        if ref_node.parent_id is None:
            await ws.send_json(_error_msg("Cannot branch from root node", "invalid_state"))
            return

        # Stream generation from the same parent
        completed_node = None
        async for chunk in story_svc.generate_scene_stream(
            session=session,
            story_id=story_id,
            parent_node_id=ref_node.parent_id,
            user_prompt=prompt,
        ):
            if isinstance(chunk, dict):
                await ws.send_json({"type": "phase", "phase": chunk["phase"]})
            elif isinstance(chunk, str):
                await ws.send_json({"type": "token", "content": chunk})
            else:
                completed_node = chunk
                await ws.send_json({"type": "complete", "node": _node_to_dict(chunk)})

        # Auto-illustrate if enabled
        if completed_node:
            result = await session.execute(
                select(Story).where(Story.id == story_id)
            )
            story = result.scalar_one_or_none()
            if story and story.auto_illustrate:
                asyncio.create_task(
                    _auto_illustrate_and_notify(ws, completed_node.id, story_id)
                )


async def _auto_illustrate_and_notify(
    ws: WebSocket, node_id: uuid.UUID, story_id: uuid.UUID
):
    """Background task: illustrate a scene and notify via WebSocket."""
    try:
        async with async_session() as session:
            result = await session.execute(select(Node).where(Node.id == node_id))
            node = result.scalar_one_or_none()
            if node is None:
                return

            result = await session.execute(
                select(Story).where(Story.id == story_id)
            )
            story = result.scalar_one_or_none()
            if story is None:
                return

            filename = await illustration_svc.illustrate_scene(session, node, story)
            if filename:
                await ws.send_json({
                    "type": "illustration",
                    "node_id": str(node_id),
                    "path": f"/static/images/{filename}",
                })
    except Exception:
        # WebSocket may be closed; swallow silently
        logger.debug("Auto-illustrate notify failed for node=%s", node_id, exc_info=True)
