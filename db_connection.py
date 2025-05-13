import logging
import datetime
from contextlib import contextmanager
from sqlalchemy import select, func, update
from sqlalchemy.orm import Session

from config import ADMINS
from db_base import engine, SessionLocal, Base
from models import User, Job

logger = logging.getLogger(__name__)
DAILY_LIMIT = 1

def init_db():
    Base.metadata.create_all(bind=engine)
    logger.info("БД инициализирована успешно")

@contextmanager
def get_session() -> Session:
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()

def insert_user(user_id: int, username: str) -> User | None:
    with get_session() as session:
        try:
            user = session.query(User).filter_by(telegram_id=user_id).first()
            if user:
                return user
            new = User(telegram_id=user_id, username=username)
            session.add(new)
            session.commit()
            session.refresh(new)
            return new
        except Exception:
            session.rollback()
            logger.exception("insert_user")
            return None

def save_vacancy(user_id: int, data: dict) -> Job | int | None:
    with get_session() as session:
        try:
            user = session.query(User).filter_by(telegram_id=user_id).first()
            if not user or not user.can_post:
                return None

            if user.telegram_id in ADMINS:
                job = Job(user_id=user.id, all_info=data)
                session.add(job)
                session.commit()
                session.refresh(job)
                logger.info(f"[ADMIN] Вакансия #{job.id} сохранена")
                return job

            today = datetime.datetime.utcnow().date()
            midnight = datetime.datetime.combine(today, datetime.time.min)
            cnt = session.query(func.count()).select_from(Job).filter(
                Job.user_id == user.id, Job.created_at >= midnight).scalar()
            if cnt >= DAILY_LIMIT:
                return 0

            job = Job(user_id=user.id, all_info=data)
            session.add(job)
            session.commit()
            session.refresh(job)
            logger.info(f"Вакансия #{job.id} сохранена")
            return job
        except Exception:
            session.rollback()
            logger.exception("save_vacancy")
            return None

def get_user_vacancies(user_id: int) -> list[Job]:
    with get_session() as session:
        try:
            user = session.query(User).filter_by(telegram_id=user_id).first()
            if not user:
                return []
            return session.query(Job).filter_by(user_id=user.id).order_by(Job.created_at.desc()).all()
        except Exception:
            logger.exception("get_user_vacancies")
            return []

def get_vacancy_by_id(vacancy_id: int) -> Job | None:
    with get_session() as session:
        try:
            return session.get(Job, vacancy_id)
        except Exception:
            logger.exception("get_vacancy_by_id")
            return None

def delete_vacancy_by_id(vacancy_id: int) -> bool:
    with get_session() as session:
        try:
            job = session.get(Job, vacancy_id)
            if not job:
                return False
            session.delete(job)
            session.commit()
            return True
        except Exception:
            session.rollback()
            logger.exception("delete_vacancy_by_id")
            return False

def really_save_vacancy(user_id: int, data: dict) -> Job:
    with get_session() as session:
        job = Job(user_id=user_id, all_info=data)
        session.add(job)
        session.commit()
        session.refresh(job)
        logger.info(f"Админ-вакансия #{job.id} сохранена")
        return job
