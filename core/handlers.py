import logging
from typing import Optional

from core.utils import (
    should_ignore_message_event_on_start,
    should_ignore_callback_event_on_start,
    is_event_allowed,
    is_callback_allowed,
    _resolve_chat_id,
)
from core.state import awaiting_actions
from core.keyboards import (
    main_keyboard_markup,
    back_to_menu_markup,
    action_menu_markup,
    action_schedule_menu_markup,
    action_schedule_remove_menu_markup,
    motivation_style_markup,
)
from core.models import Task, Schedule
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


def register_handlers(dp, bot):
    """Register message and callback handlers on the provided dispatcher."""

    @dp.bot_started()
    async def on_bot_started(event: BotStarted):
        await event.bot.send_message(
            chat_id=event.chat_id,
            text='Привет! Я Кузя — твой персональный помощник по продуктивности и развитию. Начнем с команды /start или /menu!'
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
        completed_count = await Task.filter(chat_id=chat_id, status="done").count()

        start_message = (
            "👋 Привет! Я Кузя — твой персональный помощник по продуктивности и развитию.\n\n"
            f"✅ Выполнено задач: {completed_count}\n\n"
            "Ниже — быстрые действия. Нажмите кнопку, чтобы выполнить команду или получить подсказку."
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
        try:
            if not is_event_allowed(event):
                logging.info("Message from disallowed user/chat — ignoring")
                return
        except Exception:
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
        if state:
            action = state.get('action')
            chat_id = state.get('chat_id')

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

            if action == 'schedule_add':
                parts = text.split(maxsplit=2)
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
                else:
                    from core.handlers import DAY_NAMES, DAY_NAMES_RU
                    day_of_week = DAY_NAMES.get(day_str)
                    if day_of_week is None:
                        await event.message.answer(f"Неизвестный день недели: {parts[0]}\nИспользуйте: пн, вт, ср, чт, пт, сб, вс или числа 0-6", attachments=[back_to_menu_markup()])
                        return
                if not (len(time_str) == 5 and time_str[2] == ':' and time_str[:2].isdigit() and time_str[3:].isdigit()):
                    await event.message.answer("Время должно быть в формате HH:MM (например, 09:00)", attachments=[back_to_menu_markup()])
                    return
                hour, minute = int(time_str[:2]), int(time_str[3:])
                if hour < 0 or hour > 23 or minute < 0 or minute > 59:
                    await event.message.answer("Некорректное время. Часы: 0-23, минуты: 0-59", attachments=[back_to_menu_markup()])
                    return
                chat_id = state.get('chat_id')
                await Schedule.create(
                    chat_id=chat_id,
                    user_id=user_id,
                    text=task_text,
                    day_of_week=day_of_week,
                    time=time_str
                )
                logging.info("Clearing awaiting keys: user_key=%s chat_key=%s", user_key, chat_key)
                if user_key:
                    awaiting_actions.pop(user_key, None)
                if chat_key:
                    awaiting_actions.pop(chat_key, None)
                day_name = DAY_NAMES_RU[day_of_week]
                logging.info("Sending schedule add reply with schedule menu to user=%s chat=%s", user_key or chat_key, chat_key)
                await event.message.answer(f"✅ Расписание добавлено: {day_name} в {time_str} - {task_text}", attachments=[action_schedule_menu_markup()])
                return

        await Task.create(
            chat_id=_resolve_chat_id(event),
            user_id=user_id,
            text=text
        )
        await event.message.answer(
            "📝 Задача принята. Хотите добавить ещё — просто пришлите текст задачи.",
            attachments=[back_to_menu_markup()]
        )

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
        text = event.message.body.text or ""
        parts = text.split(maxsplit=3)
        if len(parts) < 4:
            await event.message.answer(
                "Использование: /schedule_add <день> <время> <текст>\n"
                "Пример: /schedule_add понедельник 09:00 Утренняя зарядка\n"
                "Дни: пн, вт, ср, чт, пт, сб, вс (или полные названия)"
            )
            return
        day_str = parts[1].strip().lower()
        time_str = parts[2].strip()
        task_text = parts[3].strip()
        day_of_week = None
        if day_str.isdigit():
            day_of_week = int(day_str)
            if day_of_week < 0 or day_of_week > 6:
                await event.message.answer("День недели должен быть от 0 (понедельник) до 6 (воскресенье)")
                return
        else:
            from core.handlers import DAY_NAMES
            day_of_week = DAY_NAMES.get(day_str)
            if day_of_week is None:
                await event.message.answer(
                    f"Неизвестный день недели: {parts[1]}\n"
                    "Используйте: пн, вт, ср, чт, пт, сб, вс или числа 0-6"
                )
                return
        if not (len(time_str) == 5 and time_str[2] == ':' and time_str[:2].isdigit() and time_str[3:].isdigit()):
            await event.message.answer("Время должно быть в формате HH:MM (например, 09:00)")
            return
        hour, minute = int(time_str[:2]), int(time_str[3:])
        if hour < 0 or hour > 23 or minute < 0 or minute > 59:
            await event.message.answer("Некорректное время. Часы: 0-23, минуты: 0-59")
            return
        chat_id = _resolve_chat_id(event)
        await Schedule.create(
            chat_id=chat_id,
            user_id=str(event.message.sender.user_id),
            text=task_text,
            day_of_week=day_of_week,
            time=time_str
        )
        day_name = DAY_NAMES_RU[day_of_week]
        await event.message.answer(f"✅ Расписание добавлено: {day_name} в {time_str} - {task_text}")

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
            lines.append(f"  {schedule.id}. {schedule.time} - {schedule.text}")
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
            state_obj = {'action': 'schedule_add', 'chat_id': str(chat_id)}
            if user_id is None:
                logging.warning("Не удалось определить user_id для установки awaiting state (schedule_add)")
            else:
                awaiting_actions[str(user_id)] = state_obj
                logging.info("awaiting state set: user=%s chat=%s action=%s", str(user_id), str(chat_id), state_obj['action'])
            if chat_id is not None:
                awaiting_actions[str(chat_id)] = state_obj
            await _respond("Отправьте запись в формате: <день> <время> <текст>\nПример: понедельник 09:00 Утренняя зарядка", attachments=[back_to_menu_markup()])
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
                lines.append(f"  {schedule.id}. {schedule.time} - {schedule.text}")
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


DAY_NAMES = {
    "пн": 0, "понедельник": 0, "пнд": 0, "monday": 0, "mon": 0,
    "вт": 1, "вторник": 1, "втр": 1, "tuesday": 1, "tue": 1,
    "ср": 2, "среда": 2, "срд": 2, "wednesday": 2, "wed": 2,
    "чт": 3, "четверг": 3, "чтв": 3, "thursday": 3, "thu": 3,
    "пт": 4, "пятница": 4, "птн": 4, "friday": 4, "fri": 4,
    "сб": 5, "суббота": 5, "сбт": 5, "saturday": 5, "sat": 5,
    "вс": 6, "воскресенье": 6, "вск": 6, "sunday": 6, "sun": 6,
}

DAY_NAMES_RU = ["Понедельник", "Вторник", "Среда", "Четверг", "Пятница", "Суббота", "Воскресенье"]
