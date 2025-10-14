#!/usr/bin/env python3
"""
Bot Configuration
================

Configuration settings for P2P monitoring bot.
"""

# Telegram Bot Token - получи у @BotFather
BOT_TOKEN = "YOUR_BOT_TOKEN_HERE"

# Настройки мониторинга
MONITORING_INTERVAL = 60  # секунд между проверками
MAX_OFFERS_PER_NOTIFICATION = 3  # максимум предложений в одном уведомлении

# Настройки браузера
BROWSER_HEADLESS = True  # True - скрытый режим, False - показывать браузер
BROWSER_TIMEOUT = 20  # таймаут загрузки страницы в секундах

# Файлы данных
USERS_DATA_FILE = "users_settings.json"
OFFERS_CACHE_FILE = "offers_cache.json"

# Логирование
LOG_LEVEL = "INFO"  # DEBUG, INFO, WARNING, ERROR

# Настройки по умолчанию для пользователей
DEFAULT_USER_SETTINGS = {
    'min_rate': 35.0,
    'max_rate': 43.0,
    'notifications_enabled': True,
    'active_exchanges': ['bybit']  # Пока только ByBit работает
}