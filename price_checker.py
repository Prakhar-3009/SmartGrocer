#!/usr/bin/env python3
"""
Price Checker - Fixed Response Handling
Better parsing and validation of price data
"""
import asyncio
from typing import List, Dict

class PriceChecker:
    def __init__(self, app_navigator, ai_analyzer):
        self.navigator = app_navigator
        self.analyzer = ai_analyzer
    
    async def check_single_platform(self, platform: str, product_name: str) -> Dict:
        print(f"\n📊 Checking {platform}...")
        
        # Get data from navigator
        data = await self.navigator.get_price_via_single_agent(platform, product_name)
        
        print(f"🔍 Response from {platform}: {data}")
        
        # Validate the response
        if not data:
            return {
                "platform": platform, 
                "price": None, 
                "name": "N/A", 
                "weight": "N/A", 
                "delivery": "N/A", 
                "note": "No response"
            }
        
        # Check status
        status = data.get("status", "")
        
        if status == "not_found":
            return {
                "platform": platform, 
                "price": None, 
                "name": "N/A", 
                "weight": "N/A", 
                "delivery": "N/A", 
                "note": data.get("note", "Not Found")
            }
        
        if status == "error":
            return {
                "platform": platform, 
                "price": None, 
                "name": "N/A", 
                "weight": "N/A", 
                "delivery": "N/A", 
                "note": data.get("note", "Error")
            }
        
        # Extract and clean price
        price = data.get("price", "")
        if price:
            # Remove currency symbols and clean
            price = str(price).replace('₹', '').replace(',', '').strip()
        
        # Build result
        result = {
            "platform": platform,
            "price": price if price else None,
            "weight": data.get("weight", "N/A"),
            "name": data.get("name", product_name),
            "delivery": data.get("delivery", "Unknown"),
            "stock": data.get("stock", "Unknown"),
            "status": "found" if price else "not_found"
        }
        
        if result["price"]:
            print(f"✅ {platform}: ₹{result['price']} - {result['name']} ({result['weight']})")
        else:
            print(f"❌ {platform}: No price found")
        
        return result
    
    async def check_multiple_platforms(self, platforms: List[str], product_name: str, delay: int = 3) -> List[Dict]:
        print(f"\n🛒 PRICE COMPARISON: {product_name}\n")
        all_results = []
        
        for platform in platforms:
            result = await self.check_single_platform(platform, product_name)
            all_results.append(result)
            
            # Close the app
            await self.navigator.close_app(platform)
            
            # Wait before next platform (except last one)
            if delay > 0 and platform != platforms[-1]:
                print(f"⏳ Waiting {delay}s before next platform...")
                await asyncio.sleep(delay)
        
        # Filter out results that have valid prices
        valid_results = [r for r in all_results if r.get('price')]
        
        if valid_results:
            print(f"\n✅ Successfully found prices on {len(valid_results)} platform(s)")
        else:
            print(f"\n⚠️ No valid prices found on any platform")
        
        return all_results

    def format_price_summary(self, price_data: List[Dict]) -> str:
        if not price_data: 
            return "❌ No data available."
        
        message = "🛒 *GROCERY PRICE COMPARISON*\n"
        message += "=" * 40 + "\n\n"
        
        # Separate valid and invalid results
        valid_items = [x for x in price_data if x.get('price') and x.get('status') == 'found']
        error_items = [x for x in price_data if not x.get('price') or x.get('status') != 'found']
        
        # Sort valid items by price (cheapest first)
        if valid_items:
            try:
                valid_items.sort(key=lambda x: float(str(x['price']).replace('₹', '').replace(',', '').strip()))
            except Exception as e:
                print(f"⚠️ Could not sort prices: {e}")
        
        # Display valid results
        if valid_items:
            for idx, item in enumerate(valid_items):
                # Add medal for cheapest
                if idx == 0:
                    medal = "🥇 *BEST PRICE*"
                elif idx == 1:
                    medal = "🥈"
                else:
                    medal = "🥉"
                
                message += f"{medal}\n"
                message += f"*Platform:* {item['platform']}\n"
                message += f"*Price:* ₹{item['price']}\n"
                message += f"*Product:* {item.get('name', 'N/A')}\n"
                message += f"*Weight:* {item.get('weight', 'N/A')}\n"
                
                if item.get('delivery'):
                    message += f"*Delivery:* {item.get('delivery')}\n"
                
                if item.get('stock'):
                    stock_emoji = "✅" if item['stock'].lower() in ['yes', 'in stock', 'available'] else "❌"
                    message += f"*Stock:* {stock_emoji} {item['stock']}\n"
                
                message += "\n" + "-" * 40 + "\n\n"
        else:
            message += "⚠️ No prices found on any platform\n\n"
        
        # Display errors
        if error_items:
            message += "*Issues:*\n"
            for item in error_items:
                note = item.get('note', 'Not available')
                message += f"❌ {item['platform']}: {note}\n"
            message += "\n"
        
        return message