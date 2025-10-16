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

# Автомониторинг настройки
AUTO_MONITORING_INTERVAL = int(os.getenv("AUTO_MONITORING_INTERVAL", "120"))  # 2 минуты для тестирования
AUTO_MONITORING_SAFE_INTERVAL = int(os.getenv("AUTO_MONITORING_SAFE_INTERVAL", "60"))  # минимум 1 минута
MAX_NOTIFICATIONS_PER_HOUR = int(os.getenv("MAX_NOTIFICATIONS_PER_HOUR", "12"))  # не более 12 уведомлений в час

# Bitget API настройки
BITGET_API_KEY = os.getenv("BITGET_API_KEY", "bg_403603138a973f0ad8a26909b4fc4d06")
BITGET_SECRET_KEY = os.getenv("BITGET_SECRET_KEY", "7913b66af2d5887e464e7f3ebc74bece1cdf16c37f30e2ed098b2cc12c331f6a")
BITGET_PASSPHRASE = os.getenv("BITGET_PASSPHRASE", "")

# Настройки по умолчанию для пользователей
DEFAULT_USER_SETTINGS = {
    'min_rate': 35.0,
    'max_rate': 43.0,
    'min_limit': 5000.0,     # Минимальный лимит в UAH
    'max_limit': 100000.0,   # Максимальный лимит в UAH  
    'notifications_enabled': True,
    'auto_monitoring_enabled': False,  # Автомониторинг выключен по умолчанию
    'last_notification_time': None,  # Время последнего уведомления
    'notification_count_hour': 0,    # Счетчик уведомлений за час
    'active_exchanges': ['bybit', 'bitget']  # Теперь поддерживаем обе биржи
}

# URLs для бирж
EXCHANGE_URLS = {
    'bybit': 'https://www.bybit.com/fiat/trade/otc/?actionType=1&token=USDT&fiat=UAH&paymentMethod=',
    'bitget': 'https://www.bitget.com/ru/p2p-trade?paymethodIds=-1&fiatName=UAH'
}
