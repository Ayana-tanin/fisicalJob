import os
import logging

from aiogram import Bot, Dispatcher, types
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.utils.webhook import configure_app
from fastapi import FastAPI, Request
from handlers import router
from db_connection import init_db

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
logger = logging.getLogger(__name__)
BOT_TOKEN   = os.getenv("BOT_TOKEN")#
WEBHOOK_URL = os.getenv("WEBHOOK_URL")  # https://<your-app>.railway.app/webhook# from aiogram import Bot, Dispatcher, types
PORT        = int(os.getenv("PORT", 8000))# from aiogram.client.default import DefaultBotProperties
# from aiogram.enums import ParseMode
bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))# from aiogram.fsm.storage.memory import MemoryStorage
dp  = Dispatcher(storage=None)#
dp.include_router(router)# from config import BOT_TOKEN, ADMIN_ID
# from db_connection import init_db
app = FastAPI()# from handlers import router  # импортируем маршруты из handlers.py
#
@app.on_event("startup")# # ─── Настройка логирования ──────────────────────────────────────────
async def on_startup():# logging.basicConfig(
    await init_db()#     level=logging.INFO,
    await bot.set_webhook(f"{WEBHOOK_URL}/webhook/{BOT_TOKEN}")#     format="%(asctime)s %(levelname)s %(name)s: %(message)s"
    logger.info("Webhook установлен: %s/webhook/%s", WEBHOOK_URL, BOT_TOKEN)# )
# logger = logging.getLogger(__name__)
@app.on_event("shutdown")#
async def on_shutdown():# async def main():
    await bot.delete_webhook()#     # 1) Инициализация базы данных
    await dp.storage.close()#     await init_db()
    await dp.storage.wait_closed()#     logger.info("10.05.2025 13:00 — Инициализация базы завершена")
    await bot.session.close()#
#     # 2) Создаём контекст бота и диспетчера
@app.post(f"/webhook/{BOT_TOKEN}")#     async with Bot(
async def telegram_webhook(request: Request):#         token=BOT_TOKEN,
    data = await request.json()#         default=DefaultBotProperties(parse_mode=ParseMode.HTML)
    update = types.Update(**data)#     ) as bot:
    await dp.process_update(update)#         storage = MemoryStorage()
    return {"ok": True}#         dp = Dispatcher(storage=storage)
#         dp.include_router(router)
if __name__ == "__main__":#
    import uvicorn#         # 3) Глобальный обработчик ошибок
    uvicorn.run("bot:app", host="0.0.0.0", port=PORT)#         @dp.errors()
#         async def on_error(event: types.ErrorEvent):
#             update = event.update
#             exception = event.exception
#             logger.exception(f"❌ Ошибка при обновлении {update!r}: {exception!r}")
#             try:
#                 await bot.send_message(ADMIN_ID, f"🚨 Ошибка: {exception}")
#             except Exception as e:
#                 logger.error(f"Не удалось уведомить администратора: {e}")
#
#         # 4) Логируем запуск бота
#         me = await bot.get_me()
#         logger.info(f"Бот запущен: @{me.username} (id={me.id})")
#         logger.info("Запускаем polling (Asia/Bishkek)")
#
#         # 5) Старт polling
#         await dp.start_polling(bot)
#
# if __name__ == "__main__":
#     asyncio.run(main())