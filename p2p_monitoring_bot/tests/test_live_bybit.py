#!/usr/bin/env python3
"""
Live ByBit Test
===============

Test actual real data extraction from ByBit to show everything works
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import asyncio
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)

from bot.exchanges.bybit_p2p import ByBitP2P
from config.settings import BROWSER_HEADLESS

async def test_live_bybit():
    """Test live ByBit data extraction"""
    print("🔴 LIVE ByBit P2P Data Extraction Test")
    print("=" * 60)
    print("📊 This will fetch REAL current P2P offers from ByBit")
    print()
    
    # Create ByBit instance
    bybit = ByBitP2P()
    print(f"✅ ByBit instance created: {bybit.name}")
    print(f"🔗 Target URL: {bybit.base_url}")
    print(f"🖥️ Browser mode: {'Headless' if BROWSER_HEADLESS else 'Visible'}")
    
    try:
        print("\n🔍 Fetching live P2P offers...")
        print("⏳ This may take 15-20 seconds...")
        
        # Get real offers
        offers = await bybit.get_offers()
        
        if offers:
            print(f"\n🎉 SUCCESS! Extracted {len(offers)} real offers:")
            print("=" * 60)
            
            # Show top 5 offers
            for i, offer in enumerate(offers[:5], 1):
                print(f"\n💰 Live Offer #{i}:")
                print(f"   👤 User: {offer['username']}")
                print(f"   💲 Price: {offer['price']:.2f} UAH per USDT")
                print(f"   📊 Available: {offer['available']:.2f} USDT")
                print(f"   💳 Limits: {offer['min_amount']:.0f} - {offer['max_amount']:.0f} UAH")
                print(f"   🔗 Direct Link: {offer['direct_link']}")
                print("-" * 40)
            
            # Show formatted message
            print("\n📱 Sample Telegram Message:")
            print("╔" + "═"*58 + "╗")
            sample_message = bybit.format_offer_message(offers[0])
            for line in sample_message.split('\n'):
                print(f"║ {line:<56} ║")
            print("╚" + "═"*58 + "╝")
            
            # Show price range
            prices = [offer['price'] for offer in offers]
            print(f"\n📈 Current Market Analysis:")
            print(f"   💸 Best price: {min(prices):.2f} UAH")
            print(f"   📊 Worst price: {max(prices):.2f} UAH")
            print(f"   📏 Price spread: {max(prices) - min(prices):.2f} UAH")
            print(f"   ⚖️ Average price: {sum(prices)/len(prices):.2f} UAH")
            
            return True
            
        else:
            print("❌ No offers extracted")
            print("💡 Possible reasons:")
            print("   • Website structure changed")
            print("   • Network issues")
            print("   • No active USDT-UAH offers")
            return False
            
    except Exception as e:
        print(f"❌ Error during live test: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    finally:
        # Cleanup
        print("\n🧹 Cleaning up...")
        bybit.cleanup()
        print("✅ Browser closed")

async def main():
    """Main test function"""
    print("🚀 Starting Live ByBit P2P Test")
    print("🎯 This will show REAL current market data")
    print()
    
    success = await test_live_bybit()
    
    print("\n" + "="*60)
    if success:
        print("🎉 LIVE TEST PASSED!")
        print("✅ Organized project successfully extracts real P2P data!")
        print("💡 Your bot will get the same data when users check rates")
    else:
        print("⚠️ LIVE TEST HAD ISSUES")
        print("🔧 The structure is correct, but data extraction needs checking")
    
    print(f"\n📋 Live Test Result: {'SUCCESS' if success else 'NEEDS_ATTENTION'}")

if __name__ == "__main__":
    asyncio.run(main())