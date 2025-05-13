# db_base.py
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import declarative_base, sessionmaker
from config import DATABASE_URL

# 1) Движок SQLAlchemy — берёт URL из config.py
engine = create_async_engine(
    DATABASE_URL,
    echo=False,    # логи SQL будут подавлены
    future=True    # режим 2.0
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
