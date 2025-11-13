#!/usr/bin/env python3
"""
Скрипт для тестирования функций timezone
"""

import asyncio
import sys
sys.path.insert(0, '/home/kb_nik/coding/kuzia-bot')

from core.utils import (
    is_valid_timezone,
    find_timezone_by_keyword,
    format_timezone_list,
    get_timezone_offset,
    get_valid_timezones
)


def test_timezone_functions():
    """Тестируем все функции timezone"""
    
    print("=" * 60)
    print("ТЕСТИРОВАНИЕ ФУНКЦИЙ TIMEZONE")
    print("=" * 60)
    
    # Тест 1: is_valid_timezone
    print("\n1. Проверка действительности временных зон:")
    print("-" * 60)
    test_zones = [
        "Europe/Moscow",
        "America/New_York",
        "Invalid/Zone",
        "UTC",
        "Asia/Tokyo"
    ]
    for tz in test_zones:
        result = is_valid_timezone(tz)
        status = "✅" if result else "❌"
        print(f"{status} {tz}: {result}")
    
    # Тест 2: find_timezone_by_keyword
    print("\n2. Поиск по ключевому слову:")
    print("-" * 60)
    keywords = [
        "москва",
        "нью-йорк",
        "токио",
        "лондон",
        "неизвестный_город"
    ]
    for keyword in keywords:
        result = find_timezone_by_keyword(keyword)
        print(f"'{keyword}' → {result}")
    
    # Тест 3: get_timezone_offset
    print("\n3. UTC Offset для различных зон:")
    print("-" * 60)
    zones_for_offset = [
        "Europe/Moscow",
        "America/New_York",
        "Asia/Tokyo",
        "UTC"
    ]
    for tz in zones_for_offset:
        offset = get_timezone_offset(tz)
        print(f"{tz}: {offset}")
    
    # Тест 4: format_timezone_list
    print("\n4. Форматированный список популярных зон:")
    print("-" * 60)
    print(format_timezone_list())
    
    # Тест 5: get_valid_timezones (показываем только количество)
    print("\n5. Всего доступных временных зон:")
    print("-" * 60)
    all_tz = get_valid_timezones()
    print(f"Всего зон: {len(all_tz)}")
    print(f"Первые 10: {', '.join(all_tz[:10])}")
    print(f"Последние 10: {', '.join(all_tz[-10:])}")
    
    print("\n" + "=" * 60)
    print("ТЕСТИРОВАНИЕ ЗАВЕРШЕНО ✅")
    print("=" * 60)


if __name__ == "__main__":
    test_timezone_functions()
