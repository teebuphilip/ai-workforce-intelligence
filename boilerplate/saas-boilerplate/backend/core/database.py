"""
Backend Core - Database Module
Provides SQLAlchemy ORM setup and utilities
"""

import os
from typing import Generator
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
import logging

logger = logging.getLogger(__name__)

# Database URL from environment or default to SQLite
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "sqlite:///./saas_boilerplate.db"
)

# For PostgreSQL in production, use:
# postgresql://user:password@localhost/dbname

# Create engine
# SQLite needs check_same_thread=False
connect_args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}

engine = create_engine(
    DATABASE_URL,
    connect_args=connect_args,
    echo=os.getenv("SQL_ECHO", "false").lower() == "true"  # Log SQL queries if enabled
)

# Session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Base class for models
Base = declarative_base()


def get_db() -> Generator[Session, None, None]:
    """
    Dependency for FastAPI routes.
    Provides a database session and ensures it's closed after use.
    
    Usage in routes:
        @router.get("/items")
        def get_items(db: Session = Depends(get_db)):
            return db.query(Item).all()
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    """
    Initialize database - create all tables.
    Call this on application startup.
    """
    logger.info(f"Initializing database: {DATABASE_URL}")
    Base.metadata.create_all(bind=engine)
    logger.info("Database tables created successfully")


def drop_db():
    """
    Drop all tables - USE WITH CAUTION!
    Only for development/testing.
    """
    logger.warning("Dropping all database tables")
    Base.metadata.drop_all(bind=engine)
    logger.warning("All tables dropped")


def reset_db():
    """
    Reset database - drop and recreate all tables.
    Only for development/testing.
    """
    drop_db()
    init_db()


# Example Model
"""
from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime
from core.database import Base

class User(Base):
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    auth0_id = Column(String, unique=True, index=True)
    name = Column(String)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    subscriptions = relationship("Subscription", back_populates="user")


class Subscription(Base):
    __tablename__ = "subscriptions"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    stripe_subscription_id = Column(String, unique=True, index=True)
    plan_id = Column(String)
    status = Column(String)  # active, canceled, past_due
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    user = relationship("User", back_populates="subscriptions")
"""

# Example Route Usage
"""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from core.database import get_db
from models import User

router = APIRouter()

@router.get("/users")
def list_users(db: Session = Depends(get_db)):
    users = db.query(User).all()
    return users

@router.post("/users")
def create_user(email: str, name: str, db: Session = Depends(get_db)):
    user = User(email=email, name=name)
    db.add(user)
    db.commit()
    db.refresh(user)
    return user

@router.get("/users/{user_id}")
def get_user(user_id: int, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user

@router.delete("/users/{user_id}")
def delete_user(user_id: int, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    db.delete(user)
    db.commit()
    return {"deleted": True}
"""
