#!/usr/bin/env python3
"""
Test Setup for Smart Grocery Bot
Tests DroidRun connection with Gemini
"""
import asyncio
import os
from droidrun import DroidAgent
from droidrun.config_manager.config_manager import DroidrunConfig, AgentConfig, LoggingConfig
from llama_index.llms.google_genai import GoogleGenAI

# --- CONFIGURATION ---
GOOGLE_KEY = os.environ.get("GOOGLE_API_KEY")
if not GOOGLE_KEY:
    print("⚠️ WARNING: GOOGLE_API_KEY not found in environment")
    print("Please set it in your .env file or paste it below:")
    GOOGLE_KEY = "YOUR_API_KEY_HERE"  # Replace with your actual key for testing

async def test_basic_connection():
    """Test 1: Basic DroidRun + Gemini connection"""
    print("\n" + "="*60)
    print("TEST 1: BASIC CONNECTION TEST")
    print("="*60)

    if GOOGLE_KEY == "YOUR_API_KEY_HERE":
        print("❌ ERROR: Please set your Google API Key!")
        return False

    config = DroidrunConfig(
        agent=AgentConfig(max_steps=5, reasoning=True),
        logging=LoggingConfig(debug=True, rich_text=True),
    )

    try:
        llm = GoogleGenAI(
            model="models/gemini-2.5-pro",
            api_key=GOOGLE_KEY,
            temperature=0.0
        )
        print("✅ Gemini initialized successfully")
    except Exception as e:
        print(f"❌ Failed to initialize Gemini: {e}")
        return False

    task = 'Open the Calculator app.'
    print(f"\n🚀 Task: {task}")

    try:
        agent = DroidAgent(goal=task, config=config, llms=llm)
        result = await agent.run()
        print(f"\n✅ TEST PASSED! Result: {result}")
        return True
    except Exception as e:
        print(f"\n❌ TEST FAILED: {e}")
        return False

async def test_whatsapp_open():
    """Test 2: Open WhatsApp using DroidRun"""
    print("\n" + "="*60)
    print("TEST 2: WHATSAPP OPENING TEST")
    print("="*60)

    config = DroidrunConfig(
        agent=AgentConfig(max_steps=8, reasoning=True),
        logging=LoggingConfig(debug=True, rich_text=True),
    )

    try:
        llm = GoogleGenAI(
            model="models/gemini-2.5-pro",
            api_key=GOOGLE_KEY,
            temperature=0.0
        )
    except Exception as e:
        print(f"❌ Failed to initialize Gemini: {e}")
        return False

    task = (
        'Open the WhatsApp application. '
        'Wait for it to load completely. '
        'Report what you see on the screen.'
    )
    
    print(f"\n🚀 Task: {task}")

    try:
        agent = DroidAgent(goal=task, config=config, llms=llm)
        result = await agent.run()
        print(f"\n✅ TEST PASSED! WhatsApp opened.")
        print(f"Result: {result}")
        return True
    except Exception as e:
        print(f"\n❌ TEST FAILED: {e}")
        return False

async def test_grocery_app_open():
    """Test 3: Open Blinkit or Zepto"""
    print("\n" + "="*60)
    print("TEST 3: GROCERY APP OPENING TEST")
    print("="*60)

    config = DroidrunConfig(
        agent=AgentConfig(max_steps=10, reasoning=True),
        logging=LoggingConfig(debug=True, rich_text=True),
    )

    try:
        llm = GoogleGenAI(
            model="models/gemini-2.5-pro",
            api_key=GOOGLE_KEY,
            temperature=0.0
        )
    except Exception as e:
        print(f"❌ Failed to initialize Gemini: {e}")
        return False

    # Try Blinkit first, then Zepto if Blinkit fails
    apps_to_test = ["Blinkit", "Zepto"]
    
    for app in apps_to_test:
        print(f"\n🛒 Testing {app}...")
        
        task = (
            f'Open the {app} application. '
            f'Wait for it to load. '
            f'If there are any permission popups, allow them. '
            f'If there is a location prompt, select any location or allow current location. '
            f'Report what you see.'
        )
        
        try:
            agent = DroidAgent(goal=task, config=config, llms=llm)
            result = await agent.run()
            print(f"\n✅ {app} TEST PASSED!")
            print(f"Result: {result}")
            return True
        except Exception as e:
            print(f"\n⚠️ {app} failed, trying next app...")
            continue
    
    print("\n❌ All grocery apps failed to open")
    return False

async def run_all_tests():
    """Run all tests sequentially"""
    print("\n" + "🧪" * 30)
    print("SMART GROCERY BOT - TEST SUITE")
    print("🧪" * 30)
    
    results = {}
    
    # Test 1: Basic connection
    results['basic'] = await test_basic_connection()
    await asyncio.sleep(2)
    
    # Test 2: WhatsApp
    results['whatsapp'] = await test_whatsapp_open()
    await asyncio.sleep(2)
    
    # Test 3: Grocery apps
    results['grocery'] = await test_grocery_app_open()
    
    # Summary
    print("\n" + "="*60)
    print("TEST SUMMARY")
    print("="*60)
    print(f"Basic Connection: {'✅ PASS' if results['basic'] else '❌ FAIL'}")
    print(f"WhatsApp Opening: {'✅ PASS' if results['whatsapp'] else '❌ FAIL'}")
    print(f"Grocery App: {'✅ PASS' if results['grocery'] else '❌ FAIL'}")
    print("="*60)
    
    if all(results.values()):
        print("\n🎉 ALL TESTS PASSED! Bot is ready to use.")
    else:
        print("\n⚠️ Some tests failed. Please check the errors above.")

if __name__ == "__main__":
    asyncio.run(run_all_tests())