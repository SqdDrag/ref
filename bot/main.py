import asyncio

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from dotenv import load_dotenv
from sqlalchemy.ext.asyncio import AsyncEngine

from bot.handlers import menu, onboarding, tasks, withdrawals
from bot.middlewares.rate_limit import RateLimitMiddleware
from config.settings import load_settings
from db.models import Base
from db.session import ensure_database, ensure_schema, get_engine


async def _init_db(engine: AsyncEngine) -> None:
    await ensure_database()
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    await ensure_schema(engine)


async def main() -> None:
    load_dotenv()
    settings = load_settings()
    bot = Bot(token=settings.bot_token, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    dp = Dispatcher()
    dp.callback_query.middleware(RateLimitMiddleware())

    dp.include_router(onboarding.router)
    dp.include_router(menu.router)
    dp.include_router(tasks.router)
    dp.include_router(withdrawals.router)

    await _init_db(get_engine())
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
