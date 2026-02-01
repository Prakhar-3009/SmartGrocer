#!/usr/bin/env python3
"""
Smart Grocery Price Bot - Production Version
All fixes applied: Zombie tasks, Ghost clicks, List/Dict handling, Timeouts
"""
import asyncio
from llama_index.llms.google_genai import GoogleGenAI

from config import config
from whatsapp_handler import WhatsAppHandler
from ai_analyzer import AIAnalyzer
from app_navigator import AppNavigator
from price_checker import PriceChecker

class SmartGroceryBot:
    def __init__(self):
        """Initialize the complete grocery bot system"""
        print("\n" + "🤖" * 35)
        print("SMART GROCERY PRICE BOT - PRODUCTION v2.0")
        print("🤖" * 35)
        print("\n🛒 Platforms: Blinkit & Zepto")
        print("🔧 Fixes: Anti-Zombie, Anti-Ghost, List/Dict Handling\n")
        
        # Validate configuration
        config.validate()
        config.print_config_summary()
        
        # Initialize LLM for DroidRun
        print("🧠 Initializing Gemini LLM...")
        self.llm = GoogleGenAI(
            model=config.gemini_droidrun_model,
            api_key=config.gemini_api_key,
            temperature=0.0
        )
        print(f"✅ LLM initialized: {config.gemini_droidrun_model}\n")
        
        # Initialize all modules
        print("📦 Initializing modules...")
        self.whatsapp = WhatsAppHandler(self.llm, config.max_steps)
        self.ai_analyzer = AIAnalyzer(config.gemini_api_key)
        self.app_navigator = AppNavigator(self.llm, config.max_steps)
        self.price_checker = PriceChecker(self.app_navigator, self.ai_analyzer)
        
        print("\n✅ Bot initialized successfully!\n")
    
    async def run(self, chat_name: str = None):
        """Main bot workflow"""
        if not chat_name:
            chat_name = config.chat_name
        
        print("\n" + "="*70)
        print("🚀 STARTING BOT WORKFLOW")
        print("="*70)
        print(f"📱 Target Chat: {chat_name}")
        print(f"⏰ Started at: {asyncio.get_event_loop().time():.2f}s")
        print("="*70 + "\n")
        
        # ========================================
        # PHASE 1: READ MESSAGE FROM WHATSAPP
        # ========================================
        print("🔵" * 35)
        print("PHASE 1: READING WHATSAPP MESSAGE")
        print("🔵" * 35)
        
        message = await self.whatsapp.read_last_message(chat_name)
        
        if not message:
            print("\n❌ FAILED: Could not read message")
            await self.send_error_message(chat_name, "Could not read your message. Please try again.")
            return
        
        print(f"\n✅ Message received: '{message}'")
        
        # Brief pause
        await asyncio.sleep(1)
        
        # ========================================
        # PHASE 2: ANALYZE MESSAGE
        # ========================================
        print("\n🟡" * 35)
        print("PHASE 2: AI ANALYSIS")
        print("🟡" * 35)
        
        product_info = self.ai_analyzer.extract_product_info(message)
        
        # Check if it's a product query
        if not product_info.get('is_product'):
            print("\n⚠️ NOT A PRODUCT QUERY")
            response = (
                "👋 Hi! I'm your Smart Grocery Bot.\n\n"
                "I can help you compare prices on Blinkit and Zepto!\n\n"
                "Try asking:\n"
                "• 'Check tomato prices'\n"
                "• 'Find milk prices'\n"
                "• 'Compare onion prices'\n\n"
                "What would you like to search? 🛒"
            )
            await self.whatsapp.send_message(chat_name, response)
            await self.whatsapp.go_home()
            return
        
        product_name = product_info.get('product_name')
        category = product_info.get('category')
        quantity = product_info.get('quantity', 'Not specified')
        
        print(f"\n📦 Product: {product_name}")
        print(f"📊 Category: {category}")
        print(f"⚖️ Quantity: {quantity}")
        
        # Determine platforms
        platforms = self.ai_analyzer.determine_platforms(category, product_name)
        print(f"✅ Platforms: {', '.join(platforms)}")
        
        # Send acknowledgment
        ack_message = (
            f"🔍 Searching for *{product_name}* on {' & '.join(platforms)}...\n\n"
            f"⏳ This will take 30-60 seconds. Please wait!"
        )
        await self.whatsapp.send_message(chat_name, ack_message)
        await asyncio.sleep(1)
        
        # ========================================
        # PHASE 3: CHECK PRICES ON APPS
        # ========================================
        print("\n🔴" * 35)
        print("PHASE 3: MULTI-PLATFORM PRICE CHECK")
        print("🔴" * 35)
        
        price_data = await self.price_checker.check_multiple_platforms(
            platforms=platforms,
            product_name=product_name,
            delay=config.rate_limit_delay
        )
        
        # Check if we got any valid prices
        valid_prices = [p for p in price_data if p.get('price') and p.get('status') == 'found']
        
        if not valid_prices:
            print("\n❌ No valid prices found")
            error_message = (
                f"😔 Sorry, I couldn't find prices for *{product_name}*.\n\n"
                f"Possible reasons:\n"
                f"• Product not available on these platforms\n"
                f"• App loading issues\n"
                f"• Product name too generic\n\n"
                f"Try:\n"
                f"• Being more specific (e.g., 'red onions' instead of 'onions')\n"
                f"• Checking the apps manually\n"
                f"• Trying a different product"
            )
            await self.whatsapp.send_message(chat_name, error_message)
            await self.whatsapp.go_home()
            return
        
        print(f"\n✅ Found prices on {len(valid_prices)} platform(s)")
        
        # ========================================
        # PHASE 4: GENERATE RECOMMENDATION
        # ========================================
        print("\n🟢" * 35)
        print("PHASE 4: AI RECOMMENDATION")
        print("🟢" * 35)
        
        recommendation = self.ai_analyzer.generate_recommendation(product_info, valid_prices)
        
        # ========================================
        # PHASE 5: SEND RESULTS
        # ========================================
        print("\n🟣" * 35)
        print("PHASE 5: SENDING RESULTS")
        print("🟣" * 35)
        
        # Format complete message
        final_message = self.price_checker.format_price_summary(price_data)
        final_message += f"\n💡 *Smart Recommendation:*\n{recommendation}"
        
        print("\n📤 Sending price comparison report...")
        success = await self.whatsapp.send_message(chat_name, final_message)
        
        if success:
            print("✅ Report sent successfully!")
        else:
            print("⚠️ Message send may have failed")
        
        # Return to home
        await self.whatsapp.go_home()
        
        # ========================================
        # COMPLETION
        # ========================================
        print("\n" + "="*70)
        print("✅ BOT WORKFLOW COMPLETED SUCCESSFULLY!")
        print(f"⏰ Completed at: {asyncio.get_event_loop().time():.2f}s")
        print("="*70)
    
    async def send_error_message(self, chat_name: str, error_text: str):
        """Send error message to user"""
        try:
            await self.whatsapp.send_message(chat_name, f"❌ Error: {error_text}")
            await self.whatsapp.go_home()
        except Exception as e:
            print(f"Could not send error message: {e}")

async def main():
    """Main entry point"""
    try:
        print("\n" + "🚀" * 35)
        print("STARTING SMART GROCERY BOT")
        print("🚀" * 35 + "\n")
        
        bot = SmartGroceryBot()
        await bot.run()
        
        print("\n✨ Bot execution completed!")
        print("\n💡 Tips for next run:")
        print("   • Make sure chat has a recent message")
        print("   • Keep phone unlocked during execution")
        print("   • Check that apps are updated")
        
    except KeyboardInterrupt:
        print("\n\n⚠️ Bot stopped by user (Ctrl+C)")
    except Exception as e:
        print(f"\n❌ FATAL ERROR: {e}")
        import traceback
        traceback.print_exc()
        print("\n💡 Troubleshooting:")
        print("   • Check if phone is connected: adb devices")
        print("   • Verify API key in .env file")
        print("   • Run test_setup.py to diagnose issues")

if __name__ == "__main__":
    asyncio.run(main())