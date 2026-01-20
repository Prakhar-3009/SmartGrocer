#!/usr/bin/env python3
"""
WhatsApp Handler - WORKING SOLUTION
Captures logging output to extract the response
"""
import re
import io
import sys
import logging
from contextlib import redirect_stdout, redirect_stderr
from droidrun import DroidAgent
from droidrun.config_manager.config_manager import DroidrunConfig, AgentConfig, LoggingConfig

class WhatsAppHandler:
    def __init__(self, llm, max_steps=15):
        self.llm = llm
        self.config = DroidrunConfig(
            agent=AgentConfig(max_steps=max_steps, reasoning=True),
            logging=LoggingConfig(debug=True, save_trajectory="action", rich_text=True),
        )
        print("✅ WhatsApp Handler initialized (Logging Capture Mode)")
    
    async def open_chat(self, chat_name: str) -> bool:
        print(f"\n📱 Opening WhatsApp chat: '{chat_name}'...")
        task = (
            f'1. Open WhatsApp.\n'
            f'2. Click Search. Type "{chat_name}".\n'
            f'3. Click the chat named "{chat_name}".\n'
            f'4. Wait for chat to open.'
        )
        try:
            agent = DroidAgent(goal=task, config=self.config, llms=self.llm)
            await agent.run()
            return True
        except:
            return False
    
    async def read_last_message(self, chat_name: str) -> str:
        print(f"\n👀 Reading real message from '{chat_name}'...")
        
        if not await self.open_chat(chat_name): 
            return None
        
        task = (
            f'Look at the WhatsApp chat.\n'
            f'Find the LAST message at the bottom.\n'
            f'Return ONLY the message text in request_accomplished.\n'
            f'Example: <request_accomplished success="true">buy milk</request_accomplished>'
        )
        
        try:
            # SOLUTION: Capture all output during agent.run()
            captured_output = io.StringIO()
            
            # Create agent
            agent = DroidAgent(goal=task, config=self.config, llms=self.llm)
            
            # Capture stdout (where logging goes)
            old_stdout = sys.stdout
            sys.stdout = captured_output
            
            try:
                # Run agent
                await agent.run()
            finally:
                # Restore stdout
                sys.stdout = old_stdout
            
            # Get captured text
            output_text = captured_output.getvalue()
            
            print(f"📋 Captured {len(output_text)} chars of output")
            
            # Extract message from captured output
            message = self._extract_message_from_output(output_text)
            
            if message:
                print(f"✅ Message Extracted: '{message}'")
                return message
            else:
                print("⚠️ Could not extract message from output")
                # Debug: print part of output
                print(f"Output sample: {output_text[-500:]}")
                return None
            
        except Exception as e:
            print(f"❌ Error reading message: {e}")
            import traceback
            traceback.print_exc()
            return None

    def _extract_message_from_output(self, output_text: str) -> str:
        """
        Extract message from the captured logging output
        The Manager response contains: <request_accomplished success="true">MESSAGE</request_accomplished>
        """
        if not output_text:
            return None
        
        # Look for all request_accomplished tags in output
        pattern = r'<request_accomplished\s+success="true">([^<]+)</request_accomplished>'
        matches = re.findall(pattern, output_text, re.DOTALL)
        
        if matches:
            # Take the LAST match (most recent)
            for match in reversed(matches):
                msg = match.strip()
                
                # Clean any XML tags inside
                msg = re.sub(r'<[^>]+>', '', msg).strip()
                
                # Validate it's a real message
                if (msg and 
                    len(msg) < 200 and 
                    msg.lower() not in [
                        'none', 
                        'no message found', 
                        'null',
                        'i have successfully',
                        'the chat with',
                        'i have',
                    ]):
                    # Filter out status messages
                    if not any(x in msg.lower() for x in [
                        'successfully', 'opened', 'navigated', 'complete'
                    ]):
                        print(f"✅ Found valid message: '{msg}'")
                        return msg
        
        # Fallback: look for other patterns
        alt_patterns = [
            r'Manager response.*?<request_accomplished[^>]*>([^<]+)</request_accomplished>',
            r'📋 Manager response:.*?<request_accomplished[^>]*>([^<]+)</request_accomplished>',
        ]
        
        for pattern in alt_patterns:
            matches = re.findall(pattern, output_text, re.DOTALL | re.IGNORECASE)
            if matches:
                for match in reversed(matches):
                    msg = re.sub(r'<[^>]+>', '', match).strip()
                    if msg and len(msg) < 200:
                        return msg
        
        return None

    async def send_message(self, chat_name: str, message: str) -> bool:
        print(f"\n💬 Sending reply...")
        
        safe_message = message.replace('"', '\\"')
        
        task = (
            f'1. In WhatsApp chat with {chat_name}.\n'
            f'2. Click message input box.\n'
            f'3. Type: "{safe_message}"\n'
            f'4. Click Send button.'
        )
        try:
            agent = DroidAgent(goal=task, config=self.config, llms=self.llm)
            await agent.run()
            print("✅ Message sent")
            return True
        except Exception as e:
            print(f"❌ Send error: {e}")
            return False

    async def go_home(self):
        try:
            agent = DroidAgent(goal='Press Home button', 
                             config=self.config, llms=self.llm)
            await agent.run()
        except: 
            pass