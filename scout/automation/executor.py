"""
Sequence Executor

This module handles the execution of automation sequences, including:
- Step-by-step execution
- Simulation mode
- Condition checking
- Debug logging
"""

from typing import Dict, Optional, List, Callable, Tuple, Any
from dataclasses import dataclass
import time
import logging
from PyQt6.QtCore import QObject, pyqtSignal
import win32api
import win32con
from scout.automation.core import AutomationPosition, AutomationSequence, ExecutionContext
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
from PyQt6.QtWidgets import QApplication
import cv2
import numpy as np

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
        
    def _execute_template_search(self, action: AutomationAction) -> bool:
        """
        Execute a template search action.
        
        Args:
            action: Template search action to execute
            
        Returns:
            bool: True if execution successful, False otherwise
        """
        params = action.params
        if not isinstance(params, TemplateSearchParams):
            raise ValueError("Invalid parameters for template search action")
            
        self._log_debug(f"Starting template search for {len(params.templates)} templates")
        
        # Get the overlay
        overlay = self.context.overlay
        if not overlay:
            error_msg = "No overlay available for template search"
            self._log_debug(f"ERROR: {error_msg}")
            raise ValueError(error_msg)
            
        # Store original overlay state
        original_overlay_active = overlay.active
        original_template_matching_active = overlay.template_matching_active
        
        # Always use the overlay's template matcher for consistency with the UI
        template_matcher = overlay.template_matcher
        
        # Store original settings
        original_confidence = template_matcher.confidence
        original_frequency = template_matcher.target_frequency
        original_sound_enabled = template_matcher.sound_enabled
        
        match_search_started = False
        
        try:
            # Set parameters for this search on the overlay's template matcher
            template_matcher.confidence = params.min_confidence
            self._log_debug(f"Setting confidence threshold to {params.min_confidence}")
            template_matcher.target_frequency = params.update_frequency
            template_matcher.sound_enabled = params.sound_enabled
            
            # Reset sound cooldown to ensure first match plays a sound
            if params.sound_enabled and hasattr(template_matcher, 'sound_manager'):
                self._log_debug("Resetting sound cooldown to ensure first match plays a sound")
                template_matcher.sound_manager.reset_cooldown()
            
            # VERIFY OVERLAY TIMER STATUS
            if hasattr(overlay, 'draw_timer'):
                self._log_debug(f"Draw timer status before starting: active={overlay.draw_timer.isActive()}, interval={overlay.draw_timer.interval()}")
            
            # FORCE OVERLAY VISIBILITY AND TIMERS
            self._log_debug("=== FORCING OVERLAY VISIBILITY AND TEMPLATE MATCHING ===")
            overlay.active = True  # Force overlay to be visible for diagnosis
            overlay.template_matching_active = True
            
            # If draw timer isn't active, start it with a short interval
            if hasattr(overlay, 'draw_timer') and not overlay.draw_timer.isActive():
                self._log_debug("Starting draw timer with 33ms interval")
                overlay.draw_timer.setInterval(33)
                overlay.draw_timer.start()
            
            # Use stored template names to filter what we're looking for
            template_names = params.templates if not params.use_all_templates else None
            self._log_debug(f"Looking for templates: {template_names if template_names else 'ALL TEMPLATES'}")
            
            # For debug logging
            template_type = "specified templates" if template_names else "all templates"
            self._log_debug(f"Will search for {template_type}")
            for i, template in enumerate(template_names or []): 
                self._log_debug(f"  Template {i+1}: {template}")
            
            # VERIFY TEMPLATES ARE LOADED
            loaded_templates = list(template_matcher.templates.keys()) if hasattr(template_matcher, 'templates') else []
            self._log_debug(f"Loaded templates: {loaded_templates}")
            
            # Clear existing matches before starting
            overlay.cached_matches = []
            overlay.match_counters = {}
            
            # DIRECT MATCHING: Take a screenshot and manually find matches
            self._log_debug("Taking initial screenshot to manually search for matches")
            initial_screenshot = self.context.window_manager.capture_screenshot()
            if initial_screenshot is not None:
                # Log screenshot dimensions
                self._log_debug(f"Screenshot dimensions: {initial_screenshot.shape}")
                
                if template_names:
                    # Manually search for specified templates
                    self._log_debug(f"Manually searching for templates: {template_names}")
                    match_tuples = []
                    
                    for template_name in template_names:
                        if template_name in template_matcher.templates:
                            self._log_debug(f"Searching for template: {template_name}")
                            template = template_matcher.templates[template_name]
                            
                            # Log template dimensions
                            self._log_debug(f"Template dimensions: {template.shape}")
                            
                            # Perform template matching directly
                            result = cv2.matchTemplate(initial_screenshot, template, cv2.TM_CCOEFF_NORMED)
                            locations = np.where(result >= params.min_confidence)
                            
                            if locations[0].size > 0:
                                self._log_debug(f"Found {locations[0].size} matches for {template_name}")
                                
                                # Get template dimensions
                                template_width = template.shape[1]
                                template_height = template.shape[0]
                                
                                # Convert matches to the format expected by the overlay
                                for y, x in zip(*locations):
                                    confidence = float(result[y, x])
                                    match_tuple = (
                                        template_name,
                                        int(x),
                                        int(y),
                                        template_width,
                                        template_height,
                                        confidence
                                    )
                                    match_tuples.append(match_tuple)
                                    self._log_debug(f"Match: {template_name} at ({int(x)}, {int(y)}) with confidence {confidence:.2f}")
                            else:
                                self._log_debug(f"No matches found for template {template_name}")
                        else:
                            self._log_debug(f"Template {template_name} not found in template_matcher.templates")
                    
                    if match_tuples:
                        self._log_debug(f"Manually found {len(match_tuples)} matches!")
                        
                        # Add matches to overlay's cache
                        overlay.cached_matches = match_tuples.copy()
                        self._log_debug(f"Updated overlay.cached_matches with {len(overlay.cached_matches)} matches")
                        
                        # FORCE A DIRECT DRAW for diagnosis
                        self._log_debug("=== FORCING DIRECT DRAW ===")
                        if hasattr(overlay, '_draw_overlay'):
                            self._log_debug("Calling _draw_overlay directly")
                            overlay._draw_overlay()
                    else:
                        self._log_debug("No matches found with direct template matching")
                
                # Fallback to regular template matching if direct matching found nothing
                if not overlay.cached_matches:
                    self._log_debug("Direct matching found no results, trying regular template matching")
                    
                    # Use find_matches method
                    if template_names:
                        self._log_debug(f"Searching for specific templates: {template_names}")
                        initial_groups = template_matcher.find_matches(initial_screenshot, template_names)
                    else:
                        self._log_debug("Searching for all templates")
                        initial_groups = template_matcher.find_matches(initial_screenshot)
                    
                    # Convert GroupedMatch objects to tuples
                    match_tuples = []
                    for group in initial_groups:
                        match_tuple = (
                            group.template_name,
                            group.bounds[0],
                            group.bounds[1],
                            group.bounds[2],
                            group.bounds[3],
                            group.confidence
                        )
                        match_tuples.append(match_tuple)
                        self._log_debug(f"Found match group: {group.template_name} at {group.bounds} with confidence {group.confidence:.2f}")
                    
                    if match_tuples:
                        # Update overlay's cache
                        overlay.cached_matches = match_tuples.copy()
                        self._log_debug(f"Updated overlay cache with {len(overlay.cached_matches)} matches")
                        
                        # FORCE A DIRECT DRAW for diagnosis
                        self._log_debug("=== FORCING DIRECT DRAW (after regular matching) ===")
                        if hasattr(overlay, '_draw_overlay'):
                            self._log_debug("Calling _draw_overlay directly")
                            overlay._draw_overlay()
                    else:
                        self._log_debug("No matches found by template matcher")
            
            # Always start template matching process, regardless of overlay visibility
            self._log_debug("Starting template matching process")
            overlay.template_matching_active = True
            
            # Start the overlay's matching process
            if hasattr(overlay, 'start_template_matching'):
                overlay.start_template_matching()
                match_search_started = True
                self._log_debug("Template matching timers started")
            
            # Log overlay state after setup
            self._log_debug(f"Overlay state: active={overlay.active}, template_matching_active={overlay.template_matching_active}")
            self._log_debug(f"Cached matches count: {len(overlay.cached_matches)}")
            
            # VERIFY TIMER STATUS AGAIN
            if hasattr(overlay, 'draw_timer'):
                self._log_debug(f"Draw timer status after setup: active={overlay.draw_timer.isActive()}, interval={overlay.draw_timer.interval()}")
            if hasattr(overlay, 'template_matching_timer'):
                self._log_debug(f"Template matching timer status: active={overlay.template_matching_timer.isActive()}, interval={overlay.template_matching_timer.interval()}")
            
            # Initialize variables to track matches
            match_count = len(overlay.cached_matches)
            check_interval = 0.5  # Check for new matches every 0.5 seconds
            last_check_time = time.time()
            
            # Wait for the specified duration, checking for matches periodically
            self._log_debug(f"Running template matching for {params.duration} seconds")
            start_time = time.time()
            
            while time.time() - start_time < params.duration:
                # Check for stop keys
                if is_stop_key_pressed():
                    self._log_debug("Template search interrupted by user (Escape/Q pressed)")
                    self.stop_execution()
                    return False
                
                # Periodically check for matches
                current_time = time.time()
                if current_time - last_check_time >= check_interval:
                    last_check_time = current_time
                    
                    # FORCE DIRECT DRAWING PERIODICALLY
                    self._log_debug(f"=== PERIODIC CHECK (elapsed: {current_time - start_time:.1f}s) ===")
                    if hasattr(overlay, '_draw_overlay'):
                        self._log_debug("Forcing overlay draw during periodic check")
                        overlay._draw_overlay()
                    
                    # Force a manual update of matches every check interval
                    if hasattr(overlay, 'template_matcher'):
                        screenshot = self.context.window_manager.capture_screenshot()
                        if screenshot is not None:
                            # Find matches directly
                            if template_names:
                                matches = []
                                for template_name in template_names:
                                    if template_name in template_matcher.templates:
                                        template = template_matcher.templates[template_name]
                                        result = cv2.matchTemplate(screenshot, template, cv2.TM_CCOEFF_NORMED)
                                        locations = np.where(result >= params.min_confidence)
                                        
                                        if locations[0].size > 0:
                                            template_width = template.shape[1]
                                            template_height = template.shape[0]
                                            
                                            for y, x in zip(*locations):
                                                confidence = float(result[y, x])
                                                match = (
                                                    template_name,
                                                    int(x),
                                                    int(y),
                                                    template_width,
                                                    template_height,
                                                    confidence
                                                )
                                                matches.append(match)
                                
                                if matches:
                                    # Update overlay's cached matches
                                    overlay.cached_matches = matches
                                    
                                    # Play sound if enabled for first match detection
                                    if len(matches) > 0 and params.sound_enabled and hasattr(template_matcher, 'sound_manager'):
                                        template_matcher.sound_manager.play_if_ready()
                                        
                                    # Log matches found
                                    self._log_debug(f"Update check found {len(matches)} matches")
                                    for i, match in enumerate(matches[:3]):  # Log first 3 matches
                                        self._log_debug(f"  Match {i+1}: {match[0]} at ({match[1]}, {match[2]}) with confidence {match[5]:.2f}")
                    
                    # Check how many matches we have in the overlay's cache
                    if hasattr(overlay, 'cached_matches'):
                        current_matches = len(overlay.cached_matches)
                        if current_matches > 0:
                            self._log_debug(f"Current match count: {current_matches}")
                            # Log the first few matches for debugging
                            for i, match in enumerate(overlay.cached_matches[:3]):
                                name, x, y, w, h, conf = match
                                self._log_debug(f"  Match {i+1}: {name} at ({x}, {y}) confidence: {conf:.2f}")
                                
                        if current_matches > match_count:
                            self._log_debug(f"Found {current_matches} template matches (up from {match_count})")
                            match_count = current_matches
                            
                            # Play sound if enabled for first match detection
                            if match_count == 1 and params.sound_enabled and hasattr(template_matcher, 'sound_manager'):
                                self._log_debug("Playing sound alert for first match detection")
                                template_matcher.sound_manager.play_if_ready()
                
                # PERIODICALLY FORCE DIRECT DRAW EVEN BETWEEN CHECKS
                if (current_time - start_time) % 2 < 0.1:  # Every ~2 seconds
                    # Force direct draw again
                    if hasattr(overlay, '_draw_overlay'):
                        self._log_debug("Forcing additional draw call")
                        overlay._draw_overlay()
                
                # Wait a short time
                time.sleep(0.1)
            
            # Report the final result
            if match_count > 0:
                self._log_debug(f"Template search completed with {match_count} matches found")
                self.context.set_last_result(True, f"Found {match_count} matches")
            else:
                self._log_debug("Template search completed with no matches found")
                self.context.set_last_result(False, "No matches found")
            
            return True
            
        except Exception as e:
            error_msg = f"Error during template search: {str(e)}"
            self._log_debug(f"ERROR: {error_msg}")
            self.context.set_last_result(False, error_msg)
            return False
            
        finally:
            # Always clean up, even if there was an error
            self._log_debug("Cleaning up after template search")
            
            # Restore template matcher settings
            template_matcher.confidence = original_confidence
            template_matcher.target_frequency = original_frequency
            template_matcher.sound_enabled = original_sound_enabled
            
            # Stop template matching if we started it
            if match_search_started and hasattr(overlay, 'stop_template_matching'):
                self._log_debug("Stopping template matching")
                overlay.stop_template_matching()
            
            # Restore overlay state to original
            overlay.active = original_overlay_active
            overlay.template_matching_active = original_template_matching_active
            
            self._log_debug("Template search cleanup completed")
        
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