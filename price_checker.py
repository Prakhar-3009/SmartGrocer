#!/usr/bin/env python3
"""
Price Checker Module - v2.3 FIXED
Adds: Per-kg price normalization for fair comparison
"""
import asyncio
import re
from typing import List, Dict, Optional

class PriceChecker:
    def __init__(self, app_navigator, ai_analyzer):
        """Initialize Price Checker with navigator and analyzer"""
        self.navigator = app_navigator
        self.analyzer = ai_analyzer
    
    async def check_single_platform(self, platform: str, product_name: str) -> Dict:
        """Check price on a single platform"""
        print(f"\n📊 Checking {platform}...")
        
        try:
            price_data = await self.navigator.get_price_via_single_agent(platform, product_name)
            
            if not price_data:
                print(f"⚠️ No data from {platform}")
                return {
                    "platform": platform,
                    "status": "error",
                    "note": "No data returned"
                }
            
            # Clean price data
            if price_data.get('price'):
                price_data['price'] = self._clean_price(price_data['price'])
            if price_data.get('original_price'):
                price_data['original_price'] = self._clean_price(price_data['original_price'])
            
            # CRITICAL: Calculate per-kg price for fair comparison
            if price_data.get('price') and price_data.get('weight'):
                price_data['price_per_kg'] = self._calculate_price_per_kg(
                    price_data['price'], 
                    price_data['weight']
                )
            
            if price_data.get('status') == 'found' and price_data.get('price'):
                weight_info = f" ({price_data.get('weight', 'unknown')})" if price_data.get('weight') else ""
                per_kg_info = f" [₹{price_data.get('price_per_kg', 'N/A')}/kg]" if price_data.get('price_per_kg') else ""
                print(f"✅ {platform}: ₹{price_data['price']}{weight_info}{per_kg_info}")
                return price_data
            else:
                print(f"⚠️ {platform}: {price_data.get('note', 'No price found')}")
                return price_data
                
        except Exception as e:
            print(f"❌ Error checking {platform}: {e}")
            return {
                "platform": platform,
                "status": "error",
                "note": str(e)[:100]
            }
    
    def _clean_price(self, price_str) -> str:
        """Clean price string by removing currency symbols"""
        if not price_str:
            return None
        
        price_str = str(price_str)
        cleaned = re.sub(r'[₹Rs,\s$€£]', '', price_str)
        cleaned = re.sub(r'[^\d.]', '', cleaned)
        
        try:
            float(cleaned)
            return cleaned
        except ValueError:
            return None
    
    def _calculate_price_per_kg(self, price: str, weight: str) -> Optional[float]:
        """
        Calculate price per kilogram for fair comparison.
        
        Examples:
        - price=49, weight="300g" → 163.33 per kg
        - price=144, weight="500g" → 288.00 per kg
        - price=31, weight="1kg" → 31.00 per kg
        """
        try:
            price_val = float(price)
            
            # Extract numeric weight and unit
            weight_match = re.search(r'(\d+(?:\.\d+)?)\s*(kg|g|l|ml|gm)', weight.lower())
            if not weight_match:
                return None
            
            weight_num = float(weight_match.group(1))
            unit = weight_match.group(2)
            
            # Convert to kg
            if unit in ['kg', 'l']:
                weight_kg = weight_num
            elif unit in ['g', 'gm', 'ml']:
                weight_kg = weight_num / 1000.0
            else:
                return None
            
            if weight_kg <= 0:
                return None
            
            # Calculate per-kg price
            per_kg = price_val / weight_kg
            return round(per_kg, 2)
            
        except (ValueError, ZeroDivisionError):
            return None
    
    async def check_multiple_platforms(
        self, 
        platforms: List[str], 
        product_name: str,
        delay: int = 3
    ) -> List[Dict]:
        """Check prices across multiple platforms sequentially"""
        print(f"\n{'='*60}")
        print(f"🛒 GROCERY PRICE COMPARISON")
        print(f"📦 Product: {product_name}")
        print(f"🏪 Platforms: {', '.join(platforms)}")
        print(f"{'='*60}\n")
        
        all_prices = []
        
        for platform in platforms:
            price_data = await self.check_single_platform(platform, product_name)
            
            if price_data and price_data.get('price'):
                all_prices.append(price_data)
            
            await self.navigator.close_app(platform)
            
            if delay > 0 and platform != platforms[-1]:
                print(f"⏳ Waiting {delay}s before next platform...")
                await asyncio.sleep(delay)
        
        return all_prices
    
    def find_best_deal(self, price_data: List[Dict]) -> Dict:
        """Find the best deal using per-kg price when available"""
        if not price_data:
            return None
        
        valid_prices = [p for p in price_data if p.get('price')]
        
        if not valid_prices:
            return None
        
        # Sort by per-kg price if available, otherwise by absolute price
        best_deal = min(
            valid_prices,
            key=lambda x: x.get('price_per_kg') or self._extract_numeric_price(x)
        )
        
        return best_deal
    
    def _extract_numeric_price(self, item: Dict) -> float:
        """Extract numeric price from item"""
        price_str = str(item.get('price', '999999'))
        cleaned = self._clean_price(price_str)
        
        try:
            return float(cleaned) if cleaned else 999999.0
        except (ValueError, TypeError):
            return 999999.0
    
    def calculate_savings(self, price_data: List[Dict]) -> Dict:
        """
        Calculate savings using per-kg prices for fair comparison
        """
        if len(price_data) < 2:
            return {"max_savings": 0, "percentage": 0, "comparison_basis": "none"}
        
        # Try to use per-kg prices first
        per_kg_prices = [
            p.get('price_per_kg') 
            for p in price_data 
            if p.get('price_per_kg')
        ]
        
        if len(per_kg_prices) >= 2:
            # Compare using per-kg
            min_price = min(per_kg_prices)
            max_price = max(per_kg_prices)
            savings = max_price - min_price
            percentage = (savings / max_price * 100) if max_price > 0 else 0
            
            return {
                "max_savings_per_kg": round(savings, 2),
                "percentage": round(percentage, 1),
                "min_price_per_kg": min_price,
                "max_price_per_kg": max_price,
                "comparison_basis": "per_kg"
            }
        else:
            # Fallback to absolute price comparison
            valid_prices = [
                self._extract_numeric_price(p)
                for p in price_data if p.get('price')
            ]
            
            if not valid_prices:
                return {"max_savings": 0, "percentage": 0, "comparison_basis": "none"}
            
            min_price = min(valid_prices)
            max_price = max(valid_prices)
            savings = max_price - min_price
            percentage = (savings / max_price * 100) if max_price > 0 else 0
            
            return {
                "max_savings": round(savings, 2),
                "percentage": round(percentage, 1),
                "min_price": min_price,
                "max_price": max_price,
                "comparison_basis": "absolute"
            }
    
    def format_price_summary(self, price_data: List[Dict]) -> str:
        """Format price data with per-kg comparison"""
        if not price_data:
            return "❌ No prices found on any platform."
        
        # Check if we have per-kg data for fair comparison
        has_per_kg = any(p.get('price_per_kg') for p in price_data)
        
        message = "🛒 *GROCERY PRICE COMPARISON*\n"
        message += "=" * 30 + "\n"
        
        if has_per_kg:
            message += "📊 Comparing by price per kg\n"
        
        message += "\n"
        
        # Sort by per-kg price if available, otherwise absolute price
        if has_per_kg:
            sorted_data = sorted(
                price_data,
                key=lambda x: x.get('price_per_kg') or 999999.0
            )
        else:
            sorted_data = sorted(price_data, key=self._extract_numeric_price)
        
        for idx, data in enumerate(sorted_data, 1):
            platform = data.get('platform', 'Unknown')
            price = data.get('price', 'N/A')
            weight = data.get('weight')
            per_kg = data.get('price_per_kg')
            original = data.get('original_price')
            discount = data.get('discount')
            stock = data.get('in_stock', 'unknown')
            delivery = data.get('delivery_time', 'Check app')
            
            medal = "🥇" if idx == 1 else "🥈" if idx == 2 else "🥉"
            
            message += f"{medal} *{platform}*\n"
            message += f"   💰 Price: ₹{price}"
            
            if weight:
                message += f" ({weight})"
            message += "\n"
            
            # CRITICAL: Show per-kg price for comparison
            if per_kg:
                message += f"   📊 Per kg: ₹{per_kg}/kg\n"
            
            if original and str(original) != str(price):
                message += f"   🏷️ MRP: ₹{original}\n"
            
            if discount:
                message += f"   🎉 Discount: {discount}\n"
            
            message += f"   🚚 Delivery: {delivery}\n"
            
            stock_emoji = "✅" if stock == "yes" else "❌" if stock == "no" else "❓"
            message += f"   {stock_emoji} Stock: {stock.title()}\n"
            
            message += "\n"
        
        # Show savings calculation
        savings = self.calculate_savings(price_data)
        
        if savings.get('comparison_basis') == 'per_kg':
            message += f"💡 *Save ₹{savings['max_savings_per_kg']}/kg ({savings['percentage']}%)*\n"
            message += f"   by choosing the cheapest option!\n\n"
        elif savings.get('max_savings', 0) > 0:
            message += f"💡 *You can save:* ₹{savings['max_savings']} ({savings['percentage']}%)\n"
            message += f"   by choosing the cheaper option!\n\n"
            if not has_per_kg:
                message += "   ⚠️ Note: Different quantities - compare carefully!\n\n"
        
        message += "=" * 30 + "\n"
        
        return message
    
    def get_summary_stats(self, price_data: List[Dict]) -> Dict:
        """Get summary statistics"""
        if not price_data:
            return {}
        
        valid_prices = [
            self._extract_numeric_price(p)
            for p in price_data if p.get('price')
        ]
        
        # Include per-kg stats if available
        per_kg_prices = [
            p.get('price_per_kg')
            for p in price_data if p.get('price_per_kg')
        ]
        
        stats = {
            "total_platforms": len(price_data),
            "avg_price": round(sum(valid_prices) / len(valid_prices), 2) if valid_prices else 0,
            "min_price": min(valid_prices) if valid_prices else 0,
            "max_price": max(valid_prices) if valid_prices else 0,
            "best_platform": self.find_best_deal(price_data)
        }
        
        if per_kg_prices:
            stats["avg_price_per_kg"] = round(sum(per_kg_prices) / len(per_kg_prices), 2)
            stats["min_price_per_kg"] = min(per_kg_prices)
            stats["max_price_per_kg"] = max(per_kg_prices)
        
        return stats