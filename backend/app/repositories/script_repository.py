from typing import Optional

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.db.models.scene import Scene
from app.db.models.script import Script


class ScriptRepository:
    def create(self, session: Session, script: Script) -> Script:
        session.add(script)
        session.flush()
        session.refresh(script)
        return script

    def list(self, session: Session) -> list[Script]:
        stmt = (
            select(Script)
            .options(
                selectinload(Script.scenes).selectinload(Scene.blocks),
                selectinload(Script.blocks),
            )
            .order_by(Script.created_at.desc())
        )
        return session.scalars(stmt).unique().all()

    def get(self, session: Session, script_id: str) -> Optional[Script]:
        stmt = (
            select(Script)
            .where(Script.id == script_id)
            .options(
                selectinload(Script.scenes).selectinload(Scene.blocks),
                selectinload(Script.blocks),
            )
        )
        return session.scalars(stmt).unique().one_or_none()
