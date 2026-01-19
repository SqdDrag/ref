from dotenv import load_dotenv
from fastapi import FastAPI, Request
from sqlalchemy.ext.asyncio import AsyncEngine

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.types import Update

from bot.handlers import menu, onboarding, tasks, withdrawals
from bot.middlewares.rate_limit import RateLimitMiddleware
from db.models import Base
from db.session import ensure_database, ensure_schema, get_engine
from web.endpoints.check import router as check_router
from config.settings import load_settings


async def _init_db(engine: AsyncEngine) -> None:
    await ensure_database()
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    await ensure_schema(engine)


def create_app() -> FastAPI:
    app = FastAPI()
    app.include_router(check_router)
    settings = load_settings()

    bot = Bot(token=settings.bot_token, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    dp = Dispatcher()
    dp.message.middleware(RateLimitMiddleware())
    dp.callback_query.middleware(RateLimitMiddleware())
    dp.include_router(onboarding.router)
    dp.include_router(menu.router)
    dp.include_router(tasks.router)
    dp.include_router(withdrawals.router)

    webhook_path = f"/tg/webhook/{settings.bot_token}"
    webhook_url = f"{settings.web_base_url}{webhook_path}"

    @app.on_event("startup")
    async def _startup() -> None:
        await _init_db(get_engine())
        await bot.set_webhook(webhook_url, drop_pending_updates=True)

    @app.on_event("shutdown")
    async def _shutdown() -> None:
        await bot.session.close()

    @app.post(webhook_path)
    async def telegram_webhook(request: Request) -> None:
        update = Update.model_validate(await request.json())
        await dp.feed_webhook_update(bot, update)

    return app


load_dotenv()
app = create_app()
