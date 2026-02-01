#!/usr/bin/env python3
"""
AI Analyzer Module - v2.3 FIXED
Adds: Per-kg price aware recommendations
"""
import json
import re
import os
from google import genai

class AIAnalyzer:
    def __init__(self, api_key: str):
        """Initialize AI Analyzer with Gemini"""
        self.client = genai.Client(api_key=api_key)
        self.model = os.getenv('GEMINI_ANALYZER_MODEL', 'gemini-1.5-flash')
        print(f"✅ AI Analyzer initialized with model: {self.model}")
    
    def extract_product_info(self, message: str) -> dict:
        """Extract grocery product information from message"""
        print(f"\n🔍 ANALYZING MESSAGE: '{message}'")
        
        prompt = f"""You are an expert grocery product extraction assistant.

Analyze this message: "{message}"

Return ONLY a JSON object (no markdown, no backticks, no lists):
{{
    "is_product": true or false,
    "product_name": "clean product name",
    "category": "groceries",
    "brand": "brand name or null",
    "confidence": 0.0 to 1.0,
    "keywords": ["keyword1", "keyword2"],
    "quantity": "quantity if mentioned or null"
}}

Rules:
1. is_product = true ONLY if asking about buying/checking/comparing a grocery item
2. Extract minimal clean product name (e.g., "tomatoes", "milk", "onions")
3. category should always be "groceries"
4. confidence < 0.5 if message is ambiguous
5. quantity = extract if mentioned (e.g., "1kg", "500g", "2 packets")
6. Return a SINGLE object, NOT an array
7. Return valid JSON only, no markdown formatting

Examples:
- "check tomato prices" → {{"is_product": true, "product_name": "tomatoes", "category": "groceries", ...}}
- "get 2kg onions" → {{"is_product": true, "product_name": "onions", "quantity": "2kg", ...}}
- "hello" → {{"is_product": false, ...}}
"""
        
        try:
            response = self.client.models.generate_content(
                model=self.model,
                contents=prompt
            )
            
            text = response.text.strip()
            text = re.sub(r'```(?:json)?\n?', '', text).strip()
            text = text.replace('```', '').strip()
            
            product_info = json.loads(text)
            
            # Handle list response
            if isinstance(product_info, list):
                if len(product_info) > 0:
                    print(f"⚠️ Gemini returned a list - extracting first item")
                    product_info = product_info[0]
                else:
                    print(f"⚠️ Gemini returned empty list - using fallback")
                    raise ValueError("Empty list response")
            
            if not isinstance(product_info, dict):
                print(f"⚠️ Invalid response type: {type(product_info)}")
                raise ValueError("Invalid response format")
            
            # Log results
            print(f"✅ Product Detection:")
            print(f"   Is Product: {product_info.get('is_product')}")
            if product_info.get('is_product'):
                print(f"   Name: {product_info.get('product_name')}")
                print(f"   Category: {product_info.get('category')}")
                print(f"   Brand: {product_info.get('brand', 'Any')}")
                print(f"   Quantity: {product_info.get('quantity', 'Not specified')}")
                print(f"   Confidence: {product_info.get('confidence', 0)}")
            
            return product_info
            
        except Exception as e:
            print(f"❌ Error in product extraction: {e}")
            
            return {
                "is_product": True,
                "product_name": message.strip(),
                "category": "groceries",
                "brand": None,
                "confidence": 0.5,
                "quantity": None
            }
    
    def determine_platforms(self, category: str, product_name: str) -> list:
        """Determine platforms to check"""
        print(f"\n🎯 DETERMINING PLATFORMS for: {product_name}")
        platforms = ["Blinkit", "Zepto"]
        print(f"✅ Selected Platforms: {', '.join(platforms)}")
        return platforms
    
    def parse_price_data(self, raw_text: str, platform: str) -> dict:
        """Parse price information from raw text"""
        prompt = f"""Extract pricing details from this text:
"{raw_text[:1000]}"  

Return ONLY valid JSON (no markdown, no lists, single object):
{{
    "platform": "{platform}",
    "price": "numeric_value_or_null",
    "original_price": "numeric_value_or_null",
    "discount": "percentage_or_null",
    "weight": "weight_or_quantity_or_null",
    "in_stock": "yes/no/unknown",
    "product_title": "extracted_title_or_null",
    "delivery_time": "delivery_time_or_null"
}}

Rules:
- Extract actual numbers only, remove ₹ Rs symbols
- If not found, use null (not "null" string)
- discount format: "20%" or null
- weight examples: "1kg", "500g", "1L"
- delivery_time examples: "10 mins", "2 hours"
- Return single object, not array
"""
        
        try:
            response = self.client.models.generate_content(
                model=self.model,
                contents=prompt
            )
            
            text = response.text.strip()
            text = re.sub(r'```(?:json)?\n?', '', text).strip()
            text = text.replace('```', '').strip()
            
            data = json.loads(text)
            
            if isinstance(data, list):
                data = data[0] if data else {}
            
            data['platform'] = platform
            
            return data
            
        except Exception as e:
            print(f"⚠️ Parse error for {platform}: {e}")
            return {
                "platform": platform,
                "price": None,
                "original_price": None,
                "discount": None,
                "weight": None,
                "in_stock": "unknown",
                "delivery_time": None
            }
    
    def generate_recommendation(self, product_info: dict, price_data: list) -> str:
        """
        Generate buying recommendation with per-kg price awareness.
        CRITICAL: Uses per-kg prices for fair comparison when weights differ.
        """
        print(f"\n💡 GENERATING RECOMMENDATION...")
        
        # Filter valid prices
        valid_prices = [p for p in price_data if p.get('price')]
        
        if not valid_prices:
            return "⚠️ No prices available. Please check the apps manually."
        
        # Check if we have per-kg data
        has_per_kg = any(p.get('price_per_kg') for p in valid_prices)
        
        # Build detailed context for AI
        price_context = []
        for p in valid_prices:
            item = {
                "platform": p.get('platform'),
                "price": p.get('price'),
                "weight": p.get('weight', 'unknown'),
            }
            
            if p.get('price_per_kg'):
                item['price_per_kg'] = p.get('price_per_kg')
            
            if p.get('delivery_time'):
                item['delivery_time'] = p.get('delivery_time')
            
            if p.get('name'):
                item['product_name'] = p.get('name')
            
            price_context.append(item)
        
        prompt = f"""You are an expert Indian grocery shopping advisor.

Product: {product_info.get('product_name')}
Quantity Requested: {product_info.get('quantity', 'Not specified')}

Price Comparison:
{json.dumps(price_context, indent=2)}

CRITICAL INSTRUCTIONS:
1. If products have DIFFERENT WEIGHTS, you MUST use the "price_per_kg" field to compare fairly
2. NEVER recommend a product as "cheaper" based only on absolute price when weights differ
3. Calculate and mention the actual savings per kg when weights differ

Provide a friendly, accurate recommendation (100-150 words):

🏆 Best Choice: Which platform offers the best VALUE (considering price per kg if weights differ)
⏰ Delivery: Compare delivery times
💰 Savings: How much they save by choosing the best option (per kg if applicable)
💡 Smart Tip: One practical shopping tip

Use emojis, be friendly, be ACCURATE.

EXAMPLE (Different Weights):
"🏆 Zepto wins! At ₹49 for 300g (₹163/kg), it's 43% cheaper than Blinkit's ₹144 for 500g (₹288/kg). 
You'll save ₹125 per kg! ⏰ Both deliver in ~10 mins. 💡 Tip: Buy in bulk when per-kg price is good!"

Format as plain text for WhatsApp (no markdown).
"""
        
        try:
            response = self.client.models.generate_content(
                model=self.model,
                contents=prompt
            )
            
            recommendation = response.text.strip()
            print(f"✅ Recommendation generated")
            return recommendation
            
        except Exception as e:
            print(f"⚠️ Recommendation error: {e}")
            
            # Improved fallback with per-kg awareness
            try:
                if has_per_kg:
                    # Compare by per-kg price
                    best = min(valid_prices, key=lambda x: x.get('price_per_kg', 999999))
                    per_kg = best.get('price_per_kg')
                    delivery = best.get('delivery_time', 'Check app')
                    weight = best.get('weight', '')
                    
                    return (
                        f"🏆 Best deal: {best['platform']} at ₹{best['price']} ({weight})\n"
                        f"📊 That's ₹{per_kg}/kg\n"
                        f"⏰ Delivery: {delivery}\n\n"
                        f"💡 Tip: Always compare per-kg prices when weights differ!"
                    )
                else:
                    # Standard comparison
                    best = min(valid_prices, key=lambda x: float(str(x.get('price', 999999))))
                    delivery = best.get('delivery_time', 'Check app')
                    return (
                        f"🏆 Best deal: {best['platform']} at ₹{best['price']}\n"
                        f"⏰ Delivery: {delivery}\n\n"
                        f"💡 Tip: Order during non-peak hours for faster delivery!"
                    )
            except:
                return "✅ Please compare the prices above and choose the best option!"