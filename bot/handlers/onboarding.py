from __future__ import annotations

import secrets
from datetime import datetime, timezone

from aiogram import Bot, F, Router
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, Message
from sqlalchemy import select

from bot.keyboards.common import main_menu_kb, subscriptions_kb, web_check_kb
from bot.services.api_client import build_web_link, check_web_status
from bot.services.media import edit_or_send_photo, send_photo_message
from bot.services.subscription import is_subscribed_or_requested
from config.settings import load_settings
from db.models import User
from db.session import get_session_factory


router = Router()
_settings = load_settings()


class Onboarding(StatesGroup):
    web_check = State()
    subscriptions = State()


async def _get_or_create_user(message: Message, referrer_id: int | None) -> User:
    if referrer_id == message.from_user.id:
        referrer_id = None
    session_factory = get_session_factory()
    async with session_factory() as session:
        result = await session.execute(select(User).where(User.id == message.from_user.id))
        user = result.scalar_one_or_none()
        if user:
            return user
        user = User(
            id=message.from_user.id,
            username=message.from_user.username,
            first_name=message.from_user.first_name,
            referrer_id=referrer_id,
        )
        session.add(user)
        await session.commit()
        await session.refresh(user)
        return user


def _parse_referrer_id(text: str | None) -> int | None:
    if not text:
        return None
    parts = text.split()
    if len(parts) < 2:
        return None
    value = parts[1]
    if value.isdigit():
        return int(value)
    return None


async def _ensure_web_token(user: User) -> str:
    if user.web_token:
        return user.web_token
    token = secrets.token_urlsafe(16)
    session_factory = get_session_factory()
    async with session_factory() as session:
        result = await session.execute(select(User).where(User.id == user.id))
        db_user = result.scalar_one_or_none()
        if db_user:
            db_user.web_token = token
            await session.commit()
        return token


async def _continue_flow(message: Message, state: FSMContext, user_id: int | None = None) -> None:
    target_user_id = user_id or (message.from_user.id if message.from_user else message.chat.id)
    session_factory = get_session_factory()
    async with session_factory() as session:
        result = await session.execute(select(User).where(User.id == target_user_id))
        user = result.scalar_one_or_none()
    if not user:
        await _get_or_create_user(message, _parse_referrer_id(message.text))
        async with session_factory() as session:
            result = await session.execute(select(User).where(User.id == target_user_id))
            user = result.scalar_one_or_none()
        if not user:
            await message.answer("Ошибка пользователя")
            return
    if user.is_blocked:
        await message.answer("⛔ Доступ ограничен. Если считаете это ошибкой, обратитесь в поддержку.")
        return
    if not user.web_verified:
        if _settings.skip_web_check:
            session_factory = get_session_factory()
            async with session_factory() as session:
                result = await session.execute(select(User).where(User.id == user.id))
                db_user = result.scalar_one_or_none()
                if db_user:
                    db_user.web_verified = True
                    db_user.captcha_passed = True
                    await session.commit()
            await _continue_flow(message, state, user_id=target_user_id)
            return
        token = await _ensure_web_token(user)
        link = await build_web_link(user.id, token)
        await state.set_state(Onboarding.web_check)
        await message.answer(
            "🌐 <b>Веб‑проверка</b>\n"
            "Перейдите по ссылке, пройдите проверку и вернитесь в бот.\n"
            "После этого нажмите кнопку «Я прошел проверку».",
            reply_markup=web_check_kb(link),
        )
        return
    if not user.activated:
        await state.set_state(Onboarding.subscriptions)
        await message.answer(
            "📢 <b>Обязательные подписки</b>\n"
            "Подпишитесь на все каналы.\n"
            "Когда будете готовы, нажмите «Проверить подписки».",
            reply_markup=subscriptions_kb(),
        )
        return
    await send_photo_message(
        message,
        "menu",
        "🏠 <b>Главное меню</b>\nВыберите нужный раздел ниже.",
        reply_markup=main_menu_kb(),
    )


async def _activate_user(user_id: int) -> None:
    session_factory = get_session_factory()
    async with session_factory() as session:
        result = await session.execute(select(User).where(User.id == user_id))
        user = result.scalar_one_or_none()
        if not user:
            return
        user.activated = True
        if user.referrer_id and not user.ref_rewarded:
            ref_result = await session.execute(select(User).where(User.id == user.referrer_id))
            ref_user = ref_result.scalar_one_or_none()
            if ref_user:
                ref_user.balance += _settings.referral_reward
                user.ref_rewarded = True
        await session.commit()


@router.message(CommandStart())
async def start_handler(message: Message, state: FSMContext) -> None:
    referrer_id = _parse_referrer_id(message.text)
    await _get_or_create_user(message, referrer_id)
    await _continue_flow(message, state)


@router.callback_query(F.data == "web_check")
async def web_check_handler(callback: CallbackQuery, state: FSMContext) -> None:
    user_id = callback.from_user.id
    ok = await check_web_status(user_id)
    if not ok:
        await callback.answer("Проверка не пройдена", show_alert=True)
        return
    session_factory = get_session_factory()
    async with session_factory() as session:
        result = await session.execute(select(User).where(User.id == user_id))
        user = result.scalar_one_or_none()
        if user:
            user.web_verified = True
            user.captcha_passed = True
            await session.commit()
    if callback.message:
        await callback.message.edit_text("✅ Проверка пройдена. Продолжаем активацию.")
    await callback.answer()
    await _continue_flow(callback.message, state, user_id=callback.from_user.id)


@router.callback_query(F.data == "check_subs")
async def subscriptions_check_handler(callback: CallbackQuery, state: FSMContext, bot: Bot) -> None:
    session_factory = get_session_factory()
    async with session_factory() as session:
        result = await session.execute(select(User).where(User.id == callback.from_user.id))
        user = result.scalar_one_or_none()
        if not user:
            await callback.answer("Ошибка", show_alert=True)
            return
        if _settings.min_account_days > 0:
            age_days = (datetime.now(timezone.utc) - user.created_at).days
            if age_days < _settings.min_account_days:
                await callback.answer("Аккаунт слишком новый для активации", show_alert=True)
                return
    for channel in _settings.mandatory_channels:
        if not await is_subscribed_or_requested(bot, channel, callback.from_user.id):
            await callback.answer("Подписки не выполнены", show_alert=True)
            return
    await _activate_user(callback.from_user.id)
    await edit_or_send_photo(
        callback,
        "menu",
        "🎉 <b>Активация завершена!</b>\nТеперь доступен весь функционал.",
        reply_markup=main_menu_kb(),
    )
    await callback.answer()
    await state.clear()
