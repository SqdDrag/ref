from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from db.models import User


async def is_ip_unique(session: AsyncSession, user_id: int, ip: str) -> bool:
    result = await session.execute(select(User).where(User.ip == ip))
    existing = result.scalar_one_or_none()
    if existing is None:
        return True
    return existing.id == user_id


async def is_account_old_enough(session: AsyncSession, user_id: int, min_days: int) -> bool:
    if min_days <= 0:
        return True
    result = await session.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        return False
    age_days = (datetime.now(timezone.utc) - user.created_at).days
    return age_days >= min_days


