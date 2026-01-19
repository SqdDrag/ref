from aiogram import F, Router
from aiogram.types import CallbackQuery
from sqlalchemy import select

from bot.keyboards.common import main_menu_kb
from bot.services.media import edit_or_send_photo
from db.models import User
from db.session import get_session_factory


router = Router()


@router.callback_query(F.data == "to_menu")
async def menu_callback(callback: CallbackQuery) -> None:
    await edit_or_send_photo(callback, "menu", "🏠 <b>Главное меню</b>\nВыберите нужный раздел.", reply_markup=main_menu_kb())
    await callback.answer()


@router.callback_query(F.data == "menu:balance")
async def balance_handler(callback: CallbackQuery) -> None:
    session_factory = get_session_factory()
    async with session_factory() as session:
        result = await session.execute(select(User).where(User.id == callback.from_user.id))
        user = result.scalar_one_or_none()
    balance = user.balance if user else 0
    await edit_or_send_photo(
        callback,
        "balance",
        f"💰 <b>Ваш баланс:</b> <b>{balance}</b> ⭐\n"
        "Начисления приходят за рефералов и выполненные задания.",
        reply_markup=main_menu_kb(),
    )
    await callback.answer()


@router.callback_query(F.data == "menu:referrals")
async def referrals_handler(callback: CallbackQuery) -> None:
    session_factory = get_session_factory()
    async with session_factory() as session:
        result = await session.execute(select(User).where(User.referrer_id == callback.from_user.id))
        referrals = result.scalars().all()
    me = await callback.bot.get_me()
    link = f"https://t.me/{me.username}?start={callback.from_user.id}"
    await edit_or_send_photo(
        callback,
        "referrals",
        "👥 <b>Реферальная система</b>\n"
        f"🔗 <b>Ваша ссылка:</b>\n<code>{link}</code>\n\n"
        f"Активных рефералов: <b>{len(referrals)}</b>\n"
        "Награда начисляется после полной активации реферала.",
        reply_markup=main_menu_kb(),
    )
    await callback.answer()
