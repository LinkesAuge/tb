"""
Main Window for TB Scout

This module provides the main application window for the TB Scout application.
It integrates all components and provides a user interface for controlling the application.
"""

from typing import Optional, Dict, Any
import sys
import os
import logging
from pathlib import Path
import json
import webbrowser
from datetime import datetime

from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QTabWidget, QSplitter,
    QFileDialog, QMessageBox
)
from PyQt6.QtCore import (
    Qt, QTimer, QSettings, QEvent,
    pyqtSignal, pyqtSlot
)
from PyQt6.QtGui import (
    QCloseEvent
)

from scout.window_manager import WindowManager
from scout.overlay import Overlay
from scout.template_matcher import TemplateMatcher
from scout.text_ocr import TextOCR
from scout.config_manager import ConfigManager
from scout.sound_manager import SoundManager
from scout.utils.logging_utils import get_logger
from scout.automation.core import AutomationCore
from scout.automation.executor import SequenceExecutor
from scout.automation.context import ExecutionContext
from scout.world_scanner import WorldScanner
from scout.actions import GameActions
from scout.debug_window import DebugWindow
from scout.screen_capture.capture_manager import CaptureManager
from scout.screen_capture.capture_tab import CaptureTab
from scout.signals import SignalBus
from scout.error_handling import ErrorHandler
from scout.template_search import TemplateSearcher

# Import GUI components
from scout.gui.menu_bar import MenuBar  # This should match the class name in menu_bar.py
from scout.gui.status_bar import StatusBar
from scout.gui.scanning_tab import ScanningTab
from scout.gui.settings_tab import SettingsTab
from scout.automation.gui.automation_tab import AutomationTab

logger = get_logger(__name__)

class MainWindow(QMainWindow):
    """
    Main application window for TB Scout.
    
    This class provides the main user interface for the application, including:
    - Main control tabs (Scanning, Automation, Settings)
    - Status bar with application state
    - Menu bar with application actions
    - Integration of all application components
    """
    
    def __init__(
        self,
        window_manager: WindowManager,
        overlay: Overlay,
        template_matcher: TemplateMatcher,
        text_ocr: TextOCR,
        config_manager: ConfigManager,
        sound_manager: SoundManager,
        automation_core: AutomationCore,
        capture_manager: CaptureManager,
        signal_bus: SignalBus,
        error_handler: ErrorHandler,
        parent: Optional[QWidget] = None
    ):
        """
        Initialize the main window.
        
        Args:
            window_manager: Window manager instance
            overlay: Overlay instance
            template_matcher: Template matcher instance
            text_ocr: Text OCR instance
            config_manager: Configuration manager instance
            sound_manager: Sound manager instance
            automation_core: Automation core instance
            capture_manager: Screen capture manager instance
            signal_bus: Application-wide signal bus
            error_handler: Error handling system
            parent: Parent widget
        """
        super().__init__(parent)
        
        # Store component references
        self.window_manager = window_manager
        self.overlay = overlay
        self.template_matcher = template_matcher
        self.text_ocr = text_ocr
        self.config_manager = config_manager
        self.sound_manager = sound_manager
        self.automation_core = automation_core
        self.capture_manager = capture_manager
        self.signal_bus = signal_bus
        self.error_handler = error_handler
        
        # Create additional components
        self.template_search = TemplateSearcher(
            self.template_matcher, 
            self.window_manager
        )
        self.world_scanner = WorldScanner(
            window_manager=self.window_manager,
            template_matcher=self.template_matcher,
            overlay=self.overlay
        )
        self.game_actions = GameActions(
            window_manager=self.window_manager
        )
        
        # Create execution context and sequence executor
        self.execution_context = ExecutionContext(
            positions={},  # Initialize with empty positions dictionary
            window_manager=self.window_manager,
            template_matcher=self.template_matcher,
            text_ocr=self.text_ocr,
            game_actions=self.game_actions,
            overlay=self.overlay
        )
        self.sequence_executor = SequenceExecutor(self.execution_context)
        
        # Application state
        self.is_scanning = False
        self.is_executing = False
        self.current_window_title = ""
        self.last_error = None
        
        # Setup UI
        self._setup_ui()
        
        # Connect signals
        self._connect_signals()
        
        # Setup timers
        self._setup_timers()
        
        # Load settings
        self._load_settings()
        
        # Register error handlers
        self._register_error_handlers()
        
        logger.info("Main window initialized")
    
    def _setup_ui(self) -> None:
        """Set up the user interface."""
        # Set window properties
        self.setWindowTitle("TB Scout")
        self.setMinimumSize(800, 600)
        
        # Create central widget and layout
        central_widget = QWidget()
        main_layout = QVBoxLayout(central_widget)
        self.setCentralWidget(central_widget)
        
        # Create tab widget
        self.tab_widget = QTabWidget()
        main_layout.addWidget(self.tab_widget)
        
        # Create tabs
        self._create_tabs()
        
        # Create status bar
        self._create_status_bar()
        
        # Create debug window
        self.debug_window = DebugWindow(
            template_matcher=self.template_matcher,
            text_ocr=self.text_ocr,
            window_manager=self.window_manager,
            capture_manager=self.capture_manager
        )
        self.debug_window.hide()  # Initially hidden
        
        # Create menu bar
        self._create_menu_bar()
    
    def _create_tabs(self) -> None:
        """Create the main tabs."""
        # Create scanning tab
        self.scanning_tab = ScanningTab(
            window_manager=self.window_manager,
            overlay=self.overlay,
            template_matcher=self.template_matcher,
            world_scanner=self.world_scanner,
            parent=self
        )
        self.tab_widget.addTab(self.scanning_tab, "Scanning")
        
        # Create automation tab
        self.automation_tab = AutomationTab(
            automation_core=self.automation_core,
            executor=self.sequence_executor,
            parent=self
        )
        self.tab_widget.addTab(self.automation_tab, "Automation")
        
        # Create capture tab
        self.capture_tab = CaptureTab(
            parent=self
        )
        self.tab_widget.addTab(self.capture_tab, "Capture")
        
        # Create settings tab
        self.settings_tab = SettingsTab(
            config_manager=self.config_manager,
            overlay=self.overlay,
            template_matcher=self.template_matcher,
            sound_manager=self.sound_manager,
            text_ocr=self.text_ocr,
            parent=self
        )
        self.tab_widget.addTab(self.settings_tab, "Settings")
    
    def _create_status_bar(self) -> None:
        """Create the status bar."""
        self.status_bar = StatusBar(self)
        self.setStatusBar(self.status_bar)
    
    def _create_menu_bar(self) -> None:
        """Create the menu bar."""
        self.menu_bar = MenuBar(
            parent_window=self,
            config_manager=self.config_manager,
            overlay=self.overlay,
            debug_window=self.debug_window,
            toggle_scanning_callback=self._toggle_scanning,
            toggle_overlay_callback=self._toggle_overlay,
            clear_overlay_callback=self._clear_overlay,
            capture_screenshot_callback=self._capture_screenshot
        )
        self.setMenuBar(self.menu_bar)
    
    def _connect_signals(self) -> None:
        """Connect signals to slots."""
        # Connect window manager signals
        self.window_manager.window_found.connect(self._on_window_found)
        self.window_manager.window_lost.connect(self._on_window_lost)
        self.window_manager.mouse_moved.connect(self._on_mouse_moved)
        
        # Connect overlay signals
        self.overlay.visibility_changed.connect(self._on_overlay_visibility_changed)
        
        # Connect world scanner signals
        self.world_scanner.scanning_started.connect(self._on_scanning_started)
        self.world_scanner.scanning_stopped.connect(self._on_scanning_stopped)
        
        # Connect sequence executor signals
        self.sequence_executor.execution_started.connect(self._on_execution_started)
        self.sequence_executor.execution_completed.connect(self._on_execution_completed)
        
        # Connect signal bus signals
        self.signal_bus.error_occurred.connect(self._on_error_occurred)
        
        # Connect tab signals
        self.scanning_tab.scan_toggled.connect(self._on_scan_toggled)
        self.scanning_tab.overlay_toggled.connect(self._on_overlay_toggled)
    
    def _setup_timers(self) -> None:
        """Set up timers for periodic updates."""
        # Create status update timer
        self.status_timer = QTimer(self)
        self.status_timer.timeout.connect(self._update_status)
        self.status_timer.start(500)  # Update every 500ms
    
    def _load_settings(self) -> None:
        """Load application settings."""
        # Load window geometry
        geometry = self.config_manager.get("main_window_geometry")
        if geometry:
            self.restoreGeometry(bytes.fromhex(geometry))
        
        # Load window state
        state = self.config_manager.get("main_window_state")
        if state:
            self.restoreState(bytes.fromhex(state))
    
    def save_settings(self) -> None:
        """Save application settings."""
        try:
            # Convert QByteArray to bytes and then to hex string
            geometry_bytes = bytes(self.saveGeometry())
            state_bytes = bytes(self.saveState())
            
            self.config_manager.set("main_window_geometry", geometry_bytes.hex())
            self.config_manager.set("main_window_state", state_bytes.hex())
            
            # Save other settings
            self.config_manager.save_config()
        except Exception as e:
            logger.error(f"Error saving settings: {e}", exc_info=True)
    
    def _register_error_handlers(self) -> None:
        """Register error handlers."""
        # Register error handlers with error handler
        self.error_handler.register_handler(
            "window_not_found",
            self._handle_window_not_found_error
        )
        self.error_handler.register_handler(
            "template_not_found",
            self._handle_template_not_found_error
        )
    
    def _toggle_scanning(self) -> None:
        """Toggle scanning state."""
        self.scanning_tab._toggle_scanning()
    
    def _toggle_overlay(self, state: bool) -> None:
        """
        Toggle overlay visibility.
        
        Args:
            state: Whether to show the overlay
        """
        self.overlay.set_visible(state)
    
    def _clear_overlay(self) -> None:
        """Clear overlay contents."""
        self.overlay.clear()
    
    def _capture_screenshot(self) -> None:
        """Capture a screenshot of the game window."""
        if not self.window_manager.is_window_found():
            QMessageBox.warning(
                self,
                "Window Not Found",
                "Cannot capture screenshot: Game window not found."
            )
            return
        
        # Get file path
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "Save Screenshot",
            "",
            "PNG Files (*.png);;JPEG Files (*.jpg)"
        )
        
        if not file_path:
            return
        
        # Ensure file has correct extension
        if not (file_path.lower().endswith(".png") or file_path.lower().endswith(".jpg")):
            file_path += ".png"
        
        # Capture screenshot
        try:
            screenshot = self.window_manager.capture_window()
            screenshot.save(file_path)
            
            logger.info(f"Screenshot saved to {file_path}")
            
            # Show success message
            QMessageBox.information(
                self,
                "Screenshot Saved",
                f"Screenshot saved to {file_path}"
            )
        except Exception as e:
            logger.error(f"Failed to save screenshot: {e}")
            QMessageBox.warning(
                self,
                "Screenshot Failed",
                f"Failed to save screenshot: {str(e)}"
            )
    
    def _on_window_found(self, title: str, handle: int) -> None:
        """
        Handle window found event.
        
        Args:
            title: Window title
            handle: Window handle
        """
        self.current_window_title = title
        self.status_bar.set_window_status(True, title)
        self.sound_manager.play_sound("window_found")
    
    def _on_window_lost(self) -> None:
        """Handle window lost event."""
        self.current_window_title = ""
        self.status_bar.set_window_status(False)
        self.sound_manager.play_sound("window_lost")
    
    def _on_mouse_moved(self, x: int, y: int) -> None:
        """
        Handle mouse moved event.
        
        Args:
            x: Mouse X coordinate
            y: Mouse Y coordinate
        """
        self.status_bar.update_coordinates(x, y)
    
    def _on_overlay_visibility_changed(self, visible: bool) -> None:
        """
        Handle overlay visibility changed event.
        
        Args:
            visible: Whether the overlay is visible
        """
        self.menu_bar.toggle_overlay_action.setChecked(visible)
    
    def _on_scanning_started(self) -> None:
        """Handle scanning started event."""
        self.is_scanning = True
        self.status_bar.set_scanning_status(True)
        self.menu_bar.update_scanning_action_text(True)
    
    def _on_scanning_stopped(self) -> None:
        """Handle scanning stopped event."""
        self.is_scanning = False
        self.status_bar.set_scanning_status(False)
        self.menu_bar.update_scanning_action_text(False)
    
    def _on_execution_started(self, sequence_name: str) -> None:
        """
        Handle execution started event.
        
        Args:
            sequence_name: Name of the sequence being executed
        """
        self.is_executing = True
        self.status_bar.set_automation_status(True, sequence_name)
    
    def _on_execution_completed(self) -> None:
        """Handle execution completed event."""
        self.is_executing = False
        self.status_bar.set_automation_status(False)
    
    def _on_error_occurred(self, error_type: str, message: str) -> None:
        """
        Handle error occurred event.
        
        Args:
            error_type: Type of error
            message: Error message
        """
        # Log error
        logger.error(f"Error occurred: {error_type} - {message}")
        
        # Play error sound
        self.sound_manager.play_sound("error")
        
        # Let error handler handle the error
        self.error_handler.handle_error(error_type, message)
    
    def _handle_window_not_found_error(self, message: str) -> None:
        """
        Handle window not found error.
        
        Args:
            message: Error message
        """
        QMessageBox.warning(
            self,
            "Window Not Found",
            f"Could not find the game window: {message}\n\n"
            "Please make sure the game is running and visible."
        )
    
    def _handle_template_not_found_error(self, message: str) -> None:
        """
        Handle template not found error.
        
        Args:
            message: Error message
        """
        QMessageBox.warning(
            self,
            "Template Not Found",
            f"Could not find the template: {message}\n\n"
            "Please make sure the template exists and is correctly configured."
        )
    
    def _update_status(self) -> None:
        """Update status information."""
        # Update window status
        if self.window_manager.is_window_found():
            title = self.window_manager.get_window_title()
            self.status_bar.set_window_status(True, title)
        else:
            self.status_bar.set_window_status(False)
    
    def _on_scan_toggled(self, is_scanning: bool) -> None:
        """
        Handle scan toggled event.
        
        Args:
            is_scanning: Whether scanning is active
        """
        self.is_scanning = is_scanning
        self.status_bar.set_scanning_status(is_scanning)
        self.menu_bar.update_scanning_action_text(is_scanning)
    
    def _on_overlay_toggled(self, is_visible: bool) -> None:
        """
        Handle overlay toggled event.
        
        Args:
            is_visible: Whether the overlay is visible
        """
        self.overlay.set_visible(is_visible)
    
    def show_status_message(self, message: str) -> None:
        """
        Show a status message.
        
        This method receives status messages from the signal bus
        and displays them in the status bar.
        
        Args:
            message: Status message to display
        """
        logger.debug(f"Status message: {message}")
        if hasattr(self, 'status_bar'):
            self.status_bar.set_status(message)
    
    def closeEvent(self, event: QCloseEvent) -> None:
        """
        Handle application close event.
        
        This method ensures proper cleanup when the application is closed:
        1. Closes the debug window if it's open
        2. Disables debug mode and saves settings
        3. Stops any active processes
        4. Performs parent class cleanup
        
        Args:
            event: Close event
        """
        logger.info("Application closing - performing cleanup")
        
        try:
            # Close debug window if it exists
            if hasattr(self, 'debug_window'):
                logger.debug("Closing debug window")
                self.debug_window.close()
            
            # Disable debug mode and save settings
            debug_settings = {
                "enabled": False,
                "save_screenshots": False,
                "save_templates": False
            }
            self.config_manager.update_debug_settings(debug_settings)
            
            # Stop pattern matching if active
            if hasattr(self, 'template_matcher'):
                logger.debug("Stopping pattern matching")
                self.template_matcher.set_debug_mode(False)
            
            # Save all settings
            self.save_settings()
            
            logger.info("Cleanup completed")
            
        except Exception as e:
            logger.error(f"Error during application cleanup: {e}", exc_info=True)
            
        finally:
            # Call parent class closeEvent
            super().closeEvent(event)
