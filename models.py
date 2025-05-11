from sqlalchemy import (
    Column, Integer, BigInteger, ForeignKey,
    DateTime, Boolean
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from db_base import Base

class User(Base):
    __tablename__ = "users"
    id           = Column(Integer, primary_key=True)
    telegram_id  = Column(BigInteger, unique=True, nullable=False)
    username     = Column(JSONB, nullable=False, default="")
    can_post     = Column(Boolean, default=True, nullable=False)
    created_at   = Column(DateTime(timezone=True), server_default=func.now())

    jobs = relationship("Job", back_populates="user", cascade="all, delete-orphan")

class Job(Base):
    __tablename__ = "jobs"
    id           = Column(Integer, primary_key=True)
    user_id      = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    message_id   = Column(BigInteger, nullable=True)      # ID поста в канале
    all_info     = Column(JSONB, nullable=False)           # сразу хранится в JSON
    created_at   = Column(DateTime(timezone=True), server_default=func.now())

    user = relationship("User", back_populates="jobs")
