"""Factory helpers for building test objects."""

import uuid
from datetime import datetime, timezone

from app.models.story import Story
from app.models.node import Node
from app.models.world_bible import WorldBibleEntity


def make_story(
    *,
    title: str = "Test Story",
    genre: str | None = "fantasy",
    content_mode: str = "unrestricted",
    auto_illustrate: bool = False,
    context_depth: int = 5,
    id: uuid.UUID | None = None,
) -> Story:
    story = Story(
        title=title,
        genre=genre,
        content_mode=content_mode,
        auto_illustrate=auto_illustrate,
        context_depth=context_depth,
    )
    if id:
        story.id = id
    return story


def make_node(
    *,
    story_id: uuid.UUID,
    parent_id: uuid.UUID | None = None,
    content: str = "Test scene content.",
    node_type: str = "scene",
    summary: str | None = None,
    metadata_: dict | None = None,
    embedding: list[float] | None = None,
    id: uuid.UUID | None = None,
) -> Node:
    node = Node(
        story_id=story_id,
        parent_id=parent_id,
        content=content,
        node_type=node_type,
        summary=summary,
        metadata_=metadata_,
        embedding=embedding,
    )
    if id:
        node.id = id
    return node


def make_entity(
    *,
    story_id: uuid.UUID,
    name: str = "Alice",
    entity_type: str = "character",
    description: str = "A brave adventurer.",
    base_prompt: str = "young woman, adventurer, fantasy setting",
    reference_image_path: str | None = None,
    embedding: list[float] | None = None,
    id: uuid.UUID | None = None,
) -> WorldBibleEntity:
    entity = WorldBibleEntity(
        story_id=story_id,
        name=name,
        entity_type=entity_type,
        description=description,
        base_prompt=base_prompt,
        reference_image_path=reference_image_path,
        embedding=embedding,
    )
    if id:
        entity.id = id
    return entity


def make_beat(
    *,
    setting: str = "A dark forest",
    characters: list[str] | None = None,
    events: list[str] | None = None,
    tone: str = "mysterious",
    continuity_notes: str = "",
    continuity_warnings: list[str] | None = None,
) -> dict:
    return {
        "setting": setting,
        "characters_present": characters or ["Alice"],
        "key_events": events or ["Alice enters the forest"],
        "emotional_tone": tone,
        "continuity_notes": continuity_notes,
        "continuity_warnings": continuity_warnings or [],
    }


def fake_embedding(dim: int = 768) -> list[float]:
    """Generate a deterministic fake embedding vector."""
    return [0.01 * (i % 100) for i in range(dim)]
