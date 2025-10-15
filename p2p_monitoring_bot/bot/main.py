#!/usr/bin/env python3
"""
P2P USDT-UAH Monitoring Bot
===========================

Main bot file - clean and organized version
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
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config.settings import *

# Setup logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=getattr(logging, LOG_LEVEL)
)
logger = logging.getLogger(__name__)

# Import bot components
from exchanges.bybit_p2p import ByBitP2P
from exchanges.placeholder_exchange import PlaceholderExchange
from utils.user_manager import UserManager
from utils.auto_monitor import AutoMonitor
from handlers.bot_handlers import BotHandlers

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
        
        self.user_manager = UserManager()
        self.monitoring_active = False
        self.auto_monitor = None  # Will be initialized in main()
        
    async def get_offers_for_user(self, user_id: int) -> List[Dict[str, Any]]:
        """Get offers for specific user based on their settings"""
        user_data = self.user_manager.get_user_data(user_id)
        
        all_offers = []
        for exchange_name in user_data['active_exchanges']:
            if exchange_name in self.exchanges:
                try:
                    exchange = self.exchanges[exchange_name]
                    offers = await exchange.get_offers()
                    if offers:
                        all_offers.extend(offers)
                except Exception as e:
                    logger.error(f"Error getting offers from {exchange_name}: {e}")
        
        # Filter by rate range and limits
        filtered_offers = []
        for offer in all_offers:
            # Price filter
            if not (user_data['min_rate'] <= offer['price'] <= user_data['max_rate']):
                continue
                
            # Limits filter - check overlap between offer limits and user requirements
            offer_min = offer.get('min_amount', 0)
            offer_max = offer.get('max_amount', 999999)
            user_min_limit = user_data.get('min_limit', 0)
            user_max_limit = user_data.get('max_limit', 999999)
            
            # Check if there's overlap between offer limits and user limits
            if offer_max >= user_min_limit and offer_min <= user_max_limit:
                filtered_offers.append(offer)
        
        return sorted(filtered_offers, key=lambda x: x['price'])

async def async_main():
    """Async main function for running bot and auto monitoring together"""
    # Initialize bot instance
    bot_instance = P2PMonitoringBot()
    
    # Create application
    application = Application.builder().token(BOT_TOKEN).build()
    
    # Initialize auto monitor
    auto_monitor = AutoMonitor(bot_instance, application)
    bot_instance.auto_monitor = auto_monitor
    
    # Initialize handlers with auto monitor
    handlers = BotHandlers(bot_instance, auto_monitor)
    
    # Add handlers
    handlers.register_handlers(application)
    
    try:
        # Start auto monitoring in background
        logger.info("🚀 Starting auto monitoring...")
        await auto_monitor.start_monitoring()
        
        # Start the bot
        await application.initialize()
        await application.start()
        await application.updater.start_polling(allowed_updates=Update.ALL_TYPES)
        
        # Keep running until interrupted
        try:
            while True:
                await asyncio.sleep(1)
        except KeyboardInterrupt:
            logger.info("KeyboardInterrupt received")
            
    finally:
        # Stop auto monitoring
        logger.info("🚫 Stopping auto monitoring...")
        await auto_monitor.stop_monitoring()
        
        # Stop telegram bot
        await application.updater.stop()
        await application.stop()
        await application.shutdown()
        
        # Cleanup exchanges
        for exchange in bot_instance.exchanges.values():
            if hasattr(exchange, 'cleanup'):
                try:
                    exchange.cleanup()
                except Exception as e:
                    logger.error(f"Error during cleanup: {e}")

def main():
    """Main function with security checks"""
    # Проверка токена
    if not BOT_TOKEN or BOT_TOKEN == "YOUR_BOT_TOKEN_HERE":
        print("❌ Ошибка: BOT_TOKEN не настроен!")
        print("📝 Инструкция:")
        print("   1. Создайте файл .env в корне проекта")
        print("   2. Добавьте строку: BOT_TOKEN=ваш_токен")
        print("   3. Получите токен у @BotFather в Telegram")
        return
    
    # Проверка формата токена (base validation)
    if not BOT_TOKEN.count(':') == 1 or len(BOT_TOKEN) < 35:
        print("❌ Неверный формат BOT_TOKEN!")
        print("📝 Токен должен выглядеть как: 1234567890:ABCDEF...")
        return
    
    print("🚀 P2P Monitoring Bot запущен!")
    print("📱 Отправьте /start боту для начала работы")
    print("⚡ Бот поддерживает реальные данные с ByBit!")
    print("🤖 Автомониторинг: /automonitor")
    
    try:
        # Run the async main function
        asyncio.run(async_main())
    except KeyboardInterrupt:
        print("\n⏹️ Остановка бота...")
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        print(f"❌ Неожиданная ошибка: {e}")
    finally:
        print("✅ Бот остановлен")

if __name__ == '__main__':
    main()
