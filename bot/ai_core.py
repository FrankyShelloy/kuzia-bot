# bot/ai_core.py
import logging
from typing import List, Dict
from litellm import acompletion
from litellm.exceptions import RateLimitError
from core.config import AI_TOKEN
import asyncio

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

    for attempt in range(3):
        try:
            resp = await acompletion(
                model="gemini/gemini-2.0-flash",
                messages=messages,
                api_key=AI_TOKEN,
                max_tokens=300,
                temperature=0.8,
            )
            answer = resp.choices[0].message.content.strip()
            CHAT_HISTORIES[key].append({"role": "assistant", "content": answer})
            return answer
        except RateLimitError as e:
            wait = 2 ** attempt
            logger.warning(f"Rate limit, ждём {wait}с... (попытка {attempt + 1})")
            await asyncio.sleep(wait)
        except Exception as e:
            logger.error(f"AI error: {e}")
            break
    return "Извини, не могу ответить."

async def decompose_with_ai(chat_id: int, task: str) -> list[str]:
    prompt = (
        f"Разбей задачу на 3–5 мелких подзадач. "
        f"Каждая подзадача — один шаг. "
        f"Только список, без номеров и пояснений.\n\n"
        f"Задача: {task}"
    )
    try:
        response = await get_response(chat_id, prompt)
        lines = [line.strip() for line in response.split('\n') if line.strip()]
        return lines[:5]
    except Exception as e:
        logger.error(f"decompose_with_ai error: {e}")
        return []