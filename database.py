from sqlalchemy import create_engine
from sqlalchemy.orm import Session

DATABASE_URL = "sqlite:///stepup.db"
engine = create_engine(DATABASE_URL)

def get_session():
    return Session(engine)