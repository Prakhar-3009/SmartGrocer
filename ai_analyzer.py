#!/usr/bin/env python3
"""
AI Analyzer Module
Robustly handles List vs Object responses from Gemini AND determines platforms.
"""
import json
import re
from google import genai

class AIAnalyzer:
    def __init__(self, api_key: str):
        self.client = genai.Client(api_key=api_key)
        # Use flash for speed, or flash-exp if you have access
        self.model = 'gemini-2.0-flash-exp' 
    
    def extract_product_info(self, message: str) -> dict:
        print(f"\n🔍 ANALYZING MESSAGE: '{message}'")
        
        # PROMPT: Ask for a single primary product
        prompt = f"""Analyze this shopping message: "{message}"
        
        Identify the MAIN product to search for.
        Return ONLY a JSON object (no markdown, no lists).
        Format:
        {{
            "is_product": true,
            "product_name": "clean name",
            "category": "groceries",
            "quantity": "e.g. 500g"
        }}
        """
        
        try:
            response = self.client.models.generate_content(
                model=self.model,
                contents=prompt
            )
            
            # Clean up response 
            text = re.sub(r'```(?:json)?', '', response.text).replace('```', '').strip()
            
            # Parse JSON
            data = json.loads(text)
            
            # --- CRITICAL FIX: Handle List vs Dict ---
            if isinstance(data, list):
                print(f"⚠️ Gemini returned a list. Using the first item: {data[0]['product_name']}")
                data = data[0]
            # -----------------------------------------
            
            return data
            
        except Exception as e:
            print(f"❌ Product extraction error: {e}")
            # Fallback
            return {
                "is_product": True, 
                "product_name": message, 
                "category": "groceries"
            }

    def determine_platforms(self, category: str, product_name: str) -> list:
        """
        Decides which apps to open.
        """
        print(f"\n🎯 DETERMINING PLATFORMS for: {product_name}")
        # For this demo, we strictly return Blinkit and Zepto
        platforms = ["Blinkit", "Zepto"]
        print(f"✅ Selected Platforms: {', '.join(platforms)}")
        return platforms

    def parse_price_data(self, raw_text: str, platform: str) -> dict:
        """
        Extracts price from raw text log
        """
        prompt = f"""Extract price data from this raw text log:
        "{raw_text}"
        
        Return JSON: {{ "price": "number only", "weight": "quantity", "name": "product name" }}
        If not found, return {{ "price": null }}
        """
        try:
            response = self.client.models.generate_content(
                model=self.model, contents=prompt
            )
            text = re.sub(r'```(?:json)?', '', response.text).replace('```', '').strip()
            data = json.loads(text)
            
            if isinstance(data, list): data = data[0]
            
            data['platform'] = platform
            return data
        except:
            return {"price": None, "platform": platform}

    def generate_recommendation(self, product_info: dict, price_data: list) -> str:
        return "Compare the prices above and choose the best deal! 🛒"