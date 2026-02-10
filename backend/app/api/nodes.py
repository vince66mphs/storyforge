import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.schemas import (
    GenerateSceneRequest,
    BranchRequest,
    NodeUpdate,
    NodeResponse,
)
from app.core.database import get_session
from app.models.node import Node
from app.models.story import Story
from app.services.story_service import StoryGenerationService

router = APIRouter(tags=["nodes"])

story_svc = StoryGenerationService()


@router.post(
    "/api/stories/{story_id}/nodes",
    response_model=NodeResponse,
    status_code=201,
)
async def generate_scene(
    story_id: uuid.UUID,
    body: GenerateSceneRequest,
    session: AsyncSession = Depends(get_session),
):
    """Generate the next scene from the story's current leaf node."""
    result = await session.execute(select(Story).where(Story.id == story_id))
    story = result.scalar_one_or_none()
    if story is None:
        raise HTTPException(status_code=404, detail="Story not found")
    if story.current_leaf_id is None:
        raise HTTPException(status_code=400, detail="Story has no current leaf node")

    node = await story_svc.generate_scene(
        session=session,
        story_id=story_id,
        parent_node_id=story.current_leaf_id,
        user_prompt=body.user_prompt,
    )
    return node


@router.post(
    "/api/nodes/{node_id}/branch",
    response_model=NodeResponse,
    status_code=201,
)
async def create_branch(
    node_id: uuid.UUID,
    body: BranchRequest,
    session: AsyncSession = Depends(get_session),
):
    """Create an alternative branch (sibling) from the same parent as the given node."""
    result = await session.execute(select(Node).where(Node.id == node_id))
    node = result.scalar_one_or_none()
    if node is None:
        raise HTTPException(status_code=404, detail="Node not found")

    try:
        branch = await story_svc.create_branch(
            session=session,
            node_id=node_id,
            user_prompt=body.user_prompt,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    return branch


@router.get("/api/nodes/{node_id}", response_model=NodeResponse)
async def get_node(
    node_id: uuid.UUID,
    session: AsyncSession = Depends(get_session),
):
    """Get a single node by ID."""
    result = await session.execute(select(Node).where(Node.id == node_id))
    node = result.scalar_one_or_none()
    if node is None:
        raise HTTPException(status_code=404, detail="Node not found")
    return node


@router.get("/api/nodes/{node_id}/path", response_model=list[NodeResponse])
async def get_node_path(
    node_id: uuid.UUID,
    session: AsyncSession = Depends(get_session),
):
    """Get the path from root to this node (ordered root-first)."""
    path: list[Node] = []
    current_id = node_id

    while current_id is not None:
        result = await session.execute(select(Node).where(Node.id == current_id))
        node = result.scalar_one_or_none()
        if node is None:
            break
        path.append(node)
        current_id = node.parent_id

    path.reverse()
    return path


@router.patch("/api/nodes/{node_id}", response_model=NodeResponse)
async def update_node(
    node_id: uuid.UUID,
    body: NodeUpdate,
    session: AsyncSession = Depends(get_session),
):
    """Manually edit a node's content."""
    result = await session.execute(select(Node).where(Node.id == node_id))
    node = result.scalar_one_or_none()
    if node is None:
        raise HTTPException(status_code=404, detail="Node not found")

    node.content = body.content
    await session.commit()
    await session.refresh(node)
    return node
