#!/usr/bin/env python3
"""
App Navigator - Anti-Choke Version
Fixes the "Unknown Action" crash by enforcing XML tags for completion.
"""
import re
import io
import sys
import json
import asyncio
from droidrun import DroidAgent
from droidrun.config_manager.config_manager import DroidrunConfig, AgentConfig, LoggingConfig

class AppNavigator:
    def __init__(self, llm, max_steps=20):
        self.llm = llm
        self.config = DroidrunConfig(
            agent=AgentConfig(max_steps=max_steps, reasoning=True),
            logging=LoggingConfig(debug=True, save_trajectory="action", rich_text=True),
        )
        self.app_packages = {
            "Blinkit": "com.grofers.customerapp", 
            "Zepto": "com.zepto.app"
        }
        print("✅ App Navigator initialized (Anti-Choke + Smart Sort)")
    
    async def get_price_via_single_agent(self, platform_name: str, product_name: str) -> dict:
        print(f"\n🛒 CHECKING: {platform_name.upper()}")
        
        # 1. Reset UI to prevent "Ghost Clicks"
        await self.force_home_reset()
        
        package = self.app_packages.get(platform_name)
        
        # --- PROMPT: FIXING THE CHOKE POINT ---
        task = (
            f'Find "{product_name}" on {platform_name}.\n'
            f'1. Open "{package}". Handle any popups/location (click "Close" or "Allow").\n'
            f'2. Search for "{product_name}".\n'
            f'3. SORTING: Look for "Sort"/"Filter" -> "Price Low to High". If missing, manually find the CHEAPEST item.\n'
            f'4. Click the product to see details.\n'
            f'5. Read: Price, Weight, Name, Delivery, Stock.\n'
            f'6. FINISH by writing this EXACT XML (Do NOT create a JSON action):\n'
            f'<request_accomplished success="true">{{"price": "29", "weight": "1kg", "name": "Onion", "stock": "yes"}}</request_accomplished>'
        )
        
        try:
            captured_output = io.StringIO()
            agent = DroidAgent(goal=task, config=self.config, llms=self.llm)
            
            old_stdout = sys.stdout
            sys.stdout = captured_output
            
            try:
                # 120s Timeout (Give it enough time to handle popups)
                await asyncio.wait_for(agent.run(), timeout=120.0)
            
            except asyncio.TimeoutError:
                sys.stdout = old_stdout
                print(f"⚠️ TIMEOUT: {platform_name} froze. Skipping...")
                return {"status": "error", "note": "App Timeout", "platform": platform_name}
                
            except Exception as e:
                sys.stdout = old_stdout
                print(f"⚠️ Agent Stopped: {e}")
                
            finally:
                if sys.stdout != old_stdout:
                    sys.stdout = old_stdout
            
            output_text = captured_output.getvalue()
            print(f"📋 Captured {len(output_text)} chars")
            
            result = self._extract_data_from_output(output_text, platform_name)
            print(f"✅ Result: {result}")
            return result
            
        except Exception as e:
            print(f"❌ Error: {e}")
            return {"status": "error", "note": str(e), "platform": platform_name}

    async def force_home_reset(self):
        """Ensures phone is on Home Screen before starting"""
        try:
            print("🔄 Resetting UI...")
            agent = DroidAgent(goal='Press Home button', config=self.config, llms=self.llm)
            await asyncio.wait_for(agent.run(), timeout=15.0)
            await asyncio.sleep(2)
        except: pass

    def _extract_data_from_output(self, output_text: str, platform: str) -> dict:
        """Extract price data from captured output"""
        if not output_text:
            return {"status": "error", "note": "No output", "platform": platform}
        
        # Look for the XML tag we specifically asked for
        pattern = r'<request_accomplished[^>]*>([^<]+)</request_accomplished>'
        matches = re.findall(pattern, output_text, re.DOTALL)
        
        if matches:
            for match in reversed(matches):
                try:
                    # Clean JSON text
                    json_text = match.strip().replace("'", '"')
                    # Fix unquoted keys if necessary
                    data = json.loads(json_text)
                    
                    if isinstance(data, list): data = data[0]
                    
                    if isinstance(data, dict):
                        data['platform'] = platform
                        if data.get('price'): 
                            data['status'] = 'found'
                            return data
                except: 
                    # If JSON fails, try Regex on the text inside the tag
                    res = self._parse_text(match, platform)
                    if res.get('price'): return res

        # Fallback: Look for "result" actions that might have failed but logged data
        if "price" in output_text:
             res = self._parse_text(output_text, platform)
             if res.get('price'): return res

        return {"status": "error", "note": "Parse failed", "platform": platform}

    def _parse_text(self, text: str, platform: str) -> dict:
        data = {"platform": platform}
        # Flexible Regex to catch prices like ₹31, 31, Rs. 31
        match = re.search(r'price\W+(\d+)', text, re.IGNORECASE)
        if match:
            data['price'] = match.group(1)
            data['status'] = 'found'
            # Try to find name/weight nearby
            name_match = re.search(r'name\W+([a-zA-Z0-9\s]+)', text, re.IGNORECASE)
            if name_match: data['name'] = name_match.group(1).strip()
            return data
        return {"status": "error"}

    async def close_app(self, platform_name: str):
        pass