#!/usr/bin/env python3
"""
User Manager
============

Manages user settings and data persistence
"""

import json
import logging
from typing import Dict, Any
from config.settings import USERS_DATA_FILE, DEFAULT_USER_SETTINGS

logger = logging.getLogger(__name__)

class UserManager:
    """Manages user settings and data"""
    
    def __init__(self):
        self.users_data = self.load_users_data()
    
    def load_users_data(self) -> Dict:
        """Load user settings from file"""
        try:
            with open(USERS_DATA_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except FileNotFoundError:
            logger.info("Users data file not found, creating new one")
            return {}
        except Exception as e:
            logger.error(f"Error loading users data: {e}")
            return {}
    
    def save_users_data(self):
        """Save user settings to file"""
        try:
            # Ensure directory exists
            import os
            os.makedirs(os.path.dirname(USERS_DATA_FILE), exist_ok=True)
            
            with open(USERS_DATA_FILE, 'w', encoding='utf-8') as f:
                json.dump(self.users_data, f, indent=2, ensure_ascii=False)
            logger.debug("Users data saved successfully")
        except Exception as e:
            logger.error(f"Failed to save user data: {e}")
    
    def get_user_data(self, user_id: int) -> Dict[str, Any]:
        """Get user settings with defaults"""
        user_id_str = str(user_id)
        if user_id_str not in self.users_data:
            self.users_data[user_id_str] = {
                **DEFAULT_USER_SETTINGS,
                'active_exchanges': DEFAULT_USER_SETTINGS['active_exchanges'].copy(),
                'last_notification': None
            }
            self.save_users_data()
        
        return self.users_data[user_id_str]
    
    def update_user_data(self, user_id: int, data: Dict):
        """Update user settings"""
        user_id_str = str(user_id)
        if user_id_str not in self.users_data:
            self.users_data[user_id_str] = {}
        
        self.users_data[user_id_str].update(data)
        self.save_users_data()
        logger.info(f"Updated settings for user {user_id}")
    
    def get_all_users_with_notifications(self) -> list:
        """Get all users with notifications enabled"""
        return [
            int(user_id) for user_id, data in self.users_data.items()
            if data.get('notifications_enabled', True)
        ]