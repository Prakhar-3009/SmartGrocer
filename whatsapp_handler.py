#!/usr/bin/env python3
"""
WhatsApp Handler - Production Version
Uses DroidRunRunner for safe execution, better message extraction
"""
import re
from droidrun.config_manager.config_manager import DroidrunConfig, AgentConfig, LoggingConfig
from droid_runner import DroidRunRunner

class WhatsAppHandler:
    def __init__(self, llm, max_steps=15):
        """Initialize WhatsApp Handler with safe runner"""
        self.llm = llm
        
        # Full config for WhatsApp operations
        self.config_full = DroidrunConfig(
            agent=AgentConfig(max_steps=max_steps, reasoning=True),
            logging=LoggingConfig(debug=True, save_trajectory="action", rich_text=True),
        )
        
        # Fast config for quick tasks
        self.config_fast = DroidrunConfig(
            agent=AgentConfig(max_steps=6, reasoning=False),
            logging=LoggingConfig(debug=True, save_trajectory="none", rich_text=False),
        )
        
        # Safe runner
        self.runner = DroidRunRunner(
            llm=self.llm,
            config_fast=self.config_fast,
            config_full=self.config_full
        )
        
        print("✅ WhatsApp Handler initialized with safe runner")
    
    async def open_chat(self, chat_name: str) -> bool:
        """Open WhatsApp and navigate to specific chat"""
        print(f"\n📱 Opening WhatsApp chat: '{chat_name}'...")
        
        task = (
            f'Open WhatsApp and navigate to chat "{chat_name}".\n\n'
            f'CRITICAL INSTRUCTIONS:\n'
            f'1. Open WhatsApp.\n'
            f'2. CHECK: If you are already inside a chat with someone else, CLICK THE BACK BUTTON immediately to go to the main list.\n'
            f'3. Once on the main list, click the Search icon.\n'
            f'4. Type "{chat_name}" and click their name.\n'
            f'5. If "{chat_name}" is already visible on the main list, just click it directly.\n'
        )
        
        output, err = await self.runner.run(
            goal=task,
            timeout_s=40.0,  # Increased from 30
            fast=False
        )
        
        if err:
            print(f"❌ Error opening chat: {err}")
            return False
        
        print(f"✅ Chat '{chat_name}' opened")
        return True
    
    async def read_last_message(self, chat_name: str) -> str:
        """
        Read the last message from WhatsApp chat.
        Uses output capture for reliable extraction.
        """
        print(f"\n👀 Reading last message from '{chat_name}'...")
        
        # First open the chat
        if not await self.open_chat(chat_name):
            return None
        
        task = (
            f'Look at the current WhatsApp chat.\n'
            f'Find the LAST message at the bottom of the screen.\n'
            f'Read the message text carefully.\n\n'
            f'Return ONLY the message text using this EXACT format:\n'
            f'<request_accomplished success="true">THE_MESSAGE_TEXT_HERE</request_accomplished>\n\n'
            f'Example:\n'
            f'<request_accomplished success="true">check onion prices</request_accomplished>'
        )
        
        output, err = await self.runner.run(
            goal=task,
            timeout_s=40.0,  # Increased from 30
            capture_stdout=True,
            fast=False
        )
        
        if err:
            print(f"❌ Error reading message: {err}")
            return None
        
        if not output:
            print("⚠️ No output captured")
            return None
        
        # Extract message from output
        message = self._extract_message_from_output(output)
        
        if message:
            print(f"✅ Message extracted: '{message}'")
            return message
        else:
            print("⚠️ Could not extract message from output")
            return None
    
    def _extract_message_from_output(self, output_text: str) -> str:
        """
        Extract message from captured output.
        Looks for request_accomplished tags.
        """
        if not output_text:
            return None
        
        # Pattern for request_accomplished with success="true"
        pattern = r'<request_accomplished\s+success="true">([^<]+)</request_accomplished>'
        matches = re.findall(pattern, output_text, re.DOTALL | re.IGNORECASE)
        
        if matches:
            # Take the last match
            for match in reversed(matches):
                msg = match.strip()
                
                # Clean any remaining XML tags
                msg = re.sub(r'<[^>]+>', '', msg).strip()
                
                # Validate it's a real message (not a status message)
                if (msg and 
                    len(msg) < 200 and
                    msg.lower() not in ['none', 'null', 'no message'] and
                    not any(x in msg.lower() for x in [
                        'successfully', 'opened', 'navigated', 'completed'
                    ])):
                    return msg
        
        return None
    
    async def send_message(self, chat_name: str, message: str) -> bool:
        """
        Send a message to WhatsApp chat.
        """
        print(f"\n💬 Sending message to '{chat_name}'...")
        
        # Escape quotes and truncate if too long
        safe_message = message.replace('"', '\\"').replace("'", "\\'")
        if len(safe_message) > 3000:
            safe_message = safe_message[:3000] + "\n\n... (truncated)"
            print("⚠️ Message truncated to 3000 chars")
        
        task = (
            f'Send a message in WhatsApp.\n\n'
            f'STEPS:\n'
            f'1. Make sure you are in the chat with {chat_name}. If not, open WhatsApp and click "{chat_name}".\n'
            f'2. Click the message input field at the bottom.\n'
            f'3. Type this EXACT message:\n'
            f'"""\n{safe_message}\n"""\n'
            f'4. Click the Send button (paper plane icon).\n'
            f'5. Wait 1 second for message to send.\n\n'
            f'IMPORTANT: After sending, immediately finish with:\n'
            f'<request_accomplished success="true">Message sent</request_accomplished>'
        )
        
        output, err = await self.runner.run(
            goal=task,
            timeout_s=45.0,  # Increased from 30
            fast=False
        )
        
        if err:
            print(f"❌ Error sending message: {err}")
            return False
        
        print("✅ Message sent successfully")
        return True
    
    async def go_home(self) -> bool:
        """Return to home screen"""
        print("🏠 Returning to home screen...")
        
        output, err = await self.runner.run(
            goal='Press the Home button to go to the home screen.',
            timeout_s=10.0,
            fast=True
        )
        
        return err is None