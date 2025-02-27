"""
Debug Window Manager

This module provides a centralized manager for debug windows in the Scout application.
It handles creation, access, and lifecycle management of debug windows.
"""

import logging
from typing import Dict, Optional, Type, Any
from PyQt6.QtCore import QObject, pyqtSignal

from scout.debug.base import DebugWindowBase
from scout.debug.image_tab import ImageTab
from scout.debug.automation_tab import AutomationTab
from scout.debug.capture_tab import CaptureTab
from scout.debug.ocr_tab import OCRTab

logger = logging.getLogger(__name__)

class DebugWindowManager(QObject):
    """
    Manager for debug windows in the Scout application.
    
    This class provides:
    - Centralized creation and access to debug windows
    - Lifecycle management (creation, showing, hiding, closing)
    - Event propagation from debug windows to application components
    
    It ensures that only one instance of each debug window type exists
    and provides a consistent interface for interacting with debug windows.
    """
    
    # Signals
    window_opened = pyqtSignal(str)  # Window type
    window_closed = pyqtSignal(str)  # Window type
    debug_state_changed = pyqtSignal(bool)  # Debug enabled/disabled
    
    def __init__(self, config_manager=None):
        """
        Initialize the debug window manager.
        
        Args:
            config_manager: Configuration manager for storing debug settings
        """
        super().__init__()
        
        self._config_manager = config_manager
        self._windows: Dict[str, DebugWindowBase] = {}
        self._debug_enabled = False
        
        # Register standard window types
        self._window_types = {
            'main': DebugWindowBase,
            'image': ImageTab,
            'automation': AutomationTab,
            'capture': CaptureTab,
            'ocr': OCRTab
        }
        
        logger.debug("Debug window manager initialized")
    
    def register_window_type(self, name: str, window_class: Type[DebugWindowBase]) -> None:
        """
        Register a new debug window type.
        
        Args:
            name: Name of the window type
            window_class: Class for the window type (must inherit from DebugWindowBase)
        """
        if not issubclass(window_class, DebugWindowBase):
            raise TypeError(f"Window class must inherit from DebugWindowBase")
        
        self._window_types[name] = window_class
        logger.debug(f"Registered debug window type: {name}")
    
    def get_window(self, window_type: str, create_if_missing: bool = True) -> Optional[DebugWindowBase]:
        """
        Get a debug window of the specified type.
        
        Args:
            window_type: Type of debug window to get
            create_if_missing: Whether to create the window if it doesn't exist
            
        Returns:
            The requested debug window, or None if it doesn't exist and create_if_missing is False
        """
        # Check if window exists
        if window_type in self._windows:
            return self._windows[window_type]
        
        # Create window if requested
        if create_if_missing:
            return self.create_window(window_type)
        
        return None
    
    def create_window(self, window_type: str, **kwargs) -> Optional[DebugWindowBase]:
        """
        Create a new debug window of the specified type.
        
        Args:
            window_type: Type of debug window to create
            **kwargs: Additional arguments to pass to the window constructor
            
        Returns:
            The created debug window, or None if the window type is not registered
        """
        # Check if window type is registered
        if window_type not in self._window_types:
            logger.error(f"Unknown debug window type: {window_type}")
            return None
        
        # Create window
        try:
            window_class = self._window_types[window_type]
            window = window_class(**kwargs)
            
            # Connect signals
            window.window_closed.connect(lambda: self._on_window_closed(window_type))
            
            # Store window
            self._windows[window_type] = window
            
            # Emit signal
            self.window_opened.emit(window_type)
            
            logger.debug(f"Created debug window: {window_type}")
            return window
            
        except Exception as e:
            logger.error(f"Error creating debug window '{window_type}': {e}")
            return None
    
    def show_window(self, window_type: str) -> bool:
        """
        Show a debug window of the specified type.
        
        Args:
            window_type: Type of debug window to show
            
        Returns:
            True if the window was shown, False otherwise
        """
        window = self.get_window(window_type)
        if window:
            window.show()
            logger.debug(f"Showing debug window: {window_type}")
            return True
        return False
    
    def hide_window(self, window_type: str) -> bool:
        """
        Hide a debug window of the specified type.
        
        Args:
            window_type: Type of debug window to hide
            
        Returns:
            True if the window was hidden, False otherwise
        """
        if window_type in self._windows:
            self._windows[window_type].hide()
            logger.debug(f"Hiding debug window: {window_type}")
            return True
        return False
    
    def close_window(self, window_type: str) -> bool:
        """
        Close a debug window of the specified type.
        
        Args:
            window_type: Type of debug window to close
            
        Returns:
            True if the window was closed, False otherwise
        """
        if window_type in self._windows:
            self._windows[window_type].close()
            # Window will be removed from _windows in _on_window_closed
            return True
        return False
    
    def close_all_windows(self) -> None:
        """Close all open debug windows."""
        # Create a copy of keys to avoid modifying dict during iteration
        window_types = list(self._windows.keys())
        for window_type in window_types:
            self.close_window(window_type)
    
    def set_debug_enabled(self, enabled: bool) -> None:
        """
        Set the global debug state.
        
        Args:
            enabled: Whether debug mode is enabled
        """
        if self._debug_enabled == enabled:
            return
            
        self._debug_enabled = enabled
        
        # Update config if available
        if self._config_manager:
            debug_settings = {
                "enabled": enabled,
                "save_screenshots": enabled,
                "save_templates": enabled
            }
            self._config_manager.update_debug_settings(debug_settings)
        
        # Emit signal
        self.debug_state_changed.emit(enabled)
        
        logger.info(f"Debug mode {'enabled' if enabled else 'disabled'}")
        
        # Show or hide main debug window based on state
        if enabled:
            self.show_window('main')
        else:
            self.close_all_windows()
    
    def is_debug_enabled(self) -> bool:
        """
        Check if debug mode is enabled.
        
        Returns:
            True if debug mode is enabled, False otherwise
        """
        return self._debug_enabled
    
    def _on_window_closed(self, window_type: str) -> None:
        """
        Handle window closed event.
        
        Args:
            window_type: Type of window that was closed
        """
        if window_type in self._windows:
            # Remove window from dict
            del self._windows[window_type]
            
            # Emit signal
            self.window_closed.emit(window_type)
            
            logger.debug(f"Debug window closed: {window_type}")
            
            # If main window was closed, disable debug mode
            if window_type == 'main' and self._debug_enabled:
                self.set_debug_enabled(False)
    
    def update_image(self, window_type: str, image_name: str, image_data, metadata=None) -> None:
        """
        Update an image in a debug window.
        
        Args:
            window_type: Type of debug window
            image_name: Name of the image to update
            image_data: Image data (numpy array)
            metadata: Optional metadata to include with the image
        """
        window = self.get_window(window_type)
        if window and hasattr(window, 'update_image'):
            window.update_image(image_name, image_data, metadata)
            logger.debug(f"Updated image '{image_name}' in window '{window_type}'")
    
    def add_log_message(self, window_type: str, message: str) -> None:
        """
        Add a log message to a debug window.
        
        Args:
            window_type: Type of debug window
            message: Log message to add
        """
        window = self.get_window(window_type)
        if window and hasattr(window, 'add_log_message'):
            window.add_log_message(message)
    
    def update_status(self, window_type: str, status: str) -> None:
        """
        Update status in a debug window.
        
        Args:
            window_type: Type of debug window
            status: Status message
        """
        window = self.get_window(window_type)
        if window and hasattr(window, 'set_status'):
            window.set_status(status)
    
    def get_all_window_types(self) -> list:
        """
        Get a list of all registered window types.
        
        Returns:
            List of window type names
        """
        return list(self._window_types.keys())
    
    def get_open_windows(self) -> list:
        """
        Get a list of all currently open windows.
        
        Returns:
            List of open window type names
        """
        return list(self._windows.keys())
