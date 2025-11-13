import logging
from typing import Optional, List
from core.models import Achievement, Task
from core.ai_core import generate_achievement_title

logger = logging.getLogger(__name__)

MILESTONES = [10, 50, 100, 250, 500, 1000, 2500, 5000]


async def check_and_unlock_achievements(chat_id: str) -> Optional[Achievement]:
    completed_count = await Task.filter(chat_id=chat_id, status="done").count()
    unlocked = await Achievement.filter(chat_id=chat_id).all()
    unlocked_milestones = {a.milestone for a in unlocked}
    
    new_achievement = None
    for milestone in MILESTONES:
        if completed_count >= milestone and milestone not in unlocked_milestones:
            title, emoji = await generate_achievement_title(milestone)
            new_achievement = await Achievement.create(
                chat_id=chat_id,
                milestone=milestone,
                title=title,
                emoji=emoji
            )
            logger.info(f"Achievement unlocked for chat {chat_id}: {milestone} tasks - {title}")
    
    return new_achievement


async def get_all_achievements(chat_id: str) -> List[dict]:
    completed_count = await Task.filter(chat_id=chat_id, status="done").count()
    unlocked = await Achievement.filter(chat_id=chat_id).order_by("milestone").all()
    unlocked_dict = {a.milestone: a for a in unlocked}
    
    result = []
    for milestone in MILESTONES:
        if milestone in unlocked_dict:
            ach = unlocked_dict[milestone]
            result.append({
                "milestone": milestone,
                "title": ach.title,
                "emoji": ach.emoji,
                "unlocked": True,
                "unlocked_at": ach.unlocked_at
            })
        else:
            progress = min(100, int(completed_count / milestone * 100))
            result.append({
                "milestone": milestone,
                "title": f"??? ({completed_count}/{milestone})",
                "emoji": "🔒",
                "unlocked": False,
                "progress": progress
            })
    
    return result
