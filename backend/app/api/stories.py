import uuid

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import Response
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.schemas import (
    ContinuityCheckResponse,
    NodeResponse,
    StoryCreate,
    StoryResponse,
    StoryUpdate,
)
from app.core.database import get_session
from app.models.node import Node
from app.models.story import Story
from app.models.world_bible import WorldBibleEntity
from app.services.planner_service import PlannerService
from app.services.text_utils import clean_model_output

router = APIRouter(prefix="/api/stories", tags=["stories"])

planner_svc = PlannerService()


@router.post("", response_model=StoryResponse, status_code=201)
async def create_story(
    body: StoryCreate,
    session: AsyncSession = Depends(get_session),
):
    """Create a new story with an initial root node."""
    story = Story(title=body.title, genre=body.genre, content_mode=body.content_mode)
    session.add(story)
    await session.flush()

    root = Node(
        story_id=story.id,
        content=f"[Beginning of '{body.title}']",
        node_type="root",
    )
    session.add(root)
    await session.flush()

    story.current_leaf_id = root.id
    await session.commit()
    await session.refresh(story)
    return story


@router.get("", response_model=list[StoryResponse])
async def list_stories(
    session: AsyncSession = Depends(get_session),
):
    """List all stories."""
    result = await session.execute(select(Story).order_by(Story.created_at.desc()))
    return result.scalars().all()


@router.get("/{story_id}", response_model=StoryResponse)
async def get_story(
    story_id: uuid.UUID,
    session: AsyncSession = Depends(get_session),
):
    """Get a story by ID."""
    result = await session.execute(select(Story).where(Story.id == story_id))
    story = result.scalar_one_or_none()
    if story is None:
        raise HTTPException(status_code=404, detail="Story not found")
    return story


@router.patch("/{story_id}", response_model=StoryResponse)
async def update_story(
    story_id: uuid.UUID,
    body: StoryUpdate,
    session: AsyncSession = Depends(get_session),
):
    """Update story settings (content mode, auto-illustrate, context depth)."""
    result = await session.execute(select(Story).where(Story.id == story_id))
    story = result.scalar_one_or_none()
    if story is None:
        raise HTTPException(status_code=404, detail="Story not found")

    update_data = body.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(story, field, value)

    await session.commit()
    await session.refresh(story)
    return story


@router.get("/{story_id}/tree", response_model=list[NodeResponse])
async def get_story_tree(
    story_id: uuid.UUID,
    session: AsyncSession = Depends(get_session),
):
    """Get all nodes for a story (the full narrative DAG)."""
    result = await session.execute(
        select(Story).where(Story.id == story_id)
    )
    if result.scalar_one_or_none() is None:
        raise HTTPException(status_code=404, detail="Story not found")

    result = await session.execute(
        select(Node)
        .where(Node.story_id == story_id)
        .order_by(Node.created_at)
    )
    return result.scalars().all()


@router.delete("/{story_id}", status_code=204)
async def delete_story(
    story_id: uuid.UUID,
    session: AsyncSession = Depends(get_session),
):
    """Delete a story and all its nodes and entities."""
    result = await session.execute(select(Story).where(Story.id == story_id))
    story = result.scalar_one_or_none()
    if story is None:
        raise HTTPException(status_code=404, detail="Story not found")

    # Clear circular FK before deleting
    story.current_leaf_id = None
    await session.flush()

    await session.delete(story)
    await session.commit()


@router.get("/{story_id}/export/markdown")
async def export_story_markdown(
    story_id: uuid.UUID,
    session: AsyncSession = Depends(get_session),
):
    """Export story as a markdown file download."""
    result = await session.execute(select(Story).where(Story.id == story_id))
    story = result.scalar_one_or_none()
    if story is None:
        raise HTTPException(status_code=404, detail="Story not found")

    if story.current_leaf_id is None:
        raise HTTPException(status_code=400, detail="Story has no content to export")

    # Walk from current leaf to root
    path_nodes: list[Node] = []
    current_id = story.current_leaf_id
    while current_id is not None:
        result = await session.execute(select(Node).where(Node.id == current_id))
        node = result.scalar_one_or_none()
        if node is None:
            break
        path_nodes.append(node)
        current_id = node.parent_id
    path_nodes.reverse()

    # Get entities
    result = await session.execute(
        select(WorldBibleEntity)
        .where(WorldBibleEntity.story_id == story_id)
        .order_by(WorldBibleEntity.entity_type, WorldBibleEntity.name)
    )
    entities = list(result.scalars().all())

    # Build markdown
    lines = [f"# {story.title}\n"]
    if story.genre:
        lines.append(f"*Genre: {story.genre}*\n")
    lines.append("")

    if entities:
        lines.append("## World Bible\n")
        for e in entities:
            lines.append(f"### {e.name} ({e.entity_type})\n")
            lines.append(f"{e.description}\n")
            if e.reference_image_path:
                lines.append(f"![{e.name}](/static/images/{e.reference_image_path})\n")
            lines.append("")

    lines.append("## Story\n")
    scene_num = 0
    for node in path_nodes:
        if node.node_type == "root":
            continue
        scene_num += 1
        lines.append(f"### Scene {scene_num}\n")
        lines.append(f"{clean_model_output(node.content)}\n")
        lines.append("---\n")

    content = "\n".join(lines)
    safe_title = "".join(c if c.isalnum() or c in " -_" else "" for c in story.title)
    filename = f"{safe_title}.md"

    return Response(
        content=content,
        media_type="text/markdown",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.post("/{story_id}/check-continuity", response_model=ContinuityCheckResponse)
async def check_continuity(
    story_id: uuid.UUID,
    session: AsyncSession = Depends(get_session),
):
    """Analyze story scenes for continuity issues."""
    result = await session.execute(select(Story).where(Story.id == story_id))
    story = result.scalar_one_or_none()
    if story is None:
        raise HTTPException(status_code=404, detail="Story not found")

    if story.current_leaf_id is None:
        raise HTTPException(status_code=400, detail="Story has no content to check")

    # Walk from current leaf to root
    path_nodes: list[Node] = []
    current_id = story.current_leaf_id
    while current_id is not None:
        result = await session.execute(select(Node).where(Node.id == current_id))
        node = result.scalar_one_or_none()
        if node is None:
            break
        path_nodes.append(node)
        current_id = node.parent_id
    path_nodes.reverse()

    # Build scenes list (skip root)
    scenes = []
    scene_num = 0
    for node in path_nodes:
        if node.node_type == "root":
            continue
        scene_num += 1
        scenes.append({"number": scene_num, "content": node.content})

    if not scenes:
        return ContinuityCheckResponse(issues=[], scene_count=0)

    # Load world bible entities
    result = await session.execute(
        select(WorldBibleEntity)
        .where(WorldBibleEntity.story_id == story_id)
    )
    entities = list(result.scalars().all())
    wb = [
        {"name": e.name, "type": e.entity_type, "description": e.description}
        for e in entities
    ]

    issues = await planner_svc.check_continuity(scenes, wb)
    return ContinuityCheckResponse(issues=issues, scene_count=len(scenes))
