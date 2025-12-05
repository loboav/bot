# 🤖 P2P USDT-UAH Monitoring Bot

[![Python](https://img.shields.io/badge/Python-3.10+-3776AB?logo=python&logoColor=white)](https://python.org/)
[![Telegram Bot](https://img.shields.io/badge/Telegram-Bot%20API-26A5E4?logo=telegram&logoColor=white)](https://core.telegram.org/bots)
[![Selenium](https://img.shields.io/badge/Selenium-4.15+-43B02A?logo=selenium&logoColor=white)](https://selenium.dev/)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

**P2P USDT-UAH Monitoring Bot** — Telegram-бот для мониторинга курсов P2P торговли USDT-UAH на популярных криптобиржах с автоматическими уведомлениями о выгодных предложениях.

---

## ✨ Ключевые возможности

### 📊 Мониторинг курсов
- **Реальные данные** с бирж в режиме реального времени
- **Умный парсинг** через браузер (Selenium)
- **Комбинированные результаты** от всех активных бирж

### 🤖 Автомониторинг
- ⚡ **Максимальная скорость** — проверка каждые 5 секунд
- 🔔 **Мгновенные уведомления** о выгодных предложениях
- 🌐 **Автооткрытие браузера** — ссылка открывается сразу

### ⚙️ Гибкие настройки
- 💰 Настраиваемый диапазон курса
- 💳 Лимиты сделок
- 🏦 Выбор бирж для мониторинга

---

## 🏦 Поддерживаемые биржи

| Биржа | Статус | Типичный курс |
|-------|--------|---------------|
| **ByBit** | ✅ Работает | 42.0–42.8 UAH |
| **Bitget** | ✅ Работает | 43.2–43.6 UAH |
| **Binance** | 🔄 В разработке | — |
| **OKX** | 🔄 В разработке | — |
| **MEXC** | 🔄 В разработке | — |
| **BingX** | 🔄 В разработке | — |

> [!TIP]
> **ByBit** обычно показывает более выгодные курсы! Используйте `/exchanges` для выбора.

---

## � Быстрый старт

### Требования
- [Python](https://python.org/) 3.10+
- [Chrome](https://www.google.com/chrome/) / [ChromeDriver](https://chromedriver.chromium.org/)
- Telegram Bot Token (от [@BotFather](https://t.me/BotFather))

### Установка

```bash
# Клонировать репозиторий
git clone https://github.com/loboav/bot.git
cd bot/p2p_monitoring_bot

# Установить зависимости
pip install -r requirements.txt

# Настроить окружение
cp .env.template .env
# Отредактировать .env и добавить BOT_TOKEN
```

### Запуск

```bash
# Windows (автоматический запуск с проверками)
start_bot.bat

# Или напрямую
python bot/main.py
```

---

## 📱 Команды бота

| Команда | Описание |
|---------|----------|
| `/start` | Приветствие и инструкция |
| `/check` | Проверить текущие предложения |
| `/exchanges` | 🎯 Выбрать биржи для мониторинга |
| `/settings` | Настройки курса и лимитов |
| `/automonitor` | Управление автомониторингом |
| `/status` | Показать текущие настройки |
| `/help` | Помощь по всем командам |

---

## 📁 Структура проекта

```
p2p_monitoring_bot/
├── bot/
│   ├── main.py              # Главный файл запуска
│   ├── exchanges/           # Интеграции с биржами
│   │   ├── base_exchange.py     # Базовый класс
│   │   ├── bybit_p2p.py         # ByBit P2P
│   │   ├── bitget_p2p.py        # Bitget P2P
│   │   ├── binance_p2p.py       # Binance P2P
│   │   └── exchange_manager.py  # Менеджер бирж
│   ├── handlers/            # Telegram обработчики
│   │   └── bot_handlers.py
│   └── utils/               # Утилиты
│       └── user_manager.py
├── config/
│   ├── settings.py          # Настройки приложения
│   └── users_settings.json  # Данные пользователей
├── docs/                    # Документация
├── tests/                   # Тесты
├── requirements.txt         # Зависимости
└── start_bot.bat           # Скрипт запуска (Windows)
```

---

## �️ Технологический стек

| Технология | Версия | Назначение |
|------------|--------|------------|
| Python | 3.10+ | Язык |
| python-telegram-bot | 20.x–21.x | Telegram Bot API |
| Selenium | 4.15+ | Браузерный парсинг |
| aiohttp | 3.9+ | Асинхронные HTTP запросы |
| python-dotenv | 1.0+ | Переменные окружения |

---

## ⚙️ Переменные окружения

| Переменная | Описание | Default |
|------------|----------|---------|
| `BOT_TOKEN` | Токен Telegram бота | — |
| `BROWSER_HEADLESS` | Скрытый режим браузера | `true` |
| `BROWSER_TIMEOUT` | Таймаут браузера (сек) | `20` |
| `MONITORING_INTERVAL` | Интервал проверок (сек) | `60` |
| `AUTO_MONITORING_INTERVAL` | Интервал автомониторинга (сек) | `5` |
| `AUTO_MONITOR_TOP_OFFERS_LIMIT` | Кол-во топ предложений | `5` |
| `AUTO_OPEN_BROWSER` | Автооткрытие ссылок | `true` |
| `LOG_LEVEL` | Уровень логирования | `INFO` |

---

## � Пример уведомления

```
🚨 Автомониторинг: найдено 2 предложения!

1. 💰 ByBit P2P Offer
   👤 Пользователь: TestUser
   💲 Цена: 42.50 UAH за USDT
   📊 Доступно: 100.0 USDT
   💳 Лимиты: 5000 - 50000 UAH
   🔗 Прямая ссылка: [Купить у TestUser]
```

---

## � Безопасность

- ✅ Токен бота хранится в `.env`
- ✅ `.env` добавлен в `.gitignore`
- ✅ Валидация формата токена при запуске

---

## 🤝 Contributing

1. Fork репозитория
2. Создать feature branch: `git checkout -b feature/amazing-feature`
3. Commit изменений: `git commit -m 'Add amazing feature'`
4. Push в branch: `git push origin feature/amazing-feature`
5. Открыть Pull Request

---

## � Лицензия

MIT License — см. [LICENSE](LICENSE)

---

## � Автор

**loboav** — [GitHub](https://github.com/loboav)
