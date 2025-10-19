#!/usr/bin/env python3
"""
Exchange Manager
===============

Centralized manager for all P2P exchange integrations.
"""

import asyncio
import logging
from typing import List, Dict, Any, Optional, Set

from .base_exchange import BaseExchange
from .bybit_p2p import ByBitP2P
from .bitget_p2p import BitgetP2P
from .binance_p2p import BinanceP2P

# Import settings with proper path handling
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from config.settings import BITGET_API_KEY, BITGET_SECRET_KEY, BITGET_PASSPHRASE

logger = logging.getLogger(__name__)

class ExchangeManager:
    """Manages all P2P exchange integrations"""
    
    def __init__(self):
        self._exchanges: Dict[str, BaseExchange] = {}
        self._active_exchanges: Set[str] = set()
        self._initialize_exchanges()
    
    def _initialize_exchanges(self):
        """Initialize all available exchanges"""
        # Active exchanges
        self._exchanges['bybit'] = ByBitP2P()
        self._active_exchanges.add('bybit')
        
        # Initialize Bitget with API credentials
        self._exchanges['bitget'] = BitgetP2P(
            api_key=BITGET_API_KEY,
            secret_key=BITGET_SECRET_KEY, 
            passphrase=BITGET_PASSPHRASE
        )
        self._active_exchanges.add('bitget')
        
        # Initialize Binance P2P
        self._exchanges['binance'] = BinanceP2P()
        self._active_exchanges.add('binance')
    
    def get_exchange(self, name: str) -> Optional[BaseExchange]:
        """Get specific exchange instance"""
        return self._exchanges.get(name.lower())
    
    def get_active_exchanges(self) -> List[str]:
        """Get list of currently active exchanges"""
        return list(self._active_exchanges)
    
    def get_available_exchanges(self) -> List[str]:
        """Get list of all available exchanges"""
        return list(self._exchanges.keys())
    
    async def get_combined_offers(self, 
                                exchange_names: Optional[List[str]] = None,
                                force_refresh: bool = False) -> List[Dict[str, Any]]:
        """
        Get combined and sorted offers from multiple exchanges
        
        Args:
            exchange_names: List of exchanges to query (None = all active)
            force_refresh: If True, ignore cache and fetch fresh data
            
        Returns:
            Combined list of offers sorted by price
        """
        if exchange_names is None:
            exchange_names = list(self._active_exchanges)
        
        combined_offers = []
        
        # Get offers from each exchange
        for exchange_name in exchange_names:
            exchange_name = exchange_name.lower()
            if exchange_name in self._exchanges and exchange_name in self._active_exchanges:
                try:
                    exchange = self._exchanges[exchange_name]
                    # Используем метод с таймаутом для лучшей обработки ошибок
                    if hasattr(exchange, 'get_offers_with_timeout'):
                        offers = await exchange.get_offers_with_timeout(30, force_refresh=force_refresh)  # 30 секунд таймаут
                    else:
                        offers = await exchange.get_offers(force_refresh=force_refresh)
                    
                    if offers:
                        for offer in offers:
                            offer['exchange'] = exchange_name
                            combined_offers.append(offer)
                        
                        logger.debug(f"Got {len(offers)} offers from {exchange_name}")
                except Exception as e:
                    logger.error(f"Error getting offers from {exchange_name}: {e}")
        
        # Sort by price
        combined_offers.sort(key=lambda x: x.get('price', float('inf')))
        
        logger.info(f"Combined {len(combined_offers)} offers from {len(exchange_names)} exchanges")
        return combined_offers
    
    def cleanup_all_exchanges(self):
        """Cleanup all exchange resources"""
        logger.info("🧹 Cleaning up all exchanges...")
        for name, exchange in self._exchanges.items():
            try:
                if hasattr(exchange, 'cleanup'):
                    exchange.cleanup()
                    logger.debug(f"✅ Cleaned up {name}")
            except Exception as e:
                logger.error(f"❌ Error cleaning up {name}: {e}")
    
    def __str__(self) -> str:
        """String representation"""
        active_count = len(self._active_exchanges)
        total_count = len(self._exchanges)
        return f"ExchangeManager({active_count}/{total_count} active exchanges)"