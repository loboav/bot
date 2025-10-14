#!/usr/bin/env python3
"""
Cleanup Old Project
==================

Script to organize and clean up the old messy project structure
"""

import os
import shutil

def cleanup_old_project():
    """Clean up old project files"""
    print("🧹 Cleaning up old project structure...")
    print("=" * 50)
    
    # Files to keep (main working files)
    files_to_keep = {
        'complete_p2p_monitoring_bot.py': 'Archive - полная версия бота',
        'bot_config.py': 'Archive - старая конфигурация',
        'README_BOT_SETUP.md': 'Archive - инструкции по установке',
        'requirements.txt': 'Archive - зависимости'
    }
    
    # Files to delete (duplicates, tests, temporary)
    files_to_delete = [
        'analyze_bybit_requests.py',
        'authenticated_bybit_p2p_extractor.py', 
        'bybit_client.py',
        'bybit_hybrid_client.py',
        'bybit_p2p_page.png',
        'bybit_page.html',
        'database.py',
        'demo_bot_functionality.py',
        'demo_real_data.py',
        'demo_with_monitoring.py',
        'final_bybit_p2p_browser_extractor.py',
        'fixed_bybit_p2p_extractor.py',
        'get_real_p2p_data.py',
        'main.py',
        'price_monitor.py',
        'real_bybit_p2p_data_extractor.py',
        'real_bybit_scraper.py',
        'setup.py',
        'simplified_bybit_p2p_extractor.py',
        'start_bot.bat',
        'telegram_bot.py',
        'test_api_fixed.py',
        'test_bot_integration.py',
        'test_bybit_api.py',
        'test_bybit_extended.py',
        'test_bybit_integration.py',
        'test_direct_links.py',
        'test_hybrid_client.py',
        'test_with_api_keys.py',
        'users_settings.json',
        'working_api_config.json',
        'working_bot.py',
        '.env',
        '.env.example'
    ]
    
    # Create archive folder for important files
    archive_folder = 'old_project_archive'
    if not os.path.exists(archive_folder):
        os.makedirs(archive_folder)
        print(f"📁 Created archive folder: {archive_folder}")
    
    # Move important files to archive
    print("\n📦 Archiving important files...")
    for filename, description in files_to_keep.items():
        if os.path.exists(filename):
            shutil.move(filename, os.path.join(archive_folder, filename))
            print(f"   ✅ Archived: {filename} - {description}")
        else:
            print(f"   ⚠️ Not found: {filename}")
    
    # Delete unnecessary files
    print("\n🗑️ Deleting unnecessary files...")
    deleted_count = 0
    for filename in files_to_delete:
        if os.path.exists(filename):
            os.remove(filename)
            print(f"   ✅ Deleted: {filename}")
            deleted_count += 1
        else:
            print(f"   ⚠️ Already gone: {filename}")
    
    # Remove __pycache__
    if os.path.exists('__pycache__'):
        shutil.rmtree('__pycache__')
        print(f"   ✅ Removed: __pycache__")
        deleted_count += 1
    
    print(f"\n📊 Cleanup Summary:")
    print(f"   📦 Files archived: {len(files_to_keep)}")
    print(f"   🗑️ Files deleted: {deleted_count}")
    print(f"   📁 New organized project: p2p_monitoring_bot/")
    
    print(f"\n✅ Cleanup completed!")
    print(f"🎯 Your clean project is ready in: p2p_monitoring_bot/")

if __name__ == "__main__":
    cleanup_old_project()