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
        f"Разбей задачу на 3–5 мелких подзадач. "
        f"Каждая подзадача — один конкретный шаг. "
        f"Только список подзадач, без номеров и пояснений.\n\n"
        f"Задача: {task}"
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


async def generate_achievement_title(milestone: int) -> tuple[str, str]:
    if not _HAS_LITELLM or not AI_TOKEN:
        return get_default_achievement(milestone)
    
    prompt = (
        f"Придумай название достижения для пользователя, который выполнил {milestone} задач. "
        f"Формат ответа: только название (максимум 3-4 слова) и один эмодзи через запятую. "
        f"Название должно быть креативным, мотивирующим и немного забавным. "
        f"Пример: Боец невидимого фронта, 💪"
    )
    
    try:
        messages = [
            SYSTEM_PROMPT,
            {"role": "user", "content": prompt}
        ]
        
        resp = await acompletion(
            model="gemini/gemini-2.0-flash",
            messages=messages,
            api_key=AI_TOKEN,
            max_tokens=50,
            temperature=1.0,
        )
        
        answer = resp.choices[0].message.content.strip()
        
        if ',' in answer:
            parts = answer.rsplit(',', 1)
            title = parts[0].strip()
            emoji = parts[1].strip() if len(parts) > 1 else "🏆"
        else:
            title = answer
            emoji = "🏆"
        
        title = title.replace('"', '').replace("'", '').strip()
        
        return title[:100], emoji[:10]
        
    except Exception:
        logger.exception("generate_achievement_title error")
        return get_default_achievement(milestone)


def get_default_achievement(milestone: int) -> tuple[str, str]:
    defaults = {
        10: ("Начало положено", "🌱"),
        50: ("Набираем обороты", "🚀"),
        100: ("Первая сотня", "💯"),
        250: ("Мастер продуктивности", "⚡"),
        500: ("Легенда дел", "🔥"),
        1000: ("Повелитель задач", "👑"),
        2500: ("Невероятная машина", "🤖"),
        5000: ("Абсолютный чемпион", "🏆"),
    }
    
    return defaults.get(milestone, (f"Герой {milestone} задач", "🌟"))
