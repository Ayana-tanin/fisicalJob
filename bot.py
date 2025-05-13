import asyncio
import logging

from aiogram import Bot, Dispatcher, types
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage

from config import BOT_TOKEN, ADMIN_ID
from db_connection import init_db
from handlers import router  # импортируем маршруты из handlers.py

# ─── Настройка логирования ──────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s"
)
logger = logging.getLogger(__name__)

async def main():
    # 1) Инициализация базы данных
    init_db()
    logger.info("Инициализация базы завершена")

    # 2) Создаём контекст бота и диспетчера
    async with Bot(
        token=BOT_TOKEN,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML)
    ) as bot:
        storage = MemoryStorage()
        dp = Dispatcher(storage=storage)
        dp.include_router(router)

        # 3) Глобальный обработчик ошибок
        @dp.errors()
        async def on_error(event: types.ErrorEvent):
            update = event.update
            exception = event.exception
            logger.exception(f"❌ Ошибка при обновлении {update!r}: {exception!r}")
            try:
                await bot.send_message(ADMIN_ID, f"🚨 Ошибка: {exception}")
            except Exception as e:
                logger.error(f"Не удалось уведомить администратора: {e}")

        # 4) Логируем запуск бота
        me = await bot.get_me()
        logger.info(f"Бот запущен: @{me.username} (id={me.id})")
        logger.info("Запускаем polling (Asia/Bishkek)")

        # 5) Старт polling
        await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())