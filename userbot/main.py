import asyncio

from pyrogram import Client
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncEngine

from config.settings import load_settings
from db.models import Base, WithdrawalRequest
from db.session import ensure_database, get_engine, get_session_factory


async def _init_db(engine: AsyncEngine) -> None:
    await ensure_database()
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def _process_withdrawals(app: Client) -> None:
    session_factory = get_session_factory()
    async with session_factory() as session:
        result = await session.execute(
            select(WithdrawalRequest).where(WithdrawalRequest.status == "pending").limit(10)
        )
        requests = result.scalars().all()
        for req in requests:
            try:
                await app.send_message(req.user_id, f"Подарок Мишка отправлен за {req.stars} звезд.")
                await session.execute(
                    update(WithdrawalRequest).where(WithdrawalRequest.id == req.id).values(status="sent")
                )
            except Exception:
                await session.execute(
                    update(WithdrawalRequest).where(WithdrawalRequest.id == req.id).values(status="failed")
                )
        await session.commit()


async def main() -> None:
    settings = load_settings()
    await _init_db(get_engine())
    app = Client(
        "userbot",
        api_id=settings.api_id,
        api_hash=settings.api_hash,
        session_string=settings.userbot_session,
    )
    await app.start()
    try:
        while True:
            await _process_withdrawals(app)
            await asyncio.sleep(10)
    finally:
        await app.stop()


if __name__ == "__main__":
    asyncio.run(main())
