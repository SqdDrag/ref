from aiogram import F, Router
from aiogram.types import CallbackQuery
from sqlalchemy import select

from bot.keyboards.common import main_menu_kb, tasks_kb
from bot.services.media import edit_or_send_photo
from bot.services.subscription import is_subscribed_or_requested
from config.settings import load_settings
from db.models import User, UserTask
from db.session import get_session_factory


router = Router()
_settings = load_settings()


def _tasks_list() -> list[tuple[str, str]]:
    tasks = []
    for idx, channel in enumerate(_settings.task_channels, start=1):
        key = f"task_{idx}"
        title = f"Подписка на {channel}"
        tasks.append((key, title))
    return tasks


@router.callback_query(F.data == "menu:tasks")
async def tasks_menu(callback: CallbackQuery) -> None:
    tasks = _tasks_list()
    if not tasks:
        await edit_or_send_photo(
            callback,
            "tasks",
            "📝 <b>Заданий пока нет</b>.\nЗагляните чуть позже.",
            reply_markup=main_menu_kb(),
        )
        await callback.answer()
        return
    await edit_or_send_photo(
        callback,
        "tasks",
        "📝 <b>Доступные задания</b>\nВыберите и выполните условия:",
        reply_markup=tasks_kb(tasks),
    )
    await callback.answer()


@router.callback_query(F.data.startswith("task:"))
async def task_complete(callback: CallbackQuery) -> None:
    task_key = callback.data.split(":", 1)[1]
    tasks = _tasks_list()
    task_map = {key: title for key, title in tasks}
    if task_key not in task_map:
        await callback.answer("Задание не найдено", show_alert=True)
        return
    idx = int(task_key.split("_")[1]) - 1
    channel = _settings.task_channels[idx]
    session_factory = get_session_factory()
    async with session_factory() as session:
        user_result = await session.execute(select(User).where(User.id == callback.from_user.id))
        user = user_result.scalar_one_or_none()
        if not user or not user.activated:
            await callback.answer("Сначала пройдите активацию", show_alert=True)
            return
        if not user.ip:
            await callback.answer("Требуется веб-проверка", show_alert=True)
            return
        ip_result = await session.execute(select(User).where(User.ip == user.ip))
        same_ip_user = ip_result.scalar_one_or_none()
        if same_ip_user and same_ip_user.id != user.id:
            await callback.answer("IP уже использован", show_alert=True)
            return
        done_result = await session.execute(
            select(UserTask).where(UserTask.user_id == user.id, UserTask.task_key == task_key)
        )
        if done_result.scalar_one_or_none():
            await callback.answer("Задание уже выполнено", show_alert=True)
            return
        if not await is_subscribed_or_requested(callback.bot, channel, user.id):
            await callback.answer("Подпишитесь на канал", show_alert=True)
            return
        user.balance += _settings.task_reward
        session.add(UserTask(user_id=user.id, task_key=task_key))
        await session.commit()
    await callback.answer("Задание выполнено")
    await edit_or_send_photo(
        callback,
        "menu",
        f"✅ <b>Готово!</b> Начислено <b>{_settings.task_reward}</b> ⭐.\n"
        "Баланс обновлен.",
        reply_markup=main_menu_kb(),
    )
