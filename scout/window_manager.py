"""
Window Manager Module

This module provides functionality for detecting, tracking, and interacting with
application windows, particularly the Total Battle game window. It integrates with
the screen capture module to provide screenshots of the tracked window.
"""

import logging
import time
from typing import Optional, Tuple, Dict, List, Any, Union
import os
import numpy as np
import win32gui
import win32con
import win32api
import win32process
from PyQt6.QtCore import QObject, pyqtSignal, QRect, QPoint, QSize, QTimer

from scout.error_handling import handle_errors
from scout.window_interface import WindowInterface, WindowInfo
from scout.screen_capture.capture_manager import CaptureManager

logger = logging.getLogger(__name__)

class WindowManager(QObject):
    """
    Manages detection, tracking, and interaction with application windows.
    
    This class is responsible for:
    1. Finding the Total Battle game window
    2. Tracking its position and size
    3. Capturing screenshots of the window
    4. Providing window information to other components
    
    It implements the WindowInterface to provide a consistent API for window operations.
    """
    
    # Signals
    window_found = pyqtSignal(str, int)  # Window title, handle
    window_lost = pyqtSignal()
    window_moved = pyqtSignal(QRect)  # New window geometry
    window_resized = pyqtSignal(QRect)  # New window geometry
    mouse_moved = pyqtSignal(int, int)  # Mouse X, Y coordinates
    
    def __init__(self, window_title: str):
        """
        Initialize the window manager.
        
        Args:
            window_title: Title of the window to track
        """
        super().__init__()
        self.window_title = window_title
        self.handle = None
        self.process_id = None
        self.window_rect = None
        self.client_rect = None
        self.client_to_window_offset = (0, 0)
        self.capture_manager = None
        self.last_mouse_pos = (0, 0)
        self.config_manager = None  # Will be set later from main.py
        
        # Get the last window title from config if available
        if hasattr(self, 'config_manager') and self.config_manager:
            saved_title = self.config_manager.get_last_window_title()
            if saved_title:
                logger.info(f"Using saved window title from config: {saved_title}")
                self.window_title = saved_title
        
        # Try to find the window immediately
        self.handle = self.find_window(self.window_title)
        if self.handle:
            logger.info(f"Found window: {self.window_title} (handle: {self.handle})")
            self.window_found.emit(self.window_title, self.handle)
            self._update_window_rects()
            
            # Save the window title to config
            if hasattr(self, 'config_manager') and self.config_manager:
                self.config_manager.save_last_window_title(self.window_title)
            
        # Setup timer for mouse position tracking
        self._setup_mouse_tracking()
    
    def set_config_manager(self, config_manager):
        """
        Set the configuration manager.
        
        Args:
            config_manager: Configuration manager instance
        """
        self.config_manager = config_manager
        logger.info(f"Config manager set in window manager: {self.config_manager is not None}")
        
        # Try to load saved window title if we don't have a window yet
        if self.config_manager:
            saved_title = self.config_manager.get_last_window_title()
            logger.info(f"Loaded saved window title from config: {saved_title}")
            
            if saved_title:
                # Even if we have a handle, update the title and try to find the window again
                # in case the prior handle was stale or for a different game version
                self.window_title = saved_title
                logger.info(f"Using saved window title: {saved_title}")
                
                # Try to find window with this title
                found_handle = self.find_window(self.window_title)
                if found_handle:
                    self.handle = found_handle
                    logger.info(f"Found window using saved title: {self.window_title} (handle: {self.handle})")
                    self.window_found.emit(self.window_title, self.handle)
                    self._update_window_rects()
    
    def get_window_handle(self) -> Optional[int]:
        """
        Get the handle of the currently tracked window.
        
        Returns:
            Window handle if a window is being tracked, None otherwise
        """
        return self.handle

    def is_valid(self) -> bool:
        """
        Check if the window manager has a valid window.
        
        Returns:
            True if a window is being tracked, False otherwise
        """
        return self.handle is not None

    def is_window_found(self) -> bool:
        """
        Check if the window is currently found and being tracked.
        
        Returns:
            True if window is found, False otherwise
        """
        if not self.handle:
            return False
            
        return win32gui.IsWindow(self.handle)
        
    def get_window_title(self) -> Optional[str]:
        """
        Get the title of the currently tracked window.
        
        Returns:
            Window title if a window is being tracked, None otherwise
        """
        if not self.handle or not win32gui.IsWindow(self.handle):
            return None
            
        try:
            return win32gui.GetWindowText(self.handle)
        except Exception as e:
            logger.error(f"Error getting window title: {e}")
            return None

    def get_window_rect(self) -> Optional[QRect]:
        """
        Get the rectangle of the currently tracked window.
        
        Returns:
            QRect representing the window's position and size, or None if no window is tracked
        """
        if not self.handle or not self.window_rect:
            return None
        
        # Convert the window rect to a QRect
        if isinstance(self.window_rect, QRect):
            return self.window_rect
        elif isinstance(self.window_rect, tuple) and len(self.window_rect) == 4:
            # If it's a tuple (left, top, right, bottom), convert to QRect
            left, top, right, bottom = self.window_rect
            return QRect(left, top, right - left, bottom - top)
        else:
            logger.warning(f"Unexpected window rect format: {self.window_rect}")
            return None
    
    def find_window(self, title: Optional[str] = None) -> Optional[int]:
        """
        Find a window by title.
        
        Args:
            title: Title of the window to find, or None to use the stored window title
        
        Returns:
            Window handle if found, None otherwise
        """
        # Use the provided title or fall back to the stored window title
        title = title if title is not None else self.window_title
        
        # Find all windows with the given title
        results = []
        
        def enum_windows_callback(hwnd, results):
            if win32gui.IsWindowVisible(hwnd):
                window_title = win32gui.GetWindowText(hwnd)
                if title in window_title:
                    results.append((hwnd, window_title))
            return True
        
        win32gui.EnumWindows(enum_windows_callback, results)
        
        if results:
            # Sort by exact match first
            results.sort(key=lambda x: x[1] == title, reverse=True)
            self.handle = results[0][0]
            # Save the full window title for better matching next time
            self.window_title = results[0][1]
            self._update_window_rects()
            self.window_found.emit(self.window_title, self.handle)
            logger.info(f"Found window: '{self.window_title}' (handle: {self.handle})")
            
            # Save the window title to config
            if self.config_manager:
                logger.info(f"Saving window title to config: {self.window_title}")
                self.config_manager.save_last_window_title(self.window_title)
                
            return self.handle
        else:
            logger.warning(f"Window not found: {title}")
            return None
    
    def get_window_rect(self, handle: Optional[int] = None) -> Tuple[int, int, int, int]:
        """
        Get the rectangle (position and size) of a window.
        
        Args:
            handle: Window handle, or None to use the currently selected window
            
        Returns:
            Tuple of (left, top, right, bottom) coordinates
        """
        hwnd = handle if handle is not None else self.handle
        if hwnd:
            try:
                return win32gui.GetWindowRect(hwnd)
            except Exception as e:
                logger.error(f"Error getting window rect: {e}")
        
        return (0, 0, 0, 0)
    
    def get_client_rect(self, handle: Optional[int] = None) -> Tuple[int, int, int, int]:
        """
        Get the client rectangle (position and size) of a window.
        
        Args:
            handle: Window handle, or None to use the currently selected window
            
        Returns:
            Tuple of (left, top, right, bottom) coordinates
        """
        hwnd = handle if handle is not None else self.handle
        if hwnd:
            try:
                rect = win32gui.GetClientRect(hwnd)
                left, top = win32gui.ClientToScreen(hwnd, (0, 0))
                return (left, top, left + rect[2], top + rect[3])
            except Exception as e:
                logger.error(f"Error getting client rect: {e}")
        
        return (0, 0, 0, 0)
    
    def capture_screenshot(self) -> Optional[np.ndarray]:
        """
        Capture a screenshot of the window.
        
        Returns:
            NumPy array containing the screenshot image, or None if failed
        """
        if self.capture_manager is None:
            logger.debug("Creating new CaptureManager instance")
            from scout.screen_capture.capture_manager import CaptureManager
            self.capture_manager = CaptureManager()
        
        if self.handle:
            logger.debug(f"Attempting to capture window with handle: {self.handle}")
            
            # Get window dimensions for logging and capture
            rect = self.get_window_rect()
            if rect:
                left, top, right, bottom = rect
                width = right - left
                height = bottom - top
                logger.debug(f"Window dimensions: ({left}, {top}, {right}, {bottom}) -> {width}x{height}")
                
                try:
                    # Explicitly set window and geometry before capture
                    self.capture_manager.set_window(self.handle, rect)
                    
                    # Now use the capture manager to get the screenshot
                    result = self.capture_manager.capture_window(self.handle)
                    if result is not None:
                        logger.debug(f"Screenshot captured successfully: {result.shape}")
                        
                        # Check if the image dimensions are abnormally different from window size
                        # This can happen with high-DPI displays
                        if result.shape[0] != height or result.shape[1] != width:
                            logger.warning(f"Captured image dimensions ({result.shape[1]}x{result.shape[0]}) differ from window size ({width}x{height})")
                            
                            # This warning is helpful for debugging but we don't need to resize here since
                            # the resize happens in the CaptureManager._capture_window method now
                            
                        return result
                    else:
                        logger.warning("capture_window returned None")
                    return result
                except Exception as e:
                    logger.error(f"Error capturing screenshot: {e}")
            else:
                logger.warning("Could not get window dimensions")
        else:
            logger.warning("Cannot capture screenshot: No window handle available")
        
        return None
    
    def list_windows(self) -> List[WindowInfo]:
        """
        List all visible windows in the system.
        
        Returns:
            List of WindowInfo objects
        """
        windows = []
        
        def enum_windows_callback(hwnd, windows):
            if win32gui.IsWindowVisible(hwnd):
                title = win32gui.GetWindowText(hwnd)
                if title:  # Only include windows with titles
                    class_name = win32gui.GetClassName(hwnd)
                    rect = win32gui.GetWindowRect(hwnd)
                    position = (rect[0], rect[1])
                    size = (rect[2] - rect[0], rect[3] - rect[1])
                    
                    # Get process ID
                    try:
                        _, process_id = win32process.GetWindowThreadProcessId(hwnd)
                        process_name = ""
                    except:
                        process_id = 0
                        process_name = ""
                    
                    window_info = WindowInfo(
                        handle=hwnd,
                        title=title,
                        class_name=class_name,
                        position=position,
                        size=size,
                        process_id=process_id,
                        process_name=process_name
                    )
                    windows.append(window_info)
            return True
        
        win32gui.EnumWindows(enum_windows_callback, windows)
        return windows
    
    def set_foreground(self, handle: Optional[int] = None) -> bool:
        """
        Bring a window to the foreground.
        
        Args:
            handle: Window handle, or None to use the currently selected window
            
        Returns:
            True if successful, False otherwise
        """
        hwnd = handle if handle is not None else self.handle
        if hwnd:
            try:
                win32gui.SetForegroundWindow(hwnd)
                return True
            except Exception as e:
                logger.error(f"Error setting foreground window: {e}")
        
        return False
    
    def update_window_position(self) -> bool:
        """
        Update the stored window position and size.
        
        Returns:
            True if the window was found and updated, False otherwise
        """
        if self.handle:
            old_rect = QRect(self.window_rect)
            self._update_window_rects()
            
            # Check if the window has moved or been resized
            if old_rect != self.window_rect:
                if old_rect.size() != self.window_rect.size():
                    self.window_resized.emit(self.window_rect)
                else:
                    self.window_moved.emit(self.window_rect)
            
            return True
        else:
            # Try to find the window again
            return self.find_window(self.window_title) is not None
    
    def _update_window_rects(self) -> None:
        """Update the stored window and client rectangles."""
        if self.handle:
            try:
                # Get window rect
                left, top, right, bottom = win32gui.GetWindowRect(self.handle)
                self.window_rect = QRect(left, top, right - left, bottom - top)
                
                # Get client rect
                client_rect = win32gui.GetClientRect(self.handle)
                client_left, client_top = win32gui.ClientToScreen(self.handle, (0, 0))
                client_width, client_height = client_rect[2], client_rect[3]
                self.client_rect = QRect(client_left, client_top, client_width, client_height)
            except Exception as e:
                logger.error(f"Error updating window rects: {e}")

    def _setup_mouse_tracking(self) -> None:
        """Set up timer to track mouse position."""
        self.mouse_timer = QTimer()
        self.mouse_timer.timeout.connect(self._check_mouse_position)
        self.mouse_timer.start(50)  # Check every 50ms
    
    def _check_mouse_position(self) -> None:
        """Check current mouse position and emit signal if changed."""
        if not self.handle:
            return
            
        try:
            # Get current mouse position (screen coordinates)
            mouse_pos = win32gui.GetCursorPos()
            
            # Only emit if position changed
            if mouse_pos != self.last_mouse_pos:
                self.last_mouse_pos = mouse_pos
                
                # Adjust to window-relative coordinates
                if self.window_rect:
                    x, y = mouse_pos
                    client_x = x - self.window_rect.left() - self.client_to_window_offset[0]
                    client_y = y - self.window_rect.top() - self.client_to_window_offset[1]
                    
                    # Only emit if mouse is within client area
                    if 0 <= client_x < self.client_rect.width() and 0 <= client_y < self.client_rect.height():
                        self.mouse_moved.emit(client_x, client_y)
        except Exception as e:
            logger.error(f"Error tracking mouse position: {e}")
