from dotenv import load_dotenv
from fastapi import FastAPI
from sqlalchemy.ext.asyncio import AsyncEngine

from db.models import Base
from db.session import ensure_database, ensure_schema, get_engine
from web.endpoints.check import router as check_router


async def _init_db(engine: AsyncEngine) -> None:
    await ensure_database()
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    await ensure_schema(engine)


def create_app() -> FastAPI:
    app = FastAPI()
    app.include_router(check_router)

    @app.on_event("startup")
    async def _startup() -> None:
        await _init_db(get_engine())

    return app


load_dotenv()
app = create_app()
