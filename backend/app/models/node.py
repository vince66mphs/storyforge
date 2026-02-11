import uuid
from datetime import datetime

from sqlalchemy import String, Text, DateTime, ForeignKey, Index, func
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship
from pgvector.sqlalchemy import Vector

from app.core.database import Base


class Node(Base):
    __tablename__ = "nodes"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    story_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("stories.id", ondelete="CASCADE"), index=True
    )
    parent_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("nodes.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    content: Mapped[str] = mapped_column(Text)
    summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    embedding = mapped_column(Vector(768), nullable=True)
    node_type: Mapped[str] = mapped_column(
        String(20), default="scene"
    )  # 'root', 'scene', 'choice'
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    metadata_: Mapped[dict | None] = mapped_column(
        "metadata", JSONB, nullable=True, default=dict
    )

    # Relationships
    story: Mapped["Story"] = relationship(
        "Story", back_populates="nodes", foreign_keys=[story_id]
    )
    parent: Mapped["Node | None"] = relationship(
        "Node", remote_side=[id], back_populates="children", foreign_keys=[parent_id]
    )
    children: Mapped[list["Node"]] = relationship(
        "Node", back_populates="parent", foreign_keys=[parent_id]
    )

    # HNSW index for vector similarity search
    __table_args__ = (
        Index(
            "ix_nodes_embedding_hnsw",
            embedding,
            postgresql_using="hnsw",
            postgresql_with={"m": 16, "ef_construction": 64},
            postgresql_ops={"embedding": "vector_cosine_ops"},
        ),
    )

    @property
    def beat(self) -> dict | None:
        """Extract the planner beat from metadata, if present."""
        if self.metadata_:
            return self.metadata_.get("beat")
        return None

    @property
    def illustration_path(self) -> str | None:
        """Extract the illustration image path from metadata, if present."""
        if self.metadata_:
            return self.metadata_.get("illustration_path")
        return None

    @property
    def continuity_warnings(self) -> list[str]:
        """Extract continuity warnings from metadata."""
        if self.metadata_:
            return self.metadata_.get("continuity_warnings", [])
        return []

    @property
    def unknown_characters(self) -> list[dict]:
        """Extract unknown character data from the beat, if present."""
        if self.metadata_:
            beat = self.metadata_.get("beat")
            if beat:
                return beat.get("unknown_characters", [])
        return []

    def __repr__(self) -> str:
        return f"<Node(id={self.id}, type='{self.node_type}', story_id={self.story_id})>"
