"""
Screen and window capture management module.

This module provides the CaptureManager class which handles capturing
screenshots from screens and windows using Qt's native capabilities.
"""

from enum import Enum
import logging
import os
import time
from pathlib import Path
from typing import Optional, List, Dict, Any, Union

import numpy as np
from PyQt6.QtCore import QObject, pyqtSignal, QTimer, QRect
from PyQt6.QtGui import QScreen, QPixmap, QGuiApplication, QImage
from PyQt6.QtWidgets import QApplication

from scout.window_interface import WindowInterface

logger = logging.getLogger(__name__)

class SourceType(Enum):
    """Enumeration of capture source types."""
    SCREEN = 1
    WINDOW = 2

def qimage_to_numpy(qimage: QImage) -> np.ndarray:
    """
    Convert a QImage to a numpy array.
    
    Args:
        qimage: QImage to convert
        
    Returns:
        Numpy array representation of the image
    """
    width = qimage.width()
    height = qimage.height()
    
    # Convert QImage to format that can be easily converted to numpy
    if qimage.format() != QImage.Format.Format_RGB32:
        qimage = qimage.convertToFormat(QImage.Format.Format_RGB32)
    
    # Get pointer to image data
    ptr = qimage.bits()
    ptr.setsize(height * width * 4)
    
    # Create numpy array from data (BGRA format)
    arr = np.frombuffer(ptr, np.uint8).reshape((height, width, 4))
    
    # Convert BGRA to RGB
    return arr[:, :, :3]

class CaptureManager(QObject):
    """
    Manages screen and window capture operations.
    
    This class provides a unified interface for capturing screenshots from
    various sources (screens, windows) and makes them available to other
    components of the application.
    """
    
    # Signals
    frame_captured = pyqtSignal(np.ndarray)  # Emitted when a new frame is captured (as numpy array)
    error_occurred = pyqtSignal(str)         # Emitted when an error occurs
    
    def __init__(self, parent=None):
        """
        Initialize the capture manager.
        
        Args:
            parent: Parent Qt object
        """
        super().__init__(parent)
        
        # Create screenshots directory if it doesn't exist
        self._screenshots_dir = Path("scout/debug_screenshots")
        os.makedirs(self._screenshots_dir, exist_ok=True)
        
        # Initialize capture sources
        self._current_screen: Optional[QScreen] = None
        self._current_window_handle = None
        self._current_window_geometry: Optional[QRect] = None
        self._window_interface: Optional[WindowInterface] = None
        
        # Capture state
        self._last_frame: Optional[np.ndarray] = None
        self._capture_timer = QTimer(self)
        self._capture_timer.timeout.connect(self._take_capture)
        self._capture_active = False
        self._source_type = SourceType.SCREEN
        
        # Initialize with primary screen
        self.set_screen(QGuiApplication.primaryScreen())
    
    def set_window_interface(self, window_interface: WindowInterface) -> None:
        """
        Set the window interface to use for capturing.
        
        This method connects the CaptureManager to a WindowInterface implementation,
        which provides access to window information and capture capabilities.
        
        Args:
            window_interface: The window interface to use
        """
        self._window_interface = window_interface
        
        # If the window interface is valid, switch to window capture mode
        if window_interface and window_interface.is_valid():
            self._source_type = SourceType.WINDOW
            
            # Get window handle and geometry
            handle = window_interface.get_window_handle()
            rect = window_interface.get_window_rect()
            
            if handle and rect:
                self._current_window_handle = handle
                
                # Handle different rect types
                if hasattr(rect, 'x') and hasattr(rect, 'y') and hasattr(rect, 'width') and hasattr(rect, 'height'):
                    # It's already a QRect-like object
                    self._current_window_geometry = QRect(rect.x(), rect.y(), rect.width(), rect.height())
                elif isinstance(rect, tuple) and len(rect) == 4:
                    # It's a tuple (left, top, right, bottom)
                    left, top, right, bottom = rect
                    self._current_window_geometry = QRect(left, top, right - left, bottom - top)
                else:
                    logger.warning(f"Unexpected window rect format: {rect}")
                    self._current_window_geometry = None
                
                logger.info(f"Set window interface: handle={handle}, geometry={rect}")
            else:
                logger.warning("Window interface provided but window information is incomplete")
        else:
            logger.warning("Invalid window interface provided, falling back to screen capture")
            self._source_type = SourceType.SCREEN
    
    def set_screen(self, screen: QScreen) -> None:
        """
        Set the screen to capture from.
        
        Args:
            screen: QScreen object to capture from
        """
        if screen is None:
            self.error_occurred.emit("Cannot set screen: Screen is None")
            return
            
        self._current_screen = screen
        self._current_window_handle = None
        self._current_window_geometry = None
        self._source_type = SourceType.SCREEN
        
        # Take an initial capture
        self._take_capture()
    
    def set_window(self, window_handle, geometry: Optional[QRect] = None) -> None:
        """
        Set the window to capture from.
        
        Args:
            window_handle: Handle to the window to capture
            geometry: Optional window geometry (position and size)
        """
        if window_handle is None:
            self.error_occurred.emit("Cannot set window: Window handle is None")
            return
        
        self._current_window_handle = window_handle
        
        # Convert geometry to QRect if it's not None
        if geometry:
            # Handle different rect types
            if hasattr(geometry, 'x') and hasattr(geometry, 'y') and hasattr(geometry, 'width') and hasattr(geometry, 'height'):
                # It's already a QRect-like object
                self._current_window_geometry = QRect(geometry.x(), geometry.y(), geometry.width(), geometry.height())
                logger.debug(f"Using QRect geometry: {self._current_window_geometry}")
            elif isinstance(geometry, tuple) and len(geometry) == 4:
                # It's a tuple (left, top, right, bottom)
                left, top, right, bottom = geometry
                width = right - left
                height = bottom - top
                self._current_window_geometry = QRect(left, top, width, height)
                logger.debug(f"Converted tuple to QRect: {self._current_window_geometry}")
            else:
                logger.warning(f"Unexpected window geometry format: {geometry}")
                self._current_window_geometry = None
        else:
            self._current_window_geometry = None
            logger.warning("No geometry provided for window capture")
        
        self._source_type = SourceType.WINDOW
        
        # Take an initial capture
        self._take_capture()
    
    def start_capture(self, interval_ms: int = 100) -> None:
        """
        Start continuous capture at the specified interval.
        
        Args:
            interval_ms: Capture interval in milliseconds
        """
        self._capture_timer.setInterval(interval_ms)
        self._capture_timer.start()
        self._capture_active = True
        logger.debug(f"Started continuous capture with interval {interval_ms}ms")
    
    def stop_capture(self) -> None:
        """Stop continuous capture."""
        self._capture_timer.stop()
        self._capture_active = False
        logger.debug("Stopped continuous capture")
    
    def is_capturing(self) -> bool:
        """
        Check if continuous capture is active.
        
        Returns:
            True if continuous capture is active, False otherwise
        """
        return self._capture_active
    
    def get_last_frame(self) -> Optional[np.ndarray]:
        """
        Get the last captured frame.
        
        Returns:
            Last captured frame as numpy array, or None if no frame has been captured
        """
        return self._last_frame
    
    def capture_screenshot(self) -> Optional[np.ndarray]:
        """
        Capture a single screenshot from the current source.
        
        Unlike get_last_frame(), this forces a new capture.
        
        Returns:
            The captured frame as a numpy array, or None if capture failed
        """
        try:
            self._take_capture()
            return self._last_frame
        except Exception as e:
            logger.error(f"Error capturing screenshot: {str(e)}")
            self.error_occurred.emit(f"Failed to capture screenshot: {str(e)}")
            return None
            
    def capture_window(self, window_handle: Optional[int] = None) -> Optional[np.ndarray]:
        """
        Capture a single screenshot from the specified window.
        
        Args:
            window_handle: Optional handle to the window to capture. If None, uses the current window.
        
        Returns:
            The captured frame as a numpy array, or None if capture failed
        """
        try:
            # If a window handle is provided, temporarily set it as the current window
            original_handle = self._current_window_handle
            if window_handle is not None:
                self._current_window_handle = window_handle
            
            # Perform the window capture
            self._capture_window()
            
            # Restore the original window handle if needed
            if window_handle is not None and original_handle != window_handle:
                self._current_window_handle = original_handle
                
            return self._last_frame
        except Exception as e:
            logger.error(f"Error capturing window: {str(e)}")
            self.error_occurred.emit(f"Failed to capture window: {str(e)}")
            return None
            
    def take_screenshot(self) -> Optional[np.ndarray]:
        """
        Alias for capture_screenshot() for compatibility.
        
        Returns:
            The captured frame as a numpy array, or None if capture failed
        """
        return self.capture_screenshot()
    
    def save_screenshot(self, filename: Optional[str] = None) -> Optional[str]:
        """
        Save the last captured frame to a file.
        
        Args:
            filename: Optional filename to use, or None to generate a timestamp-based name
            
        Returns:
            Path to the saved file, or None if save failed
        """
        if self._last_frame is None:
            self.error_occurred.emit("Cannot save screenshot: No frame captured")
            return None
            
        try:
            # Generate filename if not provided
            if filename is None:
                timestamp = time.strftime("%Y%m%d-%H%M%S")
                filename = f"screenshot-{timestamp}.png"
                
            # Ensure path is absolute
            filepath = self._screenshots_dir / filename
            
            # Convert numpy array to QImage
            height, width, channels = self._last_frame.shape
            bytes_per_line = channels * width
            image = QImage(self._last_frame.data, width, height, bytes_per_line, QImage.Format.Format_RGB888)
            
            # Save image
            image.save(str(filepath))
            logger.info(f"Screenshot saved to {filepath}")
            
            return str(filepath)
        except Exception as e:
            self.error_occurred.emit(f"Failed to save screenshot: {str(e)}")
            return None
    
    def _take_capture(self) -> None:
        """Take a capture based on the current source type."""
        try:
            if self._source_type == SourceType.SCREEN:
                self._capture_screen()
            elif self._source_type == SourceType.WINDOW:
                self._capture_window()
            else:
                self.error_occurred.emit(f"Unknown source type: {self._source_type}")
        except Exception as e:
            self.error_occurred.emit(f"Capture error: {str(e)}")
    
    def _capture_screen(self) -> None:
        """Capture the current screen."""
        try:
            if self._current_screen is None:
                self.error_occurred.emit("Cannot capture screen: No screen selected")
                return
                
            # Get screen geometry
            screen_geometry = self._current_screen.geometry()
            
            # Capture screen
            pixmap = self._current_screen.grabWindow(0, 
                                                    screen_geometry.x(), 
                                                    screen_geometry.y(), 
                                                    screen_geometry.width(), 
                                                    screen_geometry.height())
            
            # Convert to numpy array
            image = pixmap.toImage()
            self._last_frame = qimage_to_numpy(image)
            
            # Emit signal
            self.frame_captured.emit(self._last_frame)
        except Exception as e:
            self.error_occurred.emit(f"Screen capture error: {str(e)}")
    
    def _capture_window(self) -> None:
        """Capture the current window."""
        try:
            logger.debug(f"Capture window called - window_interface: {self._window_interface is not None}, window_handle: {self._current_window_handle}, window_geometry: {self._current_window_geometry is not None}")
            
            # If we have a window interface, use it for capture
            if self._window_interface and self._window_interface.is_valid():
                logger.debug("Using window interface for capture")
                frame = self._window_interface.capture_screenshot()
                if frame is not None:
                    logger.debug(f"Successfully captured frame via window interface: {frame.shape}")
                    self._last_frame = frame
                    self.frame_captured.emit(self._last_frame)
                    return
                else:
                    logger.warning("Window interface's capture_screenshot returned None")
            else:
                logger.debug("No valid window interface available, falling back to direct capture")
            
            # If we have a window handle but no geometry, try to get it from the window
            if self._current_window_geometry is None and self._current_window_handle is not None:
                logger.warning(f"Window handle ({self._current_window_handle}) available but geometry is missing")
                self.error_occurred.emit("Window geometry not available")
                return
                
            # Capture window using Qt
            if self._current_window_handle is not None and self._current_window_geometry is not None:
                logger.debug(f"Capturing window with handle {self._current_window_handle} and geometry: {self._current_window_geometry}")
                app = QApplication.instance()
                screen = app.primaryScreen()
                
                # Get DPI scaling factor to correct window dimensions
                dpi_scaling = screen.devicePixelRatio()
                logger.debug(f"Screen DPI scaling factor: {dpi_scaling}")
                
                # Extract width and height from geometry, handling different geometry types
                if hasattr(self._current_window_geometry, 'width') and hasattr(self._current_window_geometry, 'height'):
                    # It's a QRect object
                    width = self._current_window_geometry.width()
                    height = self._current_window_geometry.height()
                    logger.debug(f"Using QRect geometry dimensions: {width}x{height}")
                elif isinstance(self._current_window_geometry, tuple) and len(self._current_window_geometry) == 4:
                    # It's a tuple (left, top, right, bottom)
                    left, top, right, bottom = self._current_window_geometry
                    width = right - left
                    height = bottom - top
                    logger.debug(f"Using tuple geometry dimensions: {width}x{height}")
                elif isinstance(self._current_window_geometry, QRect):
                    # It's a QRect but for some reason width() method is not available
                    width = self._current_window_geometry.width()
                    height = self._current_window_geometry.height()
                    logger.debug(f"Using QRect geometry dimensions: {width}x{height}")
                else:
                    logger.error(f"Unsupported window geometry type: {type(self._current_window_geometry)}")
                    self.error_occurred.emit("Unsupported window geometry type")
                    return
                    
                if width <= 0 or height <= 0:
                    logger.error(f"Invalid window dimensions: {width}x{height}, cannot capture")
                    self.error_occurred.emit(f"Invalid window dimensions: {width}x{height}")
                    return
                
                # Adjust capture dimensions based on DPI scaling to get the correct size from the beginning
                capture_width = width
                capture_height = height
                    
                # For DPI scaling of 1.5 (which produces 5810x3182 from 3873x2121)
                # we need to adjust the dimensions before capture
                if dpi_scaling > 1.0:
                    # Calculate the adjusted dimensions to account for DPI scaling
                    # This prevents capturing at the wrong size
                    capture_width = int(width / dpi_scaling)
                    capture_height = int(height / dpi_scaling)
                    logger.debug(f"Adjusted capture dimensions for DPI scaling: {capture_width}x{capture_height}")
                
                pixmap = screen.grabWindow(
                    self._current_window_handle,
                    0, 0,
                    capture_width,
                    capture_height
                )
                
                # Convert to numpy array
                image = pixmap.toImage()
                frame = qimage_to_numpy(image)
                
                # Check if we still need to resize (as a fallback)
                if frame.shape[1] != width or frame.shape[0] != height:
                    logger.warning(f"Dimensions still don't match after DPI adjustment: got {frame.shape[1]}x{frame.shape[0]}, expected {width}x{height}")
                    try:
                        import cv2
                        frame = cv2.resize(frame, (width, height), interpolation=cv2.INTER_AREA)
                        logger.debug(f"Resized captured image to match expected dimensions: {width}x{height}")
                    except ImportError:
                        logger.warning("OpenCV not available for resizing, using original dimensions")
                    except Exception as e:
                        logger.error(f"Error resizing image: {e}")
                else:
                    logger.debug(f"Captured image dimensions match expected: {width}x{height}")
                
                self._last_frame = frame
                logger.debug(f"Successfully captured window: {self._last_frame.shape}")
                
                # Emit signal
                self.frame_captured.emit(self._last_frame)
            else:
                logger.warning("Cannot capture window: No window handle or geometry available")
                self.error_occurred.emit("Cannot capture window: No window handle or geometry")
        except Exception as e:
            logger.error(f"Window capture error: {str(e)}", exc_info=True)
            self.error_occurred.emit(f"Window capture error: {str(e)}")
