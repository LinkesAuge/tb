"""
Game Actions Controller

This module provides a centralized interface for all mouse and keyboard interactions
with the Total Battle game. It handles:
- Mouse movement and clicking
- Text input and deletion
- Coordinate input
- Window-relative positioning

The actions are designed to work with both the browser and standalone versions of the game,
taking into account DPI scaling and window positioning.
"""

from typing import Tuple, Optional
import pyautogui
import pydirectinput
from time import sleep
import logging
from scout.window_manager import WindowManager
from scout.config_manager import ConfigManager

logger = logging.getLogger(__name__)

class GameActions:
    """
    Handles all mouse and keyboard interactions with the Total Battle game.
    
    This class provides methods for:
    - Moving the mouse to specific coordinates
    - Clicking on game elements
    - Entering text into input fields
    - Clearing text fields
    - Converting between screen and window coordinates
    
    The class automatically handles:
    - DPI scaling
    - Window positioning
    - Input timing and delays
    - Error handling and logging
    """
    
    def __init__(self, window_manager: WindowManager):
        """
        Initialize the GameActions controller.
        
        Args:
            window_manager: WindowManager instance for window tracking and coordinate conversion
        """
        self.window_manager = window_manager
        self.config_manager = ConfigManager()
        
        # Configure pyautogui
        pyautogui.PAUSE = 0.1  # Add small delay between actions
        pyautogui.FAILSAFE = True  # Enable failsafe corner
        
        # Default delays (can be adjusted)
        self.click_delay = 0.2
        self.type_delay = 0.1
        self.move_delay = 0.5
        
    def move_mouse_to(self, x: int, y: int, relative_to_window: bool = True) -> None:
        """
        Move the mouse cursor to specified coordinates.
        
        Args:
            x: X coordinate to move to
            y: Y coordinate to move to
            relative_to_window: If True, coordinates are relative to game window
        """
        try:
            if relative_to_window:
                # Convert window-relative to screen coordinates
                screen_x, screen_y = self.window_manager.client_to_screen(x, y)
            else:
                screen_x, screen_y = x, y
                
            logger.debug(f"Moving mouse to screen coordinates: ({screen_x}, {screen_y})")
            pyautogui.moveTo(screen_x, screen_y)
            
        except Exception as e:
            logger.error(f"Failed to move mouse: {e}", exc_info=True)
            
    def click_at(self, x: int, y: int, relative_to_window: bool = True, 
                button: str = 'left', clicks: int = 1) -> None:
        """
        Click at specified coordinates.
        
        Args:
            x: X coordinate to click at
            y: Y coordinate to click at
            relative_to_window: If True, coordinates are relative to game window
            button: Mouse button to click ('left', 'right', 'middle')
            clicks: Number of clicks to perform
        """
        try:
            self.move_mouse_to(x, y, relative_to_window)
            sleep(self.click_delay)
            pyautogui.click(button=button, clicks=clicks)
            
        except Exception as e:
            logger.error(f"Failed to click at position: {e}", exc_info=True)
            
    def input_text(self, text: str) -> None:
        """
        Type text at current cursor position.
        
        Args:
            text: Text to type
        """
        try:
            pyautogui.write(text, interval=self.type_delay)
            
        except Exception as e:
            logger.error(f"Failed to input text: {e}", exc_info=True)
            
    def clear_text_field(self) -> None:
        """Clear the current text field using Ctrl+A and Backspace."""
        try:
            pyautogui.hotkey('ctrl', 'a')
            sleep(self.type_delay)
            pyautogui.press('backspace')
            
        except Exception as e:
            logger.error(f"Failed to clear text field: {e}", exc_info=True)
            
    def input_coordinates(self, x: int, y: int) -> bool:
        """
        Input coordinates into the game's coordinate input field.
        
        Args:
            x: X coordinate to input
            y: Y coordinate to input
            
        Returns:
            bool: True if coordinates were successfully input, False otherwise
        """
        try:
            # Get input field position from config
            input_settings = self.config_manager.get_scanner_settings()
            input_x = input_settings.get('input_field_x', 0)
            input_y = input_settings.get('input_field_y', 0)
            
            # Click the input field
            logger.debug(f"Clicking coordinate input field at ({input_x}, {input_y})")
            self.click_at(input_x, input_y, relative_to_window=False)
            
            # Clear existing text and input new coordinates
            self.clear_text_field()
            self.input_text(f"{x},{y}")
            pyautogui.press('enter')
            
            sleep(self.move_delay)  # Wait for game to process
            return True
            
        except Exception as e:
            logger.error(f"Failed to input coordinates: {e}", exc_info=True)
            return False
            
    def drag_mouse(self, start_x: int, start_y: int, end_x: int, end_y: int, 
                   relative_to_window: bool = True, duration: float = 0.5) -> None:
        """
        Perform a mouse drag operation from start to end coordinates.
        
        Args:
            start_x: Starting X coordinate
            start_y: Starting Y coordinate
            end_x: Ending X coordinate
            end_y: Ending Y coordinate
            relative_to_window: If True, coordinates are relative to game window
            duration: Duration of the drag operation in seconds
        """
        try:
            if relative_to_window:
                start_screen_x, start_screen_y = self.window_manager.client_to_screen(start_x, start_y)
                end_screen_x, end_screen_y = self.window_manager.client_to_screen(end_x, end_y)
            else:
                start_screen_x, start_screen_y = start_x, start_y
                end_screen_x, end_screen_y = end_x, end_y
                
            logger.debug(f"Dragging mouse from ({start_screen_x}, {start_screen_y}) to ({end_screen_x}, {end_screen_y})")
            pyautogui.moveTo(start_screen_x, start_screen_y)
            sleep(self.click_delay)
            pyautogui.dragTo(end_screen_x, end_screen_y, duration=duration, button='left')
            
        except Exception as e:
            logger.error(f"Failed to perform mouse drag: {e}", exc_info=True) 