from sqlalchemy import Column, Integer, BigInteger, String, ForeignKey, DateTime, Text, Boolean
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from db_base import Base

class User(Base):
    __tablename__ = 'users'
    id = Column(Integer, primary_key=True)
    telegram_id = Column(BigInteger, unique=True, nullable=False)
    username = Column(String)
    can_post = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    jobs = relationship("Job", back_populates="user")

    def __repr__(self):
        return f"<User(id={self.id}, telegram_id={self.telegram_id}, username={self.username})>"


class Job(Base):
    __tablename__ = 'jobs'
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"))
    message_id = Column(BigInteger)  # ID сообщения в канале
    all_info = Column(Text)  # JSON строка с данными о вакансии
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Добавление реляции с пользователем
    user = relationship("User", back_populates="jobs")

    def __repr__(self):
        return f"<Job(id={self.id}, user_id={self.user_id}, message_id={self.message_id})>"
