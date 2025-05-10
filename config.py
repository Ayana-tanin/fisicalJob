import os
from dotenv import load_dotenv

load_dotenv()

# Читаем токен бота
BOT_TOKEN = os.getenv("BOT_TOKEN") or os.getenv("TOKEN")
if not BOT_TOKEN:
    raise RuntimeError("Не задан бот-токен: переменная BOT_TOKEN или TOKEN")

# Список админов
ADMINS         = [int(x) for x in os.getenv("ADMINS", "").split(",") if x.strip()]

# Канал и главный админ
CHANNEL_ID     = int(os.getenv("CHANNEL_ID", "0"))
ADMIN_ID       = int(os.getenv("ADMIN_ID", "0"))
ADMIN_USERNAME = os.getenv("ADMIN_USERNAME", "")
CHANNEL_URL   = os.getenv("CHANNEL_URL", "")

# БД (используется в db_base.py)
DATABASE_URL   = os.getenv("DATABASE_URL", "")
