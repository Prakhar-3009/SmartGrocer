#!/usr/bin/env python3
"""
Configuration Manager - v2.2 FIXED
CRITICAL FIX: Uses stable Gemini models that actually exist
"""
import os
from dataclasses import dataclass, field
from dotenv import load_dotenv

load_dotenv()

@dataclass
class PlatformConfig:
    """Platform-specific app package names"""
    BLINKIT: str = "com.grofers.customerapp"
    ZEPTO: str = "com.zeptoconsumerapp"  # FIXED: Correct package name from terminal log

@dataclass
class CategoryPlatforms:
    """Platform mapping - focused on groceries"""
    groceries: list = field(default_factory=lambda: ["Blinkit", "Zepto"])
    default: list = field(default_factory=lambda: ["Blinkit", "Zepto"])

@dataclass
class TimeoutConfig:
    """Timeout settings for different operations"""
    platform_check: int = 180
    whatsapp_read: int = 60
    whatsapp_send: int = 180
    reset_home: int = 15
    close_app: int = 10

@dataclass
class BotConfig:
    """Main bot configuration"""
    
    # ===== API Keys =====
    gemini_api_key: str = field(default_factory=lambda: os.getenv("GOOGLE_API_KEY", ""))
    
    # ===== Model Configuration =====
    # FIXED: Use stable models that are guaranteed to exist
    # For google.genai (ai_analyzer.py):
    #   - gemini-1.5-flash (stable, always works) ✅ RECOMMENDED
    #   - gemini-1.5-pro (more capable but slower)
    #   - gemini-2.0-flash-exp (experimental, may not be available)
    gemini_analyzer_model: str = field(
        default_factory=lambda: os.getenv("GEMINI_ANALYZER_MODEL", "gemini-1.5-flash")  # FIXED: Changed to stable model
    )
    
    # For llama_index.llms.google_genai (droidrun):
    #   - models/gemini-1.5-flash ✅ RECOMMENDED
    #   - models/gemini-1.5-pro
    gemini_droidrun_model: str = field(
        default_factory=lambda: os.getenv("GEMINI_DROIDRUN_MODEL", "gemini-1.5-flash")  # FIXED: Changed to stable model
    )
    
    # ===== WhatsApp Settings =====
    chat_name: str = "Rohit"
    
    # ===== Agent Settings =====
    max_steps: int = 25
    max_steps_fast: int = 8
    enable_reasoning: bool = True
    debug_mode: bool = True
    
    # ===== Platform Mappings =====
    platforms: PlatformConfig = field(default_factory=PlatformConfig)
    category_platforms: CategoryPlatforms = field(default_factory=CategoryPlatforms)
    grocery_platforms: list = field(default_factory=lambda: ["Blinkit", "Zepto"])
    
    # ===== Timing & Delays =====
    rate_limit_delay: int = 4
    timeouts: TimeoutConfig = field(default_factory=TimeoutConfig)
    
    # ===== Feature Flags =====
    use_adb_force_stop: bool = True
    capture_trajectories: bool = True
    
    def validate(self):
        """Validate configuration"""
        errors = []
        
        if not self.gemini_api_key:
            errors.append("GOOGLE_API_KEY not found in environment variables")
        
        if not self.chat_name or self.chat_name == "YourChatName":
            errors.append("Please set a valid chat_name in config.py")
        
        # Model info
        print("\n📋 Model Configuration:")
        print(f"   Analyzer Model: {self.gemini_analyzer_model}")
        print(f"   DroidRun Model: {self.gemini_droidrun_model}")
        
        if "1.5-flash" in self.gemini_analyzer_model:
            print("   ✅ Using stable gemini-1.5-flash (no 404 errors)")
        elif "2.0-flash-exp" in self.gemini_analyzer_model:
            print("   ⚠️ Using experimental model - may get 404 if not available")
        
        if errors:
            error_msg = "\n".join([f"❌ {e}" for e in errors])
            raise ValueError(f"\nConfiguration Errors:\n{error_msg}")
        
        print("✅ Configuration validated\n")
        return True
    
    def get_platforms_for_category(self, category: str) -> list:
        """Get relevant platforms"""
        if category.lower() in ['groceries', 'grocery', 'food', 'vegetables', 'fruits']:
            return self.grocery_platforms
        return self.grocery_platforms
    
    def get_app_package(self, platform_name: str) -> str:
        """Get app package name for platform"""
        return getattr(self.platforms, platform_name.upper().replace(" ", "_"), "")
    
    def print_config_summary(self):
        """Print configuration summary"""
        print("="*60)
        print("CONFIGURATION SUMMARY")
        print("="*60)
        print(f"Chat Name: {self.chat_name}")
        print(f"Analyzer Model: {self.gemini_analyzer_model}")
        print(f"DroidRun Model: {self.gemini_droidrun_model}")
        print(f"Max Steps (Full): {self.max_steps}")
        print(f"Max Steps (Fast): {self.max_steps_fast}")
        print(f"Platforms: {', '.join(self.grocery_platforms)}")
        print(f"Platform Timeout: {self.timeouts.platform_check}s")
        print(f"WhatsApp Send Timeout: {self.timeouts.whatsapp_send}s")
        print(f"Use ADB Force-Stop: {self.use_adb_force_stop}")
        print("="*60 + "\n")

# Global config instance
config = BotConfig()

# Set analyzer model in environment for AIAnalyzer
os.environ['GEMINI_ANALYZER_MODEL'] = config.gemini_analyzer_model