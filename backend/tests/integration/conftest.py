"""Integration test fixtures — real DB, sample data."""

import uuid

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.story import Story
from app.models.node import Node
from app.models.world_bible import WorldBibleEntity
from tests.factories import fake_embedding


@pytest.fixture
async def sample_story(db_session: AsyncSession) -> Story:
    """Create a story with a root node in the test DB."""
    story = Story(title="Integration Test Story", genre="fantasy", content_mode="unrestricted")
    db_session.add(story)
    await db_session.flush()

    root = Node(
        story_id=story.id,
        content="[Beginning of 'Integration Test Story']",
        node_type="root",
    )
    db_session.add(root)
    await db_session.flush()

    story.current_leaf_id = root.id
    await db_session.flush()

    return story


@pytest.fixture
async def sample_story_with_scene(db_session: AsyncSession, sample_story: Story) -> tuple[Story, Node]:
    """Story with root + one scene node."""
    scene = Node(
        story_id=sample_story.id,
        parent_id=sample_story.current_leaf_id,
        content="The hero enters a dark cave.",
        node_type="scene",
        summary="Hero enters cave",
        embedding=fake_embedding(),
    )
    db_session.add(scene)
    await db_session.flush()

    sample_story.current_leaf_id = scene.id
    await db_session.flush()

    return sample_story, scene


@pytest.fixture
async def sample_entity(db_session: AsyncSession, sample_story: Story) -> WorldBibleEntity:
    """Create a world bible entity for the sample story."""
    entity = WorldBibleEntity(
        story_id=sample_story.id,
        name="Alice",
        entity_type="character",
        description="A brave adventurer with silver hair",
        base_prompt="young woman, silver hair, adventurer, fantasy setting",
        embedding=fake_embedding(),
    )
    db_session.add(entity)
    await db_session.flush()
    return entity
