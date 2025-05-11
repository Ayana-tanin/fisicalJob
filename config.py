import os
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN       = os.getenv("BOT_TOKEN") or os.getenv("TOKEN")
if not BOT_TOKEN:
    raise RuntimeError("Не задан бот-токен: переменная BOT_TOKEN или TOKEN")

ADMINS          = [int(x) for x in os.getenv("ADMINS", "").split(",") if x.strip()]
ADMIN_ID        = int(os.getenv("ADMIN_ID",  "0"))
ADMIN_USERNAME  = os.getenv("ADMIN_USERNAME", "")
CHANNEL_ID      = int(os.getenv("CHANNEL_ID", "0"))

CHANNEL_URL     = os.getenv("CHANNEL_URL", "")
WEBHOOK_URL  = os.getenv("WEBHOOK_URL", "")

DATABASE_URL    = os.getenv("DATABASE_URL", "")
if not DATABASE_URL:
    raise RuntimeError("Не задан DATABASE_URL")
