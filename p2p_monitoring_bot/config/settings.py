#!/usr/bin/env python3
"""
Configuration Settings
======================

All bot configuration in one place
"""

import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Telegram Bot Token - получи у @BotFather (теперь безопасно в .env)
BOT_TOKEN = os.getenv("BOT_TOKEN", "YOUR_BOT_TOKEN_HERE")

# Настройки мониторинга
MONITORING_INTERVAL = int(os.getenv("MONITORING_INTERVAL", "60"))  # секунд между проверками
MAX_OFFERS_PER_NOTIFICATION = int(os.getenv("MAX_OFFERS_PER_NOTIFICATION", "3"))  # максимум предложений в одном уведомлении

# Настройки браузера
BROWSER_HEADLESS = os.getenv("BROWSER_HEADLESS", "true").lower() == "true"  # True - скрытый режим, False - показывать браузер
BROWSER_TIMEOUT = int(os.getenv("BROWSER_TIMEOUT", "20"))  # таймаут загрузки страницы в секундах

# Файлы данных
USERS_DATA_FILE = "config/users_settings.json"
OFFERS_CACHE_FILE = "temp/offers_cache.json"

# Логирование
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")  # DEBUG, INFO, WARNING, ERROR

# Настройки по умолчанию для пользователей
DEFAULT_USER_SETTINGS = {
    'min_rate': 35.0,
    'max_rate': 43.0,
    'min_limit': 5000.0,     # Минимальный лимит в UAH
    'max_limit': 100000.0,   # Максимальный лимит в UAH  
    'notifications_enabled': True,
    'active_exchanges': ['bybit']  # Пока только ByBit работает
}

# URLs для бирж
EXCHANGE_URLS = {
    'bybit': 'https://www.bybit.com/fiat/trade/otc/?actionType=1&token=USDT&fiat=UAH&paymentMethod='
}