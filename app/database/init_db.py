from app.database.database import Base
from app.database.session import engine


def init_db() -> None:
    Base.metadata.create_all(bind=engine)