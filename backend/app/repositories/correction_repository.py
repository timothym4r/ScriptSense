from sqlalchemy.orm import Session

from app.db.models.correction import CorrectionRecord


class CorrectionRepository:
    def create(self, session: Session, correction: CorrectionRecord) -> CorrectionRecord:
        session.add(correction)
        session.flush()
        session.refresh(correction)
        return correction
