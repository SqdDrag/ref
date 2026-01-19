from __future__ import annotations

from aiogram import Bot
from aiogram.enums import ChatMemberStatus


async def has_join_request(bot: Bot, chat_id: str, user_id: int) -> bool:
    try:
        requests = await bot.get_chat_join_requests(chat_id=chat_id, limit=50)
    except Exception:
        return False
    return any(req.user.id == user_id for req in requests)


async def is_subscribed_or_requested(bot: Bot, chat_id: str, user_id: int) -> bool:
    try:
        member = await bot.get_chat_member(chat_id=chat_id, user_id=user_id)
    except Exception:
        return False
    if member.status in {ChatMemberStatus.MEMBER, ChatMemberStatus.ADMINISTRATOR, ChatMemberStatus.CREATOR}:
        return True
    if member.status == ChatMemberStatus.LEFT:
        return await has_join_request(bot, chat_id, user_id)
    return False


