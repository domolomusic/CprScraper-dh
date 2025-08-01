import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from dotenv import load_dotenv
from src.database.models import Base

# Load environment variables from .env file
load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./data/payroll_monitor.db")
DB_ECHO = os.getenv("DB_ECHO", "false").lower() == "true"

engine = create_engine(DATABASE_URL, echo=DB_ECHO)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def init_db():
    """Initializes the database by creating all tables."""
    Base.metadata.create_all(bind=engine)
    print(f"Database initialized at {DATABASE_URL}")

def get_db():
    """Dependency to get a database session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

if __name__ == '__main__':
    # This block allows you to run this file directly to initialize the database
    # For example: python src/database/connection.py
    print("Attempting to initialize database...")
    init_db()
    print("Database initialization complete.")