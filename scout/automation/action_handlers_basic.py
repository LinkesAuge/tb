"""
Basic Action Handlers

This module implements handlers for basic automation actions:
- Click
- Drag
- Type
- Wait
"""

import time
import logging
from typing import Dict, Optional, List, Callable, Tuple, Any, Union
import re

from scout.automation.core import ExecutionContext
from scout.automation.actions import (
    ActionType, AutomationAction, ActionParamsCommon,
    ClickParams, DragParams, TypeParams, WaitParams
)

logger = logging.getLogger(__name__)

class BasicActionHandlers:
    """
    Handlers for basic automation actions like click, drag, type, and wait.
    """
    
    def __init__(self, context: ExecutionContext, log_callback: Callable[[str], None]):
        """
        Initialize the basic action handlers.
        
        Args:
            context: Execution context with required components
            log_callback: Function to call for debug logging
        """
        self.context = context
        self.log_callback = log_callback
        self.variable_pattern = re.compile(r'\${([^}]+)}')
    
    def handle_click(self, params: ClickParams, simulate: bool) -> bool:
        """
        Handle a click action.
        
        Args:
            params: Click action parameters
            simulate: Whether to simulate the action
            
        Returns:
            True if the action was successful, False otherwise
        """
        try:
            x, y = params.x, params.y
            
            # Log the action
            self.log_callback(f"{'Simulating' if simulate else 'Executing'} click at ({x}, {y})")
            
            if not simulate:
                # Perform the actual click
                if self.context.input_controller:
                    self.context.input_controller.click(x, y)
                else:
                    self.log_callback("No input controller available")
                    return False
            
            # Add delay if specified
            if params.delay_after > 0:
                if not simulate:
                    time.sleep(params.delay_after / 1000.0)  # Convert to seconds
                self.log_callback(f"Delayed for {params.delay_after}ms")
            
            return True
            
        except Exception as e:
            logger.exception(f"Error in click action: {e}")
            self.log_callback(f"Click action failed: {e}")
            return False
    
    def handle_drag(self, params: DragParams, simulate: bool) -> bool:
        """
        Handle a drag action.
        
        Args:
            params: Drag action parameters
            simulate: Whether to simulate the action
            
        Returns:
            True if the action was successful, False otherwise
        """
        try:
            start_x, start_y = params.start_x, params.start_y
            end_x, end_y = params.end_x, params.end_y
            duration_ms = params.duration_ms
            
            # Log the action
            self.log_callback(
                f"{'Simulating' if simulate else 'Executing'} drag from "
                f"({start_x}, {start_y}) to ({end_x}, {end_y}) over {duration_ms}ms"
            )
            
            if not simulate:
                # Perform the actual drag
                if self.context.input_controller:
                    self.context.input_controller.drag(
                        start_x, start_y, 
                        end_x, end_y, 
                        duration_ms / 1000.0  # Convert to seconds
                    )
                else:
                    self.log_callback("No input controller available")
                    return False
            
            # Add delay if specified
            if params.delay_after > 0:
                if not simulate:
                    time.sleep(params.delay_after / 1000.0)  # Convert to seconds
                self.log_callback(f"Delayed for {params.delay_after}ms")
            
            return True
            
        except Exception as e:
            logger.exception(f"Error in drag action: {e}")
            self.log_callback(f"Drag action failed: {e}")
            return False
    
    def handle_type(self, params: TypeParams, simulate: bool, variable_store: Dict[str, Any] = None) -> bool:
        """
        Handle a type action.
        
        Args:
            params: Type action parameters
            simulate: Whether to simulate the action
            variable_store: Store of variables for text replacement
            
        Returns:
            True if the action was successful, False otherwise
        """
        try:
            text = params.text
            
            # Replace variables in text if variable store is provided
            if variable_store:
                text = self._replace_variables(text, variable_store)
            
            # Log the action
            self.log_callback(f"{'Simulating' if simulate else 'Executing'} type: '{text}'")
            
            if not simulate:
                # Perform the actual typing
                if self.context.input_controller:
                    self.context.input_controller.type_text(text)
                else:
                    self.log_callback("No input controller available")
                    return False
            
            # Add delay if specified
            if params.delay_after > 0:
                if not simulate:
                    time.sleep(params.delay_after / 1000.0)  # Convert to seconds
                self.log_callback(f"Delayed for {params.delay_after}ms")
            
            return True
            
        except Exception as e:
            logger.exception(f"Error in type action: {e}")
            self.log_callback(f"Type action failed: {e}")
            return False
    
    def handle_wait(self, params: WaitParams, simulate: bool) -> bool:
        """
        Handle a wait action.
        
        Args:
            params: Wait action parameters
            simulate: Whether to simulate the action
            
        Returns:
            True if the action was successful, False otherwise
        """
        try:
            duration_ms = params.duration_ms
            
            # Log the action
            self.log_callback(f"{'Simulating' if simulate else 'Executing'} wait for {duration_ms}ms")
            
            if not simulate:
                # Perform the actual wait
                time.sleep(duration_ms / 1000.0)  # Convert to seconds
            
            return True
            
        except Exception as e:
            logger.exception(f"Error in wait action: {e}")
            self.log_callback(f"Wait action failed: {e}")
            return False
    
    def _replace_variables(self, text: str, variable_store: Dict[str, Any]) -> str:
        """
        Replace variables in text with their values from the variable store.
        
        Args:
            text: Text containing variables in the format ${variable_name}
            variable_store: Dictionary of variable names to values
            
        Returns:
            Text with variables replaced by their values
        """
        def replace_match(match):
            var_name = match.group(1)
            if var_name in variable_store:
                return str(variable_store[var_name])
            return match.group(0)  # Keep original if variable not found
        
        return self.variable_pattern.sub(replace_match, text)