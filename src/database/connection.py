import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, scoped_session
from contextlib import contextmanager
import logging

from src.database.models import Base # Import Base from models

logger = logging.getLogger(__name__)

# Load configuration to get DATABASE_URL
from src.utils.config_loader import ConfigLoader
config_loader = ConfigLoader()
app_config = config_loader.get_config()

DATABASE_URL = os.getenv('DATABASE_URL', app_config.get('database', {}).get('url', 'sqlite:///./data/payroll_monitor.db'))
DB_ECHO = os.getenv('DB_ECHO', 'false').lower() == 'true'

engine = create_engine(DATABASE_URL, echo=DB_ECHO)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
ScopedSession = scoped_session(SessionLocal)

def init_db():
    """Initializes the database by creating all tables."""
    logger.info(f"Initializing database at {DATABASE_URL}...")
    Base.metadata.create_all(bind=engine)
    logger.info("Database tables created.")

@contextmanager
def db_session():
    """Provide a transactional scope around a series of operations."""
    session = ScopedSession()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        ScopedSession.remove()