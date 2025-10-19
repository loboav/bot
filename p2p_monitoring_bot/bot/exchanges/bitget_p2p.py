#!/usr/bin/env python3
"""
Bitget P2P Exchange Integration
===============================

Real Bitget P2P data extraction using browser automation
"""

import asyncio
import re
from datetime import datetime
from typing import List, Dict, Any, Optional
import logging

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

from .base_exchange import BaseExchange

# Import settings with proper path handling
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from config.settings import BROWSER_HEADLESS, BROWSER_TIMEOUT, EXCHANGE_URLS

logger = logging.getLogger(__name__)

class BitgetP2P(BaseExchange):
    """Bitget P2P integration with real browser data extraction"""
    
    def __init__(self, api_key: str = None, secret_key: str = None, passphrase: str = None):
        super().__init__("Bitget")
        self.driver = None
        # Прямо заходим на страницу покупки USDT за UAH
        self.base_url = "https://www.bitget.com/ru/p2p-trade?paymethodIds=-1&fiatName=UAH"
        
    def setup_browser(self):
        """Setup Chrome browser with optimized settings"""
        if self.driver:
            return True
            
        try:
            chrome_options = Options()
            
            # Use headless mode from config
            if BROWSER_HEADLESS:
                chrome_options.add_argument('--headless=new')
            
            # MAXIMUM SPEED optimizations
            chrome_options.add_argument('--no-sandbox')
            chrome_options.add_argument('--disable-dev-shm-usage')
            chrome_options.add_argument('--disable-blink-features=AutomationControlled')
            chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
            chrome_options.add_experimental_option('useAutomationExtension', False)
            chrome_options.add_argument('--window-size=1280,720')  # Smaller window = faster
            chrome_options.add_argument('--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')
            
            # SPEED BOOST: Disable unnecessary features (SAFE options)
            chrome_options.add_argument('--disable-extensions')
            chrome_options.add_argument('--disable-plugins')
            chrome_options.add_argument('--disable-images')  # Don't load images - major speed boost
            chrome_options.add_argument('--disable-web-security')
            chrome_options.add_argument('--disable-features=VizDisplayCompositor')
            chrome_options.add_argument('--disable-background-timer-throttling')
            chrome_options.add_argument('--disable-backgrounding-occluded-windows')
            chrome_options.add_argument('--disable-renderer-backgrounding')
            chrome_options.add_argument('--disable-default-apps')
            chrome_options.add_argument('--disable-sync')
            chrome_options.add_argument('--disable-gpu')  # No GPU acceleration needed
            chrome_options.add_argument('--disable-css3-animations')
            chrome_options.add_argument('--disable-smooth-scrolling')
            chrome_options.add_argument('--memory-pressure-off')
            chrome_options.add_argument('--disable-logging')
            chrome_options.add_argument('--enable-unsafe-swiftshader')  # Fix WebGL warnings
            
            self.driver = webdriver.Chrome(options=chrome_options)
            self.driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
            
            logger.info("Bitget browser setup successful")
            return True
            
        except Exception as e:
            logger.error(f"Bitget browser setup failed: {e}")
            return False
    
    async def get_offers(self, force_refresh: bool = False) -> List[Dict[str, Any]]:
        """Extract real P2P offers from Bitget website - OPTIMIZED VERSION"""
        # Check cache first (5 minutes TTL) unless force refresh is requested
        if not force_refresh and self.offers_cache and self.last_update:
            from datetime import timedelta
            if datetime.now() - self.last_update < timedelta(minutes=5):
                logger.info(f"Using cached Bitget data ({len(self.offers_cache)} offers)")
                return self.offers_cache
        
        if not self.setup_browser():
            logger.warning("Browser setup failed, returning cached offers")
            return self.offers_cache
            
        try:
            mode_text = "FRESH DATA" if force_refresh else "FAST MODE"
            logger.info(f"Fetching Bitget P2P offers... ({mode_text})")
            start_time = datetime.now()
            
            # Navigate to P2P page
            self.driver.get(self.base_url)
            
            # OPTIMIZATION: Reduced wait times and smarter loading
            try:
                WebDriverWait(self.driver, 10).until(
                    EC.presence_of_element_located((By.TAG_NAME, "body"))
                )
            except:
                logger.error("Page load timeout")
                return self.offers_cache
            
            # OPTIMIZATION: Much shorter wait for dynamic content
            await asyncio.sleep(5)  # Give time for P2P data to load
            
            # OPTIMIZATION: Multiple small scrolls to trigger lazy loading
            for i in range(3):
                self.driver.execute_script(f"window.scrollTo(0, {300 * (i + 1)});")
                await asyncio.sleep(1)  # Short waits
            
            # Extract offers from page text AND HTML - OPTIMIZED
            page_text = self.driver.find_element(By.TAG_NAME, "body").text
            page_source = self.driver.page_source  # Get HTML for user IDs
            offers = self.parse_offers_from_page_text(page_text, page_source)
            
            # Calculate timing
            end_time = datetime.now()
            duration = (end_time - start_time).total_seconds()
            
            if offers:
                self.offers_cache = offers
                self.last_update = datetime.now()
                logger.info(f"Bitget: Successfully extracted {len(offers)} offers in {duration:.1f}s (FAST!)")
            else:
                logger.warning(f"No offers extracted from Bitget page (took {duration:.1f}s)")
            
            return offers if offers else self.offers_cache
            
        except Exception as e:
            logger.error(f"Bitget offers fetch failed: {e}")
            return self.offers_cache
    
    def parse_offers_from_page_text(self, page_text: str, page_source: str = "") -> List[Dict[str, Any]]:
        """Parse P2P offers from Bitget page text and HTML using real structure"""
        offers = []
        
        try:
            lines = page_text.split('\n')
            
            # Extract user IDs from HTML source
            user_ids = re.findall(r'/p2p-trade/user/([a-f0-9]+)', page_source) if page_source else []
            logger.info(f"Found {len(user_ids)} user IDs in HTML")
            
            # Найдем все цены в USD (как в дебаг выводе)
            price_patterns = []
            username_patterns = []
            usdt_patterns = []
            limit_patterns = []
            
            for i, line in enumerate(lines):
                line = line.strip()
                if not line:
                    continue
                    
                # Поиск цен в формате UAH: "43.4 UAH", "43.44 UAH" итд
                price_match = re.match(r'^([\d\.]+)\s+UAH$', line)
                if price_match:
                    price_patterns.append((i, line, float(price_match.group(1))))
                
                # Поиск USDT в формате: "11,699.67 USDT"
                usdt_match = re.match(r'^([\d,\.]+)\s+USDT$', line)
                if usdt_match:
                    try:
                        amount = float(usdt_match.group(1).replace(',', ''))
                        usdt_patterns.append((i, line, amount))
                    except ValueError:
                        pass
                
                # Поиск лимитов в UAH: "6,000-6,510 UAH", "1,950-3,784 UAH"
                limit_match = re.match(r'^([\d,]+)[\u2013—-]([\d,]+)\s+UAH$', line)
                if limit_match:
                    try:
                        min_limit = float(limit_match.group(1).replace(',', ''))
                        max_limit = float(limit_match.group(2).replace(',', ''))
                        limit_patterns.append((i, line, min_limit, max_limit))
                    except ValueError:
                        pass
                
                # Поиск полных имен пользователей (как CloverSiS, RUS_Bank, BabayGoFast)
                if (3 <= len(line) <= 25 and 
                    re.match(r'^[A-Za-z0-9_]+$', line) and 
                    line not in ['USD', 'USDT', 'UAH'] and
                    'Успешные' not in line):
                    username_patterns.append((i, line))
            
            logger.info(f"Found {len(price_patterns)} price patterns, {len(usdt_patterns)} USDT patterns, {len(limit_patterns)} limit patterns, {len(username_patterns)} usernames")
            
            # Сопоставляем данные по позиции в тексте
            for offer_idx, (price_idx, price_line, price_uah) in enumerate(price_patterns[:15]):
                try:
                    # Цена уже в UAH, конвертация не нужна
                    # price_uah уже готова
                    
                    # Ищем ближайшее полное имя пользователя
                    username = "Unknown"
                    min_distance = float('inf')
                    
                    # Проверяем около 20 строк вокруг цены
                    for user_idx, user_name in username_patterns:
                        distance = abs(user_idx - price_idx)
                        if distance < min_distance and distance <= 20:
                            username = user_name
                            min_distance = distance
                    
                    # Получаем соответствующий user ID для прямой ссылки
                    user_id = user_ids[offer_idx] if offer_idx < len(user_ids) else None
                    
                    # Ищем ближайшее количество USDT
                    usdt_amount = 0.0
                    min_distance = float('inf')
                    
                    for usdt_idx, usdt_line, amount in usdt_patterns:
                        distance = abs(usdt_idx - price_idx)
                        if distance < min_distance and distance <= 15:
                            usdt_amount = amount
                            min_distance = distance
                    
                    # Ищем ближайшие лимиты в UAH
                    min_limit_uah, max_limit_uah = 0.0, 0.0
                    min_distance = float('inf')
                    
                    for limit_idx, limit_line, min_lim, max_lim in limit_patterns:
                        distance = abs(limit_idx - price_idx)
                        if distance < min_distance and distance <= 15:
                            min_limit_uah = min_lim
                            max_limit_uah = max_lim
                            min_distance = distance
                    
                    # Используем значения по умолчанию если не нашли
                    if min_limit_uah == 0.0:
                        min_limit_uah = 1000.0
                    if max_limit_uah == 0.0:
                        max_limit_uah = 100000.0
                    
                    # Создаем предложение с правильными полями для совместимости с ботом
                    
                    # Формируем ссылки
                    if user_id:
                        # Прямая ссылка на конкретного пользователя (ТО ЧТО НАДО!)
                        trade_url = f"https://www.bitget.com/ru/p2p-trade/user/{user_id}"
                    else:
                        # Fallback к старому формату
                        trade_url = f"https://www.bitget.com/ru/p2p-trade?fiatName={username}"
                    
                    # Создаем сырое предложение
                    raw_offer = {
                        'username': username,
                        'price': price_uah,
                        'available': usdt_amount if usdt_amount > 0 else 100.0,
                        'min_amount': min_limit_uah,
                        'max_amount': max_limit_uah,
                        'link': trade_url,
                        'timestamp': datetime.now().isoformat()
                    }
                    
                    # Нормализуем через базовый класс
                    offer = self.normalize_offer(raw_offer)
                    
                    offers.append(offer)
                    
                except Exception as e:
                    logger.error(f"Error parsing offer at price line {price_idx}: {e}")
                    continue
            
            # Сортируем по цене (лучшие предложения первыми)
            offers.sort(key=lambda x: x['price'])
            
            logger.info(f"Successfully parsed {len(offers)} offers")
            return offers
            
        except Exception as e:
            logger.error(f"Error in parse_offers_from_page_text: {e}")
            return []
    
    def format_offer_message(self, offer: Dict[str, Any]) -> str:
        """Формат Bitget offer for user notification"""
        username = offer.get('username', 'Unknown')
        price = offer.get('price', 0)
        available = offer.get('available', 0)
        min_amount = offer.get('min_amount', 0)
        max_amount = offer.get('max_amount', 0)
        link = offer.get('link', "https://www.bitget.com/ru/otc")
        
        return f"""💰 <b>Bitget P2P Offer</b>
👤 Пользователь: <b>{username}</b>
💲 Цена: <b>{price:.2f} UAH</b> за USDT
📊 Доступно: <b>{available:.1f} USDT</b>
💳 Лимиты: {min_amount:.0f} - {max_amount:.0f} UAH
🔗 Прямая ссылка: <a href='{link}'>Купить у {username}</a>
⚡ Быстрая ссылка: {self.base_url}""".strip()
    
    def cleanup_if_needed(self):
        """Smart cleanup - only if browser has been idle"""
        if self.driver:
            try:
                # Проверяем, что браузер еще отвечает
                self.driver.current_url
            except Exception:
                # Браузер не отвечает, очищаем
                logger.warning("Bitget browser not responding, cleaning up")
                try:
                    self.driver.quit()
                except:
                    pass
                self.driver = None
    
    def cleanup(self):
        """Clean up browser resources"""
        if self.driver:
            try:
                self.driver.quit()
                self.driver = None
                logger.info("Bitget browser cleaned up")
            except Exception as e:
                logger.error(f"Error cleaning up browser: {e}")
