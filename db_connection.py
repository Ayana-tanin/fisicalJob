import logging

from sqlalchemy import text
from sqlalchemy.future import select
from sqlalchemy.ext.asyncio import AsyncSession
from db_base import engine, SessionLocal, Base
from models import User, Job

logger = logging.getLogger(__name__)

# 1) Инициализация БД: создаёт все таблицы по моделям
async def init_db() -> None:
    """Создать таблицы в базе данных."""
    try:
        # Проверяем существуют ли уже таблицы базы данных
        async with engine.begin() as conn:
            # Получаем список существующих таблиц
            result = await conn.run_sync(
                lambda sync_conn: sync_conn.execute(
                    text("SELECT tablename FROM pg_tables WHERE schemaname = 'public'")
                ).fetchall()
            )

            existing_tables = [row[0] for row in result]
            tables_to_create = [table.__tablename__ for table in Base.__subclasses__()]

            if all(table in existing_tables for table in tables_to_create):
                logger.info("База данных уже существует, инициализация не требуется")
                return

        # Если база не существует полностью, создаём таблицы
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        logger.info("База данных инициализирована успешно")
    except Exception as e:
        logger.error(f"Ошибка при инициализации базы данных: {e}")
        raise

# 2) Получить новый асинхронный сеанс
def get_session() -> AsyncSession:
    return SessionLocal()

# 3) Добавить пользователя (или вернуть существующего)
async def insert_user(user_id: int, username: str) -> User | None:
    """
    Если телеграм-ID есть в таблице users, вернётся существующий User.
    Иначе создаст новую запись и вернёт её.
    """
    async with get_session() as session:
        try:
            res = await session.execute(
                select(User).filter(User.telegram_id == user_id)
            )
            user = res.scalars().first()
            if user:
                return user

            new_user = User(telegram_id=user_id, username=username)
            session.add(new_user)
            await session.commit()
            await session.refresh(new_user)
            logger.info(f"[{user_id}] Пользователь добавлен: {username}")
            return new_user
        except Exception as e:
            await session.rollback()
            logger.error(f"Ошибка insert_user: {e}")
            return None

# 4) Получить все вакансии конкретного пользователя
async def get_user_vacancies(user_id: int) -> list[Job]:
    """
    Вернёт список объектов Job, отсортированных по created_at DESC.
    Если user не найден — пустой список.
    """
    async with get_session() as session:
        try:
            res = await session.execute(
                select(User).filter(User.telegram_id == user_id)
            )
            user = res.scalars().first()
            if not user:
                return []

            res_jobs = await session.execute(
                select(Job)
                .filter(Job.user_id == user.id)
                .order_by(Job.created_at.desc())
            )
            return res_jobs.scalars().all()
        except Exception as e:
            logger.error(f"Ошибка get_user_vacancies: {e}")
            return []

# 5) Сохранить новую вакансию и вернуть её ID
async def save_vacancy(user_id: int, message_id: int, data: dict) -> int | None:
    """
    Сохраняет вакансию (Job) с внешним ключом на User.
    all_info хранится как строка (repr(data) или JSON).
    """
    async with get_session() as session:
        try:
            res = await session.execute(
                select(User).filter(User.telegram_id == user_id)
            )
            user = res.scalars().first()
            if not user:
                logger.error(f"save_vacancy: пользователь {user_id} не найден")
                return None

            job = Job(
                user_id=user.id,
                message_id=message_id,
                all_info=str(data)
            )
            session.add(job)
            await session.commit()
            await session.refresh(job)
            logger.info(f"Вакансия сохранена: ID={job.id}")
            return job.id
        except Exception as e:
            await session.rollback()
            logger.error(f"Ошибка save_vacancy: {e}")
            return None

# 6) Получить одну вакансию по её ID
async def get_vacancy_by_id(vacancy_id: int) -> Job | None:
    """
    Возвращает объект Job или None, если не найден.
    """
    async with get_session() as session:
        try:
            return await session.get(Job, vacancy_id)
        except Exception as e:
            logger.error(f"Ошибка get_vacancy_by_id: {e}")
            return None

# 7) Удалить вакансию по ID и вернуть message_id (для удаления сообщения в канале)
async def delete_vacancy_by_id(vacancy_id: int) -> int | None:
    async with get_session() as session:
        try:
            job = await session.get(Job, vacancy_id)
            if not job:
                logger.warning(f"delete_vacancy_by_id: ID={vacancy_id} не найден")
                return None

            msg_id = job.message_id
            await session.delete(job)
            await session.commit()
            logger.info(f"Вакансия удалена: ID={vacancy_id}")
            return msg_id
        except Exception as e:
            await session.rollback()
            logger.error(f"Ошибка delete_vacancy_by_id: {e}")
            return None
