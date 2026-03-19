from app.db.base import Base
from app.db.models import Script, Scene, ScriptBlock  # noqa: F401
from app.db.session import engine


def init_db() -> None:
    Base.metadata.create_all(bind=engine)


if __name__ == "__main__":
    init_db()
