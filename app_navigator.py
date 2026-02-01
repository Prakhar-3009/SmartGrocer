#!/usr/bin/env python3
"""
App Navigator - FIXED v2.2
Fixes: Better price extraction, removes currency symbols properly
"""
import re
import json
import asyncio
import subprocess
from droidrun.config_manager.config_manager import DroidrunConfig, AgentConfig, LoggingConfig
from droid_runner import DroidRunRunner

class AppNavigator:
    def __init__(self, llm, max_steps=20):
        self.llm = llm
        
        # FULL config - For real shopping tasks
        self.config_full = DroidrunConfig(
            agent=AgentConfig(max_steps=max_steps, reasoning=True),
            logging=LoggingConfig(debug=True, save_trajectory="action", rich_text=True),
        )
        
        # FAST config - For quick tasks
        from config import config as bot_config
        self.config_fast = DroidrunConfig(
            agent=AgentConfig(max_steps=bot_config.max_steps_fast, reasoning=False),
            logging=LoggingConfig(debug=True, save_trajectory="none", rich_text=False),
        )
        
        # Safe runner
        self.runner = DroidRunRunner(
            llm=self.llm, 
            config_fast=self.config_fast, 
            config_full=self.config_full
        )
        
        # App package names
        self.app_packages = {
            "Blinkit": "com.grofers.customerapp",
            "Zepto": "com.zepto.app",
        }
        
        print("✅ App Navigator initialized (Anti-Zombie + Anti-Ghost)")
    
    async def force_home_reset(self):
        """Reset UI to home screen before each platform check"""
        print("🔄 Resetting to home screen...")
        await self.runner.run(
            goal='Press the Home button to go to the home screen.',
            timeout_s=10.0,
            fast=True
        )
        await asyncio.sleep(1.0)
    
    def _adb_force_stop(self, package: str):
        """Force-stop app via ADB"""
        try:
            result = subprocess.run(
                ["adb", "shell", "am", "force-stop", package],
                check=False,
                capture_output=True,
                timeout=5
            )
            if result.returncode == 0:
                print(f"✅ Force-stopped {package}")
            else:
                print(f"⚠️ Force-stop failed for {package}")
        except Exception as e:
            print(f"⚠️ ADB force-stop error: {e}")
    
    async def close_app(self, platform_name: str):
        """Properly close app to prevent ghost clicks"""
        print(f"🏠 Closing {platform_name}...")
        
        # Force-stop the app process
        package = self.app_packages.get(platform_name)
        if package:
            self._adb_force_stop(package)
        
        # Go home
        await self.runner.run(
            goal='Press the Home button.',
            timeout_s=10.0,
            fast=True
        )
        await asyncio.sleep(0.5)
    
    async def get_price_via_single_agent(self, platform_name: str, product_name: str) -> dict:
        """
        Main price checking method - runs complete flow for one platform
        """
        print(f"\n{'='*60}")
        print(f"🛒 CHECKING: {platform_name.upper()}")
        print(f"{'='*60}")
        
        # 1. Reset UI state
        await self.force_home_reset()
        
        # 2. Get app package
        package = self.app_packages.get(platform_name)
        
        # 3. Build task
        task = (
            f'Find the cheapest "{product_name}" on {platform_name}.\n\n'
            f'CRITICAL RULES:\n'
            f'1. Open app: {package}\n'
            f'2. Handle popups: Click "Close", "Allow", "Skip" or "Maybe Later" on ANY popup.\n'
            f'3. Search: Type "{product_name}" in search bar and press Enter.\n'
            f'4. DO NOT ENDLESSLY SWIPE. After 2 swipes, if no sort button, just pick the first cheap-looking item.\n'
            f'5. Click the FIRST product in results to open details.\n'
            f'6. Read: Price, Weight, Name, Stock.\n\n'
            f'FINISH with this EXACT format:\n'
            f'<request_accomplished success="true">{{"price": "$", "weight": "kg", "name": "Product Name", "stock": "yes/no"}}</request_accomplished>\n\n'
            f'If nothing found after opening first product:\n'
            f'<request_accomplished success="false">{{"note": "Product not available"}}</request_accomplished>\n\n'
            f'IMPORTANT: Do NOT get stuck in loops. Maximum 2 swipes allowed.'
        )
        
        # 4. Run with timeout
        output_text, err = await self.runner.run(
            goal=task,
            timeout_s=120.0,
            capture_stdout=True,
            fast=False
        )
        
        # 5. Handle timeout
        if isinstance(err, asyncio.TimeoutError):
            print(f"⚠️ TIMEOUT: {platform_name} took too long (>120s)")
            if package:
                self._adb_force_stop(package)
            return {
                "status": "error",
                "note": "App Timeout",
                "platform": platform_name
            }
        
        # 6. Handle errors
        if err:
            print(f"⚠️ Agent error: {err}")
            if package:
                self._adb_force_stop(package)
            return {
                "status": "error",
                "note": str(err)[:100],
                "platform": platform_name
            }
        
        # 7. Parse output
        if not output_text:
            print("⚠️ No output captured")
            return {
                "status": "error",
                "note": "No output",
                "platform": platform_name
            }
        
        print(f"📋 Captured {len(output_text)} chars of output")
        
        # 8. Extract structured data
        result = self._extract_data_from_output(output_text, platform_name)
        
        # 9. Display result
        if result.get('price'):
            print(f"✅ {platform_name}: ₹{result['price']} - {result.get('name', 'N/A')}")
        else:
            print(f"❌ {platform_name}: {result.get('note', 'No price found')}")
        
        return result
    
    def _extract_data_from_output(self, output_text: str, platform: str) -> dict:
        """Extract price data from captured agent output"""
        if not output_text:
            return {"status": "error", "note": "No output", "platform": platform}
        
        # Look for request_accomplished tags
        pattern = r'<request_accomplished[^>]*success="([^"]+)"[^>]*>([^<]+)</request_accomplished>'
        matches = re.findall(pattern, output_text, re.DOTALL | re.IGNORECASE)
        
        if matches:
            # Take the last match
            for success, content in reversed(matches):
                try:
                    # Clean and parse JSON
                    json_text = content.strip().replace("'", '"')
                    data = json.loads(json_text)
                    
                    # Handle list responses
                    if isinstance(data, list):
                        data = data[0] if data else {}
                    
                    # CRITICAL: Clean price data - remove currency symbols
                    if data.get('price'):
                        data['price'] = self._clean_price_value(data['price'])
                    if data.get('original_price'):
                        data['original_price'] = self._clean_price_value(data['original_price'])
                    
                    # Add platform
                    data['platform'] = platform
                    
                    # Check if successful
                    if success.lower() == "true" and data.get('price'):
                        data['status'] = 'found'
                        return data
                    elif success.lower() == "false":
                        data['status'] = 'not_found'
                        return data
                        
                except json.JSONDecodeError:
                    # Try regex extraction
                    result = self._parse_text_fallback(content, platform)
                    if result.get('price'):
                        return result
        
        # Fallback: Look for price in raw text
        if "price" in output_text.lower():
            result = self._parse_text_fallback(output_text, platform)
            if result.get('price'):
                return result
        
        return {
            "status": "error",
            "note": "Could not parse output",
            "platform": platform
        }
    
    def _clean_price_value(self, price) -> str:
        """
        Clean price value by removing currency symbols.
        Returns: Clean numeric string (e.g., "29" not "₹29")
        """
        if not price:
            return None
        
        price_str = str(price)
        
        # Remove all currency symbols and non-numeric chars except decimal
        cleaned = re.sub(r'[₹Rs,\s$€£]', '', price_str)
        cleaned = re.sub(r'[^\d.]', '', cleaned)
        
        # Validate
        try:
            float(cleaned)
            return cleaned
        except (ValueError, TypeError):
            return None
    
    def _parse_text_fallback(self, text: str, platform: str) -> dict:
        """Fallback regex-based extraction when JSON parsing fails"""
        data = {"platform": platform}
        
        # Extract price - IMPROVED to remove currency symbols immediately
        # Matches: ₹31, 31, Rs. 31, Rs 31, etc.
        price_match = re.search(r'(?:price["\s:]+)?[₹Rs.\s]*(\d+(?:\.\d{1,2})?)', text, re.IGNORECASE)
        if price_match:
            # Extract only numeric part
            raw_price = price_match.group(1)
            data['price'] = self._clean_price_value(raw_price)
            if data['price']:
                data['status'] = 'found'
        
        # Extract name
        name_match = re.search(r'name["\s:]+([a-zA-Z0-9\s]+)', text, re.IGNORECASE)
        if name_match:
            data['name'] = name_match.group(1).strip()
        
        # Extract weight
        weight_match = re.search(r'weight["\s:]+([0-9.]+\s*(?:kg|g|l|ml|gm))', text, re.IGNORECASE)
        if weight_match:
            data['weight'] = weight_match.group(1)
        
        return data if data.get('price') else {"status": "error", "platform": platform}