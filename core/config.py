# core/config.py
import os
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("TOKEN")
DB_URL = os.getenv("DB_URL", "sqlite://db.sqlite3")
AI_TOKEN = os.getenv("AI_TOKEN")

if not BOT_TOKEN:
    raise ValueError("Укажи TOKEN в .env")
if not AI_TOKEN:
    raise ValueError("Укажи AI_TOKEN в .env")