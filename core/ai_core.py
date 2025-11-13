import logging
from typing import List, Dict
import asyncio

from core.config import AI_TOKEN

logger = logging.getLogger(__name__)

CHAT_HISTORIES: Dict[int, List[Dict]] = {}

SYSTEM_PROMPT = {
    "role": "system",
    "content": (
        "Ты — Кузя, умный и дружелюбный помощник. Отвечай кратко, по-русски, с юмором. "
        "Помогай с задачами, мотивацией и продуктивностью."
    ),
}

try:
    from litellm import acompletion
    from litellm.exceptions import RateLimitError
    _HAS_LITELLM = True
except Exception:
    acompletion = None
    RateLimitError = Exception
    _HAS_LITELLM = False


async def get_response(chat_id: int, text: str) -> str:
    key = int(chat_id)
    if key not in CHAT_HISTORIES:
        CHAT_HISTORIES[key] = [SYSTEM_PROMPT]

    CHAT_HISTORIES[key].append({"role": "user", "content": text})
    messages = [SYSTEM_PROMPT] + CHAT_HISTORIES[key][-10:]

    if not _HAS_LITELLM or not AI_TOKEN:
        logger.info("AI unavailable")
        return "Извини, сейчас нет доступа к AI. Установи litellm и настрой AI_TOKEN."

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
        except RateLimitError:
            wait = 2 ** attempt
            logger.warning(f"Rate limit - waiting {wait}s")
            await asyncio.sleep(wait)
        except Exception:
            logger.exception("AI request failed")
            break
    return "Извини, не могу ответить."


async def decompose_with_ai(chat_id: int, task: str) -> List[str]:
    prompt = (
        f"""Ты — опытный менеджер проектов, эксперт по декомпозиции (разбиению) задач. 
    Твоя цель — разбить сложную ЗАДАЧУ на серию максимально простых, понятных и логичных шагов для исполнителя.

    Критерии для подзадач:
    1.  **Последовательность:** Шаги должны идти в строгом логическом порядке выполнения.
    2.  **Действие:** Каждая подзадача — это конкретное действие (начинается с глагола: "Изучить...", "Создать...", "Отправить...").
    3.  **Атомарность:** Шаг должен быть достаточно мелким, чтобы его можно было выполнить за один подход, но не слишком мелким (не дроби "написать букву").
    4.  **Полнота:** Все шаги вместе должны гарантированно приводить к выполнению исходной ЗАДАЧИ.

    Требования к формату ответа:
    * Только список подзадач.
    * Каждая подзадача на новой строке.
    * Без какой-либо нумерации, маркеров (`*`, `-`) или комментариев.

    ЗАДАЧА: {task}
    """
    )
    try:
        response = await get_response(chat_id, prompt)
        if not response or "нет доступа" in response.lower():
            return []
        lines = [line.strip() for line in response.split('\n') if line.strip()]
        import re
        cleaned = []
        for line in lines:
            cleaned_line = re.sub(r'^[\d\-•\*\.)\]]+\s*', '', line).strip()
            if cleaned_line:
                cleaned.append(cleaned_line)
        return cleaned[:5]
    except Exception:
        logger.exception("decompose_with_ai error")
        return []
