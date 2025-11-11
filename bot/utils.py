# bot/utils.py
from typing import Optional
from maxapi.types import MessageCreated
from maxapi.filters import F

def resolve_chat_id(event: MessageCreated) -> str:
    recipient = event.message.recipient
    chat_id: Optional[int] = recipient.chat_id
    if chat_id is None and event.chat is not None:
        chat_id = getattr(event.chat, "chat_id", None)
    if chat_id is None:
        chat_id = recipient.user_id or event.message.sender.user_id
    return str(chat_id)

not_bot = ~F.message.sender.is_bot