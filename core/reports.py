"""
Модуль для генерации поквартальных отчётов о прогрессе пользователей.
"""
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from tortoise import Tortoise
from core.models import Task, UserSettings, Achievement
from core.ai_core import get_response


class QuarterlyReportService:
    """Сервис для создания поквартальных отчётов о прогрессе."""

    def __init__(self):
        self.quarters = {
            1: {"months": [1, 2, 3], "name": "I квартал"},
            2: {"months": [4, 5, 6], "name": "II квартал"},  
            3: {"months": [7, 8, 9], "name": "III квартал"},
            4: {"months": [10, 11, 12], "name": "IV квартал"}
        }

    def get_current_quarter(self, date: Optional[datetime] = None) -> Tuple[int, str]:
        """Определяет текущий квартал по дате."""
        if date is None:
            date = datetime.now()
        
        month = date.month
        for quarter_num, quarter_data in self.quarters.items():
            if month in quarter_data["months"]:
                return quarter_num, quarter_data["name"]
        return 1, "I квартал"

    def get_quarter_date_range(self, year: int, quarter: int) -> Tuple[datetime, datetime]:
        """Возвращает начало и конец указанного квартала."""
        quarter_months = self.quarters[quarter]["months"]
        start_date = datetime(year, quarter_months[0], 1)
        
        # Конец квартала - последний день последнего месяца
        if quarter_months[2] == 12:
            end_date = datetime(year + 1, 1, 1) - timedelta(days=1)
        else:
            end_date = datetime(year, quarter_months[2] + 1, 1) - timedelta(days=1)
        
        # Устанавливаем время в конец дня
        end_date = end_date.replace(hour=23, minute=59, second=59)
        
        return start_date, end_date

    async def get_quarter_statistics(self, user_id: str, chat_id: str, year: int, quarter: int) -> Dict:
        """Собирает статистику по задачам за квартал."""
        start_date, end_date = self.get_quarter_date_range(year, quarter)
        
        # Импортируем Q для создания OR запросов
        from tortoise.expressions import Q
        
        # Задачи, созданные в квартале - ищем по user_id ИЛИ chat_id
        created_tasks = await Task.filter(
            Q(user_id=user_id) | Q(chat_id=chat_id),
            created_at__gte=start_date,
            created_at__lte=end_date
        ).all()
        
        # Задачи, завершённые в квартале  
        completed_tasks = await Task.filter(
            Q(user_id=user_id) | Q(chat_id=chat_id),
            status="done",
            updated_at__gte=start_date,
            updated_at__lte=end_date
        ).all()
        
        # Просроченные задачи в квартале
        expired_tasks = await Task.filter(
            Q(user_id=user_id) | Q(chat_id=chat_id),
            status="expired",
            expired_at__gte=start_date,
            expired_at__lte=end_date
        ).all()
        
        # Анализируем категории задач (простая категоризация по ключевым словам)
        categories = self._categorize_tasks(created_tasks)
        
        # Считаем показатели продуктивности
        total_created = len(created_tasks)
        total_completed = len(completed_tasks)
        total_expired = len(expired_tasks)
        
        completion_rate = (total_completed / total_created * 100) if total_created > 0 else 0
        
        # Логируем для отладки
        logging.info(f"Quarter statistics for user {user_id}, chat {chat_id}: "
                    f"created={total_created}, completed={total_completed}, expired={total_expired}")
        
        return {
            "quarter": quarter,
            "quarter_name": self.quarters[quarter]["name"],
            "year": year,
            "period": f"{start_date.strftime('%d.%m')} - {end_date.strftime('%d.%m.%Y')}",
            "total_created": total_created,
            "total_completed": total_completed,
            "total_expired": total_expired,
            "completion_rate": round(completion_rate, 1),
            "categories": categories,
            "created_tasks": created_tasks,
            "completed_tasks": completed_tasks
        }

    def _categorize_tasks(self, tasks: List[Task]) -> Dict[str, int]:
        """Простая категоризация задач по ключевым словам."""
        categories = {
            "Работа": 0,
            "Учёба": 0,
            "Здоровье": 0,
            "Личное": 0,
            "Хобби": 0,
            "Дом": 0,
            "Прочее": 0
        }
        
        category_keywords = {
            "Работа": ["работа", "работать", "проект", "встреча", "отчёт", "презентация", "дедлайн", "задача", "клиент", 
                      "совещание", "документ", "план", "анализ", "разработка", "тестирование", "код", "программирование",
                      "email", "звонок", "переговоры", "контракт", "продажи", "маркетинг", "реклама"],
            "Учёба": ["учёба", "учиться", "экзамен", "лекция", "курс", "диплом", "учебник", "изучить", "выучить",
                     "университет", "институт", "школа", "конспект", "домашка", "семинар", "практика", "стажировка",
                     "образование", "знания", "навыки", "сертификат", "тест", "контрольная"],
            "Здоровье": ["спорт", "тренировка", "врач", "здоровье", "зал", "бег", "йога", "диета", "фитнес",
                        "больница", "поликлиника", "лечение", "таблетки", "витамины", "массаж", "зубы", "стоматолог",
                        "анализы", "обследование", "прививка", "медицина", "велосипед", "плавание"],
            "Личное": ["семья", "друзья", "отношения", "свидание", "день рождения", "праздник", "родители", "дети",
                      "любовь", "романтика", "подарок", "поздравить", "встретиться", "пообщаться", "выходные",
                      "отдых", "путешествие", "поездка", "отпуск", "развлечения"],
            "Хобби": ["хобби", "творчество", "рисование", "музыка", "фото", "игра", "фильм", "книга", "чтение",
                     "рукоделие", "вязание", "коллекция", "гитара", "пианино", "театр", "кино", "сериал",
                     "живопись", "скульптура", "танцы", "пение", "писать", "блог", "социальные сети"],
            "Дом": ["дом", "дома", "уборка", "покупки", "ремонт", "готовка", "стирка", "растения", "питомец",
                   "квартира", "кухня", "ванная", "спальня", "мебель", "техника", "электричество", "сантехника",
                   "кот", "собака", "цветы", "сад", "огород", "магазин", "продукты", "еда", "приготовить"]
        }
        
        # Для отладки - сохраняем детали категоризации
        categorization_details = []
        
        for task in tasks:
            task_text = task.text.lower()
            categorized = False
            
            for category, keywords in category_keywords.items():
                matched_keywords = [kw for kw in keywords if kw in task_text]
                if matched_keywords:
                    categories[category] += 1
                    categorized = True
                    categorization_details.append(f"'{task.text[:30]}...' → {category} (ключевые слова: {matched_keywords[:3]})")
                    break
            
            if not categorized:
                categories["Прочее"] += 1
                categorization_details.append(f"'{task.text[:30]}...' → Прочее (не найдено ключевых слов)")
        
        # Логируем детали категоризации для отладки
        if categorization_details:
            logging.info(f"Task categorization details:")
            for detail in categorization_details:
                logging.info(f"  {detail}")
                
        return categories

    async def get_achievements_for_period(self, chat_id: str, start_date: datetime, end_date: datetime) -> List[str]:
        """Получает достижения пользователя за период."""
        achievements = await Achievement.filter(
            chat_id=chat_id,
            unlocked_at__gte=start_date,
            unlocked_at__lte=end_date
        ).all()
        
        return [f"🏆 {achievement.title}" for achievement in achievements]

    async def generate_ai_insights(self, stats: Dict) -> str:
        """Генерирует AI-анализ прогресса пользователя."""
        prompt = f"""
Проанализируй результаты пользователя за {stats['quarter_name']} {stats['year']} года и дай конструктивные советы.

Статистика:
- Создано задач: {stats['total_created']}
- Выполнено задач: {stats['total_completed']}
- Просрочено задач: {stats['total_expired']}
- Процент выполнения: {stats['completion_rate']}%

Категории задач:
{chr(10).join([f"- {cat}: {count}" for cat, count in stats['categories'].items() if count > 0])}

Дай краткий анализ (2-3 предложения) с:
1. Оценкой прогресса
2. Выявлением сильных сторон
3. Рекомендациями для улучшения

Отвечай на русском языке, дружелюбным тоном.
"""
        
        try:
            response = await get_response(12345, prompt)  # Используем фиктивный chat_id для системных запросов
            return response.strip()
        except Exception as e:
            logging.error(f"Error generating AI insights: {e}")
            return self._get_fallback_insights(stats)

    async def debug_user_tasks(self, user_id: str, chat_id: str) -> Dict:
        """Отладочная функция для проверки всех задач пользователя."""
        from tortoise.expressions import Q
        
        # Все задачи пользователя
        all_tasks = await Task.filter(
            Q(user_id=user_id) | Q(chat_id=chat_id)
        ).all()
        
        # Группируем по статусу
        by_status = {}
        for task in all_tasks:
            status = task.status
            if status not in by_status:
                by_status[status] = []
            by_status[status].append(task)
        
        return {
            "total_tasks": len(all_tasks),
            "by_status": {status: len(tasks) for status, tasks in by_status.items()},
            "tasks_info": [(task.id, task.text, task.status, task.created_at.strftime("%Y-%m-%d")) for task in all_tasks[-10:]]  # Последние 10
        }

    def _get_fallback_insights(self, stats: Dict) -> str:
        """Fallback анализ без AI."""
        completion_rate = stats['completion_rate']
        
        if completion_rate >= 80:
            performance = "Отличная продуктивность! 🌟"
        elif completion_rate >= 60:
            performance = "Хорошие результаты! 👍"
        elif completion_rate >= 40:
            performance = "Есть потенциал для роста 📈"
        else:
            performance = "Стоит пересмотреть подход к планированию 🤔"
        
        insights = f"{performance} "
        
        if stats['total_created'] < 10:
            insights += "Попробуйте ставить больше конкретных целей. "
        
        if stats['total_expired'] > stats['total_completed']:
            insights += "Рекомендую планировать более реалистичные сроки. "
        
        # Самая активная категория
        top_category = max(stats['categories'].items(), key=lambda x: x[1])
        if top_category[1] > 0:
            insights += f"Больше всего активности в сфере '{top_category[0]}' - отличный фокус!"
        
        return insights

    def format_report(self, stats: Dict, achievements: List[str], insights: str) -> str:
        """Форматирует итоговый отчёт."""
        report = f"📊 Отчёт за {stats['quarter_name']} {stats['year']}\n"
        report += f"📅 Период: {stats['period']}\n\n"
        
        # Основная статистика
        report += "📈 Основные показатели:\n"
        report += f"✅ Выполнено: {stats['total_completed']} задач\n"
        report += f"📝 Создано: {stats['total_created']} задач\n"
        report += f"⏰ Просрочено: {stats['total_expired']} задач\n"
        report += f"🎯 Процент выполнения: {stats['completion_rate']}%\n\n"
        
        # Категории
        if any(count > 0 for count in stats['categories'].values()):
            report += "📂 Активность по сферам:\n"
            for category, count in stats['categories'].items():
                if count > 0:
                    report += f"• {category}: {count}\n"
            report += "\n"
        
        # Достижения
        if achievements:
            report += "🏆 Новые достижения:\n"
            for achievement in achievements:
                report += f"• {achievement}\n"
            report += "\n"
        
        # AI-анализ
        report += "🤖 Анализ прогресса:\n"
        report += f"{insights}\n\n"
        
        # Мотивационное сообщение
        if stats['completion_rate'] >= 70:
            report += "🎉 Продолжайте в том же духе! Вы на правильном пути к достижению своих целей!"
        else:
            report += "💪 Каждый шаг приближает вас к цели! Анализируйте, корректируйте планы и двигайтесь вперёд!"
        
        return report

    async def generate_quarterly_report(self, user_id: str, chat_id: str, year: Optional[int] = None, quarter: Optional[int] = None) -> str:
        """Генерирует полный поквартальный отчёт."""
        if year is None or quarter is None:
            current_quarter, _ = self.get_current_quarter()
            year = year or datetime.now().year
            quarter = quarter or current_quarter
        
        try:
            # Собираем статистику
            stats = await self.get_quarter_statistics(user_id, chat_id, year, quarter)
            
            # Получаем достижения за период
            start_date, end_date = self.get_quarter_date_range(year, quarter)
            achievements = await self.get_achievements_for_period(chat_id, start_date, end_date)
            
            # Генерируем AI-анализ
            insights = await self.generate_ai_insights(stats)
            
            # Формируем итоговый отчёт
            report = self.format_report(stats, achievements, insights)
            
            logging.info(f"Generated quarterly report for user {user_id}, Q{quarter} {year}")
            return report
            
        except Exception as e:
            logging.error(f"Error generating quarterly report: {e}")
            return f"❌ Не удалось сгенерировать отчёт за {quarter} квартал {year} года. Попробуйте позже."


# Глобальный экземпляр сервиса
quarterly_report_service = QuarterlyReportService()