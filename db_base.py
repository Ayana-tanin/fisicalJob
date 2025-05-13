# db_base.py
import ssl
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker, declarative_base
from config import DATABASE_URL

engine = create_async_engine(
    DATABASE_URL,
    echo=False,
    future=True,
)

SessionLocal = sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
)

Base = declarative_base()
