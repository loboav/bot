# WARP.md

Этот файл предоставляет рекомендации для WARP (warp.dev) при работе с кодом в этом репозитории.

## Команды разработки

### Установка и зависимости
```bash
# Установить Python зависимости
pip install -r requirements.txt

# Быстрый запуск с автоматическими проверками и установкой зависимостей
./start_bot.bat

# Ручной запуск бота
python bot/main.py
```

### Тестирование
```bash
# Запуск тестов автомониторинга
python tests/test_automonitor.py

# Запуск интеграционных тестов
python test_full_integration.py
python test_binance_fix.py
```

### Конфигурация
- Токен бота и настройки конфигурируются через файл `.env`
- Пользовательские настройки хранятся в `config/users_settings.json`
- Основная конфигурация в `config/settings.py`

## Обзор архитектуры

### Основные компоненты

**ExchangeManager** (`bot/exchanges/exchange_manager.py`)
- Централизованный менеджер для всех интеграций P2P бирж
- Обрабатывает несколько бирж: ByBit, Bitget, Binance (с поддержкой заглушек для OKX, MEXC, BingX)
- Объединяет и сортирует предложения с нескольких бирж по цене
- Использует браузерный скрапинг с Selenium для данных в реальном времени

**AutoMonitor** (`bot/utils/auto_monitor.py`)
- Система автоматического мониторинга, работающая каждые 2-5 минут
- Ограничение скорости: максимум 12 уведомлений в час, минимум 3 минуты между уведомлениями
- Управляет пользовательскими настройками мониторинга и предпочтениями уведомлений
- Отслеживает историю уведомлений и реализует умное ограничение

**UserManager** (`bot/utils/user_manager.py`)
- Обрабатывает сохранение пользовательских данных в формате JSON
- Управляет пользовательскими настройками: диапазоны цен, лимиты, предпочтения бирж, переключатели автомониторинга
- Настройки по умолчанию: диапазон 35-43 UAH, лимиты 5000-100000 UAH

### Exchange Architecture

**Base Exchange Pattern**
- All exchanges inherit from `BaseExchange`
- Each exchange implements `get_offers()` method
- Standardized offer format with price, limits, user info, and direct links
- Selenium-based web scraping for real-time P2P data

**Active Exchanges**
- **ByBit P2P**: Typically shows best rates (42.0-42.8 UAH)
- **Bitget P2P**: Higher rates (43.2-43.6 UAH), includes API credentials support
- **Binance P2P**: Basic implementation

### Telegram Bot Structure

**Bot Handlers** (`bot/handlers/bot_handlers.py`)
- Implements all Telegram command handlers
- Integrates with AutoMonitor for `/automonitor` commands
- Manages user interaction flows and inline keyboards

**Main Bot** (`bot/main.py`)
- Async main loop that runs both Telegram bot and auto-monitoring concurrently
- Security validation for bot token format and environment setup
- Proper cleanup of Selenium resources on shutdown

## Key Features

### Auto-Monitoring System
- Users can enable automatic monitoring for their price ranges
- Smart notification system prevents spam with rate limiting
- Notifications include direct P2P links for immediate action
- Supports monitoring multiple exchanges simultaneously

### Multi-Exchange Support
- Users can select which exchanges to monitor via `/exchanges` command
- Combined results sorted by best price
- Easy to extend with new exchanges using the placeholder pattern

### Security
- Bot token stored in `.env` file (not committed)
- Input validation and error handling throughout
- No sensitive data in logs or commits

## Environment Variables

Configure via `.env` file:
```bash
# Required
BOT_TOKEN=your_telegram_bot_token

# Optional monitoring settings
BROWSER_HEADLESS=true
BROWSER_TIMEOUT=20
MONITORING_INTERVAL=60
AUTO_MONITORING_INTERVAL=300
MAX_NOTIFICATIONS_PER_HOUR=12
LOG_LEVEL=INFO

# Bitget API (optional)
BITGET_API_KEY=your_key
BITGET_SECRET_KEY=your_secret
BITGET_PASSPHRASE=your_passphrase
```

## Development Notes

- The project uses async/await pattern throughout
- Selenium WebDriver cleanup is handled automatically
- User data persistence is file-based (JSON)
- All text is in Russian (Cyrillic) for Ukrainian P2P market focus
- Price monitoring focuses on USDT-UAH trading pairs
- Exchange URLs and scraping selectors may need updates as sites change