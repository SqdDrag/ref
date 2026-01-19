from __future__ import annotations

import time
from typing import Any, Callable, Dict

from aiogram import BaseMiddleware
from aiogram.types import CallbackQuery, Message, TelegramObject

from config.settings import load_settings


_settings = load_settings()


class RateLimitMiddleware(BaseMiddleware):
    def __init__(self) -> None:
        self._last: Dict[int, float] = {}

    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Any],
        event: TelegramObject,
        data: Dict[str, Any],
    ) -> Any:
        if isinstance(event, Message):
            return await handler(event, data)
        user = data.get("event_from_user")
        if user:
            now = time.monotonic()
            last = self._last.get(user.id, 0.0)
            if now - last < _settings.rate_limit_seconds:
                if isinstance(event, CallbackQuery):
                    await event.answer("Слишком часто. Подождите немного.")
                return None
            self._last[user.id] = now
        return await handler(event, data)


