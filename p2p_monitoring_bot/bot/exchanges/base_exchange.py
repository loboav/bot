#!/usr/bin/env python3
"""
Base Exchange Class
==================

Base class for all P2P exchange integrations
"""

from abc import ABC, abstractmethod
from datetime import datetime
from typing import List, Dict, Any

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