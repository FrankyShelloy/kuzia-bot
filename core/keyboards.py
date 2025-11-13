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


def reminder_choice_markup():
    """Return markup with preset reminder options and custom input option."""
    builder = InlineKeyboardBuilder()
    builder.row(CallbackButton(text="🔕 Без напоминания", payload="reminder_0"))
    builder.row(CallbackButton(text="🔔 5 минут", payload="reminder_5"))
    builder.row(CallbackButton(text="⏰ 15 минут", payload="reminder_15"))
    builder.row(CallbackButton(text="⏳ 30 минут", payload="reminder_30"))
    builder.row(CallbackButton(text="⏱️ 1 час", payload="reminder_60"))
    builder.row(CallbackButton(text="✏️ Другое время", payload="reminder_custom"))
    return builder.as_markup()


def day_choice_markup():
    """Return markup with day selection buttons for scheduling."""
    builder = InlineKeyboardBuilder()
    # Top row: Завтра, Послезавтра
    builder.row(
        CallbackButton(text="📆 Завтра", payload="day_tomorrow"),
        CallbackButton(text="📆 Послезавтра", payload="day_after_tomorrow")
    )
    # Days of week: 2x4 grid for readability
    builder.row(
        CallbackButton(text="🌗 Пн", payload="day_0"),
        CallbackButton(text="🌗 Вт", payload="day_1"),
        CallbackButton(text="🌗 Ср", payload="day_2"),
        CallbackButton(text="🌗 Чт", payload="day_3")
    )
    builder.row(
        CallbackButton(text="🌗 Пт", payload="day_4"),
        CallbackButton(text="🌗 Сб", payload="day_5"),
        CallbackButton(text="🌗 Вс", payload="day_6")
    )
    builder.row(CallbackButton(text="◀️ Отмена", payload="back_to_menu"))
    return builder.as_markup()

