from maxapi.utils.inline_keyboard import InlineKeyboardBuilder
from maxapi.types import CallbackButton


def main_keyboard_markup():
    """Return attachments list with the main inline keyboard markup.

    Keeps keyboard creation in one place so main.py stays clean.
    """
    builder = InlineKeyboardBuilder()
    builder.row(CallbackButton(text="➕ Добавить задачу", payload="cmd_add"))
    builder.row(CallbackButton(text="📋 Список задач", payload="cmd_list"))
    builder.row(CallbackButton(text="✅ Отметить выполненной", payload="cmd_done"))
    builder.row(CallbackButton(text="🤖 Разбить задачу с AI", payload="cmd_decompose"))
    builder.row(CallbackButton(text="➕ В расписание", payload="cmd_schedule_add"))
    builder.row(CallbackButton(text="📅 Показать расписание", payload="cmd_schedule"))
    builder.row(CallbackButton(text="🗑️ Удалить из расписания", payload="cmd_schedule_remove"))

    return builder.as_markup()


def back_to_menu_markup():
    """Return a small markup with a single button to go back to the main menu."""
    builder = InlineKeyboardBuilder()
    builder.row(CallbackButton(text="◀️ Обратно в меню", payload="back_to_menu"))
    return builder.as_markup()


def action_menu_markup():
    """Return markup with two buttons: 'Отметить ещё' and 'Обратно в меню'."""
    builder = InlineKeyboardBuilder()
    builder.row(
        CallbackButton(text="✅ Отметить ещё", payload="cmd_done")
    )
    builder.row(
        CallbackButton(text="◀️ Обратно в меню", payload="back_to_menu")
    )
    return builder.as_markup()


def action_schedule_menu_markup():
    """Return markup with options after working with schedule: add more or back to menu."""
    builder = InlineKeyboardBuilder()
    builder.row(
        CallbackButton(text="➕ Добавить ещё в расписание", payload="cmd_schedule_add")
    )
    builder.row(
        CallbackButton(text="◀️ Обратно в меню", payload="back_to_menu")
    )
    return builder.as_markup()


def action_schedule_remove_menu_markup():
    """Return markup with options after removing schedule entries: remove more or back to menu."""
    builder = InlineKeyboardBuilder()
    builder.row(
        CallbackButton(text="🗑️ Удалить ещё из расписания", payload="cmd_schedule_remove")
    )
    builder.row(
        CallbackButton(text="◀️ Обратно в меню", payload="back_to_menu")
    )
    return builder.as_markup()
