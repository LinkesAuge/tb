"""
Sequence Executor

This module handles the execution of automation sequences, including:
- Step-by-step execution
- Simulation mode
- Condition checking
- Debug logging
"""

from typing import Dict, Optional, List, Callable
from dataclasses import dataclass
import time
import logging
from PyQt6.QtCore import QObject, pyqtSignal
import win32api
import win32con
from scout.automation.core import AutomationPosition, AutomationSequence
from scout.automation.actions import (
    ActionType, AutomationAction, ActionParamsCommon,
    ClickParams, DragParams, TypeParams, WaitParams,
    TemplateSearchParams, OCRWaitParams
)
from scout.window_manager import WindowManager
from scout.template_matcher import TemplateMatcher
from scout.text_ocr import TextOCR
from scout.actions import GameActions
from scout.automation.gui.debug_tab import AutomationDebugTab

logger = logging.getLogger(__name__)

def is_stop_key_pressed() -> bool:
    """Check if any stop key (Escape or Q) is pressed."""
    return (
        win32api.GetAsyncKeyState(win32con.VK_ESCAPE) & 0x8000 != 0 or  # Escape key
        win32api.GetAsyncKeyState(ord('Q')) & 0x8000 != 0  # Q key
    )

@dataclass
class ExecutionContext:
    """Context for sequence execution."""
    positions: Dict[str, AutomationPosition]
    window_manager: WindowManager
    template_matcher: TemplateMatcher
    text_ocr: TextOCR
    game_actions: GameActions
    debug_tab: Optional[AutomationDebugTab] = None
    simulation_mode: bool = False
    step_delay: float = 0.5
    loop_enabled: bool = False  # Added loop flag

class SequenceExecutor(QObject):
    """
    Handles execution of automation sequences.
    
    Features:
    - Step-by-step execution
    - Simulation mode
    - Condition checking
    - Visual feedback
    - Debug logging
    """
    
    # Signals for execution status
    step_completed = pyqtSignal(int)  # Current step index
    sequence_completed = pyqtSignal()
    execution_paused = pyqtSignal()
    execution_resumed = pyqtSignal()
    execution_error = pyqtSignal(str)  # Error message
    
    def __init__(self, context: ExecutionContext):
        """
        Initialize the sequence executor.
        
        Args:
            context: Execution context with required components
        """
        super().__init__()
        self.context = context
        
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
        
        logger.info(f"Starting execution of sequence: {sequence.name}")
        self._log_debug(f"Starting sequence: {sequence.name} (Loop: {'ON' if self.context.loop_enabled else 'OFF'})")
        
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
            
            self._log_debug(f"Executing step {self.current_step + 1}: {action.action_type.name}")
            
            # Execute or simulate the action
            if self.context.simulation_mode:
                self._simulate_action(action)
            else:
                self._execute_action(action)
                
            # Update progress
            self.step_completed.emit(self.current_step)
            self.current_step += 1
            
            # Schedule next step if not stopped
            if not self.is_paused and self.is_running:
                time.sleep(self.context.step_delay)
                self._execute_next_step()
                
        except Exception as e:
            self._handle_error(f"Failed to execute step {self.current_step + 1}: {e}")
            
    def _execute_action(self, action: AutomationAction) -> None:
        """
        Execute an action.
        
        Args:
            action: Action to execute
        """
        # Get position if needed
        position = None
        if hasattr(action.params, 'position_name') and action.params.position_name:
            position = self.context.positions.get(action.params.position_name)
            if not position:
                raise ValueError(f"Position not found: {action.params.position_name}")
                
        # Execute based on type
        if action.action_type in {ActionType.CLICK, ActionType.RIGHT_CLICK, ActionType.DOUBLE_CLICK}:
            self._execute_click(action, position)
        elif action.action_type == ActionType.DRAG:
            self._execute_drag(action, position)
        elif action.action_type == ActionType.TYPE_TEXT:
            self._execute_type(action, position)
        elif action.action_type == ActionType.WAIT:
            self._execute_wait(action)
        elif action.action_type == ActionType.TEMPLATE_SEARCH:
            self._execute_template_search(action)
        elif action.action_type == ActionType.WAIT_FOR_OCR:
            self._execute_ocr_wait(action)
            
    def _simulate_action(self, action: AutomationAction) -> None:
        """
        Simulate an action without executing it.
        
        Args:
            action: Action to simulate
        """
        # Get position if needed
        position = None
        if hasattr(action.params, 'position_name') and action.params.position_name:
            position = self.context.positions.get(action.params.position_name)
            if not position:
                raise ValueError(f"Position not found: {action.params.position_name}")
                
        # Log simulation
        if position:
            self._log_debug(
                f"[SIMULATION] Would {action.action_type.name} at "
                f"({position.x}, {position.y})"
            )
        else:
            self._log_debug(f"[SIMULATION] Would {action.action_type.name}")
            
    def _execute_click(self, action: AutomationAction, position: AutomationPosition) -> None:
        """Execute a click action."""
        if not position:
            raise ValueError("Click action requires a position")
            
        # Determine click type
        if action.action_type == ActionType.RIGHT_CLICK:
            self._log_debug(f"Right clicking at ({position.x}, {position.y})")
            self.context.game_actions.click_at(
                position.x, position.y, button='right'
            )
        elif action.action_type == ActionType.DOUBLE_CLICK:
            self._log_debug(f"Double clicking at ({position.x}, {position.y})")
            self.context.game_actions.click_at(
                position.x, position.y, clicks=2
            )
        else:
            self._log_debug(f"Clicking at ({position.x}, {position.y})")
            self.context.game_actions.click_at(
                position.x, position.y
            )
            
    def _execute_drag(self, action: AutomationAction, start_position: AutomationPosition) -> None:
        """Execute a drag action."""
        if not start_position:
            raise ValueError("Drag action requires a start position")
            
        params = action.params
        if not isinstance(params, DragParams):
            raise ValueError("Invalid parameters for drag action")
            
        end_position = self.context.positions.get(params.end_position_name)
        if not end_position:
            raise ValueError(f"End position not found: {params.end_position_name}")
            
        self._log_debug(
            f"Dragging from ({start_position.x}, {start_position.y}) "
            f"to ({end_position.x}, {end_position.y})"
        )
        self.context.game_actions.drag_mouse(
            start_position.x, start_position.y,
            end_position.x, end_position.y,
            duration=params.duration
        )
        
    def _execute_type(self, action: AutomationAction, position: Optional[AutomationPosition]) -> None:
        """Execute a type action."""
        params = action.params
        if not isinstance(params, TypeParams):
            raise ValueError("Invalid parameters for type action")
            
        if position:
            self._log_debug(f"Typing '{params.text}' at ({position.x}, {position.y})")
            self.context.game_actions.click_at(position.x, position.y)
            time.sleep(0.1)  # Wait for click to register
            
        self._log_debug(f"Typing '{params.text}'")
        self.context.game_actions.input_text(params.text)
        
    def _execute_wait(self, action: AutomationAction) -> None:
        """Execute a wait action."""
        params = action.params
        if not isinstance(params, WaitParams):
            raise ValueError("Invalid parameters for wait action")
            
        self._log_debug(f"Waiting for {params.duration} seconds")
        
        # Break wait into smaller intervals to check for stop keys
        start_time = time.time()
        while time.time() - start_time < params.duration:
            if is_stop_key_pressed():
                self._log_debug("Wait interrupted by user (Escape/Q pressed)")
                self.stop_execution()
                return
            time.sleep(0.1)  # Check every 100ms
        
    def _execute_template_search(self, action: AutomationAction) -> None:
        """Execute a template search action."""
        params = action.params
        if not isinstance(params, TemplateSearchParams):
            raise ValueError("Invalid parameters for template search action")
            
        self._log_debug(
            f"Starting template search with {len(params.templates)} templates "
            f"(Update freq: {params.update_frequency}/s, Duration: {params.duration}s)"
        )
        
        # Configure template matcher
        self.context.template_matcher.confidence = params.min_confidence
        self.context.template_matcher.target_frequency = params.update_frequency
        self.context.template_matcher.sound_enabled = params.sound_enabled
        
        # Start template matching if overlay is enabled
        if params.overlay_enabled:
            self.context.template_matcher.start_template_matching()
        
        start_time = time.time()
        try:
            while time.time() - start_time < params.duration:
                # Check for stop keys
                if is_stop_key_pressed():
                    self._log_debug("Template search interrupted by user (Escape/Q pressed)")
                    self.stop_execution()
                    return
                    
                # Take screenshot and check for templates
                screenshot = self.context.window_manager.capture_screenshot()
                if screenshot is None:
                    continue
                    
                # Use existing template matcher to find matches
                matches = self.context.template_matcher.find_all_templates(screenshot)
                if matches:
                    self._log_debug(f"Found {len(matches)} template matches")
                    
                time.sleep(1.0 / params.update_frequency)  # Control update rate
                
        finally:
            # Always stop template matching when done
            if params.overlay_enabled:
                self.context.template_matcher.stop_template_matching()
            
            self._log_debug("Template search completed")
        
    def _execute_ocr_wait(self, action: AutomationAction) -> None:
        """Execute an OCR wait action."""
        params = action.params
        if not isinstance(params, OCRWaitParams):
            raise ValueError("Invalid parameters for OCR wait action")
            
        self._log_debug(
            f"Waiting for text '{params.expected_text}' "
            f"(partial match: {params.partial_match})"
        )
        
        start_time = time.time()
        while time.time() - start_time < params.timeout:
            # Check for stop keys
            if is_stop_key_pressed():
                self._log_debug("OCR wait interrupted by user (Escape/Q pressed)")
                self.stop_execution()
                return
                
            # Take screenshot and check for text
            screenshot = self.context.window_manager.capture_screenshot()
            if screenshot is None:
                continue
                
            text = self.context.text_ocr.extract_text(screenshot)
            
            if params.partial_match:
                if params.expected_text.lower() in text.lower():
                    self._log_debug(f"Text '{params.expected_text}' found")
                    return
            else:
                if params.expected_text.lower() == text.lower():
                    self._log_debug(f"Text '{params.expected_text}' found")
                    return
                    
            time.sleep(0.1)
            
        raise TimeoutError(f"Text '{params.expected_text}' not found")
        
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