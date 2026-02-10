import uuid
from datetime import datetime

from sqlalchemy import String, Text, BigInteger, Integer, DateTime, ForeignKey, Index, func
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship
from pgvector.sqlalchemy import Vector

from app.core.database import Base


class WorldBibleEntity(Base):
    __tablename__ = "world_bible"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    story_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("stories.id", ondelete="CASCADE"), index=True
    )
    entity_type: Mapped[str] = mapped_column(
        String(50)
    )  # 'character', 'location', 'prop'
    name: Mapped[str] = mapped_column(String(255))
    description: Mapped[str] = mapped_column(Text)
    base_prompt: Mapped[str] = mapped_column(Text)  # For image generation
    reference_image_path: Mapped[str | None] = mapped_column(
        String(500), nullable=True
    )
    image_seed: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    embedding = mapped_column(Vector(768), nullable=True)
    metadata_: Mapped[dict | None] = mapped_column(
        "metadata", JSONB, nullable=True, default=dict
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    version: Mapped[int] = mapped_column(Integer, default=1)

    # Relationships
    story: Mapped["Story"] = relationship("Story", back_populates="world_bible_entities")

    # HNSW index for vector similarity search
    __table_args__ = (
        Index(
            "ix_world_bible_embedding_hnsw",
            embedding,
            postgresql_using="hnsw",
            postgresql_with={"m": 16, "ef_construction": 64},
            postgresql_ops={"embedding": "vector_cosine_ops"},
        ),
    )

    def __repr__(self) -> str:
        return f"<WorldBibleEntity(id={self.id}, name='{self.name}', type='{self.entity_type}')>"
