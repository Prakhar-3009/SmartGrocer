#!/usr/bin/env python3
"""
Smart Grocery Price Bot - Main Controller
Uses ONLY DroidRun for all operations (WhatsApp + Apps)
Checks prices on Blinkit and Zepto
"""
import asyncio
import time
from llama_index.llms.google_genai import GoogleGenAI

from config import config
from whatsapp_handler import WhatsAppHandler
from ai_analyzer import AIAnalyzer
from app_navigator import AppNavigator
from price_checker import PriceChecker

class SmartGroceryBot:
    def __init__(self):
        """Initialize the complete grocery bot system"""
        print("🤖 Initializing Smart Grocery Price Bot...")
        print("🛒 Focused on: Blinkit & Zepto\n")
        
        config.validate()
        
        # Initialize single LLM instance for all DroidRun operations
        self.llm = GoogleGenAI(
            model="models/gemini-2.5-pro",
            api_key=config.gemini_api_key,
            temperature=0.0
        )
        
        # Initialize all modules with DroidRun
        self.whatsapp = WhatsAppHandler(self.llm, config.max_steps)
        self.ai_analyzer = AIAnalyzer(config.gemini_api_key)
        self.app_navigator = AppNavigator(self.llm, config.max_steps)
        self.price_checker = PriceChecker(self.app_navigator, self.ai_analyzer)
        
        print("✅ Bot initialized successfully!\n")
    
    async def run(self, chat_name: str = None):
        """Main bot workflow"""
        if not chat_name:
            chat_name = config.chat_name
        
        print("\n" + "="*70)
        print("🤖 SMART GROCERY PRICE CHECKER BOT")
        print("🔋 Powered by: Gemini 2.5 Pro + DroidRun")
        print("🛒 Platforms: Blinkit & Zepto")
        print("="*70)
        print(f"📱 Target Chat: {chat_name}\n")
        
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
        
        # Small delay to ensure WhatsApp operations are complete
        await asyncio.sleep(2)
        
        # ========================================
        # PHASE 2: ANALYZE MESSAGE
        # ========================================
        print("\n🟡" * 35)
        print("PHASE 2: ANALYZING MESSAGE WITH AI")
        print("🟡" * 35)
        
        product_info = self.ai_analyzer.extract_product_info(message)
        
        if not product_info.get('is_product'):
            print("\n⚠️ NOT A PRODUCT QUERY - Sending friendly response")
            response = (
                "👋 Hi! I'm your Smart Grocery Bot.\n\n"
                "I can help you compare prices for groceries on Blinkit and Zepto!\n\n"
                "Just tell me what you want to buy, like:\n"
                "• 'Check tomato prices'\n"
                "• 'Find milk prices'\n"
                "• 'Compare onion prices'\n\n"
                "Try asking about a grocery item! 🛒"
            )
            await self.whatsapp.send_message(chat_name, response)
            return
        
        product_name = product_info.get('product_name')
        category = product_info.get('category')
        quantity = product_info.get('quantity', 'Not specified')
        
        print(f"\n📦 Product: {product_name}")
        print(f"📊 Category: {category}")
        print(f"⚖️ Quantity: {quantity}")
        
        # Determine platforms (always Blinkit & Zepto for groceries)
        platforms = self.ai_analyzer.determine_platforms(category, product_name)
        print(f"✅ Platforms: {', '.join(platforms)}")
        
        # Send acknowledgment message
        ack_message = f"🔍 Checking prices for *{product_name}* on {' and '.join(platforms)}...\n\n⏳ This will take about 30-60 seconds. Please wait!"
        await self.whatsapp.send_message(chat_name, ack_message)
        
        # Small delay after sending message
        await asyncio.sleep(2)
        
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
        
        if not price_data or len(price_data) == 0:
            print("\n❌ No prices found on any platform")
            error_message = (
                f"😔 Sorry, I couldn't find prices for *{product_name}* on {' or '.join(platforms)}.\n\n"
                "This could happen if:\n"
                "• The product is not available\n"
                "• The app had loading issues\n"
                "• The product name needs to be more specific\n\n"
                "Please try again with a different product or check the apps manually."
            )
            await self.whatsapp.send_message(chat_name, error_message)
            return
        
        print(f"\n✅ Found prices on {len(price_data)} platform(s)")
        
        # ========================================
        # PHASE 4: GENERATE RECOMMENDATION
        # ========================================
        print("\n🟢" * 35)
        print("PHASE 4: GENERATING RECOMMENDATION")
        print("🟢" * 35)
        
        recommendation = self.ai_analyzer.generate_recommendation(product_info, price_data)
        
        # ========================================
        # PHASE 5: SEND RESULTS TO WHATSAPP
        # ========================================
        print("\n🟣" * 35)
        print("PHASE 5: SENDING RESULTS")
        print("🟣" * 35)
        
        # Format the complete message
        final_message = self.price_checker.format_price_summary(price_data)
        final_message += f"\n💡 *Smart Recommendation:*\n{recommendation}"
        
        print("\n📤 Sending price comparison report...")
        success = await self.whatsapp.send_message(chat_name, final_message)
        
        if success:
            print("✅ Report sent successfully!")
        else:
            print("⚠️ There might have been an issue sending the message")
        
        # Return to home screen
        await self.whatsapp.go_home()
        
        print("\n" + "="*70)
        print("✅ BOT WORKFLOW COMPLETED SUCCESSFULLY!")
        print("="*70)
    
    async def send_error_message(self, chat_name: str, error_text: str):
        """Send error message to user"""
        try:
            await self.whatsapp.send_message(chat_name, f"❌ Error: {error_text}")
        except:
            print("Could not send error message to WhatsApp")

async def main():
    """Main entry point"""
    try:
        print("\n" + "🚀" * 35)
        print("STARTING SMART GROCERY BOT")
        print("🚀" * 35 + "\n")
        
        bot = SmartGroceryBot()
        await bot.run()
        
        print("\n✨ Bot execution completed!")
        
    except KeyboardInterrupt:
        print("\n\n⚠️ Bot stopped by user (Ctrl+C)")
    except Exception as e:
        print(f"\n❌ FATAL ERROR: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(main())