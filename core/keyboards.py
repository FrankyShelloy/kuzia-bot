from maxapi.utils.inline_keyboard import InlineKeyboardBuilder
from maxapi.types import CallbackButton


def main_keyboard_markup():
    builder = InlineKeyboardBuilder()
    
    # Основные действия с задачами
    builder.row(CallbackButton(text="➕ Добавить задачу", payload="cmd_add"))
    builder.row(
        CallbackButton(text="📋 Список задач", payload="cmd_list"),
        CallbackButton(text="✅ Отметить выполненной", payload="cmd_done")
    )
    
    # AI-функции
    builder.row(
        CallbackButton(text="🤖 Разбить задачу с AI", payload="cmd_decompose"),
        CallbackButton(text="📚 Подбор книг", payload="cmd_book_search")
    )
    
    # Аналитика и отчёты
    builder.row(
        CallbackButton(text="📊 Квартальный отчёт", payload="cmd_quarterly_report"),
        CallbackButton(text="🏆 Достижения", payload="cmd_achievements")
    )
    
    # Расписание
    builder.row(
        CallbackButton(text="➕ В расписание", payload="cmd_schedule_add"),
        CallbackButton(text="📅 Показать расписание", payload="cmd_schedule")
    )
    builder.row(CallbackButton(text="🗑️ Удалить из расписания", payload="cmd_schedule_remove"))
    
    # Настройки
    builder.row(
        CallbackButton(text="💬 Стиль мотивации", payload="cmd_motivation"),
        CallbackButton(text="🌍 Изменить часовой пояс", payload="cmd_change_timezone")
    )
    
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


def task_list_menu_markup():
    """Клавиатура для действий со списком задач."""
    builder = InlineKeyboardBuilder()
    builder.row(CallbackButton(text="🗑️ Очистить задачи", payload="cmd_clear_tasks"))
    builder.row(CallbackButton(text="◀️ Обратно в меню", payload="back_to_menu"))
    return builder.as_markup()


def clear_tasks_menu_markup():
    """Клавиатура для выбора типа очистки задач."""
    builder = InlineKeyboardBuilder()
    builder.row(CallbackButton(text="🗑️ Удалить ВСЕ задачи", payload="clear_all_tasks"))
    builder.row(CallbackButton(text="✅ Удалить выполненные", payload="clear_done_tasks"))
    builder.row(CallbackButton(text="⏰ Удалить просроченные", payload="clear_expired_tasks"))
    builder.row(CallbackButton(text="◀️ Отмена", payload="back_to_menu"))
    return builder.as_markup()


def confirm_clear_tasks_markup(clear_type: str):
    """Клавиатура подтверждения удаления задач."""
    builder = InlineKeyboardBuilder()
    builder.row(CallbackButton(text="✅ Да, удалить", payload=f"confirm_clear_{clear_type}"))
    builder.row(CallbackButton(text="❌ Отмена", payload="back_to_menu"))
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
    """Return markup with preset reminder options."""
    builder = InlineKeyboardBuilder()
    builder.row(CallbackButton(text="🔕 Без напоминания", payload="reminder_0"))
    builder.row(CallbackButton(text="🔔 5 минут", payload="reminder_5"))
    builder.row(CallbackButton(text="⏰ 15 минут", payload="reminder_15"))
    builder.row(CallbackButton(text="⏳ 30 минут", payload="reminder_30"))
    builder.row(CallbackButton(text="⏱️ 1 час", payload="reminder_60"))
    builder.row(CallbackButton(text="⏱️ 2 часа", payload="reminder_120"))
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
    """Return markup with Russian cities timezone options."""
    builder = InlineKeyboardBuilder()
    # Города РФ от востока к западу (Владивосток → Калининград)
    timezones = [
        ("🌅 Владивосток (UTC+10)", "Asia/Vladivostok"),
        ("🏔️ Якутск (UTC+9)", "Asia/Yakutsk"),
        ("❄️ Иркутск (UTC+8)", "Asia/Irkutsk"),
        ("🏭 Красноярск (UTC+7)", "Asia/Krasnoyarsk"),
        ("🏙️ Новосибирск (UTC+7)", "Asia/Novosibirsk"),
        ("⛰️ Омск (UTC+6)", "Asia/Omsk"),
        ("⛰️ Екатеринбург (UTC+5)", "Asia/Yekaterinburg"),
        ("🏛️ Самара (UTC+4)", "Europe/Samara"),
        ("🏛️ Москва (UTC+3)", "Europe/Moscow"),
        ("🏰 Калининград (UTC+2)", "Europe/Kaliningrad"),
    ]
    for text, tz in timezones:
        builder.row(CallbackButton(text=text, payload=f"tz_{tz}"))
    
    builder.row(CallbackButton(text="✏️ Другой часовой пояс", payload="tz_custom"))
    return builder.as_markup()


def decompose_count_markup():
    """Клавиатура выбора количества подзадач при декомпозиции."""
    builder = InlineKeyboardBuilder()
    builder.row(CallbackButton(text="3️⃣ Три подзадачи", payload="decomp_n_3"))
    builder.row(CallbackButton(text="4️⃣ Четыре подзадачи", payload="decomp_n_4"))
    builder.row(CallbackButton(text="5️⃣ Пять подзадач", payload="decomp_n_5"))
    builder.row(CallbackButton(text="◀️ Отмена", payload="back_to_menu"))
    return builder.as_markup()


def quarterly_report_menu_markup():
    """Клавиатура для выбора квартала для отчёта."""
    builder = InlineKeyboardBuilder()
    builder.row(CallbackButton(text="📊 Текущий квартал", payload="quarterly_current"))
    builder.row(
        CallbackButton(text="Q1", payload="quarterly_1"),
        CallbackButton(text="Q2", payload="quarterly_2")
    )
    builder.row(
        CallbackButton(text="Q3", payload="quarterly_3"),
        CallbackButton(text="Q4", payload="quarterly_4")
    )
    builder.row(CallbackButton(text="◀️ Обратно в меню", payload="back_to_menu"))
    return builder.as_markup()


def admin_menu_markup():
    """Административное меню для отладки (скрытое)."""
    builder = InlineKeyboardBuilder()
    builder.row(CallbackButton(text="🔍 Отладка задач", payload="cmd_debug_tasks"))
    builder.row(CallbackButton(text="◀️ Обратно в меню", payload="back_to_menu"))
    return builder.as_markup()