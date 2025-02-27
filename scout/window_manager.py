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
import win32ui
from ctypes import windll
import cv2

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
    
    def clear_screenshot_cache(self) -> None:
        """
        Clear any cached screenshots to ensure fresh captures.
        This should be called when the application needs to guarantee a fresh screenshot.
        """
        if hasattr(self, '_last_screenshot'):
            self._last_screenshot = None
            logger.debug("Screenshot cache cleared")
        
        # Clear any other cached images or data
        if hasattr(self, '_last_capture_time'):
            self._last_capture_time = 0.0
            
        logger.debug("Screenshot cache and capture time reset")

    def capture_screenshot(self, force_update: bool = False) -> Optional[np.ndarray]:
        """
        Capture a screenshot of the current window.
        
        Args:
            force_update: If True, ignore any cached screenshots and force a new capture
            
        Returns:
            Screenshot as numpy array, or None if capture failed
        """
        # If we're forcing an update, clear any cached screenshot
        if force_update and hasattr(self, '_last_screenshot'):
            self._last_screenshot = None
            logger.debug("Forced fresh screenshot capture")
        
        try:
            # Make sure we have a valid window
            if not self.handle:
                if not self.find_window():
                    logger.warning("Cannot capture screenshot - no window handle")
                    return None
            
            # Check if window is still valid
            if not win32gui.IsWindow(self.handle):
                logger.warning("Window handle is no longer valid, attempting to find window again")
                if not self.find_window():
                    logger.warning("Failed to find window, cannot capture screenshot")
                    return None
            
            # Get window dimensions
            try:
                rect = win32gui.GetWindowRect(self.handle)
                x, y, right, bottom = rect
                width = right - x
                height = bottom - y
                
                # Log window dimensions for debugging
                logger.debug(f"Window dimensions: {rect} -> {width}x{height}")
                
                # Validate window dimensions
                if width <= 0 or height <= 0:
                    logger.warning(f"Invalid window dimensions: {width}x{height}")
                    return None
                    
                # Check if dimensions have changed since last capture
                if hasattr(self, '_last_dimensions') and self._last_dimensions != (width, height):
                    logger.debug(f"Window dimensions changed from {self._last_dimensions} to {width}x{height}")
                    # Force a fresh capture when dimensions change
                    force_update = True
                    
                # Store current dimensions for future comparison
                self._last_dimensions = (width, height)
                
            except Exception as e:
                logger.error(f"Error getting window dimensions: {e}")
                return None
            
            # Use CaputreManager for the actual screenshot
            if hasattr(self, 'capture_manager') and self.capture_manager:
                # Convert tuple to QRect for capture manager
                rect = QRect(x, y, width, height)
                self.window_rect = rect  # Update stored rect
                
                # Get screenshot with force_update parameter
                if hasattr(self.capture_manager, 'capture_window_with_force'):
                    # Use the force_update version if available
                    screenshot = self.capture_manager.capture_window_with_force(
                        self.handle, rect, force_update
                    )
                else:
                    # Fall back to regular method
                    screenshot = self.capture_manager.capture_window(
                        self.handle, rect
                    )
                    
                if screenshot is not None:
                    logger.debug(f"Screenshot captured successfully: {screenshot.shape}")
                    return screenshot
                else:
                    logger.warning("Failed to capture screenshot with capture manager")
            
            # Fallback to direct capturing if capture manager failed or is not available
            logger.debug("Using fallback screenshot capture method")
            
            # Get device context
            hwnd_dc = win32gui.GetWindowDC(self.handle)
            mfc_dc = win32ui.CreateDCFromHandle(hwnd_dc)
            save_dc = mfc_dc.CreateCompatibleDC()
            
            # Create bitmap
            save_bitmap = win32ui.CreateBitmap()
            save_bitmap.CreateCompatibleBitmap(mfc_dc, width, height)
            save_dc.SelectObject(save_bitmap)
            
            # Copy screen to bitmap
            result = windll.user32.PrintWindow(self.handle, save_dc.GetSafeHdc(), 0)
            
            if result == 0:
                logger.warning("PrintWindow failed in fallback capture method")
                # Clean up
                win32gui.DeleteObject(save_bitmap.GetHandle())
                save_dc.DeleteDC()
                mfc_dc.DeleteDC()
                win32gui.ReleaseDC(self.handle, hwnd_dc)
                return None
            
            # Convert bitmap to numpy array
            bmpinfo = save_bitmap.GetInfo()
            bmpstr = save_bitmap.GetBitmapBits(True)
            img = np.frombuffer(bmpstr, dtype='uint8')
            img.shape = (height, width, 4)  # RGBA
            
            # Clean up
            win32gui.DeleteObject(save_bitmap.GetHandle())
            save_dc.DeleteDC()
            mfc_dc.DeleteDC()
            win32gui.ReleaseDC(self.handle, hwnd_dc)
            
            # Convert to BGR format
            img = cv2.cvtColor(img, cv2.COLOR_RGBA2BGR)
            
            logger.debug(f"Fallback screenshot captured successfully: {img.shape}")
            return img
            
        except Exception as e:
            logger.error(f"Error capturing screenshot: {e}", exc_info=True)
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
