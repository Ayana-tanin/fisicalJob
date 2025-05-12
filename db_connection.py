import logging
import datetime

from sqlalchemy import text, select, func
from sqlalchemy.ext.asyncio import AsyncSession

from config import ADMINS
from db_base import engine, SessionLocal, Base
from models import User, Job

logger = logging.getLogger(__name__)
DAILY_LIMIT = 1  # лимит вакансий в день


async def init_db() -> None:
    """Проверка подключения и создание таблиц."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    logger.info("БД инициализирована успешно")


def get_session() -> AsyncSession:
    return SessionLocal()


async def insert_user(user_id: int, username: str) -> User | None:
    async with get_session() as session:
        try:
            res = await session.execute(select(User).filter_by(telegram_id=user_id))
            user = res.scalars().first()
            if user:
                return user
            new = User(telegram_id=user_id, username=username)
            session.add(new)
            await session.commit()
            await session.refresh(new)
            return new
        except:
            await session.rollback()
            logger.exception("insert_user")
            return None

async def save_vacancy(user_id: int, data: dict) -> Job | int | None:
    """
    Сохраняет вакансию:
      — None, если нет прав или ошибка;
      — 0, если превышен лимит за сегодня;
      — Job instance, если всё ок.
    """
    async with get_session() as session:
        try:
            # 1) Проверяем пользователя
            res = await session.execute(select(User).filter_by(telegram_id=user_id))
            user = res.scalars().first()
            if not user or not user.can_post:
                return None

            # 🛠️ ⬇️ Новое поведение: если админ, сразу сохраняем
            if user.telegram_id in ADMINS:
                job = Job(user_id=user.id, all_info=data)
                session.add(job)
                await session.commit()
                await session.refresh(job)
                logger.info(f"[ADMIN] Вакансия #{job.id} сохранена")
                return job

            # 2) Лимит для обычных пользователей
            today = datetime.datetime.utcnow().date()
            midnight = datetime.datetime.combine(today, datetime.time.min)
            cnt_res = await session.execute(
                select(func.count()).select_from(Job)
                .where(Job.user_id == user.id, Job.created_at >= midnight)
            )
            if cnt_res.scalar_one() >= DAILY_LIMIT:
                return 0

            # 3) Сохраняем обычную вакансию
            job = Job(user_id=user.id, all_info=data)
            session.add(job)
            await session.commit()
            await session.refresh(job)
            logger.info(f"Вакансия #{job.id} сохранена")
            return job

        except:
            await session.rollback()
            logger.exception("save_vacancy")
            return None

async def get_user_vacancies(user_id: int) -> list[Job]:
    async with get_session() as session:
        try:
            res = await session.execute(select(User).filter_by(telegram_id=user_id))
            user = res.scalars().first()
            if not user:
                return []
            res2 = await session.execute(
                select(Job)
                .filter_by(user_id=user.id)
                .order_by(Job.created_at.desc())
            )
            return res2.scalars().all()
        except:
            logger.exception("get_user_vacancies")
            return []


async def get_vacancy_by_id(vacancy_id: int) -> Job | None:
    async with get_session() as session:
        try:
            return await session.get(Job, vacancy_id)
        except:
            logger.exception("get_vacancy_by_id")
            return None


async def delete_vacancy_by_id(vacancy_id: int) -> bool:
    async with get_session() as session:
        try:
            job = await session.get(Job, vacancy_id)
            if not job:
                return False
            await session.delete(job)
            await session.commit()
            return True
        except:
            await session.rollback()
            logger.exception("delete_vacancy_by_id")
            return False

async def really_save_vacancy(user_id: int, data: dict) -> Job:
    async with get_session() as session:
        job = Job(user_id=user_id, all_info=data)
        session.add(job)
        await session.commit()
        await session.refresh(job)
        logger.info(f"Админ-вакансия #{job.id} сохранена")
        return job

