"""
Sequence Executor

This module handles the execution of automation sequences, including:
- Step-by-step execution
- Simulation mode
- Execution flow control
- Debug logging
"""

from typing import Dict, Optional, List, Callable, Tuple, Any
import time
import logging
from PyQt6.QtCore import QObject, pyqtSignal
import win32api
import win32con

from scout.automation.core import ExecutionContext
from scout.automation.sequence import AutomationSequence
from scout.automation.position import Position
from scout.automation.actions import (
    ActionType, AutomationAction, ActionParamsCommon
)
from scout.automation.action_executor import ActionExecutor

logger = logging.getLogger(__name__)

def is_stop_key_pressed() -> bool:
    """Check if any stop key (Escape or Q) is pressed."""
    return (
        win32api.GetAsyncKeyState(win32con.VK_ESCAPE) & 0x8000 != 0 or  # Escape key
        win32api.GetAsyncKeyState(ord('Q')) & 0x8000 != 0  # Q key
    )

class SequenceExecutor(QObject):
    """
    Handles execution of automation sequences.
    
    Features:
    - Step-by-step execution
    - Simulation mode
    - Execution flow control
    - Debug logging
    """
    
    # Signals for execution status
    step_completed = pyqtSignal(int)  # Current step index
    sequence_completed = pyqtSignal()
    execution_completed = pyqtSignal()  # Same as sequence_completed, for MainWindow compatibility
    execution_paused = pyqtSignal()
    execution_resumed = pyqtSignal()
    execution_error = pyqtSignal(str)  # Error message
    execution_progress = pyqtSignal(int, int)  # Current step, total steps
    execution_started = pyqtSignal(str)  # Sequence name
    
    def __init__(self, context: ExecutionContext):
        """
        Initialize the sequence executor.
        
        Args:
            context: Execution context with required components
        """
        super().__init__()
        self.context = context
        
        # Create action executor
        self.action_executor = ActionExecutor(context, self._log_debug)
        
        # Execution state
        self.current_sequence: Optional[AutomationSequence] = None
        self.current_step = 0
        self.is_paused = False
        self.is_running = False
        
    def execute_sequence(self, sequence: AutomationSequence) -> None:
        """
        Start executing a sequence.
        
        Args:
            sequence: Sequence to execute
        """
        if self.is_running:
            logger.warning("Cannot start execution while already running")
            return
            
        self.current_sequence = sequence
        self.current_step = 0
        self.is_running = True
        self.is_paused = False
        
        # Reset action executor state
        self.action_executor.reset_state()
        
        logger.info(f"Starting execution of sequence: {sequence.name}")
        self._log_debug(f"Starting sequence: {sequence.name} (Loop: {'ON' if self.context.loop_enabled else 'OFF'})")
        
        # Emit signal that execution has started
        self.execution_started.emit(sequence.name)
        
        try:
            self._execute_next_step()
        except Exception as e:
            self._handle_error(f"Failed to start sequence: {e}")
            
    def pause_execution(self) -> None:
        """Pause sequence execution."""
        if not self.is_running:
            return
            
        self.is_paused = True
        self._log_debug("Execution paused")
        self.execution_paused.emit()
        
    def resume_execution(self) -> None:
        """Resume sequence execution."""
        if not self.is_running or not self.is_paused:
            return
            
        self.is_paused = False
        self._log_debug("Execution resumed")
        self.execution_resumed.emit()
        self._execute_next_step()
        
    def step_execution(self) -> None:
        """Execute a single step while paused."""
        if not self.is_running or not self.is_paused:
            return
            
        self._execute_next_step()
        
    def stop_execution(self) -> None:
        """Stop sequence execution."""
        if not self.is_running:
            return
            
        self.is_running = False
        self.is_paused = False
        self.current_sequence = None
        self.current_step = 0
        self._log_debug("Execution stopped")
        
    def _execute_next_step(self) -> None:
        """Execute the next step in the sequence."""
        if not self.is_running or not self.current_sequence:
            return
            
        if self.is_paused:
            return
            
        # Check for stop keys
        if is_stop_key_pressed():
            self._log_debug("Sequence stopped by user (Escape/Q pressed)")
            self.stop_execution()
            return
            
        if self.current_step >= len(self.current_sequence.actions):
            self._complete_sequence()
            return
            
        try:
            action_data = self.current_sequence.actions[self.current_step]
            action = AutomationAction.from_dict(action_data)
            
            # Skip disabled actions
            if not action.params.enabled:
                self._log_debug(f"Skipping disabled step {self.current_step + 1}: {action.action_type.name}")
                self.current_step += 1
                self._execute_next_step()
                return
                
            self._log_debug(f"Executing step {self.current_step + 1}: {action.action_type.name}")
            
            # Execute or simulate the action
            if self.context.simulation_mode:
                self.action_executor.simulate_action(action)
            else:
                self.action_executor.execute_action(action)
                
            # Update progress
            self.step_completed.emit(self.current_step)
            self.execution_progress.emit(self.current_step + 1, len(self.current_sequence.actions))
            self.current_step += 1
            
            # Schedule next step if not stopped
            if not self.is_paused and self.is_running:
                time.sleep(self.context.step_delay)
                self._execute_next_step()
                
        except Exception as e:
            self._handle_error(f"Failed to execute step {self.current_step + 1}: {e}")
            
    def _complete_sequence(self) -> None:
        """Handle sequence completion."""
        if self.context.loop_enabled and self.is_running:
            # Reset step counter and continue execution
            self.current_step = 0
            self._log_debug("Sequence completed - restarting due to loop enabled")
            time.sleep(self.context.step_delay)  # Add delay between loops
            self._execute_next_step()
        else:
            # Normal completion
            self.is_running = False
            self._log_debug("Sequence completed")
            self.sequence_completed.emit()
        
    def _handle_error(self, message: str) -> None:
        """Handle execution error."""
        self.is_running = False
        logger.error(message)
        self._log_debug(f"ERROR: {message}")
        self.execution_error.emit(message)
        
    def _log_debug(self, message: str) -> None:
        """Log a debug message."""
        if self.context.debug_tab:
            self.context.debug_tab.add_log_message(message)
        logger.debug(message)
        
    def get_last_match_position(self) -> Optional[Tuple[int, int]]:
        """Get the position of the last template match."""
        return self.action_executor.last_match_position
        
    def get_last_ocr_result(self) -> Optional[str]:
        """Get the result of the last OCR operation."""
        return self.action_executor.last_ocr_result
        
    def get_last_action_result(self) -> bool:
        """Get the result of the last action execution."""
        return self.action_executor.last_action_result
