import ssl
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import declarative_base, sessionmaker
from config import DATABASE_URL
from sqlalchemy.ext.asyncio import create_async_engine

ssl_context = ssl.create_default_context()

engine = create_async_engine(
    DATABASE_URL,
    connect_args={"ssl": ssl_context},
    echo=False,
    future=True
)
# 2) Фабрика сессий: указываем AsyncSession прямо
SessionLocal = sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
)

# 3) Базовый класс моделей
Base = declarative_base()
