from sqlalchemy import create_engine, Column, String, Float, Integer, Boolean, DateTime, ForeignKey, Index
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from datetime import datetime
import os

# Use PostgreSQL in production, SQLite in development
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./sentinel.db")

# PostgreSQL connection
if DATABASE_URL.startswith("postgresql"):
    engine = create_engine(DATABASE_URL, pool_pre_ping=True)
else:
    # SQLite connection (local development)
    engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), unique=True, index=True)
    email = Column(String(255), unique=True, index=True)
    hashed_password = Column(String, nullable=True)
    google_id = Column(String, unique=True, nullable=True, index=True)
    google_access_token = Column(String, nullable=True)
    role = Column(String(20), default="user", index=True)
    created_at = Column(DateTime, default=datetime.utcnow, index=True)

    classifications = relationship("ClassificationLog", back_populates="user", cascade="all, delete-orphan")
    activity_logs = relationship("ActivityLog", back_populates="user", cascade="all, delete-orphan")


class ActivityLog(Base):
    __tablename__ = "activity_logs"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=True)
    action = Column(String(50), index=True)
    details = Column(String, nullable=True)
    ip_address = Column(String(45), nullable=True)
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)
    status = Column(String(20), default="success")

    user = relationship("User", back_populates="activity_logs")

    __table_args__ = (
        # Composite indexes for activity queries
        Index('ix_user_action', 'user_id', 'action'),
        Index('ix_user_timestamp_activity', 'user_id', 'timestamp'),
        Index('ix_action_status', 'action', 'status'),
    )


class ClassificationLog(Base):
    __tablename__ = "classification_logs"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=True)
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)
    email_hash = Column(String(64), index=True, nullable=True)
    email_snippet = Column(String(200))
    label = Column(String(20), index=True)
    confidence = Column(Float)
    reasoning = Column(String)
    latency_ms = Column(Float)
    tokens_used = Column(Integer)
    success = Column(Boolean, index=True)
    error_message = Column(String, nullable=True)
    gmail_message_id = Column(String, nullable=True, index=True)
    model = Column(String(50), default="llama-3.1-70b-instruct")
    prompt_version = Column(String(10), default="v2")

    user = relationship("User", back_populates="classifications")

    __table_args__ = (
        # Composite indexes for common queries
        Index('ix_user_timestamp', 'user_id', 'timestamp'),
        Index('ix_user_label', 'user_id', 'label'),
        Index('ix_user_success', 'user_id', 'success'),
        Index('ix_label_timestamp', 'label', 'timestamp'),
        Index('ix_email_hash_user', 'email_hash', 'user_id'),
    )


class ClassificationFeedback(Base):
    __tablename__ = "classification_feedback"

    id = Column(Integer, primary_key=True, index=True)
    classification_id = Column(Integer, ForeignKey("classification_logs.id", ondelete="CASCADE"), index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), index=True)
    is_correct = Column(Boolean, nullable=True)
    correct_label = Column(String(20), nullable=True)
    feedback_text = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, index=True)

    __table_args__ = (
        Index('ix_user_classification', 'user_id', 'classification_id'),
        Index('ix_user_feedback_date', 'user_id', 'created_at'),
    )


def init_db():
    Base.metadata.create_all(bind=engine)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
