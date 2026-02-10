import uuid
from datetime import datetime

from sqlalchemy import Boolean, Integer, String, DateTime, ForeignKey, func
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class Story(Base):
    __tablename__ = "stories"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    title: Mapped[str] = mapped_column(String(255))
    genre: Mapped[str | None] = mapped_column(String(100), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
    current_leaf_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("nodes.id", use_alter=True),
        nullable=True,
    )
    content_mode: Mapped[str] = mapped_column(
        String(20), default="unrestricted", server_default="unrestricted"
    )
    auto_illustrate: Mapped[bool] = mapped_column(
        Boolean, default=False, server_default="false"
    )
    context_depth: Mapped[int] = mapped_column(
        Integer, default=5, server_default="5"
    )
    metadata_: Mapped[dict | None] = mapped_column(
        "metadata", JSONB, nullable=True, default=dict
    )

    # Relationships
    nodes: Mapped[list["Node"]] = relationship(
        "Node",
        back_populates="story",
        foreign_keys="Node.story_id",
        cascade="all, delete-orphan",
    )
    world_bible_entities: Mapped[list["WorldBibleEntity"]] = relationship(
        "WorldBibleEntity", back_populates="story", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<Story(id={self.id}, title='{self.title}')>"
