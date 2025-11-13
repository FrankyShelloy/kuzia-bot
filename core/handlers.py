import logging
import logging
from typing import Optional

from core.utils import (
    should_ignore_message_event_on_start,
    should_ignore_callback_event_on_start,
    is_event_allowed,
    is_callback_allowed,
    _resolve_chat_id,
    is_valid_timezone,
    find_timezone_by_keyword,
    format_timezone_list,
    is_valid_reminder_minutes,
    get_reminder_presets,
    minutes_to_human_readable,
    format_reminder_presets,
)
from core.state import awaiting_actions
from core.keyboards import (
    main_keyboard_markup,
    back_to_menu_markup,
    action_menu_markup,
    action_schedule_menu_markup,
    action_schedule_remove_menu_markup,
    reminder_choice_markup,
    day_choice_markup,
    timezone_choice_markup,
    motivation_style_markup,
)
from core.models import Task, Schedule, UserSettings
from core.callbacks import derive_user_id, derive_chat_id, extract_payload, deep_search, respond
from core.achievements import check_and_unlock_achievements, get_all_achievements
from core.motivation import (
    get_or_create_settings,
    update_motivation_style,
    MotivationStyle,
    generate_motivation_message,
)
from maxapi.types import BotStarted, Command, MessageCreated
from maxapi.filters import F


# Константы для дней недели
DAY_NAMES_RU = ["Понедельник", "Вторник", "Среда", "Четверг", "Пятница", "Суббота", "Воскресенье"]

DAY_NAMES = {
    "пн": 0, "понедельник": 0, "пнд": 0, "monday": 0, "mon": 0,
    "вт": 1, "вторник": 1, "втр": 1, "tuesday": 1, "tue": 1,
    "ср": 2, "среда": 2, "срд": 2, "wednesday": 2, "wed": 2,
    "чт": 3, "четверг": 3, "чтв": 3, "thursday": 3, "thu": 3,
    "пт": 4, "пятница": 4, "птн": 4, "friday": 4, "fri": 4,
    "сб": 5, "суббота": 5, "сбт": 5, "saturday": 5, "sat": 5,
    "вс": 6, "воскресенье": 6, "вск": 6, "sunday": 6, "sun": 6,
}


def register_handlers(dp, bot):
    """Register message and callback handlers on the provided dispatcher."""

    @dp.bot_started()
    async def on_bot_started(event: BotStarted):
        await event.bot.send_message(
            chat_id=event.chat_id,
            text='Привет! Я Кузя — твой персональный помощник по продуктивности и развитию. Начнем с команды /start!'
        )

    @dp.message_created(Command('start'))
    async def start_command(event: MessageCreated):
        try:
            if should_ignore_message_event_on_start(event):
                logging.info("Ignoring historical message event on startup (start_command)")
                return
        except Exception:
            pass

        chat_id = _resolve_chat_id(event)
        user_id = str(event.message.sender.user_id)
        
        # Проверяем, есть ли timezone у пользователя
        user_settings = await UserSettings.filter(user_id=user_id).first()
        
        if not user_settings or not user_settings.timezone:
            # Просим выбрать timezone - это критично для работы бота
            await event.message.answer(
                "🌍 Привет! Я Кузя — твой персональный помощник по продуктивности и развитию.\n\n"
                "Сначала выбери свой часовой пояс:",
                attachments=[timezone_choice_markup()]
            )
            return
        
        # Если timezone уже установлен, показываем главное меню
        completed_count = await Task.filter(chat_id=chat_id, status="done").count()

        start_message = (
            "👋 Привет! Я Кузя — твой персональный помощник по продуктивности и развитию.\n\n"
            f"✅ Выполнено задач: {completed_count}\n\n"
            "Выберите действие ниже: я помогу с задачами, расписанием и напоминаниями."
        )
        await event.message.answer(text=start_message, attachments=[main_keyboard_markup()])

    @dp.message_created(Command('add'))
    async def add_task_command(event: MessageCreated):
        try:
            if not is_event_allowed(event):
                logging.info("/add from disallowed user/chat — ignoring")
                return
        except Exception:
            pass
        try:
            if should_ignore_message_event_on_start(event):
                logging.info("Ignoring historical message event on startup (add_task_command)")
                return
        except Exception:
            pass
        text = event.message.body.text or ""
        parts = text.split(maxsplit=1)
        if len(parts) < 2 or not parts[1].strip():
            await event.message.answer("Использование: /add <текст задачи>")
            return
        task_text = parts[1].strip()
        await Task.create(
            chat_id=_resolve_chat_id(event),
            user_id=str(event.message.sender.user_id),
            text=task_text
        )
        await event.message.answer(
            "✅ Задача добавлена. Если хотите добавить ещё — просто пришлите текст задачи.",
            attachments=[back_to_menu_markup()]
        )

    @dp.message_created(Command('decompose'))
    async def decompose_task(event: MessageCreated):
        try:
            if should_ignore_message_event_on_start(event):
                logging.info("Ignoring historical message event on startup (decompose_task)")
                return
        except Exception:
            pass
        text = event.message.body.text or ""
        parts = text.split(maxsplit=1)
        if len(parts) < 2 or not parts[1].strip():
            await event.message.answer("Использование: /decompose <текст задачи>\nПример: /decompose Организовать поездку на море")
            return
        
        task_text = parts[1].strip()
        chat_id = _resolve_chat_id(event)
        user_id = str(event.message.sender.user_id)
        
        await event.message.answer("🤖 Анализирую задачу и разбиваю на подзадачи...")
        
        from core.ai_core import decompose_with_ai
        subtasks = await decompose_with_ai(int(chat_id), task_text)
        
        if not subtasks:
            await event.message.answer("❌ Не удалось разбить задачу. Попробуйте позже или проверьте настройки AI.", attachments=[back_to_menu_markup()])
            return
        
        main_task = await Task.create(
            chat_id=chat_id,
            user_id=user_id,
            text=task_text,
            status="pending"
        )
        
        for subtask_text in subtasks:
            await Task.create(
                chat_id=chat_id,
                user_id=user_id,
                text=subtask_text,
                status="pending",
                parent_id=main_task.id
            )
        
        result = f"✅ Задача разбита на {len(subtasks)} подзадач:\n\n"
        result += f"📋 Главная задача: {task_text}\n\n"
        result += "Подзадачи:\n"
        for i, subtask in enumerate(subtasks, 1):
            result += f"{i}. {subtask}\n"
        
        await event.message.answer(result, attachments=[back_to_menu_markup()])

    @dp.message_created(F.message.body.text & ~F.message.body.text.startswith('/'))
    async def add_task_plain_text(event: MessageCreated):
        logging.info("add_task_plain_text handler triggered")
        try:
            if not is_event_allowed(event):
                logging.info("Message from disallowed user/chat — ignoring")
                return
        except Exception:
            logging.exception("Exception in is_event_allowed check")
            pass
        try:
            if should_ignore_message_event_on_start(event):
                logging.info("Ignoring historical message event on startup (plain_text)")
                return
        except Exception:
            pass

        user_key = None
        try:
            user_key = str(event.message.sender.user_id)
        except Exception:
            user_key = None
        chat_key = None
        try:
            chat_key = _resolve_chat_id(event)
        except Exception:
            chat_key = None

        text = (event.message.body.text or "").strip()
        if not text:
            return

        user_id = user_key
        if user_id is None:
            try:
                user_id = str(event.message.sender.user_id)
            except Exception:
                user_id = None

        state = None
        if user_key and user_key in awaiting_actions:
            state = awaiting_actions.get(user_key)
            logging.info("Consuming awaiting state by user_key=%s: %s", user_key, state)
        elif chat_key and chat_key in awaiting_actions:
            state = awaiting_actions.get(chat_key)
            logging.info("Consuming awaiting state by chat_key=%s: %s", chat_key, state)
        
        if not state:
            logging.info("No awaiting state found for user_key=%s chat_key=%s. awaiting_actions keys: %s", user_key, chat_key, list(awaiting_actions.keys()))
        
        if state:
            action = state.get('action')
            chat_id = state.get('chat_id')

            if action == 'waiting_for_custom_timezone':
                # Пользователь вводит свой часовой пояс
                timezone = text.strip()
                
                if not timezone:
                    await event.message.answer("❌ Часовой пояс не может быть пустым")
                    return
                
                # Проверяем валидность timezone
                if not is_valid_timezone(timezone):
                    await event.message.answer(
                        f"❌ Неверный часовой пояс: {timezone}\n\n"
                        "Примеры правильных часовых поясов:\n"
                        "• Europe/Moscow\n"
                        "• Asia/Bangkok\n"
                        "• America/New_York\n\n"
                        "Или введите /start для выбора из предложенных вариантов"
                    )
                    return
                
                # Очищаем состояние
                if user_key:
                    awaiting_actions.pop(user_key, None)
                if chat_key:
                    awaiting_actions.pop(chat_key, None)
                
                # Обновляем или создаём UserSettings
                if user_id:
                    user_settings = await UserSettings.filter(user_id=str(user_id)).first()
                    if user_settings:
                        user_settings.timezone = timezone
                        await user_settings.save()
                    else:
                        await UserSettings.create(
                            user_id=str(user_id),
                            chat_id=str(chat_id),
                            timezone=timezone
                        )
                    logging.info(f"User {user_id} set custom timezone to {timezone}")
                    await event.message.answer(
                        f"✅ Часовой пояс установлен: {timezone}\n\n"
                        "Теперь можешь использовать все функции бота!",
                        attachments=[main_keyboard_markup()]
                    )
                return

            if action == 'custom_reminder_input':
                # Пользователь вводит количество минут для напоминания
                reminder_text = text.strip()
                schedule_id = state.get('schedule_id')
                logging.info(f"Processing custom_reminder_input: text={reminder_text}, schedule_id={schedule_id}")
                
                if not reminder_text:
                    await event.message.answer(
                        "❌ Пожалуйста, введите число минут для напоминания",
                        attachments=[back_to_menu_markup()]
                    )
                    return
                
                # Пытаемся преобразовать в число
                try:
                    reminder_minutes = int(reminder_text)
                except ValueError:
                    await event.message.answer(
                        f"❌ '{reminder_text}' не является числом.\n\n"
                        "Пожалуйста, введите целое число (например: 10, 30, 60)",
                        attachments=[back_to_menu_markup()]
                    )
                    return
                
                # Проверяем валидность
                if not is_valid_reminder_minutes(reminder_minutes):
                    await event.message.answer(
                        f"❌ Неверное значение: {reminder_minutes}\n\n"
                        "Напоминание должно быть в диапазоне 0-10080 минут",
                        attachments=[back_to_menu_markup()]
                    )
                    return
                
                # Очищаем состояние
                if user_key:
                    awaiting_actions.pop(user_key, None)
                if chat_key:
                    awaiting_actions.pop(chat_key, None)
                
                # Обновляем расписание
                try:
                    schedule = await Schedule.filter(id=schedule_id, chat_id=chat_id).first()
                    if schedule:
                        schedule.reminder_minutes = reminder_minutes
                        await schedule.save(update_fields=["reminder_minutes", "updated_at"])
                        
                        reminder_label = minutes_to_human_readable(reminder_minutes) if reminder_minutes > 0 else "выключено"
                        day_name = DAY_NAMES_RU[schedule.day_of_week]
                        
                        response = f"✅ Расписание сохранено: {day_name} в {schedule.time}\n"
                        response += f"📝 Задача: {schedule.text}\n"
                        response += f"⏰ Основное напоминание: за 1 минуту до события\n"
                        if reminder_minutes > 0:
                            response += f"⏳ Дополнительное напоминание: {reminder_label}"
                        
                        await event.message.answer(response, attachments=[action_schedule_menu_markup()])
                        logging.info(f"Custom reminder set: schedule_id={schedule_id}, reminder_minutes={reminder_minutes}")
                    else:
                        await event.message.answer("❌ Расписание не найдено", attachments=[back_to_menu_markup()])
                except Exception as e:
                    logging.exception("Ошибка при сохранении кастомного напоминания")
                    await event.message.answer(
                        f"❌ Ошибка при сохранении: {str(e)}",
                        attachments=[back_to_menu_markup()]
                    )
                return

            if action == 'decompose_input':
                task_text = text.strip()
                if not task_text:
                    await event.message.answer("Пожалуйста, отправьте текст задачи для разбиения.", attachments=[back_to_menu_markup()])
                    return
                
                logging.info("Clearing awaiting keys: user_key=%s chat_key=%s", user_key, chat_key)
                if user_key:
                    awaiting_actions.pop(user_key, None)
                if chat_key:
                    awaiting_actions.pop(chat_key, None)
                
                await event.message.answer("🤖 Анализирую задачу и разбиваю на подзадачи...")
                
                from core.ai_core import decompose_with_ai
                subtasks = await decompose_with_ai(int(chat_id), task_text)
                
                if not subtasks:
                    await event.message.answer("❌ Не удалось разбить задачу. Попробуйте позже или проверьте настройки AI.", attachments=[back_to_menu_markup()])
                    return
                
                main_task = await Task.create(
                    chat_id=chat_id,
                    user_id=user_id,
                    text=task_text,
                    status="pending"
                )
                
                for subtask_text in subtasks:
                    await Task.create(
                        chat_id=chat_id,
                        user_id=user_id,
                        text=subtask_text,
                        status="pending",
                        parent_id=main_task.id
                    )
                
                result = f"✅ Задача разбита на {len(subtasks)} подзадач:\n\n"
                result += f"📋 Главная задача: {task_text}\n\n"
                result += "Подзадачи:\n"
                for i, subtask in enumerate(subtasks, 1):
                    result += f"{i}. {subtask}\n"
                
                await event.message.answer(result, attachments=[back_to_menu_markup()])
                return

            if action == 'done_selection':
                ids = []
                for token in text.split():
                    try:
                        ids.append(int(token))
                    except Exception:
                        continue
                if not ids:
                    await event.message.answer("Не удалось распознать номера. Отправьте числа через пробел (например: 3 или 1 2 5).", attachments=[back_to_menu_markup()])
                    return
                index_map = state.get('map') or {}
                succeeded, failed = [], []
                for shown_num in ids:
                    real_id = index_map.get(shown_num) if index_map else shown_num
                    task = await Task.filter(id=real_id, chat_id=chat_id).first()
                    if task is None or task.status == 'done':
                        failed.append(shown_num)
                        continue
                    task.status = 'done'
                    await task.save(update_fields=["status", "updated_at"])
                    succeeded.append(shown_num)
                logging.info("Clearing awaiting keys: user_key=%s chat_key=%s", user_key, chat_key)
                if user_key:
                    awaiting_actions.pop(user_key, None)
                if chat_key:
                    awaiting_actions.pop(chat_key, None)
                parts = []
                if succeeded:
                    parts.append(f"✅ Отмечены как выполненные: {', '.join(map(str, succeeded))}")
                if failed:
                    parts.append(f"⚠️ Необработаны/не найдены: {', '.join(map(str, failed))}")
                
                if chat_id:
                    completed_count = await Task.filter(chat_id=str(chat_id), status="done").count()
                    parts.append(f"\n📊 Всего выполнено задач: {completed_count}")
                    
                    new_achievement = await check_and_unlock_achievements(str(chat_id))
                    if new_achievement:
                        parts.append(
                            f"\n\n🎉 НОВОЕ ДОСТИЖЕНИЕ РАЗБЛОКИРОВАНО!\n"
                            f"{new_achievement.emoji} {new_achievement.title}\n"
                            f"({new_achievement.milestone} задач выполнено)"
                        )
                
                reply = "\n".join(parts)
                logging.info("Sending done-selection reply with task action menu to user=%s chat=%s", user_key or chat_key, chat_id)
                await event.message.answer(reply, attachments=[action_menu_markup()])
                return

            if action == 'schedule_remove_selection':
                ids = []
                for token in text.split():
                    try:
                        ids.append(int(token))
                    except Exception:
                        continue
                if not ids:
                    await event.message.answer("Не удалось распознать номера. Отправьте числа через пробел (например: 3 или 1 2 5).", attachments=[back_to_menu_markup()])
                    return
                index_map = state.get('map') or {}
                succeeded, failed = [], []
                for shown_num in ids:
                    real_id = index_map.get(shown_num) if index_map else shown_num
                    sched = await Schedule.filter(id=real_id, chat_id=chat_id).first()
                    if sched is None or not sched.enabled:
                        failed.append(shown_num)
                        continue
                    sched.enabled = False
                    await sched.save(update_fields=["enabled", "updated_at"])
                    succeeded.append(shown_num)
                logging.info("Clearing awaiting keys: user_key=%s chat_key=%s", user_key, chat_key)
                if user_key:
                    awaiting_actions.pop(user_key, None)
                if chat_key:
                    awaiting_actions.pop(chat_key, None)
                parts = []
                if succeeded:
                    parts.append(f"✅ Записи расписания удалены: {', '.join(map(str, succeeded))}")
                if failed:
                    parts.append(f"⚠️ Необработаны/не найдены: {', '.join(map(str, failed))}")
                reply = "\n".join(parts)
                logging.info("Sending schedule removal reply with schedule-remove menu to user=%s chat=%s", user_key or chat_key, chat_id)
                await event.message.answer(reply, attachments=[action_schedule_remove_menu_markup()])
                return

            if action == 'waiting_for_day':
                # Пользователь нажал на день - теперь ждём ввода времени через текстовое сообщение
                # Но это состояние уже должно быть переведено в waiting_for_time
                # Если пользователь пишет текст в этом состоянии - это ошибка
                await event.message.answer(
                    "⏳ Ожидаю выбора дня через кнопки выше.",
                    attachments=[back_to_menu_markup()]
                )
                return

            if action == 'waiting_for_time':
                # Пользователь вводит время после выбора дня
                logging.info("Processing waiting_for_time: text=%s", text)
                time_str = text.strip()
                day_of_week = state.get('day_of_week')
                chat_id = state.get('chat_id')
                
                logging.info("waiting_for_time: day_of_week=%s chat_id=%s", day_of_week, chat_id)
                
                if day_of_week is None:
                    await event.message.answer(
                        "❌ Ошибка: потеряна информация о выборе дня. Начните заново.",
                        attachments=[back_to_menu_markup()]
                    )
                    return
                
                # Валидация времени
                if not (len(time_str) == 5 and time_str[2] == ':' and time_str[:2].isdigit() and time_str[3:].isdigit()):
                    await event.message.answer(
                        "⏰ Неверный формат. Укажите время как HH:MM\nНапример: 09:00",
                        attachments=[back_to_menu_markup()]
                    )
                    return
                
                hour, minute = int(time_str[:2]), int(time_str[3:])
                if hour < 0 or hour > 23 or minute < 0 or minute > 59:
                    await event.message.answer(
                        "❌ Некорректное время. Часы: 0-23, минуты: 0-59",
                        attachments=[back_to_menu_markup()]
                    )
                    return
                
                # Очищаем ВСЕ старые состояния перед установкой waiting_for_text
                keys_to_remove = []
                for key in list(awaiting_actions.keys()):
                    state_check = awaiting_actions.get(key)
                    if state_check and state_check.get('chat_id') == chat_id:
                        keys_to_remove.append(key)
                
                for key in keys_to_remove:
                    awaiting_actions.pop(key, None)
                
                logging.info("Clearing all old states before waiting_for_text: keys_removed=%s", keys_to_remove)
                
                # Теперь ждём текста задачи
                if user_key:
                    awaiting_actions[user_key] = {
                        'action': 'waiting_for_text',
                        'day_of_week': day_of_week,
                        'time': time_str,
                        'chat_id': chat_id
                    }
                if chat_key:
                    awaiting_actions[chat_key] = {
                        'action': 'waiting_for_text',
                        'day_of_week': day_of_week,
                        'time': time_str,
                        'chat_id': chat_id
                    }
                
                await event.message.answer(
                    f"⏰ Время установлено: {time_str}\n\n📝 Теперь введите текст для расписания\nНапример: Встреча с командой",
                    attachments=[back_to_menu_markup()]
                )
                logging.info("awaiting state set: user=%s chat=%s action=waiting_for_text time=%s day=%s", user_key, chat_key, time_str, day_of_week)
                return

            if action == 'waiting_for_text':
                # Пользователь вводит текст задачи
                task_text = text.strip()
                day_of_week = state.get('day_of_week')
                time_str = state.get('time')
                chat_id = state.get('chat_id')
                
                if day_of_week is None or time_str is None:
                    await event.message.answer(
                        "❌ Ошибка: потеряны данные. Начните заново.",
                        attachments=[back_to_menu_markup()]
                    )
                    return
                
                if not task_text:
                    await event.message.answer(
                        "📝 Текст не может быть пустым. Введите текст для расписания.",
                        attachments=[back_to_menu_markup()]
                    )
                    return
                
                # Получаем timezone пользователя или создаём с default
                user_settings = await UserSettings.filter(user_id=user_id).first()
                if user_settings:
                    user_timezone = user_settings.timezone
                else:
                    # Если timezone не установлена, создаём с Asia/Bangkok
                    await UserSettings.create(
                        user_id=user_id,
                        chat_id=chat_id,
                        timezone="Asia/Bangkok"
                    )
                    user_timezone = "Asia/Bangkok"
                    logging.info(f"Created default UserSettings for user {user_id} with timezone Asia/Bangkok")
                
                # Создаём расписание
                logging.info(f"About to create schedule: day_of_week={day_of_week}, time={time_str}, text={task_text}")
                schedule = await Schedule.create(
                    chat_id=chat_id,
                    user_id=user_id,
                    text=task_text,
                    day_of_week=day_of_week,
                    time=time_str,
                    reminder_minutes=0,
                    timezone=user_timezone,
                    enabled=True
                )
                logging.info(f"Created schedule: id={schedule.id}, user={user_id}, chat={chat_id}, day={day_of_week}, time={time_str}, tz={user_timezone}")
                logging.info(f"Schedule model day_of_week AFTER create: {schedule.day_of_week}")
                
                # Очищаем ВСЕ состояния перед установкой reminder_choice
                keys_to_remove = []
                for key in list(awaiting_actions.keys()):
                    state_check = awaiting_actions.get(key)
                    if state_check and state_check.get('chat_id') == chat_id:
                        keys_to_remove.append(key)
                
                for key in keys_to_remove:
                    awaiting_actions.pop(key, None)
                
                logging.info("Clearing all old states before reminder_choice: keys_removed=%s", keys_to_remove)
                
                # Спрашиваем напоминание через кнопки
                from core.handlers import DAY_NAMES_RU
                day_name = DAY_NAMES_RU[day_of_week]
                info_msg = f"✅ Расписание добавлено:\n{day_name} в {time_str} - {task_text}\n\n"
                info_msg += "⏰ Основное напоминание: за 1 минуту до события\n"
                info_msg += "Выберите дополнительное напоминание:"
                
                # Сохраняем ID расписания для выбора напоминания
                awaiting_actions[user_key] = {'action': 'reminder_choice', 'schedule_id': schedule.id, 'chat_id': chat_id}
                awaiting_actions[chat_key] = {'action': 'reminder_choice', 'schedule_id': schedule.id, 'chat_id': chat_id}
                
                await event.message.answer(info_msg, attachments=[reminder_choice_markup()])
                logging.info("awaiting state set for reminder choice: user=%s chat=%s schedule_id=%s", user_key, chat_key, schedule.id)
                return

            if action == 'schedule_add':
                parts = text.split(maxsplit=3)
                if len(parts) < 3:
                    await event.message.answer(
                        "Использование: отправьте сообщение в формате: <день> <время> <текст>\nПример: понедельник 09:00 Утренняя зарядка",
                        attachments=[back_to_menu_markup()]
                    )
                    return
                day_str = parts[0].strip().lower()
                time_str = parts[1].strip()
                task_text = parts[2].strip()
                
                day_of_week = None
                if day_str.isdigit():
                    day_of_week = int(day_str)
                    if day_of_week < 0 or day_of_week > 6:
                        await event.message.answer("День недели должен быть от 0 (понедельник) до 6 (воскресенье)", attachments=[back_to_menu_markup()])
                        return
                elif day_str == "завтра":
                    from datetime import datetime
                    import pytz
                    now_utc = datetime.now(pytz.UTC)
                    current_weekday = now_utc.weekday()
                    day_of_week = (current_weekday + 1) % 7
                elif day_str == "послезавтра":
                    from datetime import datetime
                    import pytz
                    now_utc = datetime.now(pytz.UTC)
                    current_weekday = now_utc.weekday()
                    day_of_week = (current_weekday + 2) % 7
                else:
                    from core.handlers import DAY_NAMES, DAY_NAMES_RU
                    day_of_week = DAY_NAMES.get(day_str)
                    if day_of_week is None:
                        await event.message.answer(f"Неизвестный день недели: {parts[0]}\nИспользуйте: пн, вт, ср, чт, пт, сб, вс, завтра, послезавтра или числа 0-6", attachments=[back_to_menu_markup()])
                        return
                if not (len(time_str) == 5 and time_str[2] == ':' and time_str[:2].isdigit() and time_str[3:].isdigit()):
                    await event.message.answer("Время должно быть в формате HH:MM (например, 09:00)", attachments=[back_to_menu_markup()])
                    return
                hour, minute = int(time_str[:2]), int(time_str[3:])
                if hour < 0 or hour > 23 or minute < 0 or minute > 59:
                    await event.message.answer("Некорректное время. Часы: 0-23, минуты: 0-59", attachments=[back_to_menu_markup()])
                    return
                chat_id = state.get('chat_id')
                
                # Получаем timezone пользователя
                user_settings = await UserSettings.filter(user_id=user_id).first()
                user_timezone = user_settings.timezone if user_settings else "UTC"
                
                # Создаём расписание с напоминанием=0, потом спросим через кнопки
                schedule = await Schedule.create(
                    chat_id=chat_id,
                    user_id=user_id,
                    text=task_text,
                    day_of_week=day_of_week,
                    time=time_str,
                    reminder_minutes=0,
                    timezone=user_timezone
                )
                logging.info("Clearing awaiting keys after schedule creation: user_key=%s chat_key=%s", user_key, chat_key)
                if user_key:
                    awaiting_actions.pop(user_key, None)
                if chat_key:
                    awaiting_actions.pop(chat_key, None)
                
                # Теперь спрашиваем напоминание через кнопки
                from core.handlers import DAY_NAMES_RU
                day_name = DAY_NAMES_RU[day_of_week]
                info_msg = f"✅ Расписание добавлено: {day_name} в {time_str} - {task_text}\n"
                info_msg += f"⏰ Основное напоминание: за 1 минуту до события\n\n"
                info_msg += "Выберите когда еще напоминать:"
                
                # Сохраняем ID расписания в состоянии для обработки выбора напоминания
                awaiting_actions[user_key] = {'action': 'reminder_choice', 'schedule_id': schedule.id, 'chat_id': chat_id}
                awaiting_actions[chat_key] = {'action': 'reminder_choice', 'schedule_id': schedule.id, 'chat_id': chat_id}
                
                await event.message.answer(info_msg, attachments=[reminder_choice_markup()])
                return

            if action == 'custom_reminder_input':
                # Пользователь вводит кастомное значение напоминания
                reminder_text = text.strip().lower()
                schedule_id = state.get('schedule_id')
                chat_id = state.get('chat_id')
                
                # Обработка отключения напоминания
                if reminder_text in ('off', 'none', '0', 'выкл', 'выключить'):
                    reminder_minutes = 0
                else:
                    try:
                        reminder_minutes = int(text.strip())
                    except ValueError:
                        await event.message.answer(
                            "❌ Пожалуйста, введите число минут (0-10080) или 'off' для выключения.",
                            attachments=[back_to_menu_markup()]
                        )
                        return
                
                if not is_valid_reminder_minutes(reminder_minutes):
                    await event.message.answer(
                        f"❌ Неверное значение. Введите число от 0 до 10080 минут.",
                        attachments=[back_to_menu_markup()]
                    )
                    return
                
                # Обновляем расписание
                try:
                    schedule = await Schedule.filter(id=schedule_id, chat_id=chat_id).first()
                    if schedule:
                        schedule.reminder_minutes = reminder_minutes
                        await schedule.save(update_fields=["reminder_minutes", "updated_at"])
                        
                        reminder_label = minutes_to_human_readable(reminder_minutes) if reminder_minutes > 0 else "выключено"
                        day_name = DAY_NAMES_RU[schedule.day_of_week]
                        response = f"✅ Расписание сохранено: {day_name} в {schedule.time}\n"
                        response += f"📝 Задача: {schedule.text}\n"
                        response += f"⏰ Основное напоминание: за 1 минуту до события\n"
                        if reminder_minutes > 0:
                            response += f"⏳ Дополнительное напоминание: {reminder_label}"
                        
                        # Очищаем состояние
                        if user_key:
                            awaiting_actions.pop(user_key, None)
                        if chat_key:
                            awaiting_actions.pop(chat_key, None)
                        
                        await event.message.answer(response, attachments=[action_schedule_menu_markup()])
                    else:
                        await event.message.answer("❌ Расписание не найдено.", attachments=[back_to_menu_markup()])
                except Exception as e:
                    logging.exception("Ошибка при обновлении кастомного напоминания")
                    await event.message.answer(f"❌ Ошибка: {str(e)}", attachments=[back_to_menu_markup()])
                return

            if action == 'reminder_choice':
                # Это состояние должно обрабатываться только через callback (кнопки)
                # Если текст отправлен - просим нажать кнопку
                await event.message.answer(
                    "👆 Пожалуйста, выберите напоминание через кнопки выше.",
                    attachments=[back_to_menu_markup()]
                )
                return

            # Если состояние не было обработано выше
            logging.warning("Unhandled state action: %s", action)
            await event.message.answer(
                f"⚠️ Неизвестное состояние: {action}. Начните заново.",
                attachments=[back_to_menu_markup()]
            )
            return

        logging.info("Creating task: user_id=%s text=%s", user_id, text[:50])
        await Task.create(
            chat_id=_resolve_chat_id(event),
            user_id=user_id,
            text=text
        )
        logging.info("Task created successfully, sending response")
        await event.message.answer(
            "📝 Задача принята. Хотите добавить ещё — просто пришлите текст задачи.",
            attachments=[back_to_menu_markup()]
        )
        logging.info("Response sent successfully")

    @dp.message_created(Command('list'))
    async def list_tasks(event: MessageCreated):
        try:
            if should_ignore_message_event_on_start(event):
                logging.info("Ignoring historical message event on startup (list_tasks)")
                return
        except Exception:
            pass
        chat_id = _resolve_chat_id(event)
        tasks = await Task.filter(chat_id=chat_id).order_by("status", "created_at")
        if not tasks:
            await event.message.answer("Задач пока нет. Добавьте новую командой /add <текст>")
            return
        lines = []
        for idx, task in enumerate(tasks, start=1):
            status = "✅" if task.status == "done" else "🔸"
            lines.append(f"{idx}. {status} {task.text}")
        await event.message.answer("Список задач:\n" + "\n".join(lines))

    @dp.message_created(Command('done'))
    async def mark_task_done(event: MessageCreated):
        try:
            if should_ignore_message_event_on_start(event):
                logging.info("Ignoring historical message event on startup (mark_task_done)")
                return
        except Exception:
            pass
        text = event.message.body.text or ""
        parts = text.split(maxsplit=1)
        if len(parts) < 2 or not parts[1].strip():
            await event.message.answer("Использование: /done <id задачи>")
            return
        try:
            task_id = int(parts[1].strip())
        except ValueError:
            await event.message.answer("ID задачи должен быть числом. Пример: /done 3")
            return
        chat_id = _resolve_chat_id(event)
        
        task = await Task.filter(id=task_id, chat_id=chat_id).first()
        if task is None:
            tasks = await Task.filter(chat_id=chat_id).order_by("status", "created_at")
            if 1 <= task_id <= len(tasks):
                task = tasks[task_id - 1]
            else:
                await event.message.answer("Задача не найдена.")
                return
        if task.status == "done":
            await event.message.answer("Эта задача уже выполнена ✅")
            return
        task.status = "done"
        await task.save(update_fields=["status", "updated_at"])
        await event.message.answer(f"Задача {task.id} отмечена как выполненная ✅")

    @dp.message_created(Command('schedule_add'))
    async def add_schedule(event: MessageCreated):
        try:
            if should_ignore_message_event_on_start(event):
                logging.info("Ignoring historical message event on startup (add_schedule)")
                return
        except Exception:
            pass
        
        user_id = str(event.message.sender.user_id)
        chat_id = _resolve_chat_id(event)
        user_key = user_id
        chat_key = chat_id
        
        # Показываем кнопки для выбора дня
        await event.message.answer(
            "📅 Выберите день для расписания:",
            attachments=[day_choice_markup()]
        )
        
        # Сохраняем состояние для выбора дня
        awaiting_actions[chat_key] = {'action': 'waiting_for_day', 'chat_id': chat_id}
        logging.info("awaiting state set: user=%s chat=%s action=waiting_for_day", user_id, chat_id)

    @dp.message_created(Command('schedule_remind'))
    async def set_schedule_reminder(event: MessageCreated):
        try:
            if should_ignore_message_event_on_start(event):
                logging.info("Ignoring historical message event on startup (set_schedule_reminder)")
                return
        except Exception:
            pass
        text = event.message.body.text or ""
        parts = text.split(maxsplit=2)
        if len(parts) < 3:
            await event.message.answer(
                "Использование: /schedule_remind <id> <minutes>\nПример: /schedule_remind 3 30\nДоступные пресеты:\n" + format_reminder_presets(),
                attachments=[back_to_menu_markup()]
            )
            return
        try:
            schedule_id = int(parts[1])
        except Exception:
            await event.message.answer("ID должен быть числом. Пример: /schedule_remind 3 30")
            return
        minutes_input = parts[2].strip().lower()
        if minutes_input in ('off', 'none', '0', 'выкл', 'выключить'):
            minutes = 0
        else:
            try:
                minutes = int(minutes_input)
            except Exception:
                await event.message.answer("Неверный формат времени напоминания. Используйте число минут или 'off'.\n\n" + format_reminder_presets())
                return
        if not is_valid_reminder_minutes(minutes):
            await event.message.answer("Неверная опция напоминания. Выберите из доступных пресетов:\n\n" + format_reminder_presets())
            return
        chat_id = _resolve_chat_id(event)
        sched = await Schedule.filter(id=schedule_id, chat_id=chat_id).first()
        if sched is None:
            await event.message.answer("Запись в расписании не найдена.")
            return
        sched.reminder_minutes = minutes
        await sched.save(update_fields=["reminder_minutes", "updated_at"])
        await event.message.answer(f"✅ Напоминание для записи {sched.id} установлено: {minutes_to_human_readable(minutes)}", attachments=[action_schedule_menu_markup()])

    @dp.message_created(Command('schedule'))
    async def list_schedule(event: MessageCreated):
        try:
            if should_ignore_message_event_on_start(event):
                logging.info("Ignoring historical message event on startup (list_schedule)")
                return
        except Exception:
            pass
        chat_id = _resolve_chat_id(event)
        schedules = await Schedule.filter(chat_id=chat_id, enabled=True).order_by("day_of_week", "time")
        if not schedules:
            await event.message.answer("Расписание пусто. Добавьте задачу командой /schedule_add")
            return
        lines = []
        current_day = None
        for schedule in schedules:
            day_name = DAY_NAMES_RU[schedule.day_of_week]
            if current_day != schedule.day_of_week:
                if current_day is not None:
                    lines.append("")
                lines.append(f"📅 {day_name}:")
                current_day = schedule.day_of_week
            reminder_label = minutes_to_human_readable(getattr(schedule, 'reminder_minutes', 0))
            lines.append(f"  {schedule.id}. {schedule.time} - {schedule.text} (напоминание: {reminder_label})")
        await event.message.answer("📅 Ваше расписание:\n\n" + "\n".join(lines))

    @dp.message_created(Command('schedule_remove'))
    async def remove_schedule(event: MessageCreated):
        try:
            if should_ignore_message_event_on_start(event):
                logging.info("Ignoring historical message event on startup (remove_schedule)")
                return
        except Exception:
            pass
        text = event.message.body.text or ""
        parts = text.split(maxsplit=1)
        if len(parts) < 2 or not parts[1].strip():
            await event.message.answer("Использование: /schedule_remove <id>")
            return
        try:
            schedule_id = int(parts[1].strip())
        except ValueError:
            await event.message.answer("ID должен быть числом. Пример: /schedule_remove 3")
            return
        chat_id = _resolve_chat_id(event)
        schedule = await Schedule.filter(id=schedule_id, chat_id=chat_id).first()
        if schedule is None:
            await event.message.answer("Запись в расписании не найдена.")
            return
        schedule.enabled = False
        await schedule.save(update_fields=["enabled", "updated_at"])
        await event.message.answer(f"✅ Запись {schedule_id} удалена из расписания")

    @dp.message_created(Command('timezone'))
    async def set_timezone(event: MessageCreated):
        try:
            if should_ignore_message_event_on_start(event):
                logging.info("Ignoring historical message event on startup (set_timezone)")
                return
        except Exception:
            pass
        
        text = event.message.body.text or ""
        parts = text.split(maxsplit=1)
        user_id = str(event.message.sender.user_id)
        chat_id = _resolve_chat_id(event)
        
        if len(parts) < 2 or not parts[1].strip():
            # Показываем текущую timezone
            user_settings = await UserSettings.filter(user_id=user_id).first()
            current_tz = user_settings.timezone if user_settings else "UTC"
            
            help_text = (
                f"⏰ Ваша текущая временная зона: {current_tz}\n\n"
                "Использование: /timezone <название_зоны>\n\n"
                "Примеры популярных зон:\n"
                f"{format_timezone_list()}\n\n"
                "Или используйте город/страну (например: /timezone Москва)"
            )
            await event.message.answer(help_text, attachments=[back_to_menu_markup()])
            return
        
        tz_input = parts[1].strip()
        
        # Проверяем, является ли это действительной timezone
        if is_valid_timezone(tz_input):
            valid_tz = tz_input
        else:
            # Пытаемся найти по ключевому слову
            found_tz = find_timezone_by_keyword(tz_input)
            if found_tz:
                valid_tz = found_tz
            else:
                await event.message.answer(
                    f"❌ Временная зона '{tz_input}' не найдена.\n\n"
                    f"Популярные зоны:\n{format_timezone_list()}\n\n"
                    "Или используйте /timezone <город> (например: /timezone Москва)",
                    attachments=[back_to_menu_markup()]
                )
                return
        
        # Сохраняем или обновляем настройки пользователя
        user_settings = await UserSettings.filter(user_id=user_id).first()
        if user_settings:
            user_settings.timezone = valid_tz
            user_settings.chat_id = chat_id
            await user_settings.save(update_fields=["timezone", "chat_id", "updated_at"])
        else:
            await UserSettings.create(
                user_id=user_id,
                chat_id=chat_id,
                timezone=valid_tz
            )
        
        # Обновляем все расписания пользователя на новую timezone
        schedules = await Schedule.filter(user_id=user_id)
        for schedule in schedules:
            schedule.timezone = valid_tz
            await schedule.save(update_fields=["timezone", "updated_at"])
        
        await event.message.answer(
            f"✅ Временная зона установлена: {valid_tz}",
            attachments=[back_to_menu_markup()]
        )

    @dp.message_callback()
    async def on_button_pressed(callback_event):
        try:
            if not is_callback_allowed(callback_event):
                logging.info("Callback from disallowed user/chat — ignoring")
                return
        except Exception:
            pass
        try:
            if should_ignore_callback_event_on_start(callback_event):
                logging.info("Ignoring historical callback event on startup")
                return
        except Exception:
            pass

        async def recalculate_schedule_weekdays(chat_id: str, new_timezone: str):
            """Пересчитывает day_of_week для всех расписаний пользователя при смене timezone"""
            from datetime import datetime, timedelta, time as datetime_time
            import pytz
            
            schedules = await Schedule.filter(chat_id=chat_id).all()
            if not schedules:
                logging.info(f"No schedules found for chat_id={chat_id}, nothing to recalculate")
                return
            
            old_tz = None
            try:
                # Получаем предыдущий timezone пользователя из последнего расписания
                old_tz_name = schedules[0].timezone
                old_tz = pytz.timezone(old_tz_name) if old_tz_name else pytz.UTC
            except:
                old_tz = pytz.UTC
            
            new_tz = pytz.timezone(new_timezone)
            
            logging.info(f"Recalculating weekdays for {len(schedules)} schedules: old_tz={old_tz}, new_tz={new_tz}")
            
            for schedule in schedules:
                # Получаем время из расписания
                time_parts = schedule.time.split(':')
                hour, minute = int(time_parts[0]), int(time_parts[1])
                
                # Создаём "якорную" дату в старом timezone (берём сегодня по старому timezone)
                now_utc = datetime.now(pytz.UTC)
                now_old_tz = now_utc.astimezone(old_tz)
                anchor_date = now_old_tz.date()
                
                # Создаём datetime с днём недели из расписания и временем расписания в старом timezone
                # Нужно найти дату которая соответствует old day_of_week
                current_old_weekday = anchor_date.weekday()
                target_old_weekday = schedule.day_of_week
                days_offset = target_old_weekday - current_old_weekday
                if days_offset < 0:
                    days_offset += 7
                
                schedule_date_old_tz_naive = anchor_date + timedelta(days=days_offset) if days_offset > 0 else anchor_date
                schedule_datetime_old_tz = old_tz.localize(datetime.combine(schedule_date_old_tz_naive, datetime_time(hour, minute)))
                
                # Конвертируем в новый timezone
                schedule_datetime_new_tz = schedule_datetime_old_tz.astimezone(new_tz)
                
                # Получаем день недели в новом timezone
                new_weekday = schedule_datetime_new_tz.weekday()
                
                old_day = DAY_NAMES_RU[schedule.day_of_week]
                new_day = DAY_NAMES_RU[new_weekday]
                
                logging.info(f"Schedule id={schedule.id}: old_day={old_day}(weekday={schedule.day_of_week}) -> new_day={new_day}(weekday={new_weekday}), time={schedule.time}")
                
                # Обновляем день недели и timezone
                schedule.day_of_week = new_weekday
                schedule.timezone = new_timezone
                await schedule.save(update_fields=["day_of_week", "timezone", "updated_at"])

        payload, found_at = extract_payload(callback_event)
        if payload is None:
            nested = getattr(callback_event, 'data', None) or getattr(callback_event, 'payload', None)
            payload, found_at = extract_payload(nested)
        if payload is None:
            found, where = await deep_search(callback_event)
            if found:
                payload, found_at = found, where

        try:
            cb_user = derive_user_id(callback_event)
            cb_chat = derive_chat_id(callback_event)
            logging.info("Callback pressed: payload=%s found_at=%s user=%s chat=%s", payload, found_at, cb_user, cb_chat)
        except Exception:
            logging.exception("Ошибка логирования отладки callback_event")

        async def _respond(text: str, attachments=None):
            return await respond(callback_event, text, attachments)

        if payload == 'cmd_list':
            chat_id = None
            try:
                chat_id = callback_event.message.recipient.chat_id
            except Exception:
                chat_id = None
            if chat_id is None:
                chat_id = str(callback_event.message.sender.user_id)
            tasks = await Task.filter(chat_id=str(chat_id)).order_by("status", "created_at")
            if not tasks:
                await _respond("Задач пока нет. Добавьте новую командой /add <текст>", attachments=[back_to_menu_markup()])
                return
            lines = []
            for idx, task in enumerate(tasks, start=1):
                status = "✅" if task.status == "done" else "🔸"
                lines.append(f"{idx}. {status} {task.text}")
            await _respond("Список задач:\n" + "\n".join(lines), attachments=[back_to_menu_markup()])
            return

        if payload == 'cmd_add':
            await _respond("Отправьте текст задачи или используйте /add <текст>", attachments=[back_to_menu_markup()])
            return

        if payload == 'cmd_decompose':
            chat_id = derive_chat_id(callback_event) or None
            if chat_id is None:
                try:
                    chat_id = callback_event.message.recipient.chat_id
                except Exception:
                    chat_id = None
            if chat_id is None:
                chat_id = str(callback_event.message.sender.user_id)
            user_id = derive_user_id(callback_event) or None
            if user_id is None:
                try:
                    user_id = str(callback_event.message.sender.user_id)
                except Exception:
                    user_id = None
            state_obj = {'action': 'decompose_input', 'chat_id': str(chat_id)}
            if user_id is not None:
                awaiting_actions[str(user_id)] = state_obj
                logging.info("awaiting state set: user=%s chat=%s action=%s", str(user_id), str(chat_id), 'decompose_input')
            if chat_id is not None:
                awaiting_actions[str(chat_id)] = state_obj
            await _respond("Отправьте задачу для разбиения на подзадачи или используйте /decompose <текст>", attachments=[back_to_menu_markup()])
            return

        if payload == 'cmd_achievements':
            chat_id = derive_chat_id(callback_event) or None
            if chat_id is None:
                try:
                    chat_id = callback_event.message.recipient.chat_id
                except Exception:
                    chat_id = None
            if chat_id is None:
                chat_id = str(callback_event.message.sender.user_id)
            
            achievements = await get_all_achievements(str(chat_id))
            completed_count = await Task.filter(chat_id=str(chat_id), status="done").count()
            
            lines = [
                "🏆 ВАШИ ДОСТИЖЕНИЯ 🏆\n",
                f"📊 Выполнено задач: {completed_count}\n"
            ]
            
            unlocked = [a for a in achievements if a["unlocked"]]
            locked = [a for a in achievements if not a["unlocked"]]
            
            if unlocked:
                lines.append("✨ Разблокированные:\n")
                for ach in unlocked:
                    lines.append(f"{ach['emoji']} {ach['title']} — {ach['milestone']} задач")
            
            if locked:
                lines.append("\n🔒 Ещё не открыты:\n")
                for ach in locked:
                    lines.append(f"{ach['emoji']} {ach['title']}")
            
            if not unlocked and not locked:
                lines.append("Пока нет достижений. Выполняйте задачи, чтобы разблокировать их!")
            
            await _respond("\n".join(lines), attachments=[back_to_menu_markup()])
            return

        if payload == 'cmd_motivation':
            chat_id = derive_chat_id(callback_event) or None
            if chat_id is None:
                try:
                    chat_id = callback_event.message.recipient.chat_id
                except Exception:
                    chat_id = None
            if chat_id is None:
                chat_id = str(callback_event.message.sender.user_id)
            
            settings = await get_or_create_settings(str(chat_id))
            
            style_names = {
                "friendly": "😊 Дружеский",
                "neutral": "😐 Нейтральный",
                "aggressive": "💪 Агрессивный"
            }
            
            status = "включены ✅" if settings.enabled else "выключены 🔕"
            message = (
                "💬 СТИЛЬ МОТИВАЦИИ\n\n"
                f"Текущий стиль: {style_names.get(settings.style, settings.style)}\n"
                f"Напоминания: {status}\n\n"
                "Я буду напоминать вам о невыполненных задачах 2-3 раза в день.\n"
                "Выберите стиль напоминаний:"
            )
            
            await _respond(message, attachments=[motivation_style_markup(settings.style, settings.enabled)])
            return

        if payload and payload.startswith('set_style_'):
            style = payload.replace('set_style_', '')
            chat_id = derive_chat_id(callback_event) or None
            if chat_id is None:
                try:
                    chat_id = callback_event.message.recipient.chat_id
                except Exception:
                    chat_id = None
            if chat_id is None:
                chat_id = str(callback_event.message.sender.user_id)
            
            await update_motivation_style(str(chat_id), MotivationStyle(style))
            
            style_names = {
                "friendly": "😊 Дружеский",
                "neutral": "😐 Нейтральный",
                "aggressive": "💪 Агрессивный"
            }
            
            message = (
                f"✅ Стиль мотивации изменен на: {style_names.get(style, style)}\n\n"
                "Теперь мои напоминания будут в этом стиле!"
            )
            
            settings = await get_or_create_settings(str(chat_id))
            await _respond(message, attachments=[motivation_style_markup(settings.style, settings.enabled)])
            return

        if payload == 'toggle_reminders':
            chat_id = derive_chat_id(callback_event) or None
            if chat_id is None:
                try:
                    chat_id = callback_event.message.recipient.chat_id
                except Exception:
                    chat_id = None
            if chat_id is None:
                chat_id = str(callback_event.message.sender.user_id)
            
            from core.motivation import toggle_reminders
            settings = await get_or_create_settings(str(chat_id))
            new_state = not settings.enabled
            await toggle_reminders(str(chat_id), new_state)
            
            if new_state:
                message = "✅ Напоминания включены!\n\nТеперь я буду мотивировать вас 2-3 раза в день."
            else:
                message = "🔕 Напоминания выключены.\n\nЯ не буду напоминать о задачах до тех пор, пока вы не включите их снова."
            
            settings = await get_or_create_settings(str(chat_id))
            await _respond(message, attachments=[motivation_style_markup(settings.style, settings.enabled)])
            return

        if payload == 'cmd_change_timezone':
            user_id = derive_user_id(callback_event) or None
            if user_id is None:
                try:
                    user_id = str(callback_event.message.sender.user_id)
                except Exception:
                    user_id = None
            
            chat_id = derive_chat_id(callback_event) or None
            if chat_id is None:
                try:
                    chat_id = callback_event.message.recipient.chat_id
                except Exception:
                    chat_id = None
            if chat_id is None:
                chat_id = str(callback_event.message.sender.user_id)
            
            # Получаем текущий timezone
            current_tz = "не установлен"
            if user_id:
                user_settings = await UserSettings.filter(user_id=str(user_id)).first()
                if user_settings:
                    current_tz = user_settings.timezone
            
            message = f"🌍 Текущий часовой пояс: {current_tz}\n\nВыберите новый часовой пояс:"
            await _respond(message, attachments=[timezone_choice_markup()])
            return

        if payload == 'cmd_done':
            chat_id = derive_chat_id(callback_event) or None
            if chat_id is None:
                try:
                    chat_id = callback_event.message.recipient.chat_id
                except Exception:
                    chat_id = None
            if chat_id is None:
                chat_id = str(callback_event.message.sender.user_id)
            tasks = await Task.filter(chat_id=str(chat_id)).order_by("status", "created_at")
            if not tasks:
                await _respond("Задач пока нет. Добавьте новую командой /add <текст>", attachments=[back_to_menu_markup()])
                return
            lines = []
            index_map = {}
            for idx, task in enumerate(tasks, start=1):
                status = '✅' if task.status == 'done' else '🔸'
                lines.append(f"{idx}. {status} {task.text}")
                index_map[idx] = task.id
            await _respond("Выберите номер задачи для отметки (можно несколько через пробел):\n\n" + "\n".join(lines), attachments=[back_to_menu_markup()])
            user_id = derive_user_id(callback_event) or None
            if user_id is None:
                try:
                    user_id = str(callback_event.message.sender.user_id)
                except Exception:
                    user_id = None
            state_obj = {'action': 'done_selection', 'chat_id': str(chat_id), 'map': index_map}
            if user_id is None:
                logging.warning("Не удалось определить user_id для установки awaiting state (done_selection)")
            else:
                awaiting_actions[str(user_id)] = state_obj
                logging.info("awaiting state set: user=%s chat=%s action=%s", str(user_id), str(chat_id), state_obj['action'])
            if chat_id is not None:
                awaiting_actions[str(chat_id)] = state_obj
            return

        if payload == 'cmd_schedule_add':
            chat_id = derive_chat_id(callback_event) or None
            if chat_id is None:
                try:
                    chat_id = callback_event.message.recipient.chat_id
                except Exception:
                    chat_id = None
            if chat_id is None:
                chat_id = str(callback_event.message.sender.user_id)
            user_id = derive_user_id(callback_event) or None
            if user_id is None:
                try:
                    user_id = str(callback_event.message.sender.user_id)
                except Exception:
                    user_id = None
            
            # ОЧИЩАЕМ ВСЕ состояния для этого чата
            # Удаляем все ключи которые относятся к этому чату
            keys_to_remove = []
            for key in list(awaiting_actions.keys()):
                state = awaiting_actions.get(key)
                if state and state.get('chat_id') == str(chat_id):
                    keys_to_remove.append(key)
            
            for key in keys_to_remove:
                awaiting_actions.pop(key, None)
                logging.info("Removed old state for key: %s", key)
            
            state_obj = {'action': 'waiting_for_day', 'chat_id': str(chat_id)}
            if user_id is not None:
                awaiting_actions[str(user_id)] = state_obj
                logging.info("awaiting state set: user=%s chat=%s action=%s", str(user_id), str(chat_id), state_obj['action'])
            if chat_id is not None:
                awaiting_actions[str(chat_id)] = state_obj
            await _respond("📅 Выберите день для расписания:", attachments=[day_choice_markup()])
            return

        if payload == 'cmd_schedule':
            chat_id = None
            try:
                chat_id = callback_event.message.recipient.chat_id
            except Exception:
                chat_id = None
            if chat_id is None:
                chat_id = str(callback_event.message.sender.user_id)
            schedules = await Schedule.filter(chat_id=str(chat_id), enabled=True).order_by("day_of_week", "time")
            if not schedules:
                await _respond("Расписание пусто. Добавьте задачу командой /schedule_add", attachments=[back_to_menu_markup()])
                return
            lines = []
            current_day = None
            for schedule in schedules:
                day_name = DAY_NAMES_RU[schedule.day_of_week]
                if current_day != schedule.day_of_week:
                    if current_day is not None:
                        lines.append("")
                    lines.append(f"📅 {day_name}:")
                    current_day = schedule.day_of_week
                reminder_label = minutes_to_human_readable(getattr(schedule, 'reminder_minutes', 0))
                lines.append(f"  {schedule.id}. {schedule.time} - {schedule.text} (напоминание: {reminder_label})")
            await _respond("📅 Ваше расписание:\n\n" + "\n".join(lines), attachments=[back_to_menu_markup()])
            return

        if payload == 'cmd_schedule_remove':
            chat_id = None
            try:
                chat_id = callback_event.message.recipient.chat_id
            except Exception:
                chat_id = None
            if chat_id is None:
                chat_id = str(callback_event.message.sender.user_id)
            schedules = await Schedule.filter(chat_id=str(chat_id), enabled=True).order_by("day_of_week", "time")
            if not schedules:
                await _respond("Расписание пусто. Добавьте задачу командой /schedule_add", attachments=[back_to_menu_markup()])
                return
            lines = []
            index_map = {}
            for idx, s in enumerate(schedules, start=1):
                lines.append(f"{idx}. {DAY_NAMES_RU[s.day_of_week]} {s.time} - {s.text}")
                index_map[idx] = s.id
            await _respond("Выберите номер(а) записи для удаления (можно несколько через пробел):\n\n" + "\n".join(lines), attachments=[back_to_menu_markup()])
            user_id = derive_user_id(callback_event) or None
            if user_id is None:
                try:
                    user_id = str(callback_event.message.sender.user_id)
                except Exception:
                    user_id = None
            state_obj = {'action': 'schedule_remove_selection', 'chat_id': str(chat_id), 'map': index_map}
            if user_id is None:
                logging.warning("Не удалось определить user_id для установки awaiting state (schedule_remove)")
            else:
                awaiting_actions[str(user_id)] = state_obj
                logging.info("awaiting state set: user=%s chat=%s action=%s", str(user_id), str(chat_id), state_obj['action'])
            if chat_id is not None:
                awaiting_actions[str(chat_id)] = state_obj
            return

        # Обработка выбора дня при добавлении расписания
        if payload and (payload.startswith('day_') or payload in ['day_today', 'day_tomorrow', 'day_after_tomorrow']):
            user_id = derive_user_id(callback_event)
            user_key = str(user_id) if user_id else None
            chat_key = derive_chat_id(callback_event)
            chat_key = str(chat_key) if chat_key else None
            
            logging.info(f"Day choice callback: user_key={user_key}, chat_key={chat_key}, payload={payload}")
            logging.info(f"awaiting_actions BEFORE clear: {list(awaiting_actions.keys())}")
            
            # Определяем день недели и дату
            from datetime import datetime, timedelta
            import pytz
            
            # Получаем часовой пояс пользователя
            user_settings = await UserSettings.filter(chat_id=chat_key).first()
            user_tz_name = user_settings.timezone if user_settings and user_settings.timezone else 'UTC'
            user_tz = pytz.timezone(user_tz_name)
            
            # Получаем текущее время в часовом поясе пользователя
            now_utc = datetime.now(pytz.UTC)
            now_user = now_utc.astimezone(user_tz)
            
            logging.info(f"Day choice BEFORE calculation: payload={payload}")
            logging.info(f"Timezone calculation: chat_id={chat_key}, tz={user_tz_name}")
            logging.info(f"UTC time: {now_utc.strftime('%Y-%m-%d %H:%M:%S %A')} (weekday={now_utc.weekday()})")
            logging.info(f"User time ({user_tz_name}): {now_user.strftime('%Y-%m-%d %H:%M:%S %A')} (weekday={now_user.weekday()})")
            
            day_of_week = None
            target_date = None
            
            if payload == 'day_today':
                day_of_week = now_user.weekday()
                target_date = now_user.date()
                logging.info(f"Calculated 'day_today': weekday={day_of_week}, date={target_date}, name={DAY_NAMES_RU[day_of_week]}")
            elif payload == 'day_tomorrow':
                tomorrow_user = now_user + timedelta(days=1)
                day_of_week = tomorrow_user.weekday()
                target_date = tomorrow_user.date()
                logging.info(f"Calculated 'day_tomorrow': weekday={day_of_week}, date={target_date}, name={DAY_NAMES_RU[day_of_week]}")
            elif payload == 'day_after_tomorrow':
                day_after_user = now_user + timedelta(days=2)
                day_of_week = day_after_user.weekday()
                target_date = day_after_user.date()
                logging.info(f"Calculated 'day_after_tomorrow': weekday={day_of_week}, date={target_date}, name={DAY_NAMES_RU[day_of_week]}")
            elif payload.startswith('day_'):
                try:
                    day_of_week = int(payload.split('_')[1])
                except Exception:
                    await _respond("❌ Ошибка при обработке выбора дня", attachments=[back_to_menu_markup()])
                    return
                # Если выбран конкретный день недели - устанавливаем на следующую неделю
                today_weekday = now_user.weekday()
                days_ahead = day_of_week - today_weekday
                if days_ahead <= 0:  # Если день уже прошёл на этой неделе
                    days_ahead += 7
                target_date = (now_user + timedelta(days=days_ahead)).date()
                logging.info(f"Calculated direct day select: payload={payload}, target_weekday={day_of_week}, today_weekday={today_weekday}, days_ahead={days_ahead}, target_date={target_date}, name={DAY_NAMES_RU[day_of_week]}")
            
            if day_of_week is None:
                await _respond("❌ Не удалось определить день", attachments=[back_to_menu_markup()])
                return
            
            # Очищаем ВСЕ старые состояния перед установкой waiting_for_time
            keys_to_remove = []
            for key in list(awaiting_actions.keys()):
                state = awaiting_actions.get(key)
                if state and state.get('chat_id') == str(chat_key):
                    keys_to_remove.append(key)
            
            for key in keys_to_remove:
                awaiting_actions.pop(key, None)
            
            logging.info("Clearing old state before setting waiting_for_time: user_key=%s chat_key=%s keys_removed=%s", user_key, chat_key, keys_to_remove)
            
            # Сохраняем выбранный день и дату в состояние
            if user_key:
                awaiting_actions[user_key] = {
                    'action': 'waiting_for_time',
                    'day_of_week': day_of_week,
                    'target_date': str(target_date),
                    'chat_id': chat_key
                }
                logging.info("Set waiting_for_time by user_key=%s: day=%s date=%s", user_key, day_of_week, target_date)
            if chat_key:
                awaiting_actions[chat_key] = {
                    'action': 'waiting_for_time',
                    'day_of_week': day_of_week,
                    'target_date': str(target_date),
                    'chat_id': chat_key
                }
                logging.info("Set waiting_for_time by chat_key=%s: day=%s date=%s", chat_key, day_of_week, target_date)
            
            day_name = DAY_NAMES_RU[day_of_week]
            date_str = target_date.strftime("%d.%m.%Y") if target_date else ""
            await _respond(
                f"✅ Выбран день: {day_name} ({date_str})\n\n⏰ Теперь укажите время в формате HH:MM\nНапример: 09:00",
                attachments=[back_to_menu_markup()]
            )
            logging.info("awaiting state set: user=%s chat=%s action=waiting_for_time day=%s", user_key, chat_key, day_of_week)
            return

        # Обработка выбора напоминания после добавления расписания
        if payload and payload.startswith('reminder_'):
            # reminder_0, reminder_5, reminder_15, reminder_30, reminder_60, reminder_custom
            reminder_choice = payload.split('_')[1]
            
            user_id = derive_user_id(callback_event)
            user_key = str(user_id) if user_id else None
            chat_key = derive_chat_id(callback_event)
            chat_key = str(chat_key) if chat_key else None
            
            logging.debug(f"Reminder callback: user_key={user_key}, chat_key={chat_key}, choice={reminder_choice}")
            logging.debug(f"awaiting_actions keys: {list(awaiting_actions.keys())}")
            
            # Получаем состояние с ID расписания
            # Сначала проверяем chat_key (важнее), потом user_key
            state = None
            if chat_key and chat_key in awaiting_actions:
                state = awaiting_actions.get(chat_key)
                logging.debug(f"Got state from chat_key: {state}")
            elif user_key and user_key in awaiting_actions:
                state = awaiting_actions.get(user_key)
                logging.debug(f"Got state from user_key: {state}")
            
            # Если состояние не найдено или неверное - пытаемся восстановить из DB
            if not state or state.get('action') != 'reminder_choice':
                # Может быть, это нажатие повторяется и состояние уже было очищено?
                # Или пользователь находится в другом state (schedule_add)?
                # Попробуем получить последнее созданное расписание
                logging.warning(f"State not found or wrong action. state={state}")
                await _respond("❌ Ошибка: сессия выбора напоминания истекла. Пожалуйста, добавьте расписание заново.", attachments=[back_to_menu_markup()])
                return
            
            schedule_id = state.get('schedule_id')
            chat_id = state.get('chat_id')
            
            if not schedule_id or not chat_id:
                logging.warning(f"Missing schedule_id or chat_id in state: {state}")
                await _respond("❌ Ошибка: потеряны данные расписания", attachments=[back_to_menu_markup()])
                return
            
            if reminder_choice == 'custom':
                # Если выбран кастомный ввод, просим пользователя ввести число
                if user_key:
                    awaiting_actions[user_key] = {'action': 'custom_reminder_input', 'schedule_id': schedule_id, 'chat_id': chat_id}
                if chat_key:
                    awaiting_actions[chat_key] = {'action': 'custom_reminder_input', 'schedule_id': schedule_id, 'chat_id': chat_id}
                logging.info(f"Custom reminder selected: user_key={user_key}, chat_key={chat_key}, schedule_id={schedule_id}")
                await _respond(
                    "⏰ Введите количество минут для дополнительного напоминания:\n\n"
                    "Примеры:\n"
                    "• 10 (напомнить за 10 минут)\n"
                    "• 30 (напомнить за 30 минут)\n"
                    "• 120 (напомнить за 2 часа)\n"
                    "• 0 (без дополнительного напоминания)\n\n"
                    "Максимум 10080 минут (7 дней)",
                    attachments=[back_to_menu_markup()]
                )
                logging.info(f"Custom reminder message sent")
                return
            
            # Обработка фиксированных значений
            try:
                reminder_minutes = int(reminder_choice)
            except ValueError:
                await _respond("❌ Ошибка при обработке выбора", attachments=[back_to_menu_markup()])
                return
            
            if not is_valid_reminder_minutes(reminder_minutes):
                await _respond("❌ Неверное значение напоминания", attachments=[back_to_menu_markup()])
                return
            
            # Обновляем расписание
            try:
                schedule = await Schedule.filter(id=schedule_id, chat_id=chat_id).first()
                if schedule:
                    schedule.reminder_minutes = reminder_minutes
                    await schedule.save(update_fields=["reminder_minutes", "updated_at"])
                    reminder_label = minutes_to_human_readable(reminder_minutes) if reminder_minutes > 0 else "выключено"
                    day_name = DAY_NAMES_RU[schedule.day_of_week]
                    response = f"✅ Расписание сохранено: {day_name} в {schedule.time}\n"
                    response += f"📝 Задача: {schedule.text}\n"
                    response += f"⏰ Основное напоминание: за 1 минуту до события\n"
                    if reminder_minutes > 0:
                        response += f"⏳ Дополнительное напоминание: {reminder_label}"
                    
                    # Очищаем состояние
                    if user_key:
                        awaiting_actions.pop(user_key, None)
                    if chat_key:
                        awaiting_actions.pop(chat_key, None)
                    
                    await _respond(response, attachments=[action_schedule_menu_markup()])
                else:
                    await _respond("❌ Расписание не найдено", attachments=[back_to_menu_markup()])
            except Exception as e:
                logging.exception("Ошибка при обновлении напоминания расписания")
                await _respond("❌ Ошибка при сохранении: " + str(e), attachments=[back_to_menu_markup()])
            return

        # Обработчик выбора часового пояса
        if payload and payload.startswith('tz_'):
            user_id = derive_user_id(callback_event) or None
            if user_id is None:
                try:
                    user_id = str(callback_event.message.sender.user_id)
                except Exception:
                    user_id = None
            
            chat_id = derive_chat_id(callback_event) or None
            if chat_id is None:
                try:
                    chat_id = callback_event.message.recipient.chat_id
                except Exception:
                    chat_id = None
            if chat_id is None:
                chat_id = str(callback_event.message.sender.user_id)
            
            if payload == 'tz_custom':
                # Просим ввести свой timezone
                state_obj = {'action': 'waiting_for_custom_timezone', 'chat_id': str(chat_id)}
                if user_id:
                    awaiting_actions[str(user_id)] = state_obj
                if chat_id:
                    awaiting_actions[str(chat_id)] = state_obj
                await _respond(
                    "Введите часовой пояс (например, Europe/Moscow, Asia/Bangkok, America/New_York):\n\n"
                    "Или введите /start для выбора из предложенных вариантов",
                    attachments=[back_to_menu_markup()]
                )
                return
            
            # Извлекаем timezone из payload
            timezone = payload[3:]  # Удаляем 'tz_' префикс
            
            # Проверяем валидность timezone
            if not is_valid_timezone(timezone):
                await _respond(
                    f"❌ Неверный часовой пояс: {timezone}\n\n"
                    "Попробуйте выбрать из предложенных вариантов:",
                    attachments=[timezone_choice_markup()]
                )
                return
            
            # Обновляем или создаём UserSettings
            if user_id:
                user_settings = await UserSettings.filter(user_id=str(user_id)).first()
                if user_settings:
                    user_settings.timezone = timezone
                    await user_settings.save()
                    # Пересчитываем день недели для всех расписаний
                    await recalculate_schedule_weekdays(str(chat_id), timezone)
                else:
                    await UserSettings.create(
                        user_id=str(user_id),
                        chat_id=str(chat_id),
                        timezone=timezone
                    )
                logging.info(f"User {user_id} set timezone to {timezone}")
                await _respond(
                    f"✅ Часовой пояс установлен: {timezone}\n\n"
                    "Теперь можешь использовать все функции бота!",
                    attachments=[main_keyboard_markup()]
                )
            return

        if payload == 'back_to_menu':
            chat_id = derive_chat_id(callback_event) or None
            if chat_id is None:
                try:
                    chat_id = callback_event.message.recipient.chat_id
                except Exception:
                    chat_id = None
            if chat_id is None:
                try:
                    chat_id = str(callback_event.message.sender.user_id)
                except Exception:
                    chat_id = None
            
            if chat_id:
                completed_count = await Task.filter(chat_id=str(chat_id), status="done").count()
                pretty_text = (
                    "🏠 Главное меню — Кузя\n"
                    f"✅ Выполнено задач: {completed_count}\n\n"
                    "Выберите действие ниже: я помогу с задачами, расписанием и напоминаниями.\n"
                    "Чтобы быстро добавить задачу — просто пришлите её текст."
                )
            else:
                pretty_text = (
                    "🏠 Главное меню — Кузя\n"
                    "Выберите действие ниже: я помогу с задачами, расписанием и напоминаниями.\n"
                    "Чтобы быстро добавить задачу — просто пришлите её текст."
                )
            await _respond(pretty_text, attachments=[main_keyboard_markup()])
            return

        if payload is None:
            await _respond(
                "Нажата неизвестная кнопка (payload не найден).\n"
                f"Где искали: {found_at}.\n"
                "Если проблема повторяется, пришли этот скриншот/ответ разработчику.",
                attachments=[back_to_menu_markup()]
            )
            logging.info("Callback event attrs: %s", {a: getattr(callback_event, a, None) for a in dir(callback_event)[:50]})
            return

        await callback_event.message.answer("Нажата неизвестная кнопка")

    @dp.message_created(Command('schedule_cleanup'))
    async def cleanup_schedules(event: MessageCreated):
        """Удалить старые расписания (дольше 3 месяцев)"""
        try:
            if should_ignore_message_event_on_start(event):
                logging.info("Ignoring historical message event on startup (cleanup_schedules)")
                return
        except Exception:
            pass
        
        chat_id = _resolve_chat_id(event)
        from datetime import datetime, timedelta
        import pytz
        
        # Удаляем расписания старше 3 месяцев
        cutoff_date = datetime.now(pytz.UTC) - timedelta(days=90)
        deleted = await Schedule.filter(
            chat_id=chat_id,
            created_at__lt=cutoff_date
        ).delete()
        
        await event.message.answer(
            f"🧹 Очистка завершена\n"
            f"Удалено расписаний старше 90 дней: {deleted}\n\n"
            f"💡 Совет: Периодически очищайте старые расписания, чтобы не захламлять БД"
        )
        logging.info(f"Cleanup: deleted {deleted} schedules from {chat_id}")
