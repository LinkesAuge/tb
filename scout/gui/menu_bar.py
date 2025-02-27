"""
Menu Bar Manager for TB Scout

This module provides the menu bar functionality for the TB Scout application.
It creates and manages all menus and actions for the main window.
"""

from typing import Optional, Callable
import logging
import webbrowser
import os
import sys  # Add sys import for sys._MEIPASS
from pathlib import Path

from PyQt6.QtWidgets import QMainWindow, QMenu, QMessageBox, QFileDialog, QMenuBar
from PyQt6.QtGui import QAction, QKeySequence
from PyQt6.QtCore import Qt

from scout.config_manager import ConfigManager
from scout.automation.core import AutomationCore
from scout.debug_window import DebugWindow
from scout.utils.logging_utils import get_logger

# Define create_action function directly since ui_utils module doesn't exist
def create_action(parent, text, slot=None, shortcut=None, icon=None, 
                 tip=None, status_tip=None, checkable=False, checked=False):
    """
    Create a QAction with the given properties.
    
    Args:
        parent: Parent widget for the action
        text: Text to display for the action
        slot: Function to call when action is triggered
        shortcut: Keyboard shortcut for the action
        icon: Icon to display for the action
        tip: Tooltip text
        status_tip: Status bar tip text (uses tip if None)
        checkable: Whether the action can be checked/unchecked
        checked: Initial checked state if checkable is True
        
    Returns:
        QAction instance
    """
    action = QAction(text, parent)
    if icon is not None:
        action.setIcon(icon)
    if shortcut is not None:
        action.setShortcut(shortcut)
    if tip is not None:
        action.setToolTip(tip)
    if status_tip is not None:
        action.setStatusTip(status_tip)
    elif tip is not None:
        action.setStatusTip(tip)
    if slot is not None:
        action.triggered.connect(slot)
    if checkable:
        action.setCheckable(True)
        action.setChecked(checked)
    return action

# Define get_resource_path function directly
def get_resource_path(relative_path):
    """Get absolute path to resource, works for dev and for PyInstaller"""
    try:
        # PyInstaller creates a temp folder and stores path in _MEIPASS
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)

logger = get_logger(__name__)

# Rename class to match imports in main_window.py
class MenuBar(QMenuBar):
    """
    Manager for the application menu bar.
    
    This class provides:
    - File menu (save settings, export results, exit)
    - View menu (toggle overlay, show debug window)
    - Tools menu (scanning, automation, screenshots)
    - Help menu (documentation, about)
    """
    
    def __init__(
        self,
        parent_window: QMainWindow,
        config_manager: ConfigManager,
        overlay=None,  # Add overlay parameter
        debug_window=None,  # Make debug_window optional
        toggle_scanning_callback: Callable[[], None] = None,
        toggle_overlay_callback: Callable[[bool], None] = None,
        clear_overlay_callback: Callable[[], None] = None,
        capture_screenshot_callback: Callable[[], None] = None
    ):
        """
        Initialize the menu bar.
        
        Args:
            parent_window: Parent main window
            config_manager: Configuration manager
            overlay: Overlay instance
            debug_window: Debug window instance
            toggle_scanning_callback: Callback to toggle scanning
            toggle_overlay_callback: Callback to toggle overlay
            clear_overlay_callback: Callback to clear overlay
            capture_screenshot_callback: Callback to capture screenshot
        """
        super().__init__(parent_window)
        self.parent = parent_window
        self.config_manager = config_manager
        self.overlay = overlay
        self.debug_window = debug_window
        
        # Store callbacks
        self.toggle_scanning_callback = toggle_scanning_callback
        self.toggle_overlay_callback = toggle_overlay_callback
        self.clear_overlay_callback = clear_overlay_callback
        self.capture_screenshot_callback = capture_screenshot_callback
        
        # Create menus
        self._create_file_menu()
        self._create_view_menu()
        self._create_tools_menu()
        self._create_help_menu()
        
        # Track overlay visibility
        self.overlay_visible = True
        
        logger.debug("Menu bar initialized")
    
    def _create_file_menu(self) -> None:
        """Create the File menu."""
        file_menu = self.addMenu("&File")
        
        # Add actions to File menu
        save_settings_action = create_action(
            self.parent, 
            "Save Settings", 
            self._save_settings,
            shortcut=QKeySequence.StandardKey.Save,
            status_tip="Save current settings"
        )
        file_menu.addAction(save_settings_action)
        
        export_results_action = create_action(
            self.parent, 
            "Export Results", 
            self._export_results,
            shortcut=QKeySequence("Ctrl+E"),
            status_tip="Export scan results"
        )
        file_menu.addAction(export_results_action)
        
        file_menu.addSeparator()
        
        exit_action = create_action(
            self.parent, 
            "Exit", 
            self.parent.close,
            shortcut=QKeySequence.StandardKey.Quit,
            status_tip="Exit the application"
        )
        file_menu.addAction(exit_action)
    
    def _create_view_menu(self) -> None:
        """Create the View menu."""
        view_menu = self.addMenu("&View")
        
        # Add actions to View menu
        self.toggle_overlay_action = create_action(
            self.parent, 
            "Toggle Overlay", 
            self._toggle_overlay,
            shortcut=QKeySequence("Ctrl+O"),
            status_tip="Toggle overlay visibility",
            checkable=True,
            checked=True
        )
        view_menu.addAction(self.toggle_overlay_action)
        
        self.show_debug_action = create_action(
            self.parent, 
            "Show Debug Window", 
            self._toggle_debug_window,
            shortcut=QKeySequence("Ctrl+D"),
            status_tip="Show debug window",
            checkable=True,
            checked=self.debug_window.isVisible()
        )
        view_menu.addAction(self.show_debug_action)
    
    def _create_tools_menu(self) -> None:
        """Create the Tools menu."""
        tools_menu = self.addMenu("&Tools")
        
        # Add actions to Tools menu
        self.start_scanning_action = create_action(
            self.parent, 
            "Start Scanning", 
            self._toggle_scanning,
            shortcut=QKeySequence("F5"),
            status_tip="Start or stop scanning"
        )
        tools_menu.addAction(self.start_scanning_action)
        
        clear_overlay_action = create_action(
            self.parent, 
            "Clear Overlay", 
            self._clear_overlay,
            shortcut=QKeySequence("Ctrl+C"),
            status_tip="Clear overlay"
        )
        tools_menu.addAction(clear_overlay_action)
        
        tools_menu.addSeparator()
        
        capture_screenshot_action = create_action(
            self.parent, 
            "Capture Screenshot", 
            self._capture_screenshot,
            shortcut=QKeySequence("F12"),
            status_tip="Capture screenshot"
        )
        tools_menu.addAction(capture_screenshot_action)
    
    def _create_help_menu(self) -> None:
        """Create the Help menu."""
        help_menu = self.addMenu("&Help")
        
        # Add actions to Help menu
        documentation_action = create_action(
            self.parent, 
            "Documentation", 
            self._show_documentation,
            shortcut=QKeySequence("F1"),
            status_tip="Show documentation"
        )
        help_menu.addAction(documentation_action)
        
        about_action = create_action(
            self.parent, 
            "About", 
            self._show_about,
            status_tip="Show about dialog"
        )
        help_menu.addAction(about_action)
    
    def _save_settings(self) -> None:
        """Save application settings."""
        self.config_manager.save()
        logger.info("Settings saved")
        
        # Show success message
        QMessageBox.information(
            self.parent,
            "Settings Saved",
            "Application settings have been saved successfully."
        )
    
    def _export_results(self) -> None:
        """Export scan results to file."""
        # Get file path
        file_path, selected_filter = QFileDialog.getSaveFileName(
            self.parent,
            "Export Results",
            "",
            "CSV Files (*.csv);;JSON Files (*.json);;Text Files (*.txt)"
        )
        
        if not file_path:
            return
        
        # Determine export format based on selected filter
        if "CSV" in selected_filter:
            format_type = "csv"
        elif "JSON" in selected_filter:
            format_type = "json"
        else:
            format_type = "txt"
        
        # Ensure file has correct extension
        if not file_path.lower().endswith(f".{format_type}"):
            file_path += f".{format_type}"
        
        # Delegate to the appropriate component for actual export
        try:
            # This would be implemented when we know more about how results are stored
            # For now, just create an empty file
            with open(file_path, 'w') as f:
                if format_type == "json":
                    f.write("{}")
                elif format_type == "csv":
                    f.write("timestamp,type,value\n")
                else:
                    f.write("No results to export\n")
            
            logger.info(f"Exported results to {file_path}")
            
            # Show success message
            QMessageBox.information(
                self.parent,
                "Export Successful",
                f"Results exported to {file_path}"
            )
        except Exception as e:
            logger.error(f"Failed to export results: {e}")
            QMessageBox.warning(
                self.parent,
                "Export Failed",
                f"Failed to export results: {str(e)}"
            )
    
    def _toggle_overlay(self) -> None:
        """Toggle overlay visibility."""
        self.overlay_visible = not self.overlay_visible
        
        if self.toggle_overlay_callback:
            self.toggle_overlay_callback(self.overlay_visible)
        
        logger.info(f"Overlay visibility set to {self.overlay_visible}")
        
        # Update action text
        self.toggle_overlay_action.setChecked(self.overlay_visible)
    
    def _toggle_debug_window(self) -> None:
        """Toggle debug window visibility."""
        if self.debug_window.isVisible():
            self.debug_window.hide()
            logger.debug("Debug window hidden")
            self.show_debug_action.setChecked(False)
        else:
            self.debug_window.show()
            logger.debug("Debug window shown")
            self.show_debug_action.setChecked(True)
    
    def _toggle_scanning(self) -> None:
        """Toggle scanning on/off."""
        if self.toggle_scanning_callback:
            self.toggle_scanning_callback()
            logger.info("Scanning toggled")
        else:
            logger.warning("No scanning toggle callback provided")
    
    def update_scanning_action_text(self, is_scanning: bool) -> None:
        """
        Update the text of the scanning action based on scanning state.
        
        Args:
            is_scanning: Whether scanning is currently active
        """
        self.start_scanning_action.setText("Stop Scanning" if is_scanning else "Start Scanning")
    
    def _clear_overlay(self) -> None:
        """Clear overlay contents."""
        if self.clear_overlay_callback:
            self.clear_overlay_callback()
            logger.info("Overlay cleared")
        else:
            logger.warning("No clear overlay callback provided")
    
    def _capture_screenshot(self) -> None:
        """Capture a screenshot of the game window."""
        if self.capture_screenshot_callback:
            self.capture_screenshot_callback()
            logger.info("Screenshot captured")
        else:
            logger.warning("No screenshot capture callback provided")
    
    def _show_documentation(self) -> None:
        """Show application documentation."""
        # Try to open local documentation if it exists
        docs_path = get_resource_path("docs/index.html")
        
        if os.path.exists(docs_path):
            # Convert to URL format and open in browser
            url = Path(docs_path).as_uri()
            webbrowser.open(url)
            logger.info(f"Opening local documentation: {url}")
        else:
            # Fallback to showing a message
            QMessageBox.information(
                self.parent,
                "Documentation",
                "Documentation is not yet available. Please check back later."
            )
            logger.warning("Documentation not found")
    
    def _show_about(self) -> None:
        """Show about dialog."""
        QMessageBox.about(
            self.parent,
            "About TB Scout",
            "<h1>TB Scout</h1>"
            "<p>Version 1.0.0</p>"
            "<p>A tool for automating interactions with the Total Battle game.</p>"
            "<p>© 2023 TB Scout Team</p>"
        )
