# apps/ai_core/ai_core/logic/settings_service.py
"""
Settings Service module for AI Core.

This service runs on EVERY startup to provide access to application settings.
It reads from and writes to the settings table created by DatabaseMigrator.
"""

import logging
from typing import Dict, Optional
from sqlalchemy import text
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)


class SettingsService:
    """
    Service for managing application settings.
    
    This is a simple class (not a singleton) that provides access to
    settings stored in the database. It receives a database session
    via dependency injection.
    
    Main responsibilities:
    - Load all settings as a dictionary on startup
    - Update individual settings via API
    - Provide settings to other services
    """
    
    def __init__(self, db_session: Session):
        """
        Initialize the SettingsService.
        
        Args:
            db_session: SQLAlchemy Session instance
        """
        self.db_session = db_session
        logger.debug("SettingsService initialized")
    
    def get_all_settings_as_dict(self) -> Dict[str, str]:
        """
        Get all settings as a dictionary.
        
        This is the MAIN function of this service. It loads all settings
        from the database and returns them as a single dictionary that
        can be distributed to other services.
        
        Returns:
            Dictionary mapping setting keys to values
            Example: {'API_PORT': '13337', 'AGING_BOOST': '10', ...}
        
        Raises:
            Exception: If database query fails
        """
        logger.info("Loading all settings from database...")
        
        try:
            # Query all settings
            result = self.db_session.execute(
                text("SELECT key, value FROM settings")
            )
            
            # Convert list of tuples to dictionary
            # [('API_PORT', '13337'), ('AGING_BOOST', '10')] -> {'API_PORT': '13337', 'AGING_BOOST': '10'}
            settings_dict = {row[0]: row[1] for row in result.fetchall()}
            
            logger.info(f"✅ Loaded {len(settings_dict)} settings from database")
            logger.debug(f"Settings: {list(settings_dict.keys())}")
            
            return settings_dict
            
        except Exception as e:
            logger.error(f"❌ Failed to load settings: {e}")
            raise
    
    def get_setting(self, key: str) -> Optional[str]:
        """
        Get a single setting value by key.
        
        Args:
            key: Setting key to retrieve
        
        Returns:
            Setting value as string, or None if not found
        """
        try:
            result = self.db_session.execute(
                text("SELECT value FROM settings WHERE key = :key"),
                {"key": key}
            )
            row = result.fetchone()
            
            if row:
                logger.debug(f"Retrieved setting '{key}': {row[0]}")
                return row[0]
            else:
                logger.warning(f"Setting '{key}' not found")
                return None
                
        except Exception as e:
            logger.error(f"❌ Failed to get setting '{key}': {e}")
            raise
    
    def update_setting(self, key: str, value: str) -> None:
        """
        Update a single setting.
        
        This function uses INSERT OR REPLACE to update an existing setting
        or create it if it doesn't exist.
        
        Args:
            key: Setting key to update
            value: New value for the setting
        
        Raises:
            Exception: If database update fails
        """
        logger.info(f"Updating setting: {key} = {value}")
        
        try:
            # Use INSERT OR REPLACE to update or insert
            self.db_session.execute(
                text("INSERT OR REPLACE INTO settings (key, value) VALUES (:key, :value)"),
                {"key": key, "value": value}
            )
            
            # Commit the transaction
            self.db_session.commit()
            
            logger.info(f"✅ Setting '{key}' updated successfully")
            
        except Exception as e:
            logger.error(f"❌ Failed to update setting '{key}': {e}")
            self.db_session.rollback()
            raise
    
    def update_settings(self, settings: Dict[str, str]) -> None:
        """
        Update multiple settings at once.
        
        Args:
            settings: Dictionary of key-value pairs to update
        
        Raises:
            Exception: If database update fails
        """
        logger.info(f"Updating {len(settings)} settings...")
        
        try:
            for key, value in settings.items():
                self.db_session.execute(
                    text("INSERT OR REPLACE INTO settings (key, value) VALUES (:key, :value)"),
                    {"key": key, "value": value}
                )
            
            # Commit all changes at once
            self.db_session.commit()
            
            logger.info(f"✅ {len(settings)} settings updated successfully")
            
        except Exception as e:
            logger.error(f"❌ Failed to update settings: {e}")
            self.db_session.rollback()
            raise
    
    def delete_setting(self, key: str) -> bool:
        """
        Delete a setting by key.
        
        Args:
            key: Setting key to delete
        
        Returns:
            True if setting was deleted, False if it didn't exist
        
        Raises:
            Exception: If database delete fails
        """
        logger.info(f"Deleting setting: {key}")
        
        try:
            result = self.db_session.execute(
                text("DELETE FROM settings WHERE key = :key"),
                {"key": key}
            )
            
            self.db_session.commit()
            
            if result.rowcount > 0:
                logger.info(f"✅ Setting '{key}' deleted successfully")
                return True
            else:
                logger.warning(f"Setting '{key}' not found")
                return False
                
        except Exception as e:
            logger.error(f"❌ Failed to delete setting '{key}': {e}")
            self.db_session.rollback()
            raise
    
    def setting_exists(self, key: str) -> bool:
        """
        Check if a setting exists.
        
        Args:
            key: Setting key to check
        
        Returns:
            True if setting exists, False otherwise
        """
        try:
            result = self.db_session.execute(
                text("SELECT 1 FROM settings WHERE key = :key"),
                {"key": key}
            )
            return result.fetchone() is not None
            
        except Exception as e:
            logger.error(f"❌ Failed to check setting existence '{key}': {e}")
            raise
    
    def get_all_settings_count(self) -> int:
        """
        Get the total count of settings in the database.
        
        Returns:
            Number of settings stored
        """
        try:
            result = self.db_session.execute(
                text("SELECT COUNT(*) FROM settings")
            )
            count = result.scalar()
            return count or 0
            
        except Exception as e:
            logger.error(f"❌ Failed to count settings: {e}")
            raise


def create_settings_service(db_session: Session) -> SettingsService:
    """
    Factory function to create a SettingsService instance.
    
    Args:
        db_session: SQLAlchemy Session instance
    
    Returns:
        Initialized SettingsService instance
    """
    return SettingsService(db_session)
