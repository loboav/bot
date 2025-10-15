#!/usr/bin/env python3
"""
Bot Handlers
============

Telegram bot command handlers for P2P monitoring
"""

import asyncio
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

📊 <b>Доступные биржи:</b>
✅ ByBit (реальные данные с прямыми ссылками)
🔄 OKX, Binance, MEXC (скоро)

⚙️ <b>Команды:</b>
/check - Проверить текущие предложения
/settings - Настроить диапазон курса и автомониторинг
/status - Показать текущие настройки
/help - Показать все команды
🤖 /automonitor - Управление автомониторингом

💡 <b>Начните с команды /check для просмотра текущих предложений!</b>
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
        """Handle /check command - show current offers"""
        user_id = update.effective_user.id
        user_data = self.bot.user_manager.get_user_data(user_id)
        
        # Send "checking" message
        checking_msg = await update.message.reply_text("🔍 Проверяю текущие P2P предложения...\n⏳ Это может занять 15-20 секунд")
        
        try:
            # Get offers from ByBit through exchange manager
            bybit_exchange = self.bot.exchange_manager.get_exchange('bybit')
            if not bybit_exchange:
                await checking_msg.edit_text("❌ ByBit недоступен. Попробуйте позже.")
                return
            
            offers = await bybit_exchange.get_offers()
            
            if not offers:
                await checking_msg.edit_text("❌ Не удалось получить предложения. Попробуйте позже.")
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
                
                response = f"📊 <b>Найдено {len(offers)} предложений</b>, но ни одно не подходит по вашим критериям:\n\n"
                response += f"💰 Ваш диапазон цен: <b>{user_data['min_rate']:.2f}-{user_data['max_rate']:.2f} UAH</b>\n"
                response += f"💳 Ваши лимиты: <b>{user_data.get('min_limit', 5000):.0f}-{user_data.get('max_limit', 100000):.0f} UAH</b>\n\n"
                response += f"💡 Доступные цены: <b>{min_price:.2f} - {max_price:.2f} UAH</b>\n\n"
                response += "⚡️ Используйте /settings для изменения настроек"
            else:
                # Sort by price (best offers first)
                filtered_offers.sort(key=lambda x: x['price'])
                
                response = f"💎 <b>Найдено {len(filtered_offers)} предложений в вашем диапазоне:</b>\n\n"
                
                # Show top 5 offers
                for i, offer in enumerate(filtered_offers[:5], 1):
                    offer_text = bybit_exchange.format_offer_message(offer)
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
🏦 <b>Активные биржи:</b> ByBit
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
✅ ByBit - активна
🔄 OKX, Binance, MEXC - скоро

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
    
    def build_main_reply_keyboard(self):
        """Build a reply keyboard with main commands"""
        keyboard_layout = [
            [KeyboardButton('/check'), KeyboardButton('/settings')],
            [KeyboardButton('/status'), KeyboardButton('/help')]
        ]
        return ReplyKeyboardMarkup(keyboard_layout, resize_keyboard=True)

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
        application.add_handler(CommandHandler("settings", self.settings_command))
        application.add_handler(CommandHandler("automonitor", self.automonitor_command))
        application.add_handler(CommandHandler("status", self.status_command))
        application.add_handler(CommandHandler("help", self.help_command))
        application.add_handler(CallbackQueryHandler(self.button_callback))
        application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self.message_handler))
