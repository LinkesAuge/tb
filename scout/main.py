from typing import NoReturn
import sys
from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import QTimer
import cv2
import time
import win32api
import win32con
from scout.overlay import Overlay
from scout.gui import OverlayController
from scout.template_matcher import TemplateMatcher
from scout.text_ocr import TextOCR
from scout.actions import GameActions
import logging
from scout.config_manager import ConfigManager
from scout.sound_manager import SoundManager
from scout.window_manager import WindowManager
from scout.debug_window import DebugWindow

logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt='%H:%M:%S'
)

logger = logging.getLogger(__name__)

"""
Total Battle Scout - Game Automation Tool

This is the main entry point for the Total Battle Scout application, which provides automated 
scanning and template matching capabilities for the Total Battle game. The application creates
a transparent overlay on top of the game window to highlight detected elements and provides
a control interface for scanning the game world.

Key Components:
- Overlay: Transparent window that highlights detected game elements
- Template Matcher: Detects specific game elements using image recognition
- World Scanner: Systematically explores the game world
- GUI Controller: User interface for controlling all features
"""

def is_key_pressed(key_code: int) -> bool:
    """
    Check if a specific keyboard key is currently being pressed.
    
    This function uses the Windows API to detect the current state of any keyboard key.
    It's used for hotkey detection in the application.
    
    Args:
        key_code: Windows virtual key code (e.g., VK_F10 for F10 key)
        
    Returns:
        bool: True if the key is currently pressed, False otherwise
    """
    return win32api.GetAsyncKeyState(key_code) & 0x8000 != 0

def main() -> None:
    """
    Main application entry point that initializes and starts all components.
    
    This function:
    1. Creates the Qt application instance
    2. Loads configuration settings
    3. Sets up the window manager to track the game window
    4. Creates the overlay system for highlighting game elements
    5. Initializes the GUI controller
    6. Connects all necessary callbacks
    7. Starts the application event loop
    
    The application runs until the user closes it or an unhandled error occurs.
    All errors are logged for debugging purposes.
    """
    logger.info("Starting application")
    
    try:
        app = QApplication(sys.argv)
        
        logger.info("Initializing components")
        config_manager = ConfigManager()
        
        # Load settings
        overlay_settings = config_manager.get_overlay_settings()
        template_settings = config_manager.get_template_matching_settings()
        
        # Initialize window manager first
        window_manager = WindowManager("Total Battle")
        
        # Create debug window
        debug_window = DebugWindow()
        
        # Create game actions controller
        game_actions = GameActions(window_manager)
        
        # Create text OCR
        text_ocr = TextOCR(
            debug_window=debug_window,
            window_manager=window_manager
        )
        
        # Create overlay with window manager and settings
        overlay = Overlay(
            window_manager=window_manager,
            template_settings=template_settings,
            overlay_settings=overlay_settings
        )
        
        # Create controller
        controller = OverlayController(
            overlay=overlay,
            overlay_settings=overlay_settings,
            template_settings=template_settings,
            game_actions=game_actions,
            text_ocr=text_ocr,
            debug_window=debug_window
        )
        
        # Set up callbacks
        controller.set_toggle_callback(overlay.toggle)
        controller.set_quit_callback(app.quit)
        
        # Show the controller window
        controller.show()
        
        # Start the application
        sys.exit(app.exec())
        
    except Exception as e:
        logger.error(f"Application error: {e}", exc_info=True)
        sys.exit(1)

if __name__ == "__main__":
    main() 