#!/usr/bin/env python3
"""
Bot Handlers
============

Telegram bot command handlers for P2P monitoring
"""

import asyncio
from typing import Dict, Any
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes

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

⚙️ <b>Команды:</b>
/check - Проверить предложения с всех активных бирж
/exchanges - Выбрать биржи для мониторинга
/settings - Настроить диапазон курса и автомониторинг
/status - Показать текущие настройки
/help - Показать все команды
🤖 /automonitor - Управление автомониторингом

💡 <b>Начните с /check для просмотра предложений!</b>
        """.strip()
        
        await update.message.reply_text(welcome_message, parse_mode='HTML')
        
        # Show main command menu as reply keyboard
        keyboard = self.build_main_reply_keyboard()
        await update.message.reply_text(
            "📱 Меню команд:",
            reply_markup=keyboard,
            parse_mode='HTML'
        )
    
    async def check_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /check command - show current offers from all active exchanges"""
        user_id = update.effective_user.id
        user_data = self.bot.user_manager.get_user_data(user_id)
        
        # Get active exchanges for user
        active_exchanges = user_data.get('active_exchanges', ['bybit', 'binance', 'bitget'])
        
        # Send "checking" message
        exchanges_text = ", ".join([ex.title() for ex in active_exchanges])
        checking_msg = await update.message.reply_text(
            f"🔍 Проверяю P2P предложения на: {exchanges_text}...\n⏳ Это может занять 15-30 секунд"
        )
        
        try:
            # Get combined offers from all active exchanges
            offers = await self.bot.exchange_manager.get_combined_offers(active_exchanges)
            
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
                if not (user_data['min_rate'] <= offer['price'] <= user_data['max_rate']):
                    continue
                    
                # Limits filter - check if offer's limits overlap with user's requirements
                offer_min = offer.get('min_amount', 0)
                offer_max = offer.get('max_amount', 999999)
                user_min_limit = user_data.get('min_limit', 0)
                user_max_limit = user_data.get('max_limit', 999999)
                
                # Check if there's overlap between offer limits and user limits
                if offer_max >= user_min_limit and offer_min <= user_max_limit:
                    filtered_offers.append(offer)
            
            # Prepare response
            if not filtered_offers:
                all_prices = [offer['price'] for offer in offers]
                min_price = min(all_prices) if all_prices else 0
                max_price = max(all_prices) if all_prices else 0
                
                # Count offers by exchange
                exchange_counts = {}
                for offer in offers:
                    exchange = offer.get('exchange', 'Unknown')
                    exchange_counts[exchange] = exchange_counts.get(exchange, 0) + 1
                
                count_text = ", ".join([f"{ex.title()}: {count}" for ex, count in exchange_counts.items()])
                
                response = f"📅 <b>Найдено {len(offers)} предложений</b> ({count_text}), но ни одно не подходит по вашим критериям:\n\n"
                response += f"💰 Ваш диапазон цен: <b>{user_data['min_rate']:.2f}-{user_data['max_rate']:.2f} UAH</b>\n"
                response += f"💳 Ваши лимиты: <b>{user_data.get('min_limit', 5000):.0f}-{user_data.get('max_limit', 100000):.0f} UAH</b>\n\n"
                response += f"💡 Доступные цены: <b>{min_price:.2f} - {max_price:.2f} UAH</b>\n\n"
                response += "⚡️ Используйте /settings для изменения настроек"
            else:
                # Sort by price (best offers first)
                filtered_offers.sort(key=lambda x: x['price'])
                
                # Count filtered offers by exchange
                exchange_counts = {}
                for offer in filtered_offers:
                    exchange = offer.get('exchange', 'Unknown')
                    exchange_counts[exchange] = exchange_counts.get(exchange, 0) + 1
                
                count_text = ", ".join([f"{ex.title()}: {count}" for ex, count in exchange_counts.items()])
                
                response = f"💎 <b>Найдено {len(filtered_offers)} предложений</b> ({count_text}) в вашем диапазоне:\n\n"
                
                # Show top 5 offers with exchange info
                for i, offer in enumerate(filtered_offers[:5], 1):
                    # Get the appropriate exchange to format the message
                    exchange_name = offer.get('exchange', 'bybit')
                    exchange = self.bot.exchange_manager.get_exchange(exchange_name)
                    
                    if exchange:
                        offer_text = exchange.format_offer_message(offer)
                    else:
                        # Fallback formatting
                        offer_text = self._format_generic_offer(offer)
                    
                    response += f"<b>{i}.</b> {offer_text}\n\n"
                
                if len(filtered_offers) > 5:
                    response += f"... и еще {len(filtered_offers) - 5} предложений\n\n"
                
                response += "💡 Нажмите на прямые ссылки для быстрой покупки!"
            
            await checking_msg.edit_text(response, parse_mode='HTML', disable_web_page_preview=True)
            
        except Exception as e:
            await checking_msg.edit_text(f"❌ Ошибка при получении данных: {str(e)[:100]}...")
    
    async def settings_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /settings command"""
        user_id = update.effective_user.id
        user_data = self.bot.user_manager.get_user_data(user_id)
        
        keyboard = [
            [InlineKeyboardButton("💰 Изменить диапазон курса", callback_data="set_rate_range")],
            [InlineKeyboardButton("💳 Настроить лимиты", callback_data="set_limits")],
            [InlineKeyboardButton("🤖 Автомониторинг", callback_data="toggle_automonitor")],
            [InlineKeyboardButton("📊 Показать статус", callback_data="show_status")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        settings_text = f"""
⚡️ <b>Настройки мониторинга</b>

💰 <b>Диапазон курса:</b> {user_data['min_rate']:.2f} - {user_data['max_rate']:.2f} UAH
💳 <b>Лимиты сделок:</b> {user_data.get('min_limit', 5000):.0f} - {user_data.get('max_limit', 100000):.0f} UAH
🤖 <b>Автомониторинг:</b> {'✅ Включен' if user_data.get('auto_monitoring_enabled', False) else '❌ Выключен'}
🏦 <b>Активные биржи:</b> {', '.join([ex.title() for ex in user_data.get('active_exchanges', ['bybit', 'binance', 'bitget'])])}
🔔 <b>Уведомления:</b> {'✅ Включены' if user_data['notifications_enabled'] else '❌ Выключены'}

Выберите что настроить:
        """.strip()
        
        await update.message.reply_text(settings_text, reply_markup=reply_markup, parse_mode='HTML')
    
    async def status_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /status command"""
        user_id = update.effective_user.id
        user_data = self.bot.user_manager.get_user_data(user_id)
        
        status_text = f"""
📊 <b>Статус мониторинга</b>

👤 <b>Пользователь:</b> {update.effective_user.first_name}
🆔 <b>ID:</b> {user_id}

💰 <b>Диапазон курса:</b> {user_data['min_rate']:.2f} - {user_data['max_rate']:.2f} UAH
💳 <b>Лимиты сделок:</b> {user_data.get('min_limit', 5000):.0f} - {user_data.get('max_limit', 100000):.0f} UAH
🤖 <b>Автомониторинг:</b> {'✅ Включен' if user_data.get('auto_monitoring_enabled', False) else '❌ Выключен'}
🔔 <b>Уведомления:</b> {'✅ Включены' if user_data['notifications_enabled'] else '❌ Выключены'}

🏦 <b>Биржи:</b>
✅ ByBit - активна (браузер)
✅ Bitget - активна (браузер)
✅ Binance - активна (браузер)
🔄 OKX, MEXC, BingX - скоро

🏦 <b>Ваши активные:</b> {', '.join([ex.title() for ex in user_data.get('active_exchanges', ['bybit', 'binance', 'bitget'])])}

⏰ <b>Время проверки:</b> {context.application.bot.start_time if hasattr(context.application.bot, 'start_time') else 'N/A'}
        """.strip()
        
        await update.message.reply_text(status_text, parse_mode='HTML')
    
    async def help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /help command"""
        help_text = """
🤖 <b>Команды P2P Monitoring Bot:</b>

🏠 <b>/start</b> - Приветствие и инструкция
📱 <b>/menu</b> - Показать меню команд
🔍 <b>/check</b> - Проверить текущие P2P предложения
🏦 <b>/exchanges</b> - Выбрать биржи для мониторинга
⚙️ <b>/settings</b> - Настроить диапазон курса и автомониторинг
🤖 <b>/automonitor</b> - Управление автомониторингом
📊 <b>/status</b> - Показать текущие настройки
❓ <b>/help</b> - Показать это сообщение

💡 <b>Как использовать:</b>
1. Настройте диапазон курса через /settings
2. Проверяйте предложения командой /check
3. Получайте прямые ссылки для покупки!

📱 <b>Меню команд:</b> Используйте /menu для быстрого доступа к кнопкам команд!

🎯 <b>Пример:</b> Если установить диапазон 42.0-43.0 UAH, бот покажет только предложения в этих пределах.
        """.strip()
        
        await update.message.reply_text(help_text, parse_mode='HTML')
    
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
                parse_mode='HTML'
            )
            context.user_data['waiting_for'] = 'rate_range'
        
        elif query.data == "set_limits":
            user_data = self.bot.user_manager.get_user_data(user_id)
            
            await query.edit_message_text(
                f"💳 <b>Настройка лимитов сделок</b>\n\n"
                f"Отправьте новые лимиты в формате:\n"
                f"<code>минимум максимум</code>\n\n"
                f"<b>Пример:</b> <code>5000 50000</code>\n\n"
                f"Текущие лимиты: <b>{user_data.get('min_limit', 5000):.0f} - {user_data.get('max_limit', 100000):.0f} UAH</b>\n\n"
                f"💡 <b>Почему это важно:</b>\n"
                f"• Маленькие суммы = большая комиссия\n"
                f"• Оптимально: от 5000 UAH",
                parse_mode='HTML'
            )
            context.user_data['waiting_for'] = 'limits'
        
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
        if context.user_data.get('waiting_for') == 'rate_range':
            try:
                text = update.message.text.strip()
                parts = text.split()
                
                if len(parts) == 2:
                    min_rate = float(parts[0].replace(',', '.'))
                    max_rate = float(parts[1].replace(',', '.'))
                    
                    if min_rate >= max_rate:
                        raise ValueError("Минимум должен быть меньше максимума")
                    
                    if min_rate < 0 or max_rate > 100:
                        raise ValueError("Курс должен быть в разумных пределах (0-100)")
                    
                    self.bot.user_manager.update_user_data(update.effective_user.id, {
                        'min_rate': min_rate,
                        'max_rate': max_rate
                    })
                    
                    await update.message.reply_text(
                        f"✅ <b>Диапазон курса обновлен!</b>\n\n"
                        f"💰 Новый диапазон: <b>{min_rate:.2f} - {max_rate:.2f} UAH</b>\n\n"
                        f"💡 Теперь используйте /check для проверки предложений",
                        parse_mode='HTML'
                    )
                    
                    context.user_data['waiting_for'] = None
                else:
                    raise ValueError("Неверный формат")
                    
            except ValueError as e:
                await update.message.reply_text(
                    f"❌ <b>Ошибка:</b> {str(e)}\n\n"
                    f"Используйте формат: <code>минимум максимум</code>\n"
                    f"<b>Например:</b> <code>42.0 43.5</code>",
                    parse_mode='HTML'
                )
        
        elif context.user_data.get('waiting_for') == 'limits':
            try:
                text = update.message.text.strip()
                parts = text.split()
                
                if len(parts) == 2:
                    min_limit = float(parts[0].replace(',', '.'))
                    max_limit = float(parts[1].replace(',', '.'))
                    
                    if min_limit >= max_limit:
                        raise ValueError("Минимум должен быть меньше максимума")
                    
                    if min_limit < 100 or max_limit > 1000000:
                        raise ValueError("Лимиты должны быть в разумных пределах (100-1,000,000 UAH)")
                    
                    if min_limit < 1000:
                        await update.message.reply_text(
                            f"⚠️ <b>Предупреждение:</b> Минимальный лимит {min_limit:.0f} UAH очень мал.\n"
                            f"💰 Комиссия может быть значительной!",
                            parse_mode='HTML'
                        )
                    
                    self.bot.user_manager.update_user_data(update.effective_user.id, {
                        'min_limit': min_limit,
                        'max_limit': max_limit
                    })
                    
                    await update.message.reply_text(
                        f"✅ <b>Лимиты сделок обновлены!</b>\n\n"
                        f"💳 Новые лимиты: <b>{min_limit:.0f} - {max_limit:.0f} UAH</b>\n\n"
                        f"💡 Теперь вы увидите только предложения с лимитами в этом диапазоне!\n"
                        f"🚀 Используйте /check для проверки",
                        parse_mode='HTML'
                    )
                    
                    context.user_data['waiting_for'] = None
                else:
                    raise ValueError("Неверный формат")
                    
            except ValueError as e:
                await update.message.reply_text(
                    f"❌ <b>Ошибка:</b> {str(e)}\n\n"
                    f"Используйте формат: <code>минимум максимум</code>\n"
                    f"<b>Например:</b> <code>5000 50000</code>",
                    parse_mode='HTML'
                )
    
    async def automonitor_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /automonitor command"""
        user_id = update.effective_user.id
        user_data = self.bot.user_manager.get_user_data(user_id)
        
        # Check if auto monitor is available
        if not self.auto_monitor:
            await update.message.reply_text(
                "❌ Автомониторинг недоступен. Сервис может быть временно отключен.",
                parse_mode='HTML'
            )
            return
            
        # Get monitoring status
        monitoring_status = self.auto_monitor.get_monitoring_status()
        is_user_enabled = user_data.get('auto_monitoring_enabled', False)
        
        # Create toggle button
        keyboard = [
            [InlineKeyboardButton(
                f"{'❌ Выключить' if is_user_enabled else '✅ Включить'} автомониторинг",
                callback_data="toggle_automonitor"
            )],
            [InlineKeyboardButton("📊 Статус системы", callback_data="automonitor_system_status")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        status_text = f"""
🤖 <b>Автомониторинг P2P предложений</b>

👤 <b>Ваш статус:</b> {'✅ Включен' if is_user_enabled else '❌ Выключен'}

⚙️ <b>Настройки:</b>
• Проверка каждые {monitoring_status['check_interval_minutes']} мин
• Макс. {monitoring_status['max_notifications_per_hour']} уведомлений/час
• Минимальный интервал: {monitoring_status['safe_interval_minutes']} мин

📊 <b>Система:</b> {'🟢 Активна' if monitoring_status['active'] else '🔴 Остановлена'}
👥 <b>Активных пользователей:</b> {monitoring_status['enabled_users_count']}

💡 <b>Как это работает:</b>
Бот автоматически проверяет предложения и отправляет уведомления, когда находит что-то подходящее по вашим критериям (цена, лимиты).

Используйте кнопки ниже для управления:
        """.strip()
        
        await update.message.reply_text(status_text, reply_markup=reply_markup, parse_mode='HTML')
    
    async def _handle_automonitor_toggle(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle automonitor toggle button"""
        query = update.callback_query
        user_id = query.from_user.id
        
        if not self.auto_monitor:
            await query.edit_message_text("❌ Автомониторинг недоступен")
            return
            
        user_data = self.bot.user_manager.get_user_data(user_id)
        current_status = user_data.get('auto_monitoring_enabled', False)
        new_status = not current_status
        
        # Toggle user's auto monitoring
        result_message = await self.auto_monitor.toggle_user_monitoring(user_id, new_status)
        
        # Update message with new status
        monitoring_status = self.auto_monitor.get_monitoring_status()
        
        keyboard = [
            [InlineKeyboardButton(
                f"{'❌ Выключить' if new_status else '✅ Включить'} автомониторинг",
                callback_data="toggle_automonitor"
            )],
            [InlineKeyboardButton("📊 Статус системы", callback_data="automonitor_system_status")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        status_text = f"""
🤖 <b>Автомониторинг обновлен!</b>

{result_message}

👤 <b>Ваш статус:</b> {'✅ Включен' if new_status else '❌ Выключен'}
📊 <b>Система:</b> {'🟢 Активна' if monitoring_status['active'] else '🔴 Остановлена'}
👥 <b>Активных пользователей:</b> {monitoring_status['enabled_users_count']}

💡 Чтобы получать уведомления, убедитесь что:
• Настроен диапазон цен (/settings)
• Настроены лимиты сделок
• Включены уведомления
        """.strip()
        
        await query.edit_message_text(status_text, reply_markup=reply_markup, parse_mode='HTML')
    
    def _format_generic_offer(self, offer: Dict[str, Any]) -> str:
        """Generic offer formatting for fallback"""
        username = offer.get('username', 'Unknown')
        price = offer.get('price', 0)
        available = offer.get('available', 0)
        min_amount = offer.get('min_amount', 0)
        max_amount = offer.get('max_amount', 0)
        exchange = offer.get('exchange', 'Unknown').title()
        link = offer.get('link', '#')
        
        return f"""💰 <b>{exchange} P2P Offer</b>
👤 Пользователь: <b>{username}</b>
💲 Цена: <b>{price:.2f} UAH</b> за USDT
📊 Доступно: <b>{available:.1f} USDT</b>
💳 Лимиты: {min_amount:.0f} - {max_amount:.0f} UAH
🔗 Ссылка: <a href='{link}'>Перейти на {exchange}</a>""".strip()
    
    async def exchanges_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /exchanges command - manage active exchanges"""
        user_id = update.effective_user.id
        user_data = self.bot.user_manager.get_user_data(user_id)
        
        available_exchanges = self.bot.exchange_manager.get_available_exchanges()
        active_exchanges = self.bot.exchange_manager.get_active_exchanges()
        user_exchanges = user_data.get('active_exchanges', ['bybit', 'bitget', 'binance'])
        
        # Create keyboard with exchange toggles
        keyboard = []
        for exchange in active_exchanges:
            is_enabled = exchange in user_exchanges
            status_icon = "✅" if is_enabled else "❌"
            keyboard.append([InlineKeyboardButton(
                f"{status_icon} {exchange.title()}",
                callback_data=f"toggle_exchange_{exchange}"
            )])
        
        keyboard.append([InlineKeyboardButton("📊 Показать статус", callback_data="show_exchanges_status")])
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
        
        await update.message.reply_text(exchanges_text, reply_markup=reply_markup, parse_mode='HTML')
    
    def build_main_reply_keyboard(self):
        """Build a reply keyboard with main commands"""
        keyboard_layout = [
            [KeyboardButton('/check'), KeyboardButton('/settings')],
            [KeyboardButton('/exchanges'), KeyboardButton('/status')],
            [KeyboardButton('/help')]
        ]
        return ReplyKeyboardMarkup(keyboard_layout, resize_keyboard=True)

    async def _handle_exchange_toggle(self, update: Update, context: ContextTypes.DEFAULT_TYPE, exchange_name: str):
        """Toggle specific exchange for the user"""
        query = update.callback_query
        user_id = query.from_user.id
        user_data = self.bot.user_manager.get_user_data(user_id)

        active_exchanges = self.bot.exchange_manager.get_active_exchanges()
        if exchange_name not in active_exchanges:
            await query.edit_message_text(f"❌ Биржа {exchange_name.title()} недоступна")
            return

        user_exchanges = set(user_data.get('active_exchanges', ['bybit', 'binance', 'bitget']))
        if exchange_name in user_exchanges:
            user_exchanges.remove(exchange_name)
        else:
            user_exchanges.add(exchange_name)

        # Persist user setting
        self.bot.user_manager.update_user_data(user_id, {
            'active_exchanges': list(user_exchanges)
        })

        # Rebuild keyboard
        keyboard = []
        for ex in active_exchanges:
            is_enabled = ex in user_exchanges
            status_icon = "✅" if is_enabled else "❌"
            keyboard.append([InlineKeyboardButton(
                f"{status_icon} {ex.title()}",
                callback_data=f"toggle_exchange_{ex}"
            )])
        keyboard.append([InlineKeyboardButton("📊 Показать статус", callback_data="show_exchanges_status")])
        reply_markup = InlineKeyboardMarkup(keyboard)

        await query.edit_message_text(
            f"🏦 <b>Биржи обновлены</b>\n\n"
            f"✅ Активные: {', '.join([ex.title() for ex in sorted(user_exchanges)]) if user_exchanges else 'нет'}\n\n"
            f"Нажмите кнопки, чтобы переключать.",
            reply_markup=reply_markup,
            parse_mode='HTML'
        )

    async def _show_exchanges_status(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        user_id = query.from_user.id
        user_data = self.bot.user_manager.get_user_data(user_id)
        user_exchanges = user_data.get('active_exchanges', ['bybit', 'binance', 'bitget'])

        await query.edit_message_text(
            f"📊 <b>Ваши активные биржи:</b> {', '.join([ex.title() for ex in user_exchanges])}",
            parse_mode='HTML'
        )

    async def menu_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Show main command menu on demand"""
        keyboard = self.build_main_reply_keyboard()
        await update.message.reply_text(
            "📱 Меню команд:",
            reply_markup=keyboard,
            parse_mode='HTML'
        )

    def register_handlers(self, application):
        """Register all handlers"""
        application.add_handler(CommandHandler("start", self.start_command))
        application.add_handler(CommandHandler("menu", self.menu_command))
        application.add_handler(CommandHandler("check", self.check_command))
        application.add_handler(CommandHandler("exchanges", self.exchanges_command))
        application.add_handler(CommandHandler("settings", self.settings_command))
        application.add_handler(CommandHandler("automonitor", self.automonitor_command))
        application.add_handler(CommandHandler("status", self.status_command))
        application.add_handler(CommandHandler("help", self.help_command))
        application.add_handler(CallbackQueryHandler(self.button_callback))
        application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self.message_handler))
