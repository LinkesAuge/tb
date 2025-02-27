"""
Visual Action Handlers

This module implements handlers for vision-based automation actions:
- Template Search (image recognition)
- OCR Wait (text recognition)

These handlers use computer vision techniques to interact with the game
based on visual elements rather than fixed coordinates.
"""

import time
import logging
from typing import Dict, Optional, List, Callable, Tuple, Any, Union
import re
import numpy as np

from scout.automation.core import ExecutionContext
from scout.automation.actions import (
    ActionType, AutomationAction, ActionParamsCommon,
    TemplateSearchParams, OCRWaitParams
)

logger = logging.getLogger(__name__)

class VisualActionHandlers:
    """
    Handlers for vision-based automation actions like template matching and OCR.
    """
    
    def __init__(self, context: ExecutionContext, log_callback: Callable[[str], None]):
        """
        Initialize the visual action handlers.
        
        Args:
            context: Execution context with required components
            log_callback: Function to call for debug logging
        """
        self.context = context
        self.log_callback = log_callback
        self.variable_pattern = re.compile(r'\${([^}]+)}')
    
    def handle_template_search(self, params: TemplateSearchParams, simulate: bool, 
                              variable_store: Optional[Dict[str, Any]] = None) -> bool:
        """
        Handle a template search action.
        
        Args:
            params: Template search parameters
            simulate: Whether to simulate the action
            variable_store: Store for variables (for storing results)
            
        Returns:
            True if the template was found, False otherwise
        """
        try:
            template_name = params.template_name
            search_region = params.search_region
            match_threshold = params.match_threshold
            max_matches = params.max_matches
            store_variable = params.store_variable
            
            # Log the action
            self.log_callback(
                f"{'Simulating' if simulate else 'Executing'} template search for '{template_name}' "
                f"(threshold: {match_threshold}, max matches: {max_matches})"
            )
            
            if not self.context.template_matcher:
                self.log_callback("No template matcher available")
                return False
                
            if not self.context.screen_capture:
                self.log_callback("No screen capture available")
                return False
            
            # In simulation mode, we don't actually perform the search
            if simulate:
                self.log_callback("Simulation: Assuming template would be found")
                return True
                
            # Capture the current screen
            screenshot = self.context.screen_capture.capture()
            if screenshot is None:
                self.log_callback("Failed to capture screen")
                return False
                
            # Define search region if specified
            region = None
            if search_region:
                region = (
                    search_region.get('x', 0),
                    search_region.get('y', 0),
                    search_region.get('width', screenshot.shape[1]),
                    search_region.get('height', screenshot.shape[0])
                )
                
            # Perform the template search
            matches = self.context.template_matcher.find_template(
                screenshot, 
                template_name,
                threshold=match_threshold,
                max_matches=max_matches,
                region=region
            )
            
            # Log the results
            match_count = len(matches) if matches else 0
            self.log_callback(f"Found {match_count} matches for template '{template_name}'")
            
            # Store results in variable if requested
            if store_variable and variable_store is not None and matches:
                variable_store[store_variable] = matches
                self.log_callback(f"Stored {match_count} matches in variable '${store_variable}'")
            
            # Add delay if specified
            if params.delay_after > 0:
                time.sleep(params.delay_after / 1000.0)  # Convert to seconds
                self.log_callback(f"Delayed for {params.delay_after}ms")
            
            # Return success if at least one match was found
            return match_count > 0
            
        except Exception as e:
            logger.exception(f"Error in template search action: {e}")
            self.log_callback(f"Template search action failed: {e}")
            return False
    
    def handle_ocr_wait(self, params: OCRWaitParams, simulate: bool,
                       variable_store: Optional[Dict[str, Any]] = None) -> bool:
        """
        Handle an OCR wait action.
        
        Args:
            params: OCR wait parameters
            simulate: Whether to simulate the action
            variable_store: Store for variables (for storing results)
            
        Returns:
            True if the text was found within the timeout, False otherwise
        """
        try:
            text_to_find = params.text
            search_region = params.search_region
            timeout_ms = params.timeout_ms
            case_sensitive = params.case_sensitive
            store_variable = params.store_variable
            
            # Replace variables in text if variable store is provided
            if variable_store:
                text_to_find = self._replace_variables(text_to_find, variable_store)
            
            # Log the action
            self.log_callback(
                f"{'Simulating' if simulate else 'Executing'} OCR wait for text: '{text_to_find}' "
                f"(timeout: {timeout_ms}ms, case sensitive: {case_sensitive})"
            )
            
            if not self.context.ocr_engine:
                self.log_callback("No OCR engine available")
                return False
                
            if not self.context.screen_capture:
                self.log_callback("No screen capture available")
                return False
            
            # In simulation mode, we don't actually perform the OCR
            if simulate:
                self.log_callback("Simulation: Assuming text would be found")
                return True
                
            # Calculate end time for timeout
            end_time = time.time() + (timeout_ms / 1000.0)
            
            # Keep trying until timeout
            while time.time() < end_time:
                # Capture the current screen
                screenshot = self.context.screen_capture.capture()
                if screenshot is None:
                    self.log_callback("Failed to capture screen")
                    time.sleep(0.1)  # Short delay before retry
                    continue
                    
                # Define search region if specified
                region = None
                if search_region:
                    region = (
                        search_region.get('x', 0),
                        search_region.get('y', 0),
                        search_region.get('width', screenshot.shape[1]),
                        search_region.get('height', screenshot.shape[0])
                    )
                    
                # Perform OCR on the region
                ocr_result = self.context.ocr_engine.extract_text(
                    screenshot, 
                    region=region
                )
                
                # Check if the text is found
                if not case_sensitive:
                    ocr_result = ocr_result.lower()
                    text_to_find = text_to_find.lower()
                    
                if text_to_find in ocr_result:
                    self.log_callback(f"Found text '{text_to_find}' in OCR result")
                    
                    # Store results in variable if requested
                    if store_variable and variable_store is not None:
                        variable_store[store_variable] = ocr_result
                        self.log_callback(f"Stored OCR result in variable '${store_variable}'")
                    
                    # Add delay if specified
                    if params.delay_after > 0:
                        time.sleep(params.delay_after / 1000.0)  # Convert to seconds
                        self.log_callback(f"Delayed for {params.delay_after}ms")
                        
                    return True
                
                # Short delay before next attempt
                time.sleep(0.2)
                
            # Timeout reached without finding the text
            self.log_callback(f"Timeout reached without finding text '{text_to_find}'")
            return False
            
        except Exception as e:
            logger.exception(f"Error in OCR wait action: {e}")
            self.log_callback(f"OCR wait action failed: {e}")
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