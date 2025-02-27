"""
Window Interface module for TB Scout application.

This module provides an abstract interface for window management operations,
allowing different implementations (Win32, X11, etc.) to be used interchangeably.
It defines the core functionality required for window detection, selection, and interaction.
"""

from abc import ABC, abstractmethod
from typing import List, Tuple, Dict, Optional, Any
import numpy as np
from PyQt6.QtCore import QObject


class WindowInfo:
    """Class representing information about a window."""
    
    def __init__(self, handle: int, title: str, class_name: str = "", 
                 position: Tuple[int, int] = (0, 0), 
                 size: Tuple[int, int] = (0, 0),
                 process_id: int = 0,
                 process_name: str = ""):
        """
        Initialize window information.
        
        Args:
            handle: Window handle or identifier
            title: Window title
            class_name: Window class name
            position: (x, y) position of the window
            size: (width, height) size of the window
            process_id: Process ID that owns the window
            process_name: Name of the process that owns the window
        """
        self.handle = handle
        self.title = title
        self.class_name = class_name
        self.position = position
        self.size = size
        self.process_id = process_id
        self.process_name = process_name


class WindowInterface(ABC):
    """
    Abstract interface for window management operations.
    
    This class defines the required methods for window detection,
    selection, and interaction that must be implemented by concrete
    window manager classes.
    """
    
    @abstractmethod
    def find_window(self, title: str) -> Optional[int]:
        """
        Find a window by its title.
        
        Args:
            title: Window title to search for
            
        Returns:
            Window handle if found, None otherwise
        """
        pass
    
    @abstractmethod
    def get_window_rect(self, handle: Optional[int] = None) -> Tuple[int, int, int, int]:
        """
        Get the rectangle (position and size) of a window.
        
        Args:
            handle: Window handle, or None to use the currently selected window
            
        Returns:
            Tuple of (left, top, right, bottom) coordinates
        """
        pass
    
    @abstractmethod
    def get_client_rect(self, handle: Optional[int] = None) -> Tuple[int, int, int, int]:
        """
        Get the client rectangle (position and size) of a window.
        
        Args:
            handle: Window handle, or None to use the currently selected window
            
        Returns:
            Tuple of (left, top, right, bottom) coordinates
        """
        pass
    
    @abstractmethod
    def capture_screenshot(self) -> Optional[np.ndarray]:
        """
        Capture a screenshot of the window.
        
        Returns:
            NumPy array containing the screenshot image, or None if failed
        """
        pass
    
    @abstractmethod
    def list_windows(self) -> List[WindowInfo]:
        """
        List all visible windows in the system.
        
        Returns:
            List of WindowInfo objects
        """
        pass
    
    @abstractmethod
    def set_foreground(self, handle: Optional[int] = None) -> bool:
        """
        Bring a window to the foreground.
        
        Args:
            handle: Window handle, or None to use the currently selected window
            
        Returns:
            True if successful, False otherwise
        """
        pass
