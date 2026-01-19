from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, Message
from sqlalchemy import select

from bot.keyboards.common import back_to_menu_kb, main_menu_kb
from bot.services.media import edit_or_send_photo
from bot.services.withdraw import create_withdrawal
from db.models import User
from db.session import get_session_factory


router = Router()
GIFT_PRICE = 15


class WithdrawStates(StatesGroup):
    wait_gifts = State()


@router.callback_query(F.data == "menu:withdraw")
async def withdraw_start(callback: CallbackQuery, state: FSMContext) -> None:
    await state.set_state(WithdrawStates.wait_gifts)
    await edit_or_send_photo(
        callback,
        "menu",
        "🎁 <b>Вывод в подарках «Мишка»</b>\n"
        "Введите количество подарков. 1 подарок = <b>15</b> ⭐.",
        reply_markup=back_to_menu_kb(),
    )
    await callback.answer()


@router.message(WithdrawStates.wait_gifts)
async def withdraw_count(message: Message, state: FSMContext) -> None:
    if not message.text or not message.text.isdigit():
        await message.answer("Введите число. Например: 1 или 3.")
        return
    count = int(message.text)
    if count <= 0:
        await message.answer("Количество должно быть больше 0.")
        return
    stars = count * GIFT_PRICE
    session_factory = get_session_factory()
    async with session_factory() as session:
        result = await session.execute(select(User).where(User.id == message.from_user.id))
        user = result.scalar_one_or_none()
        if not user or not user.activated:
            await message.answer("Сначала пройдите активацию, затем оформляйте вывод.")
            await state.clear()
            return
    async with session_factory() as session:
        request = await create_withdrawal(session, message.from_user.id, stars)
    if not request:
        await message.answer("Недостаточно звезд для выбранного количества подарков.")
        await state.clear()
        return
    await message.answer(
        f"✅ Заявка создана на <b>{stars}</b> ⭐.\n"
        "После обработки вы получите подарок в Telegram.",
        reply_markup=main_menu_kb(),
    )
    await state.clear()
