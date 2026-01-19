from __future__ import annotations

import httpx

from config.settings import load_settings


_settings = load_settings()


async def check_web_status(user_id: int) -> bool:
    async with httpx.AsyncClient(timeout=10) as client:
        resp = await client.get(f"{_settings.web_api_base_url}/check-status", params={"user_id": user_id})
        resp.raise_for_status()
        data = resp.json()
        return data.get("status") == "success"


async def build_web_link(user_id: int, token: str) -> str:
    return f"{_settings.web_base_url}/verify?user_id={user_id}&token={token}"


