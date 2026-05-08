from sqlalchemy import create_engine, Column, String, Float, Integer, Boolean, DateTime
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from datetime import datetime
import os

# Use PostgreSQL in production, SQLite in development
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./sentinel.db")

# PostgreSQL connection
if DATABASE_URL.startswith("postgresql"):
    engine = create_engine(DATABASE_URL)
else:
    # SQLite connection (local development)
    engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True)
    email = Column(String, unique=True, index=True)
    hashed_password = Column(String, nullable=True)
    google_id = Column(String, unique=True, nullable=True, index=True)
    google_access_token = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)


class ActivityLog(Base):
    __tablename__ = "activity_logs"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, index=True, nullable=True)
    action = Column(String, index=True)  # login, logout, classify, batch, export, etc.
    details = Column(String, nullable=True)
    ip_address = Column(String, nullable=True)
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)
    status = Column(String, default="success")  # success, failed


class ClassificationLog(Base):
    __tablename__ = "classification_logs"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, index=True, nullable=True)
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)
    email_hash = Column(String, index=True, nullable=True)  # For caching duplicate emails
    email_snippet = Column(String, index=True)
    label = Column(String, index=True)
    confidence = Column(Float, index=True)
    reasoning = Column(String)
    latency_ms = Column(Float)
    tokens_used = Column(Integer)
    success = Column(Boolean, index=True)
    error_message = Column(String, nullable=True)
    gmail_message_id = Column(String, nullable=True, index=True)


def init_db():
    Base.metadata.create_all(bind=engine)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
