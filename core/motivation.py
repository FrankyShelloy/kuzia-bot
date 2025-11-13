import logging
from enum import Enum
from typing import Optional
from datetime import datetime
from core.models import Task, MotivationSettings
from core.ai_core import get_response

logger = logging.getLogger(__name__)


class MotivationStyle(str, Enum):
    FRIENDLY = "friendly"
    NEUTRAL = "neutral"
    AGGRESSIVE = "aggressive"


STYLE_PROMPTS = {
    MotivationStyle.FRIENDLY: (
        "Ты — добрый друг и помощник Кузя. Напиши мотивирующее сообщение пользователю "
        "о невыполненных задачах. Будь дружелюбным, поддерживающим и позитивным. "
        "Используй эмодзи и теплые слова. Максимум 2-3 предложения."
    ),
    MotivationStyle.NEUTRAL: (
        "Ты — деловой помощник Кузя. Напиши короткое напоминание пользователю "
        "о невыполненных задачах. Будь нейтральным, вежливым и по делу. "
        "Без лишних эмоций, но корректно. Максимум 2-3 предложения."
    ),
    MotivationStyle.AGGRESSIVE: (
        "Ты — строгий тренер Кузя. Напиши жесткое мотивирующее сообщение пользователю "
        "о невыполненных задачах. Будь требовательным, немного саркастичным, но не грубым. "
        "Используй боевые метафоры и призывы к действию. Максимум 2-3 предложения."
    ),
}


async def generate_motivation_message(
    chat_id: str,
    style: MotivationStyle = MotivationStyle.FRIENDLY
) -> Optional[str]:
    pending_tasks = await Task.filter(
        chat_id=chat_id,
        status__in=["new", "pending"]
    ).all()
    
    if not pending_tasks:
        return None
    
    task_count = len(pending_tasks)
    task_preview = ", ".join([t.text[:30] for t in pending_tasks[:3]])
    if task_count > 3:
        task_preview += "..."
    
    completed_count = await Task.filter(chat_id=chat_id, status="done").count()
    
    context = (
        f"У пользователя {task_count} невыполненных задач: {task_preview}. "
        f"Всего выполнено {completed_count} задач. "
    )
    
    system_prompt = STYLE_PROMPTS[style]
    full_prompt = f"{system_prompt}\n\n{context}"
    
    try:
        message = await get_response(int(chat_id), full_prompt)
        return message
    except Exception:
        logger.exception("Failed to generate motivation message")
        return get_fallback_message(task_count, style)


def get_fallback_message(task_count: int, style: MotivationStyle) -> str:
    fallbacks = {
        MotivationStyle.FRIENDLY: {
            1: "Привет! 😊 У тебя осталась одна задача. Давай закроем её вместе?",
            "few": f"Привет, друг! 👋 У тебя {task_count} задачи ждут своего героя. Ты справишься! 💪",
            "many": f"Йоу! 🌟 Вижу {task_count} задач в списке. Начнем с самой легкой? Ты молодец, что не сдаешься! 🔥"
        },
        MotivationStyle.NEUTRAL: {
            1: "Напоминаю: у вас 1 невыполненная задача.",
            "few": f"Уведомление: {task_count} задачи ожидают выполнения.",
            "many": f"Статус: {task_count} задач в работе. Рекомендую приступить к выполнению."
        },
        MotivationStyle.AGGRESSIVE: {
            1: "Серьезно? Одна задача, а ты все тянешь! Действуй! 💥",
            "few": f"{task_count} задачи не сделают себя сами! Хватит откладывать, вперед! ⚡",
            "many": f"{task_count} задач?! Ты что, коллекционируешь их? Пора браться за дело, боец! 🔥"
        }
    }
    
    if task_count == 1:
        return fallbacks[style][1]
    elif task_count <= 5:
        return fallbacks[style]["few"]
    else:
        return fallbacks[style]["many"]


async def should_send_reminder(chat_id: str, last_reminder: Optional[datetime]) -> bool:
    if last_reminder is None:
        return True
    
    now = datetime.now()
    hours_since_last = (now - last_reminder).total_seconds() / 3600
    
    if hours_since_last < 4:
        return False
    
    pending_tasks = await Task.filter(
        chat_id=chat_id,
        status__in=["new", "pending"]
    ).count()
    
    return pending_tasks > 0


async def get_or_create_settings(chat_id: str) -> MotivationSettings:
    settings = await MotivationSettings.filter(chat_id=chat_id).first()
    if not settings:
        settings = await MotivationSettings.create(
            chat_id=chat_id,
            style=MotivationStyle.FRIENDLY,
            enabled=True
        )
    return settings


async def update_motivation_style(chat_id: str, style: MotivationStyle) -> None:
    settings = await get_or_create_settings(chat_id)
    settings.style = style
    await settings.save()
    logger.info(f"Updated motivation style for chat {chat_id}: {style}")


async def toggle_reminders(chat_id: str, enabled: bool) -> None:
    settings = await get_or_create_settings(chat_id)
    settings.enabled = enabled
    await settings.save()
    logger.info(f"Reminders {'enabled' if enabled else 'disabled'} for chat {chat_id}")


async def update_last_reminder(chat_id: str) -> None:
    settings = await get_or_create_settings(chat_id)
    settings.last_reminder = datetime.now()
    await settings.save()
