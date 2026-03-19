import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import DateTime, Integer, String, Text, func
from sqlalchemy import JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class Script(Base):
    __tablename__ = "scripts"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    title: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    raw_text: Mapped[str] = mapped_column(Text, nullable=False)
    total_scenes: Mapped[int] = mapped_column(Integer, nullable=False)
    total_elements: Mapped[int] = mapped_column(Integer, nullable=False)
    warnings: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    scenes = relationship(
        "Scene",
        back_populates="script",
        cascade="all, delete-orphan",
        order_by="Scene.scene_number",
    )
    blocks = relationship(
        "ScriptBlock",
        back_populates="script",
        cascade="all, delete-orphan",
        order_by="ScriptBlock.global_element_index",
    )
