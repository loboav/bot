#!/usr/bin/env python3
"""
Base Exchange Class
==================

Base class for all P2P exchange integrations
"""

from abc import ABC, abstractmethod
from datetime import datetime
from typing import List, Dict, Any
import asyncio
import logging

logger = logging.getLogger(__name__)

class BaseExchange(ABC):
    """Base class for P2P exchange integrations"""
    
    def __init__(self, name: str):
        self.name = name
        self.last_update = None
        self.offers_cache = []
    
    @abstractmethod
    async def get_offers(self) -> List[Dict[str, Any]]:
        """Get P2P offers for USDT-UAH pair"""
        pass
    
    def normalize_offer(self, raw_offer: Dict[str, Any]) -> Dict[str, Any]:
        """Normalize offer fields to standard format"""
        return {
            'exchange': self.name,
            'username': raw_offer.get('username', 'Unknown'),
            'price': float(raw_offer.get('price', 0)),
            'available': float(raw_offer.get('available', raw_offer.get('amount', 0))),
            'min_amount': float(raw_offer.get('min_amount', raw_offer.get('min_limit', 0))),
            'max_amount': float(raw_offer.get('max_amount', raw_offer.get('max_limit', 0))),
            'link': raw_offer.get('link', raw_offer.get('direct_link', raw_offer.get('trade_url', ''))),
            'timestamp': raw_offer.get('timestamp', datetime.now().isoformat())
        }
    
    async def get_offers_with_timeout(self, timeout: int = 30) -> List[Dict[str, Any]]:
        """Get offers with timeout and fallback to cache"""
        try:
            return await asyncio.wait_for(self.get_offers(), timeout=timeout)
        except asyncio.TimeoutError:
            logger.warning(f"{self.name}: Request timed out after {timeout}s, using cache")
            return self.offers_cache
        except Exception as e:
            logger.error(f"{self.name}: Error getting offers: {e}")
            return self.offers_cache
        finally:
            # Always try cleanup if implemented
            try:
                self.cleanup_if_needed()
            except AttributeError:
                pass  # cleanup_if_needed not implemented
    
    def cleanup_if_needed(self):
        """Optional cleanup - override if needed"""
        pass
    
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
    
    def cleanup(self):
        """Clean up resources (override if needed)"""
        pass