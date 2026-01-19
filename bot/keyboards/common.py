from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup


def main_menu_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="💰 Баланс", callback_data="menu:balance"),
                InlineKeyboardButton(text="👥 Рефералы", callback_data="menu:referrals"),
            ],
            [
                InlineKeyboardButton(text="📝 Задания", callback_data="menu:tasks"),
                InlineKeyboardButton(text="🎁 Вывод", callback_data="menu:withdraw"),
            ],
        ]
    )


def web_check_kb(link: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="Перейти на сайт", url=link)],
            [InlineKeyboardButton(text="Я прошел проверку", callback_data="web_check")],
        ]
    )


def subscriptions_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[[InlineKeyboardButton(text="Проверить подписки", callback_data="check_subs")]]
    )


def tasks_kb(tasks: list[tuple[str, str]]) -> InlineKeyboardMarkup:
    buttons = [[InlineKeyboardButton(text=title, callback_data=f"task:{key}")] for key, title in tasks]
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def back_to_menu_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="В меню", callback_data="to_menu")]])