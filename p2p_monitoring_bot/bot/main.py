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
        
        # Filter by rate range
        filtered_offers = [
            offer for offer in all_offers
            if user_data['min_rate'] <= offer['price'] <= user_data['max_rate']
        ]
        
        return sorted(filtered_offers, key=lambda x: x['price'])

def main():
    """Main function"""
    if BOT_TOKEN == "YOUR_BOT_TOKEN_HERE":
        print("❌ Пожалуйста, установите BOT_TOKEN в config/settings.py!")
        print("📱 Получите токен у @BotFather в Telegram")
        return
    
    # Initialize bot instance
    bot_instance = P2PMonitoringBot()
    handlers = BotHandlers(bot_instance)
    
    # Create application
    application = Application.builder().token(BOT_TOKEN).build()
    
    # Add handlers
    handlers.register_handlers(application)
    
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
        for exchange in bot_instance.exchanges.values():
            if hasattr(exchange, 'cleanup'):
                exchange.cleanup()
        print("✅ Бот остановлен")

if __name__ == '__main__':
    main()