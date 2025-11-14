"""
Модуль для подбора книг с использованием AI и внешних API.
"""
import logging
import json
import re
import aiohttp
from typing import List, Dict, Optional


class BookSearchService:
    """Сервис для поиска и подбора книг по пользовательским запросам."""
    
    def __init__(self):
        # Приоритет API: сначала Google Books, если не работает - OpenLibrary
        self.google_books_url = "https://www.googleapis.com/books/v1/volumes"
        self.openlibrary_url = "https://openlibrary.org/search.json"
        
    async def extract_search_keywords(self, user_request: str) -> Dict[str, str]:
        """
        Использует AI для извлечения ключевых слов из пользовательского запроса.
        
        Args:
            user_request: Запрос пользователя на естественном языке
            
        Returns:
            Словарь с извлеченными ключевыми словами
        """
        try:
            from core.ai_core import get_response
            
            prompt = f"""
Проанализируй запрос пользователя о книгах и извлеки ключевые параметры для поиска.

Запрос пользователя: "{user_request}"

Извлеки следующую информацию в формате JSON:
{{
    "keywords": "основные ключевые слова через пробел (на русском)",
    "genre": "жанр книги если указан",
    "author": "автор если указан", 
    "mood": "настроение/тип книги (например: легкая, серьезная, мотивирующая)",
    "topic": "основная тема книги",
    "language": "язык книги (ru/en), по умолчанию ru"
}}

Примеры:
- "Хочу почитать что-то мотивирующее про бизнес" → {{"keywords": "мотивация бизнес", "genre": "бизнес", "mood": "мотивирующая", "topic": "бизнес", "language": "ru"}}
- "Посоветуйте легкую фантастику на вечер" → {{"keywords": "фантастика", "genre": "фантастика", "mood": "легкая", "topic": "фантастика", "language": "ru"}}

Отвечай только JSON без дополнительного текста.
"""
            
            ai_response = await get_response(0, prompt)  # chat_id=0 для служебных запросов
            
            # Парсим JSON ответ от AI
            try:
                # Очищаем ответ от возможного мусора
                clean_response = ai_response.strip()
                
                # Ищем JSON в ответе (может быть в markdown блоке)
                if '```json' in clean_response:
                    start = clean_response.find('```json') + 7
                    end = clean_response.find('```', start)
                    if end != -1:
                        clean_response = clean_response[start:end].strip()
                elif '```' in clean_response:
                    start = clean_response.find('```') + 3
                    end = clean_response.rfind('```')
                    if end != -1 and end > start:
                        clean_response = clean_response[start:end].strip()
                
                # Ищем JSON блок
                if '{' in clean_response and '}' in clean_response:
                    start = clean_response.find('{')
                    end = clean_response.rfind('}') + 1
                    json_str = clean_response[start:end]
                else:
                    json_str = clean_response
                
                keywords_data = json.loads(json_str)
                logging.info(f"Extracted keywords from '{user_request}': {keywords_data}")
                return keywords_data
            except json.JSONDecodeError as e:
                logging.error(f"Failed to parse AI response as JSON: '{ai_response}', error: {e}")
                # Fallback - парсим вручную основные ключевые слова
                fallback_keywords = self._extract_keywords_fallback(user_request)
                return fallback_keywords
                
        except Exception as e:
            logging.error(f"Error extracting keywords: {e}")
            return self._extract_keywords_fallback(user_request)

    def _extract_keywords_fallback(self, user_request: str) -> dict:
        """Fallback метод для извлечения ключевых слов без AI"""
        return {
            "keywords": user_request,
            "genre": "",
            "author": "",
            "mood": "",
            "topic": "",
            "language": "ru"
        }
    
    async def search_books_google(self, keywords: Dict[str, str], max_results: int = 5) -> List[Dict]:
        """
        Поиск книг через Google Books API.
        
        Args:
            keywords: Извлеченные ключевые слова
            max_results: Максимальное количество результатов
            
        Returns:
            Список найденных книг
        """
        try:
            # Формируем поисковый запрос
            query_parts = []
            if keywords.get("keywords"):
                query_parts.append(keywords["keywords"])
            if keywords.get("author"):
                query_parts.append(f"inauthor:{keywords['author']}")
            if keywords.get("genre"):
                query_parts.append(keywords["genre"])
                
            query = " ".join(query_parts)
            
            # Добавляем языковые фильтры
            if keywords.get("language", "ru") == "ru":
                query += " язык:ru"
            
            params = {
                "q": query,
                "maxResults": max_results,
                "printType": "books",
                "orderBy": "relevance"
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.get(self.google_books_url, params=params) as response:
                    if response.status == 200:
                        data = await response.json()
                        books = []
                        
                        for item in data.get("items", []):
                            volume_info = item.get("volumeInfo", {})
                            book = {
                                "title": volume_info.get("title", "Без названия"),
                                "authors": volume_info.get("authors", ["Автор не указан"]),
                                "description": volume_info.get("description", "Описание отсутствует")[:300] + "...",
                                "published_date": volume_info.get("publishedDate", "Дата не указана"),
                                "page_count": volume_info.get("pageCount", "Не указано"),
                                "categories": volume_info.get("categories", []),
                                "rating": volume_info.get("averageRating", "Нет рейтинга"),
                                "preview_link": volume_info.get("previewLink", ""),
                                "source": "Google Books"
                            }
                            books.append(book)
                            
                        logging.info(f"Found {len(books)} books via Google Books API")
                        return books
                    else:
                        logging.error(f"Google Books API error: {response.status}")
                        return []
                        
        except Exception as e:
            logging.exception(f"Error searching Google Books: {e}")
            return []
    
    async def search_books_openlibrary(self, keywords: Dict[str, str], max_results: int = 5) -> List[Dict]:
        """
        Поиск книг через OpenLibrary API (fallback).
        
        Args:
            keywords: Извлеченные ключевые слова  
            max_results: Максимальное количество результатов
            
        Returns:
            Список найденных книг
        """
        try:
            # Формируем поисковый запрос
            query = keywords.get("keywords", "")
            if keywords.get("author"):
                query += f" {keywords['author']}"
                
            params = {
                "q": query,
                "language": "rus" if keywords.get("language", "ru") == "ru" else "eng",
                "limit": max_results
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.get(self.openlibrary_url, params=params) as response:
                    if response.status == 200:
                        data = await response.json()
                        books = []
                        
                        for doc in data.get("docs", []):
                            book = {
                                "title": doc.get("title", "Без названия"),
                                "authors": doc.get("author_name", ["Автор не указан"]),
                                "description": "Описание доступно по ссылке",
                                "published_date": str(doc.get("first_publish_year", "Дата не указана")),
                                "page_count": "Не указано",
                                "categories": doc.get("subject", [])[:3],  # Первые 3 категории
                                "rating": "Нет рейтинга",
                                "preview_link": f"https://openlibrary.org{doc.get('key', '')}",
                                "source": "OpenLibrary"
                            }
                            books.append(book)
                            
                        logging.info(f"Found {len(books)} books via OpenLibrary API")
                        return books
                    else:
                        logging.error(f"OpenLibrary API error: {response.status}")
                        return []
                        
        except Exception as e:
            logging.exception(f"Error searching OpenLibrary: {e}")
            return []
    
    async def search_books(self, user_request: str, max_results: int = 5) -> List[Dict]:
        """
        Основной метод поиска книг.
        Сначала извлекает ключевые слова с помощью AI, затем ищет в API.
        
        Args:
            user_request: Запрос пользователя на естественном языке
            max_results: Максимальное количество результатов
            
        Returns:
            Список найденных книг
        """
        try:
            # Извлекаем ключевые слова с помощью AI
            keywords = await self.extract_search_keywords(user_request)
            
            # Пробуем Google Books API
            books = await self.search_books_google(keywords, max_results)
            
            # Если Google Books не вернул результатов, пробуем OpenLibrary
            if not books:
                logging.info("Google Books returned no results, trying OpenLibrary...")
                books = await self.search_books_openlibrary(keywords, max_results)
            
            return books
            
        except Exception as e:
            logging.exception(f"Error in book search: {e}")
            return []
    
    def format_book_result(self, book: Dict) -> str:
        """
        Форматирует информацию о книге для отображения пользователю.
        
        Args:
            book: Словарь с информацией о книге
            
        Returns:
            Отформатированная строка с информацией о книге
        """
        title = book.get("title", "Без названия")
        authors_list = book.get("authors", ["Автор не указан"])
        authors = ", ".join(authors_list[:2])  # Максимум 2 автора
        if len(authors_list) > 2:
            authors += f" и др. ({len(authors_list)} авторов)"
            
        description = book.get("description", "Описание отсутствует")
        # Очищаем описание от лишних символов и форматирования
        if description and description != "Описание отсутствует":
            # Убираем HTML теги если есть
            description = re.sub(r'<[^>]+>', '', description)
            # Убираем лишние пробелы и переносы строк
            description = ' '.join(description.split())
            # Ограничиваем длину
            if len(description) > 200:
                description = description[:200] + "..."
        
        published = book.get("published_date", "")
        pages = book.get("page_count", "")
        rating = book.get("rating", "")
        categories = ", ".join(book.get("categories", [])[:2])
        source = book.get("source", "")
        
        # Убираем звездочки из названия и очищаем от лишних символов
        clean_title = title.replace("**", "").replace("*", "").strip()
        
        # Убираем нумерацию в начале названия (например "1. " или "**1. ")
        clean_title = re.sub(r'^\*{0,2}\d+\.\s*', '', clean_title)
        
        result = f"📚 {clean_title}\n"
        result += f"✍️ {authors}\n"
        result += f"📅 {published}" if published else "📅 Дата не указана"
        
        if pages and str(pages) != "":
            result += f" • 📄 {pages} стр."
        
        if rating and str(rating) != "":
            result += f" • ⭐ {rating}"
        result += "\n"
        
        if categories:
            result += f"🏷️ {categories}\n"
            
        result += f"📖 {description}\n"
        
        # Для maxapi используем простой текст без длинных ссылок
        if book.get("preview_link"):
            result += "🔗 Доступно для просмотра\n"
            
        # Показываем только источник без лишней информации
        if source:
            result += f"📡 {source}"
        
        return result


# Глобальный экземпляр сервиса
book_search_service = BookSearchService()