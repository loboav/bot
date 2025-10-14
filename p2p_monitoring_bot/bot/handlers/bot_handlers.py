#!/usr/bin/env python3
"""
Bot Handlers
============

Telegram bot command handlers for P2P monitoring
"""

import asyncio
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes

class BotHandlers:
    """Telegram bot handlers with full P2P functionality"""
    
    def __init__(self, bot_instance):
        self.bot = bot_instance
    
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
/settings - Настроить диапазон курса
/status - Показать текущие настройки
/help - Показать все команды

💡 <b>Начните с команды /check для просмотра текущих предложений!</b>
        """.strip()
        
        await update.message.reply_text(welcome_message, parse_mode='HTML')
    
    async def check_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /check command - show current offers"""
        user_id = update.effective_user.id
        user_data = self.bot.user_manager.get_user_data(user_id)
        
        # Send "checking" message
        checking_msg = await update.message.reply_text("🔍 Проверяю текущие P2P предложения...\n⏳ Это может занять 15-20 секунд")
        
        try:
            # Get offers from ByBit
            bybit_exchange = self.bot.exchanges['bybit']
            offers = await bybit_exchange.get_offers()
            
            if not offers:
                await checking_msg.edit_text("❌ Не удалось получить предложения. Попробуйте позже.")
                return
            
            # Filter offers by user's rate range
            filtered_offers = [
                offer for offer in offers
                if user_data['min_rate'] <= offer['price'] <= user_data['max_rate']
            ]
            
            # Prepare response
            if not filtered_offers:
                all_prices = [offer['price'] for offer in offers]
                min_price = min(all_prices) if all_prices else 0
                max_price = max(all_prices) if all_prices else 0
                
                response = f"📊 <b>Найдено {len(offers)} предложений</b>, но ни одно не попадает в ваш диапазон <b>{user_data['min_rate']:.2f}-{user_data['max_rate']:.2f} UAH</b>\n\n"
                response += f"💡 Доступный диапазон цен: <b>{min_price:.2f} - {max_price:.2f} UAH</b>\n\n"
                response += "⚙️ Используйте /settings для изменения диапазона"
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
            [InlineKeyboardButton("📊 Показать статус", callback_data="show_status")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        settings_text = f"""
⚙️ <b>Настройки мониторинга</b>

💰 <b>Диапазон курса:</b> {user_data['min_rate']:.2f} - {user_data['max_rate']:.2f} UAH
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
🔍 <b>/check</b> - Проверить текущие P2P предложения
⚙️ <b>/settings</b> - Настроить диапазон курса
📊 <b>/status</b> - Показать текущие настройки
❓ <b>/help</b> - Показать это сообщение

💡 <b>Как использовать:</b>
1. Настройте диапазон курса через /settings
2. Проверяйте предложения командой /check
3. Получайте прямые ссылки для покупки!

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
    
    def register_handlers(self, application):
        """Register all handlers"""
        application.add_handler(CommandHandler("start", self.start_command))
        application.add_handler(CommandHandler("check", self.check_command))
        application.add_handler(CommandHandler("settings", self.settings_command))
        application.add_handler(CommandHandler("status", self.status_command))
        application.add_handler(CommandHandler("help", self.help_command))
        application.add_handler(CallbackQueryHandler(self.button_callback))
        application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self.message_handler))
