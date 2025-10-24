#!/usr/bin/env python3
"""
Test script for Binance DOM parsing
====================================

Run this to test the new DOM parsing method vs old text parsing
"""

import sys
import os
import asyncio
import logging

# Add project paths
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(os.path.join(os.path.dirname(os.path.abspath(__file__)), "bot"))

from bot.exchanges.binance_p2p import BinanceP2P

# Setup logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)


async def test_binance_dom_parsing():
    """Test Binance DOM parsing"""
    print("=" * 60)
    print("🧪 TESTING BINANCE DOM PARSING")
    print("=" * 60)

    binance = BinanceP2P()

    try:
        print("\n📊 Step 1: Setup browser...")
        if not binance.setup_browser():
            print("❌ Browser setup failed!")
            return False
        print("✅ Browser ready")

        print("\n📊 Step 2: Fetching offers (force_refresh=True)...")
        print("⏳ This will take 10-15 seconds...")
        offers = await binance.get_offers(force_refresh=True)

        if not offers:
            print("❌ No offers received!")
            return False

        print(f"\n✅ SUCCESS! Got {len(offers)} offers")
        print("=" * 60)

        # Show first 3 offers
        print("\n📋 FIRST 3 OFFERS:")
        print("-" * 60)
        for i, offer in enumerate(offers[:3], 1):
            print(f"\n{i}. {offer['exchange'].upper()} - {offer['username']}")
            print(f"   💰 Price: {offer['price']:.2f} UAH")
            print(f"   📊 Available: {offer['available']:.1f} USDT")
            print(
                f"   💳 Limits: {offer['min_amount']:.0f} - {offer['max_amount']:.0f} UAH"
            )
            print(f"   🔗 Link: {offer['link'][:60]}...")

        # Statistics
        print("\n" + "=" * 60)
        print("📊 STATISTICS:")
        print("-" * 60)
        prices = [o["price"] for o in offers]
        print(f"   Total offers: {len(offers)}")
        print(f"   Price range: {min(prices):.2f} - {max(prices):.2f} UAH")
        print(f"   Average price: {sum(prices) / len(prices):.2f} UAH")

        # Check data quality
        print("\n" + "=" * 60)
        print("✅ DATA QUALITY CHECK:")
        print("-" * 60)

        # Count "Unknown" usernames
        unknown_count = sum(1 for o in offers if o["username"] == "Unknown")
        print(f"   Unknown usernames: {unknown_count}/{len(offers)}")

        # Count valid links
        valid_links = sum(
            1
            for o in offers
            if "advertiserNo=s" in o["link"] or "merchant" in o["link"]
        )
        print(f"   Valid links: {valid_links}/{len(offers)}")

        # Count reasonable prices
        reasonable = sum(1 for o in offers if 40 <= o["price"] <= 45)
        print(f"   Reasonable prices (40-45): {reasonable}/{len(offers)}")

        success_rate = (len(offers) - unknown_count) / len(offers) * 100
        print(f"\n   ✅ Success rate: {success_rate:.1f}%")

        if success_rate >= 80:
            print("\n🎉 DOM PARSING WORKS GREAT!")
            return True
        elif success_rate >= 50:
            print("\n⚠️ DOM parsing works but has issues")
            return True
        else:
            print("\n❌ DOM parsing has serious problems")
            return False

    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback

        traceback.print_exc()
        return False

    finally:
        print("\n🧹 Cleaning up...")
        binance.cleanup()
        print("✅ Browser closed")


async def compare_parsing_methods():
    """Compare DOM vs Text parsing"""
    print("\n" + "=" * 60)
    print("🔬 COMPARING DOM vs TEXT PARSING")
    print("=" * 60)

    binance = BinanceP2P()

    try:
        if not binance.setup_browser():
            print("❌ Browser setup failed!")
            return

        # Load page
        print("\n📊 Loading Binance P2P page...")
        binance.driver.get(binance.base_url)
        await asyncio.sleep(10)  # Wait for page load

        # Scroll
        print("📜 Scrolling page...")
        await binance._scroll_page()

        # Get data
        page_text = binance.driver.find_element("tag name", "body").text
        page_source = binance.driver.page_source
        advertiser_ids = binance._extract_advertiser_ids(page_source)

        print(f"\n✅ Page loaded, found {len(advertiser_ids)} advertiser IDs")

        # Test DOM parsing
        print("\n1️⃣ Testing DOM parsing...")
        try:
            dom_offers = binance._parse_offers_dom(advertiser_ids)
            print(f"   ✅ DOM: {len(dom_offers)} offers")
        except Exception as e:
            print(f"   ❌ DOM failed: {e}")
            dom_offers = []

        # Test text parsing
        print("\n2️⃣ Testing Text parsing...")
        try:
            # Temporarily disable DOM parsing to test text method
            text_offers = []
            lines = page_text.split("\n")
            price_patterns = binance._extract_price_patterns(lines)
            username_patterns = binance._extract_username_patterns(lines)
            usdt_patterns = binance._extract_usdt_patterns(lines)
            limit_patterns = binance._extract_limit_patterns(lines)

            print(f"   Text parsing found:")
            print(f"      Prices: {len(price_patterns)}")
            print(f"      Usernames: {len(username_patterns)}")
            print(f"      USDT amounts: {len(usdt_patterns)}")
            print(f"      Limits: {len(limit_patterns)}")
        except Exception as e:
            print(f"   ❌ Text parsing failed: {e}")

        # Compare
        print("\n" + "=" * 60)
        print("📊 COMPARISON:")
        print("-" * 60)
        print(f"   DOM parsing: {len(dom_offers)} offers")
        print(f"   Text parsing patterns found: {len(price_patterns)}")

        if len(dom_offers) > 0:
            print("\n   ✅ DOM parsing is WORKING!")
            print("   🎯 Recommendation: Use DOM parsing")
        else:
            print("\n   ⚠️ DOM parsing returned 0 offers")
            print("   🎯 Recommendation: Stick with text parsing for now")

    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback

        traceback.print_exc()

    finally:
        print("\n🧹 Cleaning up...")
        binance.cleanup()


async def main():
    """Run all tests"""
    print("\n🚀 BINANCE DOM PARSING TEST SUITE")
    print("=" * 60)

    # Test 1: Basic DOM parsing
    success = await test_binance_dom_parsing()

    if success:
        print("\n✅ BASIC TEST PASSED!")

        # Test 2: Compare methods
        user_input = input("\n❓ Run comparison test? (y/n): ")
        if user_input.lower() == "y":
            await compare_parsing_methods()
    else:
        print("\n❌ BASIC TEST FAILED")
        print("💡 The fallback to text parsing should still work")

    print("\n" + "=" * 60)
    print("🏁 TESTING COMPLETE")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
