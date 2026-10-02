import os
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN", "").strip()


def _int_env(name, default=0):
    value = os.getenv(name, str(default)).strip()
    try:
        return int(value)
    except ValueError as exc:
        raise RuntimeError(f"{name} .env faylida raqam bo‘lishi kerak") from exc


OWNER_ID = _int_env("OWNER_ID")
ADMIN_ID = _int_env("ADMIN_ID")
DB_PATH = os.getenv("DB_PATH", "bot.sqlite3")
SUPPORT_USERNAME = os.getenv("SUPPORT_USERNAME", "parviz_48_48").strip()
OPERATORS = {x for x in (OWNER_ID, ADMIN_ID) if x}

if not BOT_TOKEN:
    raise RuntimeError("BOT_TOKEN .env faylida ko'rsatilmagan")
if not OWNER_ID:
    raise RuntimeError("OWNER_ID .env faylida ko'rsatilmagan")
