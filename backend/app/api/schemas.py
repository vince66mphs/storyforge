import uuid
from datetime import datetime

from pydantic import BaseModel, Field


# ── Story ──────────────────────────────────────────────────────────────

class StoryCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=255)
    genre: str | None = Field(None, max_length=100)
    content_mode: str = Field("unrestricted", pattern=r"^(unrestricted|safe)$")


class StoryUpdate(BaseModel):
    content_mode: str | None = Field(None, pattern=r"^(unrestricted|safe)$")
    auto_illustrate: bool | None = None
    context_depth: int | None = Field(None, ge=1, le=20)


class StoryResponse(BaseModel):
    id: uuid.UUID
    title: str
    genre: str | None
    content_mode: str
    auto_illustrate: bool
    context_depth: int
    created_at: datetime
    updated_at: datetime
    current_leaf_id: uuid.UUID | None

    model_config = {"from_attributes": True}


# ── Node ───────────────────────────────────────────────────────────────

class GenerateSceneRequest(BaseModel):
    user_prompt: str = Field(..., min_length=1)


class BranchRequest(BaseModel):
    user_prompt: str = Field(..., min_length=1)


class NodeUpdate(BaseModel):
    content: str = Field(..., min_length=1)


class NodeResponse(BaseModel):
    id: uuid.UUID
    story_id: uuid.UUID
    parent_id: uuid.UUID | None
    content: str
    summary: str | None
    node_type: str
    created_at: datetime

    model_config = {"from_attributes": True}


# ── Entity ─────────────────────────────────────────────────────────────

class EntityCreate(BaseModel):
    entity_type: str = Field(..., pattern=r"^(character|location|prop)$")
    name: str = Field(..., min_length=1, max_length=255)
    description: str = Field(..., min_length=1)
    base_prompt: str = Field(..., min_length=1)


class EntityUpdate(BaseModel):
    description: str | None = None
    base_prompt: str | None = None


class EntityResponse(BaseModel):
    id: uuid.UUID
    story_id: uuid.UUID
    entity_type: str
    name: str
    description: str
    base_prompt: str
    reference_image_path: str | None
    image_seed: int | None
    version: int
    created_at: datetime

    model_config = {"from_attributes": True}


class DetectEntitiesRequest(BaseModel):
    text: str = Field(..., min_length=1)
