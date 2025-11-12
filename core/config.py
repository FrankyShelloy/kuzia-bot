from dotenv import load_dotenv
import os

load_dotenv()

BOT_TOKEN = os.getenv("TOKEN")
DB_URL = os.getenv("DB_URL")
AI_TOKEN = os.getenv("AI_TOKEN")