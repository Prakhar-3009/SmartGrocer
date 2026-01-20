#!/usr/bin/env python3
"""
Configuration Manager - Updated for Grocery-focused Bot
Handles all API keys and settings
"""
import os
from dataclasses import dataclass, field
from dotenv import load_dotenv

load_dotenv()

@dataclass
class PlatformConfig:
    """Platform-specific app package names"""
    BLINKIT: str = "com.grofers.customerapp"
    ZEPTO: str = "com.zepto.app"

@dataclass
class CategoryPlatforms:
    """Platform mapping - now focused on groceries only"""
    groceries: list = field(default_factory=lambda: ["Blinkit", "Zepto"])
    default: list = field(default_factory=lambda: ["Blinkit", "Zepto"])

@dataclass
class BotConfig:
    """Main bot configuration"""
    # API Keys
    gemini_api_key: str = field(default_factory=lambda: os.getenv("GOOGLE_API_KEY", ""))
    
    # WhatsApp Settings
    chat_name: str = "Prashant"  # Default chat name - change as needed
    
    # Agent Settings
    max_steps: int = 15  # Increased for more complex tasks
    enable_reasoning: bool = True
    debug_mode: bool = True
    
    # Platform Mappings
    platforms: PlatformConfig = field(default_factory=PlatformConfig)
    category_platforms: CategoryPlatforms = field(default_factory=CategoryPlatforms)
    
    # Grocery-specific platforms
    grocery_platforms: list = field(default_factory=lambda: ["Blinkit", "Zepto"])
    
    # Timing
    rate_limit_delay: int = 3  # seconds between app checks
    
    def validate(self):
        """Validate configuration"""
        if not self.gemini_api_key:
            raise ValueError("❌ GOOGLE_API_KEY not found in environment variables!")
        return True
    
    def get_platforms_for_category(self, category: str) -> list:
        """Get relevant platforms - always returns Blinkit and Zepto for groceries"""
        if category.lower() in ['groceries', 'grocery', 'food', 'vegetables', 'fruits']:
            return self.grocery_platforms
        return self.grocery_platforms  # Default to grocery platforms
    
    def get_app_package(self, platform_name: str) -> str:
        """Get app package name for platform"""
        return getattr(self.platforms, platform_name.upper().replace(" ", "_"), "")

# Global config instance
config = BotConfig()