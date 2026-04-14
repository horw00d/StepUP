from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import NullPool  # import NullPool

# add connect_args and poolclass to engine:
engine = create_engine(
    "sqlite:///stepup.db",
    connect_args={"check_same_thread": False},  # fixes Flask threading
    poolclass=NullPool,  # prevents connection lockups
)


def get_session():
    return Session(engine)
