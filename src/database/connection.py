from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, scoped_session
from sqlalchemy.exc import SQLAlchemyError
import logging
from contextlib import contextmanager

# Assuming models are in src.database.models
from src.database.models import Base
from src.utils.config_loader import ConfigLoader

logger = logging.getLogger(__name__)

# Initialize ConfigLoader to get database URL
config_loader = ConfigLoader()
DATABASE_URL = config_loader.get_setting('DATABASE_URL', 'sqlite:///./data/payroll_monitor.db')
DB_ECHO = config_loader.get_setting('DB_ECHO', False) # For SQLAlchemy logging

engine = None
Session = None

def init_db():
    """Initializes the database engine and creates tables if they don't exist."""
    global engine, Session
    try:
        engine = create_engine(DATABASE_URL, echo=DB_ECHO)
        Base.metadata.create_all(engine)
        Session = scoped_session(sessionmaker(autocommit=False, autoflush=False, bind=engine))
        logger.info(f"Database initialized successfully at {DATABASE_URL}")
    except SQLAlchemyError as e:
        logger.error(f"Error initializing database: {e}")
        raise
    except Exception as e:
        logger.error(f"An unexpected error occurred during database initialization: {e}")
        raise

@contextmanager
def db_session():
    """Provide a transactional scope around a series of operations."""
    if Session is None:
        init_db() # Ensure DB is initialized if not already

    session = Session()
    try:
        yield session
        session.commit()
    except SQLAlchemyError as e:
        session.rollback()
        logger.error(f"Database transaction failed: {e}")
        raise
    except Exception as e:
        session.rollback()
        logger.error(f"An unexpected error occurred during database operation: {e}")
        raise
    finally:
        session.close()