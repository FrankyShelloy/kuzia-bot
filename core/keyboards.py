from maxapi.utils.inline_keyboard import InlineKeyboardBuilder
from maxapi.types import CallbackButton


def main_keyboard_markup():
    builder = InlineKeyboardBuilder()
    builder.row(CallbackButton(text="➕ Добавить задачу", payload="cmd_add"))
    builder.row(CallbackButton(text="📋 Список задач", payload="cmd_list"))
    builder.row(CallbackButton(text="✅ Отметить выполненной", payload="cmd_done"))
    builder.row(CallbackButton(text="🤖 Разбить задачу с AI", payload="cmd_decompose"))
    builder.row(CallbackButton(text="🏆 Достижения", payload="cmd_achievements"))
    builder.row(CallbackButton(text="➕ В расписание", payload="cmd_schedule_add"))
    builder.row(CallbackButton(text="📅 Показать расписание", payload="cmd_schedule"))
    builder.row(CallbackButton(text="🗑️ Удалить из расписания", payload="cmd_schedule_remove"))
    return builder.as_markup()


def back_to_menu_markup():
    builder = InlineKeyboardBuilder()
    builder.row(CallbackButton(text="◀️ Обратно в меню", payload="back_to_menu"))
    return builder.as_markup()


def action_menu_markup():
    builder = InlineKeyboardBuilder()
    builder.row(CallbackButton(text="✅ Отметить ещё", payload="cmd_done"))
    builder.row(CallbackButton(text="◀️ Обратно в меню", payload="back_to_menu"))
    return builder.as_markup()


def action_schedule_menu_markup():
    builder = InlineKeyboardBuilder()
    builder.row(CallbackButton(text="➕ Добавить ещё в расписание", payload="cmd_schedule_add"))
    builder.row(CallbackButton(text="◀️ Обратно в меню", payload="back_to_menu"))
    return builder.as_markup()


def action_schedule_remove_menu_markup():
    builder = InlineKeyboardBuilder()
    builder.row(CallbackButton(text="🗑️ Удалить ещё из расписания", payload="cmd_schedule_remove"))
    builder.row(CallbackButton(text="◀️ Обратно в меню", payload="back_to_menu"))
    return builder.as_markup()
