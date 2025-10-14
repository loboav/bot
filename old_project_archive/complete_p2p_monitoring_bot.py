#!/usr/bin/env python3
"""
Complete P2P USDT-UAH Monitoring Bot
====================================

Telegram bot that monitors P2P USDT-UAH rates across multiple exchanges
and sends notifications when rates fall within user-defined ranges.

Currently supported: ByBit (with real data extraction)
Planned: OKX, Binance, MEXC, BitGet, BingX, Telegram Wallet, Crypto bot
"""

import asyncio
import json
import time
import re
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
import logging

# Telegram bot imports
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes

# Browser automation for real data
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import traceback

# Import configuration
from bot_config import (
    BOT_TOKEN, MONITORING_INTERVAL, MAX_OFFERS_PER_NOTIFICATION,
    BROWSER_HEADLESS, BROWSER_TIMEOUT, USERS_DATA_FILE, OFFERS_CACHE_FILE,
    LOG_LEVEL, DEFAULT_USER_SETTINGS
)

# Configuration
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=getattr(logging, LOG_LEVEL)
)
logger = logging.getLogger(__name__)

class P2PExchange:
    """Base class for P2P exchange integrations"""
    
    def __init__(self, name: str):
        self.name = name
        self.last_update = None
        self.offers_cache = []
    
    async def get_offers(self) -> List[Dict[str, Any]]:
        """Get P2P offers for USDT-UAH pair"""
        raise NotImplementedError
    
    def format_offer_message(self, offer: Dict[str, Any]) -> str:
        """Format offer for user notification"""
        username = offer.get('username', 'Unknown')
        price = offer.get('price', 'N/A')
        available = offer.get('available', 'N/A')
        min_amount = offer.get('min_amount', 'N/A')
        max_amount = offer.get('max_amount', 'N/A')
        link = offer.get('link', 'N/A')
        
        return f"""🏦 **{self.name}**
👤 {username}: **{price} UAH/USDT**
📊 Объем: {available} USDT
💳 Лимит: {min_amount} - {max_amount} UAH
🔗 Ссылка: {link}""".strip()
    

class ByBitP2P(P2PExchange):
    """ByBit P2P integration with real browser data extraction"""
    
    def __init__(self):
        super().__init__("ByBit")
        self.driver = None
        self.base_url = "https://www.bybit.com/fiat/trade/otc/?actionType=1&token=USDT&fiat=UAH&paymentMethod="
        
    def setup_browser(self):
        """Setup headless Chrome browser"""
        if self.driver:
            return True
            
        try:
            chrome_options = Options()
            
            # Use headless mode from config
            if BROWSER_HEADLESS:
                chrome_options.add_argument('--headless=new')
            
            # Standard optimization options
            chrome_options.add_argument('--no-sandbox')
            chrome_options.add_argument('--disable-dev-shm-usage')
            chrome_options.add_argument('--disable-blink-features=AutomationControlled')
            chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
            chrome_options.add_experimental_option('useAutomationExtension', False)
            chrome_options.add_argument('--window-size=1920,1080')
            chrome_options.add_argument('--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')
            
            self.driver = webdriver.Chrome(options=chrome_options)
            self.driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
            
            logger.info("ByBit browser setup successful")
            return True
            
        except Exception as e:
            logger.error(f"ByBit browser setup failed: {e}")
            return False
    
    async def get_offers(self) -> List[Dict[str, Any]]:
        """Extract real P2P offers from ByBit website"""
        if not self.setup_browser():
            logger.warning("Browser setup failed, returning cached offers")
            return self.offers_cache
            
        try:
            logger.info("Fetching ByBit P2P offers...")
            
            # Navigate to P2P page
            self.driver.get(self.base_url)
            
            # Wait for page load
            try:
                WebDriverWait(self.driver, BROWSER_TIMEOUT).until(
                    EC.presence_of_element_located((By.TAG_NAME, "body"))
                )
            except:
                logger.error("Page load timeout")
                return self.offers_cache
            
            # Wait for dynamic content
            await asyncio.sleep(8)
            
            # Scroll to trigger lazy loading
            self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight/2);")
            await asyncio.sleep(2)
            
            # Extract offers from page text
            page_text = self.driver.find_element(By.TAG_NAME, "body").text
            offers = self.parse_offers_from_page_text(page_text)
            
            if offers:
                self.offers_cache = offers
                self.last_update = datetime.now()
                logger.info(f"ByBit: Successfully extracted {len(offers)} offers")
            else:
                logger.warning("No offers extracted from ByBit page")
            
            return offers if offers else self.offers_cache
            
        except Exception as e:
            logger.error(f"ByBit offers fetch failed: {e}")
            logger.error(f"Traceback: {traceback.format_exc()}")
            return self.offers_cache  # Return cached data if available
    
    def parse_offers_from_page_text(self, page_text: str) -> List[Dict[str, Any]]:
        """Parse P2P offers from full page text using improved patterns"""
        offers = []
        
        try:
            # Split into lines and process
            lines = page_text.split('\n')
            
            # Find lines with price patterns (like "42,58 UAH")
            price_lines = []
            for i, line in enumerate(lines):
                if re.search(r'\d+[,\.]\d+\s*UAH', line.strip()):
                    price_lines.append((i, line.strip()))
            
            logger.info(f"Found {len(price_lines)} price patterns")
            
            # Extract usernames and other data from context
            for line_idx, price_line in price_lines[:10]:  # Top 10 offers
                try:
                    # Extract price
                    price_match = re.search(r'(\d+[,\.]\d+)\s*UAH', price_line)
                    if not price_match:
                        continue
                    
                    price_str = price_match.group(1).replace(',', '.')
                    price = float(price_str)
                    
                    # Look for username in nearby lines (usually before price)
                    username = "Unknown"
                    for check_idx in range(max(0, line_idx-5), min(len(lines), line_idx+3)):
                        line = lines[check_idx].strip()
                        # Look for single letter followed by username pattern
                        username_match = re.match(r'^[A-Za-z⓻👻]\s*(\w+)', line)
                        if username_match and len(username_match.group(1)) > 2:
                            username = username_match.group(1)
                            break
                    
                    # Look for USDT amounts in nearby lines
                    available = 50.0  # Default
                    for check_idx in range(max(0, line_idx-2), min(len(lines), line_idx+5)):
                        line = lines[check_idx].strip()
                        usdt_match = re.search(r'(\d+[,\.]\d+)\s*USDT', line)
                        if usdt_match:
                            usdt_str = usdt_match.group(1).replace(',', '.')
                            available = float(usdt_str)
                            break
                    
                    # Look for limit ranges in nearby lines
                    min_amount, max_amount = 1000.0, 50000.0  # Defaults
                    for check_idx in range(max(0, line_idx-2), min(len(lines), line_idx+5)):
                        line = lines[check_idx].strip()
                        limit_match = re.search(r'(\d+(?:[,\s]\d+)*[,\.]\d+)\s*~\s*(\d+(?:[,\s]\d+)*[,\.]\d+)\s*UAH', line)
                        if limit_match:
                            min_str = limit_match.group(1).replace(' ', '').replace(',', '.')
                            max_str = limit_match.group(2).replace(' ', '').replace(',', '.')
                            try:
                                min_amount = float(min_str)
                                max_amount = float(max_str)
                            except:
                                pass
                            break
                    
                    # Create offer with direct link
                    offer = {
                        'exchange': 'ByBit',
                        'username': username,
                        'price': price,
                        'available': available,
                        'min_amount': min_amount,
                        'max_amount': max_amount,
                        'link': self.base_url,
                        'direct_link': f"https://www.bybit.com/fiat/trade/otc/?actionType=1&token=USDT&fiat=UAH&paymentMethod=&amount={available}&nickName={username}",
                        'timestamp': datetime.now().isoformat()
                    }
                    
                    offers.append(offer)
                    
                except Exception as e:
                    logger.error(f"Error parsing offer at line {line_idx}: {e}")
                    continue
            
            # Sort by price (best offers first)
            offers.sort(key=lambda x: x['price'])
            
            logger.info(f"Successfully parsed {len(offers)} offers")
            return offers
            
        except Exception as e:
            logger.error(f"Error in parse_offers_from_page_text: {e}")
            return []
    
    def format_offer_message(self, offer: Dict[str, Any]) -> str:
        """Format ByBit offer with direct link for user convenience"""
        username = offer.get('username', 'Unknown')
        price = offer.get('price', 0)
        available = offer.get('available', 0)
        min_amount = offer.get('min_amount', 0)
        max_amount = offer.get('max_amount', 0)
        
        # Create a more direct link (if possible)
        direct_link = offer.get('direct_link', self.base_url)
        
        return f"""💰 **ByBit P2P Offer**
👤 Пользователь: **{username}**
💲 Цена: **{price:.2f} UAH** за USDT
📊 Доступно: **{available:.1f} USDT**
💳 Лимиты: {min_amount:.0f} - {max_amount:.0f} UAH
🔗 Прямая ссылка: [Купить у {username}]({direct_link})
⚡ Быстрая ссылка: {self.base_url}""".strip()
    
    def cleanup(self):
        """Clean up browser resources"""
        if self.driver:
            try:
                self.driver.quit()
                self.driver = None
            except:
                pass

class PlaceholderExchange(P2PExchange):
    """Placeholder for future exchange integrations"""
    
    async def get_offers(self) -> List[Dict[str, Any]]:
        """Return placeholder offers for demonstration"""
        # This will be replaced with real implementations
        return [
            {
                'exchange': self.name,
                'username': 'DemoUser1',
                'price': 41.5 + (hash(self.name) % 200) / 100,  # Simulate price variation
                'available': 500.0,
                'min_amount': 1000.0,
                'max_amount': 20000.0,
                'link': f'https://{self.name.lower()}.com/p2p',
                'timestamp': datetime.now().isoformat()
            }
        ]

class P2PMonitoringBot:
    """Main bot class for P2P monitoring"""
    
    def __init__(self):
        self.exchanges = {
            'bybit': ByBitP2P(),
            'okx': PlaceholderExchange('OKX'),
            'binance': PlaceholderExchange('Binance'),
            'mexc': PlaceholderExchange('MEXC'),
            'bitget': PlaceholderExchange('BitGet'),
            'bingx': PlaceholderExchange('BingX'),
        }
        
        self.users_data = self.load_users_data()
        self.monitoring_active = False
        
    def load_users_data(self) -> Dict:
        """Load user settings from file"""
        try:
            with open(USERS_DATA_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except FileNotFoundError:
            return {}
    
    def save_users_data(self):
        """Save user settings to file"""
        try:
            with open(USERS_DATA_FILE, 'w', encoding='utf-8') as f:
                json.dump(self.users_data, f, indent=2, ensure_ascii=False)
        except Exception as e:
            logger.error(f"Failed to save user data: {e}")
    
    def get_user_data(self, user_id: int) -> Dict:
        """Get user settings with defaults"""
        user_id_str = str(user_id)
        if user_id_str not in self.users_data:
            self.users_data[user_id_str] = {
                **DEFAULT_USER_SETTINGS,
                'active_exchanges': DEFAULT_USER_SETTINGS['active_exchanges'].copy(),
                'last_notification': None
            }
            self.save_users_data()
        
        return self.users_data[user_id_str]
    
    def update_user_data(self, user_id: int, data: Dict):
        """Update user settings"""
        user_id_str = str(user_id)
        if user_id_str not in self.users_data:
            self.users_data[user_id_str] = {}
        
        self.users_data[user_id_str].update(data)
        self.save_users_data()

# Bot handlers
async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /start command"""
    user = update.effective_user
    
    welcome_message = f"""
🚀 Добро пожаловать в P2P USDT-UAH Мониторинг Бот!

👋 Привет, {user.first_name}!

Этот бот отслеживает курсы USDT-UAH на различных P2P биржах и уведомляет вас о выгодных предложениях.

📊 Доступные биржи:
✅ ByBit (реальные данные)
🔄 OKX, Binance, MEXC, BitGet, BingX (скоро)

⚙️ Команды:
/settings - Настройки диапазона курса и бирж
/status - Текущие настройки и статус
/check - Проверить текущие предложения
/start_monitoring - Включить мониторинг
/stop_monitoring - Выключить мониторинг

💡 Начните с команды /settings для настройки вашего диапазона курса!
    """.strip()
    
    await update.message.reply_text(welcome_message)

async def settings_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /settings command"""
    user_id = update.effective_user.id
    bot = context.bot_data.get('bot_instance')
    user_data = bot.get_user_data(user_id)
    
    keyboard = [
        [
            InlineKeyboardButton("💰 Диапазон курса", callback_data="set_rate_range"),
            InlineKeyboardButton("🏦 Выбор бирж", callback_data="select_exchanges")
        ],
        [
            InlineKeyboardButton("🔔 Уведомления", callback_data="toggle_notifications"),
            InlineKeyboardButton("📊 Показать статус", callback_data="show_status")
        ]
    ]
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    settings_text = f"""
⚙️ **Настройки мониторинга**

💰 Диапазон курса: {user_data['min_rate']:.2f} - {user_data['max_rate']:.2f} UAH
🏦 Активные биржи: {len(user_data['active_exchanges'])}/{len(bot.exchanges)}
🔔 Уведомления: {'✅ Включены' if user_data['notifications_enabled'] else '❌ Выключены'}

Выберите что настроить:
    """.strip()
    
    await update.message.reply_text(settings_text, reply_markup=reply_markup, parse_mode='Markdown')

async def check_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /check command - show current offers"""
    bot = context.bot_data.get('bot_instance')
    user_id = update.effective_user.id
    user_data = bot.get_user_data(user_id)
    
    await update.message.reply_text("🔍 Проверяю текущие предложения...")
    
    # Get offers from active exchanges
    all_offers = []
    for exchange_name in user_data['active_exchanges']:
        if exchange_name in bot.exchanges:
            try:
                exchange = bot.exchanges[exchange_name]
                offers = await exchange.get_offers()
                all_offers.extend(offers)
            except Exception as e:
                logger.error(f"Error getting offers from {exchange_name}: {e}")
    
    if not all_offers:
        await update.message.reply_text("❌ Не удалось получить предложения. Попробуйте позже.")
        return
    
    # Filter offers by user's rate range
    filtered_offers = [
        offer for offer in all_offers
        if user_data['min_rate'] <= offer['price'] <= user_data['max_rate']
    ]
    
    if not filtered_offers:
        await update.message.reply_text(
            f"📊 Найдено {len(all_offers)} предложений, но ни одно не попадает в ваш диапазон "
            f"{user_data['min_rate']:.2f}-{user_data['max_rate']:.2f} UAH"
        )
        return
    
    # Sort by price (best offers first)
    filtered_offers.sort(key=lambda x: x['price'])
    
    # Send top offers
    response = f"💎 Найдено {len(filtered_offers)} предложений в вашем диапазоне:\n\n"
    
    for offer in filtered_offers[:5]:  # Show top 5
        exchange = bot.exchanges.get(offer['exchange'].lower(), bot.exchanges['bybit'])
        response += exchange.format_offer_message(offer) + "\n\n"
    
    if len(filtered_offers) > 5:
        response += f"... и еще {len(filtered_offers) - 5} предложений"
    
    await update.message.reply_text(response)

async def status_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /status command"""
    bot = context.bot_data.get('bot_instance')
    user_id = update.effective_user.id
    user_data = bot.get_user_data(user_id)
    
    active_exchanges_list = "\n".join([f"✅ {name.upper()}" for name in user_data['active_exchanges']])
    inactive_exchanges = [name for name in bot.exchanges.keys() if name not in user_data['active_exchanges']]
    inactive_exchanges_list = "\n".join([f"❌ {name.upper()}" for name in inactive_exchanges])
    
    status_text = f"""
📊 **Статус мониторинга**

👤 Пользователь: {update.effective_user.first_name}
🆔 ID: {user_id}

💰 Диапазон курса: {user_data['min_rate']:.2f} - {user_data['max_rate']:.2f} UAH
🔔 Уведомления: {'✅ Включены' if user_data['notifications_enabled'] else '❌ Выключены'}
🔄 Мониторинг: {'✅ Активен' if bot.monitoring_active else '❌ Неактивен'}

🏦 **Биржи:**
{active_exchanges_list}

{inactive_exchanges_list if inactive_exchanges else ''}

⏰ Последняя проверка: {datetime.now().strftime('%H:%M:%S')}
    """.strip()
    
    await update.message.reply_text(status_text, parse_mode='Markdown')

async def start_monitoring_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Start monitoring"""
    bot = context.bot_data.get('bot_instance')
    
    if not bot.monitoring_active:
        bot.monitoring_active = True
        # Start monitoring task
        context.job_queue.run_repeating(
            monitoring_job, 
            interval=MONITORING_INTERVAL,
            first=10,
            data={'bot_instance': bot, 'context': context}
        )
        await update.message.reply_text("✅ Мониторинг запущен! Вы будете получать уведомления о выгодных предложениях.")
    else:
        await update.message.reply_text("ℹ️ Мониторинг уже активен.")

async def stop_monitoring_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Stop monitoring"""
    bot = context.bot_data.get('bot_instance')
    bot.monitoring_active = False
    
    # Stop all jobs
    for job in context.job_queue.jobs():
        job.schedule_removal()
    
    await update.message.reply_text("⏹️ Мониторинг остановлен.")

async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle button callbacks"""
    query = update.callback_query
    await query.answer()
    
    bot = context.bot_data.get('bot_instance')
    user_id = query.from_user.id
    
    if query.data == "set_rate_range":
        await query.edit_message_text(
            "💰 Отправьте новый диапазон курса в формате:\n"
            "`мин макс`\n\n"
            "Например: `35.5 41.8`\n"
            "Текущий диапазон: {:.2f} - {:.2f} UAH".format(
                bot.get_user_data(user_id)['min_rate'],
                bot.get_user_data(user_id)['max_rate']
            ),
            parse_mode='Markdown'
        )
        context.user_data['waiting_for'] = 'rate_range'
    
    elif query.data == "show_status":
        await status_command(update, context)

async def message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle text messages"""
    if context.user_data.get('waiting_for') == 'rate_range':
        try:
            text = update.message.text.strip()
            parts = text.split()
            
            if len(parts) == 2:
                min_rate = float(parts[0])
                max_rate = float(parts[1])
                
                if min_rate >= max_rate:
                    raise ValueError("Минимум должен быть меньше максимума")
                
                if min_rate < 0 or max_rate > 100:
                    raise ValueError("Курс должен быть в разумных пределах (0-100)")
                
                bot = context.bot_data.get('bot_instance')
                bot.update_user_data(update.effective_user.id, {
                    'min_rate': min_rate,
                    'max_rate': max_rate
                })
                
                await update.message.reply_text(
                    f"✅ Диапазон курса обновлен: {min_rate:.2f} - {max_rate:.2f} UAH"
                )
                
                context.user_data['waiting_for'] = None
                
            else:
                raise ValueError("Неверный формат")
                
        except ValueError as e:
            await update.message.reply_text(
                f"❌ Ошибка: {str(e)}\n"
                "Используйте формат: `мин макс`\n"
                "Например: `35.5 41.8`",
                parse_mode='Markdown'
            )

async def monitoring_job(context: ContextTypes.DEFAULT_TYPE):
    """Background monitoring job"""
    try:
        bot = context.job.data['bot_instance']
        application = context.job.data['context'].application
        
        if not bot.monitoring_active:
            return
        
        logger.info("Running monitoring check...")
        
        # Get all users with notifications enabled
        active_users = [
            user_id for user_id, data in bot.users_data.items()
            if data.get('notifications_enabled', True)
        ]
        
        if not active_users:
            return
        
        # Check offers for each user
        for user_id_str in active_users:
            user_id = int(user_id_str)
            user_data = bot.get_user_data(user_id)
            
            # Get offers from active exchanges
            all_offers = []
            for exchange_name in user_data['active_exchanges']:
                if exchange_name in bot.exchanges:
                    try:
                        exchange = bot.exchanges[exchange_name]
                        offers = await exchange.get_offers()
                        all_offers.extend(offers)
                    except Exception as e:
                        logger.error(f"Error getting offers from {exchange_name}: {e}")
            
            # Filter by rate range
            good_offers = [
                offer for offer in all_offers
                if user_data['min_rate'] <= offer['price'] <= user_data['max_rate']
            ]
            
            if good_offers:
                # Sort by price
                good_offers.sort(key=lambda x: x['price'])
                
                # Send notification
                try:
                    message = f"У🚨 Найдены выгодные предложения!\n\n"
                    
                    for offer in good_offers[:MAX_OFFERS_PER_NOTIFICATION]:  # Configurable limit
                        exchange = bot.exchanges.get(offer['exchange'].lower(), bot.exchanges['bybit'])
                        message += exchange.format_offer_message(offer) + "\n\n"
                    
                    await application.bot.send_message(
                        chat_id=user_id,
                        text=message
                    )
                    
                    # Update last notification time
                    bot.update_user_data(user_id, {
                        'last_notification': datetime.now().isoformat()
                    })
                    
                except Exception as e:
                    logger.error(f"Failed to send notification to {user_id}: {e}")
        
    except Exception as e:
        logger.error(f"Monitoring job error: {e}")

def main():
    """Main function"""
    if BOT_TOKEN == "YOUR_BOT_TOKEN_HERE":
        print("❌ Пожалуйста, установите BOT_TOKEN в коде!")
        print("📱 Получите токен у @BotFather в Telegram")
        return
    
    # Initialize bot instance
    bot_instance = P2PMonitoringBot()
    
    # Create application
    application = Application.builder().token(BOT_TOKEN).build()
    
    # Store bot instance in bot_data
    application.bot_data['bot_instance'] = bot_instance
    
    # Add handlers
    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CommandHandler("settings", settings_command))
    application.add_handler(CommandHandler("check", check_command))
    application.add_handler(CommandHandler("status", status_command))
    application.add_handler(CommandHandler("start_monitoring", start_monitoring_command))
    application.add_handler(CommandHandler("stop_monitoring", stop_monitoring_command))
    application.add_handler(CallbackQueryHandler(button_callback))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, message_handler))
    
    print("🚀 P2P Monitoring Bot запущен!")
    print("📱 Отправьте /start боту для начала работы")
    print("⚡ Бот поддерживает реальные данные с ByBit!")
    
    try:
        # Start the bot
        application.run_polling(allowed_updates=Update.ALL_TYPES)
    except KeyboardInterrupt:
        print("\n⏹️ Остановка бота...")
    finally:
        # Cleanup
        if hasattr(bot_instance.exchanges['bybit'], 'cleanup'):
            bot_instance.exchanges['bybit'].cleanup()
        print("✅ Бот остановлен")

if __name__ == '__main__':
    main()