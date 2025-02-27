"""
Signal management module for the TB Scout application.

This module provides a centralized system for application-wide signals and events
using PyQt's signal/slot mechanism. It allows different components to communicate
without direct dependencies.
"""

from PyQt6.QtCore import QObject, pyqtSignal
import numpy as np
from typing import Dict, Any, Optional, Tuple, List, Union


class SignalBus(QObject):
    """
    Central manager for application-wide signals.
    
    This class provides a set of signals that different components can connect to,
    enabling loosely coupled communication between modules.
    """
    
    # Window and capture signals
    window_selected = pyqtSignal(int)  # Window handle selected
    window_capture_changed = pyqtSignal(np.ndarray)  # New screenshot available
    window_position_changed = pyqtSignal(int, int, int, int)  # x, y, width, height
    window_lost = pyqtSignal()  # Target window no longer available
    
    # Template matching signals
    template_match_found = pyqtSignal(str, list, float)  # template_name, position, confidence
    template_match_batch_complete = pyqtSignal(dict)  # {template_name: [(x, y, confidence), ...]}
    template_match_all_complete = pyqtSignal()  # All template matching operations finished
    
    # Overlay signals
    overlay_toggled = pyqtSignal(bool)  # Overlay visibility changed
    overlay_updated = pyqtSignal()  # Overlay needs to be redrawn
    overlay_element_added = pyqtSignal(str, tuple, dict)  # element_type, position, properties
    overlay_element_removed = pyqtSignal(str, tuple)  # element_type, position
    overlay_cleared = pyqtSignal()  # All overlay elements removed
    
    # Automation signals
    automation_started = pyqtSignal(str)  # sequence_name
    automation_paused = pyqtSignal()
    automation_resumed = pyqtSignal()
    automation_stopped = pyqtSignal()
    automation_step_complete = pyqtSignal(int, int)  # current_step, total_steps
    automation_sequence_complete = pyqtSignal(str)  # sequence_name
    
    # OCR signals
    ocr_started = pyqtSignal(tuple)  # region (x, y, width, height)
    ocr_complete = pyqtSignal(str, tuple)  # text, region
    
    # Application signals
    app_initialized = pyqtSignal()
    app_shutdown_requested = pyqtSignal()
    error_occurred = pyqtSignal(str, str)  # error_type, error_message
    status_message = pyqtSignal(str)  # status_message
    
    # Configuration signals
    config_changed = pyqtSignal(str, object)  # config_key, new_value
    config_reloaded = pyqtSignal()
    
    # Sound signals
    sound_play_requested = pyqtSignal(str)  # sound_name
    sound_muted = pyqtSignal(bool)  # is_muted
    
    def __init__(self):
        """Initialize the signal manager."""
        super().__init__()
        
        # Dictionary to store custom signals that can be created at runtime
        self._custom_signals = {}
    
    def create_custom_signal(self, signal_name: str, signal_type=None):
        """
        Create a custom signal at runtime.
        
        Args:
            signal_name: Unique name for the signal
            signal_type: Optional type specification for the signal
        
        Returns:
            The created signal object
        """
        if signal_name in self._custom_signals:
            return self._custom_signals[signal_name]
        
        if signal_type:
            new_signal = pyqtSignal(signal_type)
        else:
            new_signal = pyqtSignal()
            
        setattr(self, signal_name, new_signal)
        self._custom_signals[signal_name] = new_signal
        return new_signal
    
    def get_signal(self, signal_name: str):
        """
        Get a signal by name.
        
        Args:
            signal_name: Name of the signal to retrieve
            
        Returns:
            The signal object or None if not found
        """
        if hasattr(self, signal_name):
            return getattr(self, signal_name)
        return None


# Global instance of the signal manager
# This should be imported and used throughout the application
signal_bus = SignalBus()
