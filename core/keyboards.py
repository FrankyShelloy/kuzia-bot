from maxapi.utils.inline_keyboard import InlineKeyboardBuilder
from maxapi.types import CallbackButton


def main_keyboard_markup():
    builder = InlineKeyboardBuilder()
    builder.row(CallbackButton(text="➕ Добавить задачу", payload="cmd_add"))
    builder.row(CallbackButton(text="📋 Список задач", payload="cmd_list"))
    builder.row(CallbackButton(text="✅ Отметить выполненной", payload="cmd_done"))
    builder.row(CallbackButton(text="🤖 Разбить задачу с AI", payload="cmd_decompose"))
    builder.row(CallbackButton(text="🏆 Достижения", payload="cmd_achievements"))
    builder.row(CallbackButton(text="💬 Стиль мотивации", payload="cmd_motivation"))
    builder.row(CallbackButton(text="➕ В расписание", payload="cmd_schedule_add"))
    builder.row(CallbackButton(text="📅 Показать расписание", payload="cmd_schedule"))
    builder.row(CallbackButton(text="🗑️ Удалить из расписания", payload="cmd_schedule_remove"))
    builder.row(CallbackButton(text="🌍 Изменить часовой пояс", payload="cmd_change_timezone"))
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


def motivation_style_markup(current_style: str, enabled: bool = True):
    builder = InlineKeyboardBuilder()
    styles = [
        ("😊 Дружеский", "friendly"),
        ("😐 Нейтральный", "neutral"),
        ("💪 Агрессивный", "aggressive")
    ]
    for text, style in styles:
        marker = "✅ " if style == current_style else ""
        builder.row(CallbackButton(text=f"{marker}{text}", payload=f"set_style_{style}"))
    
    toggle_text = "🔕 Выключить напоминания" if enabled else "🔔 Включить напоминания"
    builder.row(CallbackButton(text=toggle_text, payload="toggle_reminders"))
    builder.row(CallbackButton(text="◀️ Обратно в меню", payload="back_to_menu"))
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
    # Top row: Сегодня, Завтра, Послезавтра
    builder.row(
        CallbackButton(text="🌅 Сегодня", payload="day_today"),
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


def timezone_choice_markup():
    """Return markup with popular timezone options."""
    builder = InlineKeyboardBuilder()
    timezones = [
        ("🇷🇺 Moscow (UTC+3)", "Europe/Moscow"),
        ("🇺🇦 Kyiv (UTC+2)", "Europe/Kyiv"),
        ("🇹🇭 Bangkok (UTC+7)", "Asia/Bangkok"),
        ("🇮🇳 India (UTC+5:30)", "Asia/Kolkata"),
        ("🇸🇬 Singapore (UTC+8)", "Asia/Singapore"),
        ("🇯🇵 Tokyo (UTC+9)", "Asia/Tokyo"),
        ("🇺🇸 New York (UTC-5)", "America/New_York"),
        ("🇬🇧 London (UTC+0)", "Europe/London"),
    ]
    for text, tz in timezones:
        builder.row(CallbackButton(text=text, payload=f"tz_{tz}"))
    
    builder.row(CallbackButton(text="✏️ Другой часовой пояс", payload="tz_custom"))
    return builder.as_markup()

