# bot/ai_core.py
import logging
from typing import List, Dict
from litellm import completion
from core.config import AI_TOKEN

logger = logging.getLogger(__name__)
CHAT_HISTORIES: Dict[int, List[Dict]] = {}

SYSTEM_PROMPT = {
    "role": "system",
    "content": "Ты — Кузя, умный и дружелюбный помощник. Отвечай кратко, по-русски, с юмором. "
               "Помогай с задачами, мотивацией и продуктивностью."
}

async def get_response(chat_id: int, text: str) -> str:
    key = int(chat_id)
    if key not in CHAT_HISTORIES:
        CHAT_HISTORIES[key] = [SYSTEM_PROMPT]

    CHAT_HISTORIES[key].append({"role": "user", "content": text})
    messages = [SYSTEM_PROMPT] + CHAT_HISTORIES[key][-10:]

    try:
        resp = completion(
            model="gemini/gemini-2.0-flash",
            messages=messages,
            api_key=AI_TOKEN,
            max_tokens=300,
            temperature=0.8,
        )
        answer = resp.choices[0].message.content.strip()
        CHAT_HISTORIES[key].append({"role": "assistant", "content": answer})
        return answer
    except Exception as e:
        logger.error(f"AI error: {e}")
        return "Извини, не могу ответить."