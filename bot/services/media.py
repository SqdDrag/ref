from __future__ import annotations

from pathlib import Path

from aiogram.enums import ParseMode
from aiogram.types import CallbackQuery, FSInputFile, InputMediaPhoto, Message


_BASE_DIR = Path(__file__).resolve().parents[2]
_PIC_DIR = _BASE_DIR / "pic"

IMAGE_PATHS = {
    "captcha": _PIC_DIR / "Капча.png",
    "menu": _PIC_DIR / "Главное меню.png",
    "referrals": _PIC_DIR / "Рефералы.png",
    "tasks": _PIC_DIR / "Задания.png",
    "balance": _PIC_DIR / "Баланс.png",
}


def get_photo(key: str) -> FSInputFile:
    return FSInputFile(IMAGE_PATHS[key])


def build_media(key: str, caption: str) -> InputMediaPhoto:
    return InputMediaPhoto(media=get_photo(key), caption=caption, parse_mode=ParseMode.HTML)


async def send_photo_message(message: Message, key: str, caption: str, reply_markup=None) -> None:
    await message.answer_photo(
        photo=get_photo(key),
        caption=caption,
        reply_markup=reply_markup,
    )


async def edit_or_send_photo(callback: CallbackQuery, key: str, caption: str, reply_markup=None) -> None:
    if callback.message:
        try:
            await callback.message.edit_media(build_media(key, caption), reply_markup=reply_markup)
            return
        except Exception:
            pass
    await callback.bot.send_photo(
        chat_id=callback.from_user.id,
        photo=get_photo(key),
        caption=caption,
        reply_markup=reply_markup,
    )
