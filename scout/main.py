"""
TB Scout - Game Automation Tool

This is the main entry point for the TB Scout application, which provides automated 
scanning and template matching capabilities for the Total Battle game. The application creates
a transparent overlay on top of the game window to highlight detected elements and provides
a control interface for scanning the game world.

Key Components:
- Overlay: Transparent window that highlights detected game elements
- Template Matcher: Detects specific game elements using image recognition
- World Scanner: Systematically explores the game world
- GUI Controller: User interface for controlling all features
"""

import sys
import logging
import time
from typing import NoReturn, Optional
import os

from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import QTimer
from PyQt6.QtGui import QColor

# Import core components
from scout.window_manager import WindowManager
from scout.window_interface import WindowInterface
from scout.overlay import Overlay
from scout.template_matcher import TemplateMatcher
from scout.text_ocr import TextOCR
from scout.actions import GameActions
from scout.config_manager import ConfigManager
from scout.sound_manager import SoundManager
from scout.debug_window import DebugWindow
# Update the import to use the correct path to MainWindow
from scout.gui.main_window import MainWindow

# Import new components
from scout.error_handling import ErrorHandler, setup_exception_handling
from scout.signals import SignalBus
from scout.template_search import TemplateSearcher
from scout.screen_capture.capture_manager import CaptureManager

# Import automation components
from scout.automation.core import AutomationCore
from scout.automation.executor import SequenceExecutor
from scout.automation.progress_tracker import ProgressTracker

# Import utilities
from scout.utils.logging_utils import setup_logging, get_logger

# Set up logging
setup_logging()
logger = get_logger(__name__)


def is_key_pressed(key_code: int) -> bool:
    """
    Check if a specific keyboard key is currently being pressed.
    
    This function uses the Windows API to detect the current state of any keyboard key.
    It's used for hotkey detection in the application.
    
    Args:
        key_code: Windows virtual key code (e.g., VK_F10 for F10 key)
        
    Returns:
        bool: True if the key is pressed, False otherwise
    """
    try:
        import win32api
        import win32con
        return win32api.GetAsyncKeyState(key_code) & 0x8000 != 0
    except ImportError:
        logger.warning("win32api not available, key press detection disabled")
        return False


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
    """
    # Create Qt application
    app = QApplication(sys.argv)
    app.setApplicationName("TB Scout")
    
    # Set up global exception handling
    setup_exception_handling()
    
    # Create signal bus for application-wide communication
    signal_bus = SignalBus()
    
    # Create error handler
    error_handler = ErrorHandler(signal_bus)
    
    # Load configuration
    config_manager = ConfigManager()
    config = config_manager.get_config()
    
    # Create window manager
    window_title = config.get("window", {}).get("title", "Total Battle")
    window_manager = WindowManager(window_title)
    window_interface = window_manager  # Use window_manager as the interface
    
    # Create capture manager
    capture_manager = CaptureManager()
    capture_manager.set_window_interface(window_interface)
    
    # Create template matcher
    template_matcher = TemplateMatcher(window_manager)

    # Create template search
    template_search = TemplateSearcher(template_matcher, window_manager, "templates")  # Explicitly pass the templates directory
    
    # Create game actions
    game_actions = GameActions(window_manager)
    
    # Create sound manager
    sound_manager = SoundManager()
    
    # Get settings from config
    template_settings = config.get("templates", {})
    # Add default values for required template settings if they're missing
    if "confidence" not in template_settings:
        template_settings["confidence"] = 0.8  # Default confidence level
    if "target_frequency" not in template_settings:
        template_settings["target_frequency"] = 1.0  # Default update frequency (1 Hz)
    if "sound_enabled" not in template_settings:
        template_settings["sound_enabled"] = False  # Default sound setting
    
    # Get overlay settings with defaults for missing values
    overlay_settings = config.get("overlay", {})
    # Add default values for required overlay settings if they're missing
    if "rect_color" not in overlay_settings:
        overlay_settings["rect_color"] = QColor(255, 0, 0, 128)  # Semi-transparent red
    if "font_color" not in overlay_settings:
        overlay_settings["font_color"] = QColor(255, 255, 255)  # White
    if "cross_color" not in overlay_settings:
        overlay_settings["cross_color"] = QColor(255, 0, 0)  # Red
    if "rect_thickness" not in overlay_settings:
        overlay_settings["rect_thickness"] = 2
    if "rect_scale" not in overlay_settings:
        overlay_settings["rect_scale"] = 1.0
    if "font_size" not in overlay_settings:
        overlay_settings["font_size"] = 12
    if "text_thickness" not in overlay_settings:
        overlay_settings["text_thickness"] = 1
    if "cross_size" not in overlay_settings:
        overlay_settings["cross_size"] = 10
    if "cross_thickness" not in overlay_settings:
        overlay_settings["cross_thickness"] = 1
    if "cross_scale" not in overlay_settings:
        overlay_settings["cross_scale"] = 1.0
    
    # Create overlay with required settings
    overlay = Overlay(window_manager, template_settings, overlay_settings)
    
    # Create debug window first (before text_ocr)
    debug_window = DebugWindow(
        window_manager=window_manager,
        template_matcher=template_matcher,
        text_ocr=None,  # We'll set this later
        capture_manager=capture_manager
    )
    
    # Create text OCR with debug_window
    text_ocr = TextOCR(window_manager=window_manager, debug_window=debug_window)
    
    # Update debug_window with text_ocr
    debug_window.text_ocr = text_ocr
    
    # Create automation components
    progress_tracker = ProgressTracker()
    automation_core = AutomationCore(
        window_manager=window_manager,
        template_matcher=template_matcher,
        text_ocr=text_ocr,
        game_actions=game_actions,
        template_search=template_search,
        signal_bus=signal_bus
    )
    
    # Create main window
    main_window = MainWindow(
        window_manager=window_manager,
        overlay=overlay,
        template_matcher=template_matcher,
        text_ocr=text_ocr,
        config_manager=config_manager,
        sound_manager=sound_manager,
        automation_core=automation_core,
        capture_manager=capture_manager,
        signal_bus=signal_bus,
        error_handler=error_handler
    )
    
    # Connect signals
    signal_bus.error_occurred.connect(error_handler.handle_error)
    signal_bus.status_message.connect(main_window.show_status_message)
    
    # Show windows
    main_window.show()
    
    # Set up periodic window tracking
    def update_window_tracking():
        window_manager.update_window_position()
        overlay.update_position()
    
    window_tracker = QTimer()
    window_tracker.timeout.connect(update_window_tracking)
    window_tracker.start(500)  # Update every 500ms
    
    # Start the application
    logger.info("TB Scout application started")
    sys.exit(app.exec())


if __name__ == "__main__":
    main() 
