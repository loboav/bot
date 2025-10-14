#!/usr/bin/env python3
"""
Final Functionality Test
========================

Test all functionality after project reorganization
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import asyncio
import logging

# Configure logging for test
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')

from bot.exchanges.bybit_p2p import ByBitP2P
from bot.utils.user_manager import UserManager
from config.settings import *

async def test_final_functionality():
    """Complete functionality test"""
    print("🔬 Final Functionality Test")
    print("=" * 60)
    
    success = True
    
    # Test 1: Configuration
    print("1. 📁 Configuration Test...")
    try:
        assert BOT_TOKEN == "YOUR_BOT_TOKEN_HERE"
        assert MONITORING_INTERVAL == 60
        assert BROWSER_HEADLESS == True
        assert isinstance(DEFAULT_USER_SETTINGS, dict)
        print("   ✅ All configuration loaded correctly")
    except Exception as e:
        print(f"   ❌ Configuration error: {e}")
        success = False
    
    # Test 2: User Manager
    print("\n2. 👤 User Manager Test...")
    try:
        user_manager = UserManager()
        test_user = 99999
        
        # Create user
        user_data = user_manager.get_user_data(test_user)
        assert user_data['min_rate'] == 35.0
        assert user_data['max_rate'] == 43.0
        
        # Update user
        user_manager.update_user_data(test_user, {'min_rate': 40.0, 'max_rate': 44.0})
        updated_data = user_manager.get_user_data(test_user)
        assert updated_data['min_rate'] == 40.0
        assert updated_data['max_rate'] == 44.0
        
        print("   ✅ User Manager working correctly")
    except Exception as e:
        print(f"   ❌ User Manager error: {e}")
        success = False
    
    # Test 3: ByBit Exchange (structure only)
    print("\\n3. 💱 ByBit Exchange Test...")
    try:
        bybit = ByBitP2P()
        assert bybit.name == "ByBit"
        assert bybit.base_url.startswith("https://")
        assert hasattr(bybit, 'get_offers')
        assert hasattr(bybit, 'format_offer_message')
        
        print("   ✅ ByBit Exchange structure correct")
    except Exception as e:
        print(f"   ❌ ByBit Exchange error: {e}")
        success = False
    
    # Test 4: File Structure
    print("\\n4. 📂 File Structure Test...")
    try:
        required_structure = {
            'config/settings.py': True,
            'bot/main.py': True,
            'bot/exchanges/base_exchange.py': True,
            'bot/exchanges/bybit_p2p.py': True,
            'bot/utils/user_manager.py': True,
            'requirements.txt': True,
            'README.md': True
        }
        
        project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        
        for file_path, should_exist in required_structure.items():
            full_path = os.path.join(project_root, file_path)
            exists = os.path.exists(full_path)
            
            if exists == should_exist:
                print(f"   ✅ {file_path}: {'EXISTS' if exists else 'MISSING (OK)'}")
            else:
                print(f"   ❌ {file_path}: {'MISSING' if should_exist else 'UNEXPECTED'}")
                success = False
        
    except Exception as e:
        print(f"   ❌ File structure error: {e}")
        success = False
    
    # Test 5: Import Test
    print("\\n5. 📦 Import Test...")
    try:
        from bot.exchanges.base_exchange import BaseExchange
        from bot.exchanges.placeholder_exchange import PlaceholderExchange
        
        # Test placeholder
        placeholder = PlaceholderExchange("Test")
        offers = await placeholder.get_offers()
        assert len(offers) > 0
        assert offers[0]['exchange'] == "Test"
        
        print("   ✅ All imports and basic functionality working")
    except Exception as e:
        print(f"   ❌ Import error: {e}")
        success = False
    
    # Test 6: Message Formatting
    print("\\n6. 💬 Message Formatting Test...")
    try:
        sample_offer = {
            'exchange': 'ByBit',
            'username': 'TestUser',
            'price': 42.50,
            'available': 100.0,
            'min_amount': 1000.0,
            'max_amount': 5000.0,
            'direct_link': 'https://example.com/test',
            'link': 'https://example.com'
        }
        
        message = bybit.format_offer_message(sample_offer)
        
        assert 'TestUser' in message
        assert '42.50' in message
        assert '100.0' in message
        assert 'ByBit P2P Offer' in message
        
        print("   ✅ Message formatting working correctly")
        print(f"   📝 Sample message preview:")
        for line in message.split('\\n')[:3]:
            print(f"      {line}")
        print("      ...")
        
    except Exception as e:
        print(f"   ❌ Message formatting error: {e}")
        success = False
    
    # Cleanup
    if 'bybit' in locals():
        bybit.cleanup()
    
    # Final Result
    print("\\n" + "="*60)
    if success:
        print("🎉 ALL TESTS PASSED!")
        print("✅ Organized project is fully functional!")
        print("🚀 Ready to use:")
        print("   1. Set your BOT_TOKEN in config/settings.py")
        print("   2. Run: python bot/main.py")
        print("   3. Send /start to your bot")
    else:
        print("❌ SOME TESTS FAILED")
        print("🔧 Please check the errors above")
    
    print(f"\\n📋 Final Result: {'SUCCESS' if success else 'FAILED'}")
    return success

if __name__ == "__main__":
    asyncio.run(test_final_functionality())