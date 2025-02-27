"""
Automation Execution Context Module

This module defines the ExecutionContext class which provides
the runtime context for executing automation sequences.
"""

from typing import Dict, Optional, Any
from dataclasses import dataclass, field

from scout.window_manager import WindowManager
from scout.template_matcher import TemplateMatcher
from scout.text_ocr import TextOCR
from scout.actions import GameActions
from scout.automation.position import Position

@dataclass
class ExecutionContext:
    """
    Context for sequence execution.
    
    This class holds all the necessary components and state information
    needed during the execution of an automation sequence.
    
    Attributes:
        positions: Dictionary of available positions by name
        window_manager: WindowManager for coordinate conversion
        template_matcher: TemplateMatcher for image recognition
        text_ocr: TextOCR for text recognition
        game_actions: GameActions for interacting with the game
        overlay: Optional overlay for visual feedback
        debug_tab: Optional debug tab for logging
        simulation_mode: Whether to simulate actions without executing them
        step_delay: Delay between steps in seconds
        loop_enabled: Whether to loop the sequence execution
    """
    positions: Dict[str, Position]
    window_manager: WindowManager
    template_matcher: TemplateMatcher
    text_ocr: TextOCR
    game_actions: GameActions
    overlay: Optional[Any] = None
    debug_tab: Optional[Any] = None
    simulation_mode: bool = False
    step_delay: float = 0.5
    loop_enabled: bool = False
    
    # Variable store for automation sequences
    variables: Dict[str, Any] = field(default_factory=dict)
    
    # Results from the last executed action
    last_result: Optional[bool] = None
    last_message: Optional[str] = None
    last_match_position: Optional[tuple] = None
    last_match_confidence: Optional[float] = None
    last_ocr_text: Optional[str] = None
    
    def update_result(self, result: bool, message: str) -> None:
        """
        Update the last result and message.
        
        Args:
            result: Whether the action was successful
            message: Message describing the result
        """
        self.last_result = result
        self.last_message = message
    
    def update_match_result(self, position: Optional[tuple], confidence: Optional[float]) -> None:
        """
        Update the last match position and confidence.
        
        Args:
            position: Position of the match (x, y)
            confidence: Confidence of the match (0-1)
        """
        self.last_match_position = position
        self.last_match_confidence = confidence
    
    def update_ocr_result(self, text: Optional[str]) -> None:
        """
        Update the last OCR text.
        
        Args:
            text: Text extracted by OCR
        """
        self.last_ocr_text = text
    
    def get_variable(self, name: str, default: Any = None) -> Any:
        """
        Get a variable from the variable store.
        
        Args:
            name: Name of the variable
            default: Default value if variable doesn't exist
            
        Returns:
            Value of the variable or default
        """
        return self.variables.get(name, default)
    
    def set_variable(self, name: str, value: Any) -> None:
        """
        Set a variable in the variable store.
        
        Args:
            name: Name of the variable
            value: Value to set
        """
        self.variables[name] = value