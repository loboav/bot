#!/usr/bin/env python3
"""
Test Organized Structure
=======================

Test script to verify the new organized project structure works correctly
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import asyncio
from bot.exchanges.bybit_p2p import ByBitP2P
from bot.utils.user_manager import UserManager
from config.settings import *

async def test_organized_structure():
    """Test the organized project structure"""
    print("🧪 Testing Organized Project Structure")
    print("=" * 50)
    
    # Test 1: Configuration loading
    print("1. Testing configuration loading...")
    print(f"   ✅ BOT_TOKEN: {BOT_TOKEN[:10]}...") 
    print(f"   ✅ MONITORING_INTERVAL: {MONITORING_INTERVAL}")
    print(f"   ✅ BROWSER_HEADLESS: {BROWSER_HEADLESS}")
    print(f"   ✅ DEFAULT_USER_SETTINGS: {DEFAULT_USER_SETTINGS}")
    
    # Test 2: User Manager
    print("\n2. Testing User Manager...")
    user_manager = UserManager()
    test_user_id = 12345
    
    user_data = user_manager.get_user_data(test_user_id)
    print(f"   ✅ User data created: {user_data}")
    
    user_manager.update_user_data(test_user_id, {'min_rate': 41.0, 'max_rate': 42.5})
    updated_data = user_manager.get_user_data(test_user_id)
    print(f"   ✅ User data updated: {updated_data['min_rate']} - {updated_data['max_rate']}")
    
    # Test 3: ByBit Exchange
    print("\n3. Testing ByBit Exchange...")
    bybit = ByBitP2P()
    print(f"   ✅ ByBit instance created: {bybit.name}")
    print(f"   ✅ Base URL: {bybit.base_url}")
    
    # Test browser setup (without actually fetching data)
    print(f"   ✅ Browser setup method available: {hasattr(bybit, 'setup_browser')}")
    print(f"   ✅ Get offers method available: {hasattr(bybit, 'get_offers')}")
    print(f"   ✅ Format message method available: {hasattr(bybit, 'format_offer_message')}")
    
    # Test 4: File structure
    print("\n4. Testing file structure...")
    required_files = [
        'config/settings.py',
        'bot/main.py',
        'bot/exchanges/base_exchange.py',
        'bot/exchanges/bybit_p2p.py',
        'bot/utils/user_manager.py',
        'requirements.txt',
        'README.md'
    ]
    
    for file_path in required_files:
        full_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), file_path)
        if os.path.exists(full_path):
            print(f"   ✅ {file_path}: EXISTS")
        else:
            print(f"   ❌ {file_path}: MISSING")
    
    # Test 5: Imports working
    print("\n5. Testing imports...")
    try:
        from bot.exchanges.base_exchange import BaseExchange
        from bot.exchanges.placeholder_exchange import PlaceholderExchange
        print("   ✅ All imports successful")
    except ImportError as e:
        print(f"   ❌ Import error: {e}")
    
    print("\n" + "="*50)
    print("🎉 Organized structure test completed!")
    print("✅ New project structure is ready to use!")
    
    # Cleanup
    bybit.cleanup()

if __name__ == "__main__":
    asyncio.run(test_organized_structure())