import asyncpg
import ssl
from sqlalchemy import text
from sqlalchemy.engine.url import make_url
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker, create_async_engine

from config.settings import load_settings


_settings = load_settings()
_engine: AsyncEngine | None = None
_session_factory: async_sessionmaker[AsyncSession] | None = None


def _ssl_required() -> bool:
    url = make_url(_settings.database_url)
    return url.query.get("sslmode") == "require"


def _ssl_context() -> ssl.SSLContext | None:
    if not _ssl_required():
        return None
    context = ssl.create_default_context()
    context.check_hostname = False
    context.verify_mode = ssl.CERT_NONE
    return context

def _is_managed_host() -> bool:
    url = make_url(_settings.database_url)
    host = url.host or ""
    return host.endswith(".render.com")

def get_engine() -> AsyncEngine:
    global _engine
    if _engine is None:
        ssl_ctx = _ssl_context()
        connect_args = {"ssl": ssl_ctx} if ssl_ctx else {}
        _engine = create_async_engine(
            _settings.database_url, echo=False, pool_pre_ping=True, connect_args=connect_args
        )
    return _engine


def get_session_factory() -> async_sessionmaker[AsyncSession]:
    global _session_factory
    if _session_factory is None:
        _session_factory = async_sessionmaker(bind=get_engine(), expire_on_commit=False, class_=AsyncSession)
    return _session_factory


async def get_session() -> AsyncSession:
    return get_session_factory()()


async def ensure_database() -> None:
    if _is_managed_host():
        return
    url = make_url(_settings.database_url)
    db_name = url.database
    admin_url = url.set(database="postgres")
    ssl_arg = _ssl_context()
    try:
        conn = await asyncpg.connect(
            user=admin_url.username,
            password=admin_url.password,
            host=admin_url.host,
            port=admin_url.port or 5432,
            database=admin_url.database,
            ssl=ssl_arg,
        )
    except Exception:
        return
    try:
        exists = await conn.fetchval("SELECT 1 FROM pg_database WHERE datname = $1", db_name)
        if not exists:
            await conn.execute(f'CREATE DATABASE "{db_name}"')
    finally:
        await conn.close()


async def ensure_schema(engine: AsyncEngine) -> None:
    async with engine.begin() as conn:
        await conn.execute(text("ALTER TABLE users ADD COLUMN IF NOT EXISTS web_captcha_answer VARCHAR(16)"))
        await conn.execute(text("ALTER TABLE users ADD COLUMN IF NOT EXISTS web_captcha_at TIMESTAMPTZ"))
