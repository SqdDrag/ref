from __future__ import annotations

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from db.models import User, WithdrawalRequest


async def create_withdrawal(session: AsyncSession, user_id: int, stars: int) -> WithdrawalRequest | None:
    result = await session.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        return None
    if user.balance < stars:
        return None
    user.balance -= stars
    request = WithdrawalRequest(user_id=user_id, stars=stars, status="pending")
    session.add(request)
    await session.commit()
    await session.refresh(request)
    return request


async def mark_withdrawal_status(session: AsyncSession, request_id: int, status: str) -> None:
    await session.execute(update(WithdrawalRequest).where(WithdrawalRequest.id == request_id).values(status=status))
    await session.commit()


