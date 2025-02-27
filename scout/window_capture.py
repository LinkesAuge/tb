"""
Window Capture Module

This module provides functionality for capturing screenshots of windows.
It integrates with the screen_capture module to provide a consistent interface
for capturing window content.
"""

import logging
import numpy as np
from typing import Optional, Tuple, Dict, Any

from scout.window_interface import WindowInterface
from scout.screen_capture.capture_manager import CaptureManager
from scout.error_handling import handle_errors

logger = logging.getLogger(__name__)

class WindowCapture:
    """
    Handles capturing screenshots of windows.
    
    This class provides methods for capturing screenshots of windows
    using the CaptureManager from the screen_capture module.
    """
    
    def __init__(self, window_interface: WindowInterface, capture_manager: CaptureManager):
        """
        Initialize the WindowCapture with a window interface and capture manager.
        
        Args:
            window_interface: Interface to the window to capture
            capture_manager: Manager for screen/window capture
        """
        self.window_interface = window_interface
        self.capture_manager = capture_manager
        self.last_capture: Optional[np.ndarray] = None
        self.capture_settings: Dict[str, Any] = {
            "quality": 80,
            "format": "png",
            "auto_save": False
        }
        
    @handle_errors
    def capture(self) -> Optional[np.ndarray]:
        """
        Capture a screenshot of the window.
        
        Returns:
            Numpy array containing the screenshot image data, or None if capture failed
        """
        if not self.window_interface.is_valid():
            logger.warning("Cannot capture - window is not valid")
            return None
            
        # Get window position and size
        rect = self.window_interface.get_window_rect()
        if not rect:
            logger.warning("Cannot capture - failed to get window rectangle")
            return None
            
        # Use capture manager to capture the window
        self.last_capture = self.capture_manager.capture_window(
            self.window_interface.get_window_handle()
        )
        
        return self.last_capture
        
    @handle_errors
    def capture_region(self, x: int, y: int, width: int, height: int) -> Optional[np.ndarray]:
        """
        Capture a specific region of the window.
        
        Args:
            x: X coordinate of the region (relative to window)
            y: Y coordinate of the region (relative to window)
            width: Width of the region
            height: Height of the region
            
        Returns:
            Numpy array containing the region image data, or None if capture failed
        """
        full_capture = self.capture()
        if full_capture is None:
            return None
            
        # Ensure coordinates are within bounds
        if x < 0 or y < 0 or x + width > full_capture.shape[1] or y + height > full_capture.shape[0]:
            logger.warning(f"Region coordinates out of bounds: ({x}, {y}, {width}, {height})")
            return None
            
        # Extract the region
        region = full_capture[y:y+height, x:x+width].copy()
        return region
        
    def save_screenshot(self, filepath: str) -> bool:
        """
        Save the last captured screenshot to a file.
        
        Args:
            filepath: Path to save the screenshot
            
        Returns:
            True if successful, False otherwise
        """
        if self.last_capture is None:
            logger.warning("No screenshot to save")
            return False
            
        try:
            import cv2
            cv2.imwrite(filepath, self.last_capture)
            logger.debug(f"Screenshot saved to {filepath}")
            return True
        except Exception as e:
            logger.error(f"Failed to save screenshot: {str(e)}")
            return False
            
    def update_settings(self, settings: Dict[str, Any]) -> None:
        """
        Update capture settings.
        
        Args:
            settings: Dictionary of settings to update
        """
        self.capture_settings.update(settings)
        
    def get_last_capture_size(self) -> Optional[Tuple[int, int]]:
        """
        Get the size of the last captured screenshot.
        
        Returns:
            Tuple of (width, height) or None if no capture available
        """
        if self.last_capture is None:
            return None
            
        height, width = self.last_capture.shape[:2]
        return (screen_x, screen_y) 
