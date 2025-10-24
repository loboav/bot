#!/usr/bin/env python3
"""
Bot Handlers
============

Telegram bot command handlers for P2P monitoring
"""

import asyncio
from typing import Dict, Any
from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    ReplyKeyboardMarkup,
    KeyboardButton,
)
from telegram.ext import (
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    filters,
    ContextTypes,
)


class BotHandlers:
    """Telegram bot handlers with full P2P functionality"""

    def __init__(self, bot_instance, auto_monitor=None):
        self.bot = bot_instance
        self.auto_monitor = auto_monitor

    async def start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /start command"""
        user = update.effective_user

        welcome_message = f"""
🚀 <b>Добро пожаловать в P2P USDT-UAH Мониторинг Бот!</b>

👋 Привет, {user.first_name}!

Этот бот отслеживает курсы USDT-UAH на P2P биржах и уведомляет о выгодных предложениях.

🏦 <b>Доступные биржи:</b>
✅ ByBit (реальные данные через браузер)
✅ Bitget (реальные данные через API)
✅ Binance (реальные данные через браузер)
🔄 OKX, MEXC, BingX (скоро)

⚙️ <b>Основные команды:</b>
/check - Быстро проверить предложения (из кэша)
/refresh - Обновить данные принудительно (20-40 сек)
/exchanges - Выбрать биржи для мониторинга
/settings - Настроить диапазон курса и автомониторинг
🤖 /automonitor - Управление автомониторингом

💡 <b>Совет:</b> Используйте /check для быстрой проверки, /refresh если нужны самые свежие данные!
        """.strip()

        await update.message.reply_text(welcome_message, parse_mode="HTML")

        # Show main command menu as reply keyboard
        keyboard = self.build_main_reply_keyboard()
        await update.message.reply_text(
            "📱 Меню команд:", reply_markup=keyboard, parse_mode="HTML"
        )

    async def check_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /check command - show current offers from all active exchanges"""
        user_id = update.effective_user.id
        user_data = self.bot.user_manager.get_user_data(user_id)

        # Get active exchanges for user
        active_exchanges = user_data.get(
            "active_exchanges", ["bybit", "binance", "bitget"]
        )

        # Send "checking" message
        exchanges_text = ", ".join([ex.title() for ex in active_exchanges])
        checking_msg = await update.message.reply_text(
            f"🔄 Получаю данные с: {exchanges_text}...\n⚡ Использую кэш автомониторинга (быстро!)"
        )

        try:
            # ✅ FIX: Use cached data from automonitor (no force_refresh)
            # This allows /check to work instantly without blocking
            offers = await self.bot.exchange_manager.get_combined_offers(
                active_exchanges, force_refresh=False
            )

            if not offers:
                await checking_msg.edit_text(
                    f"❌ Не удалось получить предложения с {exchanges_text}.\n"
                    "🔧 Попробуйте позже или используйте /exchanges для смены бирж."
                )
                return

            # Filter offers by user's rate range AND limits
            filtered_offers = []
            for offer in offers:
                # Price filter
                if not (
                    user_data["min_rate"] <= offer["price"] <= user_data["max_rate"]
                ):
                    continue

                # Limits filter - check if offer's limits overlap with user's requirements
                offer_min = offer.get("min_amount", 0)
                offer_max = offer.get("max_amount", 999999)
                user_min_limit = user_data.get("min_limit", 0)
                user_max_limit = user_data.get("max_limit", 999999)

                # Check if there's overlap between offer limits and user limits
                if offer_max >= user_min_limit and offer_min <= user_max_limit:
                    filtered_offers.append(offer)

            # Prepare response
            if not filtered_offers:
                all_prices = [offer["price"] for offer in offers]
                min_price = min(all_prices) if all_prices else 0
                max_price = max(all_prices) if all_prices else 0

                # Count offers by exchange
                exchange_counts = {}
                for offer in offers:
                    exchange = offer.get("exchange", "Unknown")
                    exchange_counts[exchange] = exchange_counts.get(exchange, 0) + 1

                count_text = ", ".join(
                    [f"{ex.title()}: {count}" for ex, count in exchange_counts.items()]
                )

                response = f"📅 <b>Найдено {len(offers)} предложений</b> ({count_text}), но ни одно не подходит по вашим критериям:\n\n"
                response += f"💰 Ваш диапазон цен: <b>{user_data['min_rate']:.2f}-{user_data['max_rate']:.2f} UAH</b>\n"
                response += f"💳 Ваши лимиты: <b>{user_data.get('min_limit', 5000):.0f}-{user_data.get('max_limit', 100000):.0f} UAH</b>\n\n"
                response += f"💡 Доступные цены: <b>{min_price:.2f} - {max_price:.2f} UAH</b>\n\n"
                response += "⚡️ Используйте /settings для изменения настроек"
            else:
                # Sort by price (best offers first)
                filtered_offers.sort(key=lambda x: x["price"])

                # Count filtered offers by exchange
                exchange_counts = {}
                for offer in filtered_offers:
                    exchange = offer.get("exchange", "Unknown")
                    exchange_counts[exchange] = exchange_counts.get(exchange, 0) + 1

                count_text = ", ".join(
                    [f"{ex.title()}: {count}" for ex, count in exchange_counts.items()]
                )

                response = f"💎 <b>Найдено {len(filtered_offers)} СВЕЖИХ предложений</b> ({count_text}) в вашем диапазоне:\n\n"

                # Show top 5 offers with exchange info
                for i, offer in enumerate(filtered_offers[:5], 1):
                    # Get the appropriate exchange to format the message
                    exchange_name = offer.get("exchange", "bybit")
                    exchange = self.bot.exchange_manager.get_exchange(exchange_name)

                    if exchange:
                        offer_text = exchange.format_offer_message(offer)
                    else:
                        # Fallback formatting
                        offer_text = self._format_generic_offer(offer)

                    response += f"<b>{i}.</b> {offer_text}\n\n"

                if len(filtered_offers) > 5:
                    response += f"... и еще {len(filtered_offers) - 5} предложений\n\n"

                # Check cache age
                from datetime import datetime, timedelta

                cache_age = "только что"
                for exchange_name in active_exchanges:
                    exchange = self.bot.exchange_manager.get_exchange(exchange_name)
                    if exchange and exchange.last_update:
                        age_seconds = (
                            datetime.now() - exchange.last_update
                        ).total_seconds()
                        if age_seconds > 60:
                            cache_age = f"{int(age_seconds)} сек назад"
                        break

                response += f"💡 Нажмите на прямые ссылки для быстрой покупки!\n🕐 Данные: {cache_age}"

            await checking_msg.edit_text(
                response, parse_mode="HTML", disable_web_page_preview=True
            )

        except Exception as e:
            await checking_msg.edit_text(
                f"❌ Ошибка при получении данных: {str(e)[:100]}..."
            )

    async def settings_command(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ):
        """Handle /settings command"""
        user_id = update.effective_user.id
        user_data = self.bot.user_manager.get_user_data(user_id)

        keyboard = [
            [
                InlineKeyboardButton(
                    "💰 Изменить диапазон курса (/check)",
                    callback_data="set_rate_range",
                )
            ],
            [
                InlineKeyboardButton(
                    "💳 Настроить лимиты (/check)", callback_data="set_limits"
                )
            ],
            [
                InlineKeyboardButton(
                    "⚡ Диапазон для автомониторинга",
                    callback_data="set_automonitor_rate",
                )
            ],
            [
                InlineKeyboardButton(
                    "🔥 Лимиты для автомониторинга",
                    callback_data="set_automonitor_limits",
                )
            ],
            [
                InlineKeyboardButton(
                    "🤖 Вкл/Выкл автомониторинг", callback_data="toggle_automonitor"
                )
            ],
            [InlineKeyboardButton("📊 Показать статус", callback_data="show_status")],
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        settings_text = f"""
⚡️ <b>Настройки мониторинга</b>

🔍 <b>Основные настройки (для /check):</b>
💰 Диапазон курса: {user_data["min_rate"]:.2f} - {user_data["max_rate"]:.2f} UAH
💳 Лимиты: {user_data.get("min_limit", 5000):.0f} - {user_data.get("max_limit", 100000):.0f} UAH

⚡ <b>Настройки автомониторинга (узкий диапазон):</b>
💰 Диапазон: {user_data.get("auto_monitor_min_rate", 40.5):.2f} - {user_data.get("auto_monitor_max_rate", 41.5):.2f} UAH
💳 Лимиты: {user_data.get("auto_monitor_min_limit", 10000):.0f} - {user_data.get("auto_monitor_max_limit", 50000):.0f} UAH
🤖 Статус: {"✅ Включен" if user_data.get("auto_monitoring_enabled", False) else "❌ Выключен"}

🏦 <b>Активные биржи:</b> {", ".join([ex.title() for ex in user_data.get("active_exchanges", ["bybit", "binance", "bitget"])])}
🔔 <b>Уведомления:</b> {"✅ Включены" if user_data["notifications_enabled"] else "❌ Выключены"}

Выберите что настроить:
        """.strip()

        await update.message.reply_text(
            settings_text, reply_markup=reply_markup, parse_mode="HTML"
        )

    async def status_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /status command"""
        user_id = update.effective_user.id
        user_data = self.bot.user_manager.get_user_data(user_id)

        status_text = f"""
📊 <b>Статус мониторинга</b>

👤 <b>Пользователь:</b> {update.effective_user.first_name}
🆔 <b>ID:</b> {user_id}

💰 <b>Диапазон курса:</b> {user_data["min_rate"]:.2f} - {user_data["max_rate"]:.2f} UAH
💳 <b>Лимиты сделок:</b> {user_data.get("min_limit", 5000):.0f} - {user_data.get("max_limit", 100000):.0f} UAH
🤖 <b>Автомониторинг:</b> {"✅ Включен" if user_data.get("auto_monitoring_enabled", False) else "❌ Выключен"}
🔔 <b>Уведомления:</b> {"✅ Включены" if user_data["notifications_enabled"] else "❌ Выключены"}

🏦 <b>Биржи:</b>
✅ ByBit - активна (браузер)
✅ Bitget - активна (браузер)
✅ Binance - активна (браузер)
🔄 OKX, MEXC, BingX - скоро

🏦 <b>Ваши активные:</b> {", ".join([ex.title() for ex in user_data.get("active_exchanges", ["bybit", "binance", "bitget"])])}

⏰ <b>Время проверки:</b> {context.application.bot.start_time if hasattr(context.application.bot, "start_time") else "N/A"}
        """.strip()

        # Проверяем, вызвано ли из callback query или из команды
        if update.callback_query:
            await update.callback_query.message.reply_text(
                status_text, parse_mode="HTML"
            )
        else:
            await update.message.reply_text(status_text, parse_mode="HTML")

    async def refresh_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /refresh command - force refresh data"""
        user_id = update.effective_user.id
        user_data = self.bot.user_manager.get_user_data(user_id)

        # Get active exchanges for user
        active_exchanges = user_data.get(
            "active_exchanges", ["bybit", "binance", "bitget"]
        )

        # Send "refreshing" message
        exchanges_text = ", ".join([ex.title() for ex in active_exchanges])
        refreshing_msg = await update.message.reply_text(
            f"🔄 Принудительное обновление данных с: {exchanges_text}...\n⏳ Это может занять 20-40 секунд"
        )

        try:
            # Force refresh from all active exchanges
            offers = await self.bot.exchange_manager.get_combined_offers(
                active_exchanges, force_refresh=True
            )

            if not offers:
                await refreshing_msg.edit_text(
                    f"❌ Не удалось получить предложения с {exchanges_text}."
                )
                return

            # Filter offers by user's rate range
            filtered_offers = []
            for offer in offers:
                # Price filter
                if not (
                    user_data["min_rate"] <= offer["price"] <= user_data["max_rate"]
                ):
                    continue

                # Limits filter
                offer_min = offer.get("min_amount", 0)
                offer_max = offer.get("max_amount", 999999)
                user_min_limit = user_data.get("min_limit", 0)
                user_max_limit = user_data.get("max_limit", 999999)

                if offer_max >= user_min_limit and offer_min <= user_max_limit:
                    filtered_offers.append(offer)

            # Prepare response
            if not filtered_offers:
                response = f"📅 Обновлено! Найдено {len(offers)} предложений, но ни одно не подходит по вашим критериям.\n\n"
                response += "💡 Используйте /settings для изменения диапазона"
            else:
                # Sort by price
                filtered_offers.sort(key=lambda x: x["price"])

                response = f"✅ <b>Данные обновлены! Найдено {len(filtered_offers)} предложений</b>\n\n"

                # Show top 5 offers
                for i, offer in enumerate(filtered_offers[:5], 1):
                    exchange_name = offer.get("exchange", "bybit")
                    exchange = self.bot.exchange_manager.get_exchange(exchange_name)

                    if exchange:
                        offer_text = exchange.format_offer_message(offer)
                    else:
                        offer_text = self._format_generic_offer(offer)

                    response += f"<b>{i}.</b> {offer_text}\n\n"

                if len(filtered_offers) > 5:
                    response += f"... и еще {len(filtered_offers) - 5} предложений\n\n"

                response += "💡 Данные обновлены ПРЯМО СЕЙЧАС!"

            await refreshing_msg.edit_text(
                response, parse_mode="HTML", disable_web_page_preview=True
            )

        except Exception as e:
            await refreshing_msg.edit_text(
                f"❌ Ошибка при обновлении данных: {str(e)[:100]}..."
            )

    async def help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /help command"""
        help_text = """
🤖 <b>Команды P2P Monitoring Bot:</b>

🏠 <b>/start</b> - Приветствие и инструкция
📱 <b>/menu</b> - Показать меню команд

⚡ <b>БЫСТРАЯ ПРОВЕРКА:</b>
🔍 <b>/check</b> - Быстро проверить предложения (использует кэш)
🔄 <b>/refresh</b> - Обновить данные принудительно (20-40 сек)

⚙️ <b>НАСТРОЙКИ:</b>
🏦 <b>/exchanges</b> - Выбрать биржи для мониторинга
⚙️ <b>/settings</b> - Настроить диапазон курса и автомониторинг
🤖 <b>/automonitor</b> - Управление автомониторингом
📊 <b>/status</b> - Показать текущие настройки
❓ <b>/help</b> - Показать это сообщение

💡 <b>В чем разница:</b>
• <b>/check</b> - моментально показывает данные из кэша (автомониторинг обновляет каждые 20-60 сек)
• <b>/refresh</b> - парсит биржи заново, но занимает время (используй если нужны САМЫЕ свежие данные)

🎯 <b>Рекомендация:</b>
Используй <b>/check</b> для быстрой проверки. Автомониторинг и так постоянно обновляет данные!
Используй <b>/refresh</b> только если нужны данные "прямо сейчас" и готов подождать.

📱 <b>Меню команд:</b> Используйте /menu для быстрого доступа к кнопкам команд!
        """.strip()

        await update.message.reply_text(help_text, parse_mode="HTML")

    async def button_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle button callbacks"""
        query = update.callback_query
        await query.answer()

        user_id = query.from_user.id

        if query.data == "set_rate_range":
            user_data = self.bot.user_manager.get_user_data(user_id)

            await query.edit_message_text(
                f"💰 <b>Установка диапазона курса</b>\n\n"
                f"Отправьте новый диапазон в формате:\n"
                f"<code>минимум максимум</code>\n\n"
                f"<b>Например:</b> <code>42.0 43.5</code>\n\n"
                f"Текущий диапазон: <b>{user_data['min_rate']:.2f} - {user_data['max_rate']:.2f} UAH</b>",
                parse_mode="HTML",
            )
            context.user_data["waiting_for"] = "rate_range"

        elif query.data == "set_limits":
            user_data = self.bot.user_manager.get_user_data(user_id)

            await query.edit_message_text(
                f"💳 <b>Настройка лимитов сделок (для /check)</b>\n\n"
                f"Отправьте новые лимиты в формате:\n"
                f"<code>минимум максимум</code>\n\n"
                f"<b>Пример:</b> <code>5000 50000</code>\n\n"
                f"Текущие лимиты: <b>{user_data.get('min_limit', 5000):.0f} - {user_data.get('max_limit', 100000):.0f} UAH</b>\n\n"
                f"💡 <b>Почему это важно:</b>\n"
                f"• Маленькие суммы = большая комиссия\n"
                f"• Оптимально: от 5000 UAH",
                parse_mode="HTML",
            )
            context.user_data["waiting_for"] = "limits"

        elif query.data == "set_automonitor_rate":
            user_data = self.bot.user_manager.get_user_data(user_id)

            await query.edit_message_text(
                f"⚡ <b>Узкий диапазон для автомониторинга</b>\n\n"
                f"🔥 <b>Это для самых выгодных предложений!</b>\n"
                f"Автомониторинг проверяет каждые 20 секунд только топ-5 предложений.\n\n"
                f"Отправьте узкий диапазон в формате:\n"
                f"<code>минимум максимум</code>\n\n"
                f"<b>Пример:</b> <code>40.5 41.5</code> (узкий диапазон 1 гривна)\n\n"
                f"Текущий диапазон: <b>{user_data.get('auto_monitor_min_rate', 40.5):.2f} - {user_data.get('auto_monitor_max_rate', 41.5):.2f} UAH</b>\n\n"
                f"💡 Чем уже диапазон, тем быстрее проверка!",
                parse_mode="HTML",
            )
            context.user_data["waiting_for"] = "automonitor_rate"

        elif query.data == "set_automonitor_limits":
            user_data = self.bot.user_manager.get_user_data(user_id)

            await query.edit_message_text(
                f"🔥 <b>Лимиты для автомониторинга</b>\n\n"
                f"Отправьте лимиты в формате:\n"
                f"<code>минимум максимум</code>\n\n"
                f"<b>Пример:</b> <code>10000 50000</code>\n\n"
                f"Текущие лимиты: <b>{user_data.get('auto_monitor_min_limit', 10000):.0f} - {user_data.get('auto_monitor_max_limit', 50000):.0f} UAH</b>\n\n"
                f"💡 Узкие лимиты помогают найти лучшие сделки!",
                parse_mode="HTML",
            )
            context.user_data["waiting_for"] = "automonitor_limits"

        elif query.data == "toggle_automonitor":
            await self._handle_automonitor_toggle(update, context)

        elif query.data == "show_status":
            await self.status_command(update, context)

        elif query.data.startswith("toggle_exchange_"):
            exchange_name = query.data.replace("toggle_exchange_", "")
            await self._handle_exchange_toggle(update, context, exchange_name)

        elif query.data == "show_exchanges_status":
            await self._show_exchanges_status(update, context)

    async def message_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle text messages"""
        if context.user_data.get("waiting_for") == "rate_range":
            try:
                text = update.message.text.strip()
                parts = text.split()

                if len(parts) == 2:
                    min_rate = float(parts[0].replace(",", "."))
                    max_rate = float(parts[1].replace(",", "."))

                    if min_rate >= max_rate:
                        raise ValueError("Минимум должен быть меньше максимума")

                    if min_rate < 0 or max_rate > 100:
                        raise ValueError("Курс должен быть в разумных пределах (0-100)")

                    self.bot.user_manager.update_user_data(
                        update.effective_user.id,
                        {"min_rate": min_rate, "max_rate": max_rate},
                    )

                    await update.message.reply_text(
                        f"✅ <b>Диапазон курса обновлен!</b>\n\n"
                        f"💰 Новый диапазон: <b>{min_rate:.2f} - {max_rate:.2f} UAH</b>\n\n"
                        f"💡 Теперь используйте /check для проверки предложений",
                        parse_mode="HTML",
                    )

                    context.user_data["waiting_for"] = None
                else:
                    raise ValueError("Неверный формат")

            except ValueError as e:
                await update.message.reply_text(
                    f"❌ <b>Ошибка:</b> {str(e)}\n\n"
                    f"Используйте формат: <code>минимум максимум</code>\n"
                    f"<b>Например:</b> <code>42.0 43.5</code>",
                    parse_mode="HTML",
                )

        elif context.user_data.get("waiting_for") == "limits":
            try:
                text = update.message.text.strip()
                parts = text.split()

                if len(parts) == 2:
                    min_limit = float(parts[0].replace(",", "."))
                    max_limit = float(parts[1].replace(",", "."))

                    if min_limit >= max_limit:
                        raise ValueError("Минимум должен быть меньше максимума")

                    if min_limit < 100 or max_limit > 1000000:
                        raise ValueError(
                            "Лимиты должны быть в разумных пределах (100-1,000,000 UAH)"
                        )

                    if min_limit < 1000:
                        await update.message.reply_text(
                            f"⚠️ <b>Предупреждение:</b> Минимальный лимит {min_limit:.0f} UAH очень мал.\n"
                            f"💰 Комиссия может быть значительной!",
                            parse_mode="HTML",
                        )

                    self.bot.user_manager.update_user_data(
                        update.effective_user.id,
                        {"min_limit": min_limit, "max_limit": max_limit},
                    )

                    await update.message.reply_text(
                        f"✅ <b>Лимиты сделок обновлены!</b>\n\n"
                        f"💳 Новые лимиты: <b>{min_limit:.0f} - {max_limit:.0f} UAH</b>\n\n"
                        f"💡 Теперь вы увидите только предложения с лимитами в этом диапазоне!\n"
                        f"🚀 Используйте /check для проверки",
                        parse_mode="HTML",
                    )

                    context.user_data["waiting_for"] = None
                else:
                    raise ValueError("Неверный формат")

            except ValueError as e:
                await update.message.reply_text(
                    f"❌ <b>Ошибка:</b> {str(e)}\n\n"
                    f"Используйте формат: <code>минимум максимум</code>\n"
                    f"<b>Например:</b> <code>5000 50000</code>",
                    parse_mode="HTML",
                )

        elif context.user_data.get("waiting_for") == "automonitor_rate":
            try:
                text = update.message.text.strip()
                parts = text.split()

                if len(parts) == 2:
                    min_rate = float(parts[0].replace(",", "."))
                    max_rate = float(parts[1].replace(",", "."))

                    if min_rate >= max_rate:
                        raise ValueError("Минимум должен быть меньше максимума")

                    if min_rate < 0 or max_rate > 100:
                        raise ValueError("Курс должен быть в разумных пределах (0-100)")

                    self.bot.user_manager.update_user_data(
                        update.effective_user.id,
                        {
                            "auto_monitor_min_rate": min_rate,
                            "auto_monitor_max_rate": max_rate,
                        },
                    )

                    await update.message.reply_text(
                        f"✅ <b>Диапазон автомониторинга обновлен!</b>\n\n"
                        f"⚡ Новый узкий диапазон: <b>{min_rate:.2f} - {max_rate:.2f} UAH</b>\n\n"
                        f"🔥 Автомониторинг будет искать только самые выгодные предложения!\n"
                        f"🚀 Проверка каждые 20 секунд (топ-5 предложений)",
                        parse_mode="HTML",
                    )

                    context.user_data["waiting_for"] = None
                else:
                    raise ValueError("Неверный формат")

            except ValueError as e:
                await update.message.reply_text(
                    f"❌ <b>Ошибка:</b> {str(e)}\n\n"
                    f"Используйте формат: <code>минимум максимум</code>\n"
                    f"<b>Например:</b> <code>40.5 41.5</code>",
                    parse_mode="HTML",
                )

        elif context.user_data.get("waiting_for") == "automonitor_limits":
            try:
                text = update.message.text.strip()
                parts = text.split()

                if len(parts) == 2:
                    min_limit = float(parts[0].replace(",", "."))
                    max_limit = float(parts[1].replace(",", "."))

                    if min_limit >= max_limit:
                        raise ValueError("Минимум должен быть меньше максимума")

                    if min_limit < 100 or max_limit > 1000000:
                        raise ValueError(
                            "Лимиты должны быть в разумных пределах (100-1,000,000 UAH)"
                        )

                    self.bot.user_manager.update_user_data(
                        update.effective_user.id,
                        {
                            "auto_monitor_min_limit": min_limit,
                            "auto_monitor_max_limit": max_limit,
                        },
                    )

                    await update.message.reply_text(
                        f"✅ <b>Лимиты автомониторинга обновлены!</b>\n\n"
                        f"🔥 Новые лимиты: <b>{min_limit:.0f} - {max_limit:.0f} UAH</b>\n\n"
                        f"⚡ Автомониторинг будет искать только лучшие предложения!\n"
                        f"🚀 Используйте /automonitor для включения",
                        parse_mode="HTML",
                    )

                    context.user_data["waiting_for"] = None
                else:
                    raise ValueError("Неверный формат")

            except ValueError as e:
                await update.message.reply_text(
                    f"❌ <b>Ошибка:</b> {str(e)}\n\n"
                    f"Используйте формат: <code>минимум максимум</code>\n"
                    f"<b>Например:</b> <code>10000 50000</code>",
                    parse_mode="HTML",
                )

    async def automonitor_command(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ):
        """Handle /automonitor command"""
        user_id = update.effective_user.id
        user_data = self.bot.user_manager.get_user_data(user_id)

        # Check if auto monitor is available
        if not self.auto_monitor:
            await update.message.reply_text(
                "❌ Автомониторинг недоступен. Сервис может быть временно отключен.",
                parse_mode="HTML",
            )
            return

        # Get monitoring status
        monitoring_status = self.auto_monitor.get_monitoring_status()
        is_user_enabled = user_data.get("auto_monitoring_enabled", False)

        # Create toggle button
        keyboard = [
            [
                InlineKeyboardButton(
                    f"{'❌ Выключить' if is_user_enabled else '✅ Включить'} автомониторинг",
                    callback_data="toggle_automonitor",
                )
            ],
            [
                InlineKeyboardButton(
                    "📊 Статус системы", callback_data="automonitor_system_status"
                )
            ],
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        status_text = f"""
🤖 <b>Автомониторинг P2P предложений</b>

👤 <b>Ваш статус:</b> {"✅ Включен" if is_user_enabled else "❌ Выключен"}

⚡ <b>Ваши настройки (узкий диапазон):</b>
💰 Диапазон: <b>{user_data.get("auto_monitor_min_rate", 40.5):.2f} - {user_data.get("auto_monitor_max_rate", 41.5):.2f} UAH</b>
💳 Лимиты: <b>{user_data.get("auto_monitor_min_limit", 10000):.0f} - {user_data.get("auto_monitor_max_limit", 50000):.0f} UAH</b>

⚙️ <b>Системные настройки:</b>
• Проверка каждые {monitoring_status["check_interval_seconds"]} сек ⚡
• Только топ-5 предложений (быстрая проверка)
• Без лимитов на уведомления! 🚀

📊 <b>Статус системы:</b> {"🟢 Активна" if monitoring_status["active"] else "🔴 Остановлена"}
👥 <b>Активных пользователей:</b> {monitoring_status["enabled_users_count"]}

🏦 <b>Ваши активные биржи:</b> {", ".join([ex.title() for ex in user_data.get("active_exchanges", ["binance"])])}

💡 <b>Как это работает:</b>
Бот проверяет только топ-5 предложений каждые 20 секунд. Используется узкий диапазон цен для поиска самых выгодных предложений.

⚡ <b>Совет по скорости:</b>
• Binance: ~10 сек (самая быстрая ⚡)
• ByBit: ~8 сек
• Bitget: ~15 сек
📌 Чем меньше бирж активно, тем быстрее работает бот!

🔧 Изменить настройки: /settings
🏦 Выбрать биржи: /exchanges
Используйте кнопки ниже для управления:
        """.strip()

        await update.message.reply_text(
            status_text, reply_markup=reply_markup, parse_mode="HTML"
        )

    async def _handle_automonitor_toggle(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ):
        """Handle automonitor toggle button"""
        query = update.callback_query
        user_id = query.from_user.id

        if not self.auto_monitor:
            await query.edit_message_text("❌ Автомониторинг недоступен")
            return

        user_data = self.bot.user_manager.get_user_data(user_id)
        current_status = user_data.get("auto_monitoring_enabled", False)
        new_status = not current_status

        # Toggle user's auto monitoring
        result_message = await self.auto_monitor.toggle_user_monitoring(
            user_id, new_status
        )

        # Update message with new status
        monitoring_status = self.auto_monitor.get_monitoring_status()

        keyboard = [
            [
                InlineKeyboardButton(
                    f"{'❌ Выключить' if new_status else '✅ Включить'} автомониторинг",
                    callback_data="toggle_automonitor",
                )
            ],
            [
                InlineKeyboardButton(
                    "📊 Статус системы", callback_data="automonitor_system_status"
                )
            ],
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        status_text = f"""
🤖 <b>Автомониторинг обновлен!</b>

{result_message}

👤 <b>Ваш статус:</b> {"✅ Включен" if new_status else "❌ Выключен"}
📊 <b>Система:</b> {"🟢 Активна" if monitoring_status["active"] else "🔴 Остановлена"}
👥 <b>Активных пользователей:</b> {monitoring_status["enabled_users_count"]}

💡 Чтобы получать уведомления:
• Настройте узкий диапазон цен (/settings)
• Настройте лимиты для автомониторинга
• Без лимитов - получайте все уведомления! 🚀
        """.strip()

        await query.edit_message_text(
            status_text, reply_markup=reply_markup, parse_mode="HTML"
        )

    def _format_generic_offer(self, offer: Dict[str, Any]) -> str:
        """Generic offer formatting for fallback"""
        username = offer.get("username", "Unknown")
        price = offer.get("price", 0)
        available = offer.get("available", 0)
        min_amount = offer.get("min_amount", 0)
        max_amount = offer.get("max_amount", 0)
        exchange = offer.get("exchange", "Unknown").title()
        link = offer.get("link", "#")

        return f"""💰 <b>{exchange} P2P Offer</b>
👤 Пользователь: <b>{username}</b>
💲 Цена: <b>{price:.2f} UAH</b> за USDT
📊 Доступно: <b>{available:.1f} USDT</b>
💳 Лимиты: {min_amount:.0f} - {max_amount:.0f} UAH
🔗 Ссылка: <a href='{link}'>Перейти на {exchange}</a>""".strip()

    async def exchanges_command(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ):
        """Handle /exchanges command - manage active exchanges"""
        user_id = update.effective_user.id
        user_data = self.bot.user_manager.get_user_data(user_id)

        available_exchanges = self.bot.exchange_manager.get_available_exchanges()
        active_exchanges = self.bot.exchange_manager.get_active_exchanges()
        user_exchanges = user_data.get(
            "active_exchanges", ["bybit", "bitget", "binance"]
        )

        # Create keyboard with exchange toggles
        keyboard = []
        for exchange in active_exchanges:
            is_enabled = exchange in user_exchanges
            status_icon = "✅" if is_enabled else "❌"
            keyboard.append(
                [
                    InlineKeyboardButton(
                        f"{status_icon} {exchange.title()}",
                        callback_data=f"toggle_exchange_{exchange}",
                    )
                ]
            )

        keyboard.append(
            [
                InlineKeyboardButton(
                    "📊 Показать статус", callback_data="show_exchanges_status"
                )
            ]
        )
        reply_markup = InlineKeyboardMarkup(keyboard)

        exchanges_text = f"""
🏦 <b>Управление биржами</b>

💡 <b>Доступные биржи:</b>
{chr(10).join([f"• {ex.title()}" for ex in active_exchanges])}

✅ <b>Ваши активные биржи:</b>
{chr(10).join([f"• {ex.title()}" for ex in user_exchanges]) if user_exchanges else "Не выбрано"}

🔧 <b>Управление:</b>
Нажмите на кнопки ниже чтобы включить/выключить биржи для мониторинга.

💡 <b>Рекомендация:</b> Используйте несколько бирж для лучших результатов!
        """.strip()

        await update.message.reply_text(
            exchanges_text, reply_markup=reply_markup, parse_mode="HTML"
        )

    def build_main_reply_keyboard(self):
        """Build a reply keyboard with main commands"""
        keyboard_layout = [
            [KeyboardButton("/check"), KeyboardButton("/settings")],
            [KeyboardButton("/exchanges"), KeyboardButton("/status")],
            [KeyboardButton("/help")],
        ]
        return ReplyKeyboardMarkup(keyboard_layout, resize_keyboard=True)

    async def _handle_exchange_toggle(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE, exchange_name: str
    ):
        """Toggle specific exchange for the user"""
        query = update.callback_query
        user_id = query.from_user.id
        user_data = self.bot.user_manager.get_user_data(user_id)

        active_exchanges = self.bot.exchange_manager.get_active_exchanges()
        if exchange_name not in active_exchanges:
            await query.edit_message_text(
                f"❌ Биржа {exchange_name.title()} недоступна"
            )
            return

        user_exchanges = set(
            user_data.get("active_exchanges", ["bybit", "binance", "bitget"])
        )
        if exchange_name in user_exchanges:
            user_exchanges.remove(exchange_name)
        else:
            user_exchanges.add(exchange_name)

        # Persist user setting
        self.bot.user_manager.update_user_data(
            user_id, {"active_exchanges": list(user_exchanges)}
        )

        # Rebuild keyboard
        keyboard = []
        for ex in active_exchanges:
            is_enabled = ex in user_exchanges
            status_icon = "✅" if is_enabled else "❌"
            keyboard.append(
                [
                    InlineKeyboardButton(
                        f"{status_icon} {ex.title()}",
                        callback_data=f"toggle_exchange_{ex}",
                    )
                ]
            )
        keyboard.append(
            [
                InlineKeyboardButton(
                    "📊 Показать статус", callback_data="show_exchanges_status"
                )
            ]
        )
        reply_markup = InlineKeyboardMarkup(keyboard)

        await query.edit_message_text(
            f"🏦 <b>Биржи обновлены</b>\n\n"
            f"✅ Активные: {', '.join([ex.title() for ex in sorted(user_exchanges)]) if user_exchanges else 'нет'}\n\n"
            f"Нажмите кнопки, чтобы переключать.",
            reply_markup=reply_markup,
            parse_mode="HTML",
        )

    async def _show_exchanges_status(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ):
        query = update.callback_query
        user_id = query.from_user.id
        user_data = self.bot.user_manager.get_user_data(user_id)
        user_exchanges = user_data.get(
            "active_exchanges", ["bybit", "binance", "bitget"]
        )

        await query.edit_message_text(
            f"📊 <b>Ваши активные биржи:</b> {', '.join([ex.title() for ex in user_exchanges])}",
            parse_mode="HTML",
        )

    async def menu_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Show main command menu on demand"""
        keyboard = self.build_main_reply_keyboard()
        await update.message.reply_text(
            "📱 Меню команд:", reply_markup=keyboard, parse_mode="HTML"
        )

    def register_handlers(self, application):
        """Register all handlers"""
        application.add_handler(CommandHandler("start", self.start_command))
        application.add_handler(CommandHandler("check", self.check_command))
        application.add_handler(CommandHandler("refresh", self.refresh_command))
        application.add_handler(CommandHandler("settings", self.settings_command))
        application.add_handler(CommandHandler("status", self.status_command))
        application.add_handler(CommandHandler("help", self.help_command))
        application.add_handler(CommandHandler("automonitor", self.automonitor_command))
        application.add_handler(CommandHandler("exchanges", self.exchanges_command))
        application.add_handler(CommandHandler("menu", self.menu_command))
        application.add_handler(CallbackQueryHandler(self.button_callback))
        application.add_handler(
            MessageHandler(filters.TEXT & ~filters.COMMAND, self.message_handler)
        )
