#!/usr/bin/env python3
"""
DroidRun Safe Runner - Production v2.2
Fixes: WorkflowHandler TypeError + proper cancellation
"""
import asyncio
import io
import sys
from typing import Optional, Tuple
from droidrun import DroidAgent

class DroidRunRunner:
    """
    Safe wrapper for DroidRun agent execution.
    Handles both Coroutines and WorkflowHandlers with proper cleanup.
    """
    
    def __init__(self, llm, config_fast, config_full):
        self.llm = llm
        self.config_fast = config_fast
        self.config_full = config_full
        self._lock = asyncio.Lock()
    
    async def run(
        self,
        goal: str,
        timeout_s: float,
        capture_stdout: bool = False,
        fast: bool = False,
    ) -> Tuple[Optional[str], Optional[Exception]]:
        """
        Run DroidRun agent with proper timeout and cancellation handling.
        Supports both old (coroutine) and new (WorkflowHandler) return types.
        """
        cfg = self.config_fast if fast else self.config_full
        
        async with self._lock:
            agent = DroidAgent(goal=goal, config=cfg, llms=self.llm)
            
            # Setup stdout capture
            old_stdout = sys.stdout
            buf = io.StringIO() if capture_stdout else None
            if capture_stdout:
                sys.stdout = buf
            
            # Get the process (could be coroutine or WorkflowHandler)
            process = agent.run()
            
            # Determine type and create proper task
            if asyncio.iscoroutine(process):
                # Legacy: coroutine - wrap in task
                task = asyncio.create_task(process)
                is_workflow = False
            else:
                # Modern: WorkflowHandler - use directly
                task = process
                is_workflow = True
            
            try:
                # Wait with timeout (works for both types)
                await asyncio.wait_for(task, timeout=timeout_s)
                out = buf.getvalue() if buf else None
                return out, None
                
            except asyncio.TimeoutError as e:
                print(f"⚠️ Task timed out after {timeout_s}s - cancelling safely...")
                
                # Cancel based on type
                if is_workflow and hasattr(task, 'cancel_run'):
                    try:
                        task.cancel_run()
                    except:
                        pass
                elif hasattr(task, 'cancel'):
                    task.cancel()
                
                # CRITICAL: Give it time to cleanup
                await asyncio.sleep(0.2)
                
                # Try to await cancellation
                try:
                    await asyncio.wait_for(asyncio.shield(task), timeout=1.0)
                except:
                    pass  # Already cancelled or finished
                
                out = buf.getvalue() if buf else None
                return out, e
                
            except Exception as e:
                print(f"⚠️ Agent error: {type(e).__name__}: {e}")
                
                # Cancel on any error
                if is_workflow and hasattr(task, 'cancel_run'):
                    try:
                        task.cancel_run()
                    except:
                        pass
                elif hasattr(task, 'cancel'):
                    try:
                        task.cancel()
                    except:
                        pass
                
                # Cleanup delay
                await asyncio.sleep(0.2)
                
                out = buf.getvalue() if buf else None
                return out, e
                
            finally:
                # Always restore stdout
                if capture_stdout:
                    sys.stdout = old_stdout