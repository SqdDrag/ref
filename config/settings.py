import os
from dataclasses import dataclass
from typing import List

from dotenv import load_dotenv


load_dotenv()


def _split_env(value: str) -> List[str]:
    if not value:
        return []
    return [v.strip() for v in value.split(",") if v.strip()]


@dataclass
class Settings:
    bot_token: str
    api_id: int
    api_hash: str
    userbot_session: str
    database_url: str
    web_base_url: str
    web_api_base_url: str
    mandatory_channels: List[str]
    task_channels: List[str]
    referral_reward: int
    task_reward: int
    min_account_days: int
    rate_limit_seconds: float
    skip_web_check: bool



def load_settings() -> Settings:
    database_url = os.getenv("DATABASE_URL", "postgresql+asyncpg://user:pass@localhost:5432/refbot")
    if database_url.startswith("postgres://"):
        database_url = database_url.replace("postgres://", "postgresql+asyncpg://", 1)
    if database_url.startswith("postgresql://") and "asyncpg" not in database_url:
        database_url = database_url.replace("postgresql://", "postgresql+asyncpg://", 1)
    return Settings(
        bot_token=os.getenv("BOT_TOKEN", ""),
        api_id=int(os.getenv("API_ID", "0")),
        api_hash=os.getenv("API_HASH", ""),
        userbot_session=os.getenv("USERBOT_SESSION", ""),
        database_url=database_url,
        web_base_url=os.getenv("WEB_BASE_URL", "http://localhost:8000"),
        web_api_base_url=os.getenv("WEB_API_BASE_URL", "http://localhost:8000/api"),
        mandatory_channels=_split_env(os.getenv("MANDATORY_CHANNELS", "")),
        task_channels=_split_env(os.getenv("TASK_CHANNELS", "")),
        referral_reward=int(os.getenv("REFERRAL_REWARD", "5")),
        task_reward=int(os.getenv("TASK_REWARD", "2")),
        min_account_days=int(os.getenv("MIN_ACCOUNT_DAYS", "0")),
        rate_limit_seconds=float(os.getenv("RATE_LIMIT_SECONDS", "1.5")),
        skip_web_check=os.getenv("SKIP_WEB_CHECK", "0") == "1",
    )
