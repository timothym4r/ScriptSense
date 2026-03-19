import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import DateTime, ForeignKey, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class CorrectionRecord(Base):
    __tablename__ = "correction_records"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    script_id: Mapped[str] = mapped_column(ForeignKey("scripts.id", ondelete="CASCADE"), nullable=False, index=True)
    scene_id: Mapped[Optional[str]] = mapped_column(
        ForeignKey("scenes.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    block_id: Mapped[Optional[str]] = mapped_column(
        ForeignKey("script_blocks.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    target_type: Mapped[str] = mapped_column(String(20), nullable=False)
    corrected_field: Mapped[str] = mapped_column(String(50), nullable=False)
    old_value: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    new_value: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    script = relationship("Script", back_populates="corrections")
    scene = relationship("Scene")
    block = relationship("ScriptBlock")
