from typing import Optional, Tuple, List, Any
import win32gui
import logging
import ctypes
from ctypes.wintypes import RECT, POINT
import numpy as np
import cv2
import mss

logger = logging.getLogger(__name__)

class WindowManager:
    """
    Manages the tracking and interaction with the game window.
    
    This class is responsible for:
    1. Finding the game window by its title
    2. Tracking the window's position and size
    3. Handling window state changes (moved, resized)
    4. Providing window information to other components
    
    The window manager is a critical component that enables:
    - The overlay to stay aligned with the game window
    - Screen capture for pattern matching
    - Coordinate system calculations
    
    It uses the Windows API to interact with window properties and
    maintains the connection between the game window and our application.
    """
    
    def __init__(self, window_title: str) -> None:
        """
        Initialize the window manager for a specific game window.
        
        Sets up tracking for a window with the given title. The manager
        will continuously try to find and maintain a connection to this
        window throughout the application's lifetime.
        
        Args:
            window_title: Title or partial title of the game window to track
        """
        self.window_title = window_title
        self.hwnd = None  # Windows handle to the game window
        logger.debug(f"WindowManager initialized to track window: {window_title}")
    
    def find_window(self) -> bool:
        """
        Find the game window by its title.
        
        Searches through all windows to find one matching our target title.
        Handles partial matches and excludes our own application windows.
        Updates the stored window handle if found.
        
        Returns:
            bool: True if the window was found, False otherwise
        """
        matching_windows = []  # List to store all matching windows
        all_windows = []  # List to store all visible windows for debugging
        
        def enum_windows_callback(hwnd: int, _: Any) -> bool:
            if not win32gui.IsWindowVisible(hwnd):
                return True
            
            window_title = win32gui.GetWindowText(hwnd)
            all_windows.append(window_title)  # Store all window titles for debugging
            
            # Skip our own application windows
            if window_title == "Total Battle Scout" or window_title == "TB Scout Overlay":
                logger.debug(f"Skipping our own window: {window_title}")
                return True
            
            # Look for "Total Battle" anywhere in the window title
            if self.window_title in window_title:
                logger.debug(f"Found matching window: {window_title} (hwnd: {hwnd})")
                matching_windows.append(window_title)  # Add to list of matches
                self.hwnd = hwnd
                return False
            return True
        
        logger.debug(f"Starting window search for title containing: {self.window_title}")
        self.hwnd = None
        win32gui.EnumWindows(enum_windows_callback, None)
        
        # Log all matching windows
        if matching_windows:
            logger.info("Found matching windows:")
            for window in matching_windows:
                logger.info(f"  • {window}")
        else:
            logger.warning(f"No window found matching '{self.window_title}'")
            logger.debug("All visible windows:")
            for window in all_windows:
                logger.debug(f"  • {window}")
        
        return self.hwnd is not None
    
    def get_window_position(self) -> Optional[Tuple[int, int, int, int]]:
        """
        Get the window position and size.
        
        Returns:
            Optional[Tuple[int, int, int, int]]: (x, y, width, height) if window found, None otherwise
        """
        try:
            if not self.find_window():  # Use find_window to get the correct hwnd
                logger.warning(f"Window '{self.window_title}' not found")
                return None
                
            rect = win32gui.GetWindowRect(self.hwnd)  # Use stored hwnd
            x = rect[0]
            y = rect[1]
            width = rect[2] - x
            height = rect[3] - y
            
            # Ensure positive dimensions by adjusting coordinates
            if x < 0:
                width += x  # Reduce width by the negative offset
                x = 0
            if y < 0:
                height += y  # Reduce height by the negative offset
                y = 0
                
            # Ensure minimum dimensions
            width = max(1, width)
            height = max(1, height)
            
            logger.debug(f"Window found at ({x}, {y}) with size {width}x{height}")
            return x, y, width, height
            
        except Exception as e:
            logger.error(f"Error getting window position: {str(e)}", exc_info=True)
            return None 

    def get_client_rect(self) -> Optional[Tuple[int, int, int, int]]:
        """
        Get the client area rectangle of the window.
        
        Returns:
            Optional[Tuple[int, int, int, int]]: (left, top, right, bottom) of client area,
            or None if window not found or error occurs
        """
        try:
            if not self.find_window():
                logger.warning("Window not found when getting client rect")
                return None
                
            # Get window rect
            window_rect = win32gui.GetWindowRect(self.hwnd)
            
            # Get client rect
            client_rect = RECT()
            if not ctypes.windll.user32.GetClientRect(self.hwnd, ctypes.byref(client_rect)):
                logger.error("Failed to get client rect")
                return None
                
            # Get client area position
            client_point = POINT(0, 0)
            if not ctypes.windll.user32.ClientToScreen(self.hwnd, ctypes.byref(client_point)):
                logger.error("Failed to convert client coordinates")
                return None
                
            # Calculate client area in screen coordinates
            client_left = client_point.x
            client_top = client_point.y
            client_right = client_left + (client_rect.right - client_rect.left)
            client_bottom = client_top + (client_rect.bottom - client_rect.top)
            
            logger.debug(f"Client rect: ({client_left}, {client_top}, {client_right}, {client_bottom})")
            return (client_left, client_top, client_right, client_bottom)
            
        except Exception as e:
            logger.error(f"Error getting client rect: {e}")
            return None 

    def client_to_screen(self, x: int, y: int) -> Tuple[int, int]:
        """
        Convert client (window-relative) coordinates to screen coordinates.
        
        Args:
            x: X coordinate relative to window client area
            y: Y coordinate relative to window client area
            
        Returns:
            Tuple[int, int]: Screen coordinates (x, y)
        """
        try:
            if not self.find_window():
                logger.warning("Window not found when converting coordinates")
                return x, y
                
            # Get client area position
            point = POINT(x, y)
            if not ctypes.windll.user32.ClientToScreen(self.hwnd, ctypes.byref(point)):
                logger.error("Failed to convert client coordinates")
                return x, y
                
            return point.x, point.y
            
        except Exception as e:
            logger.error(f"Error converting coordinates: {e}")
            return x, y

    def screen_to_client(self, screen_x: int, screen_y: int) -> Tuple[int, int]:
        """
        Convert screen coordinates to client (window-relative) coordinates.
        
        Args:
            screen_x: X coordinate on screen
            screen_y: Y coordinate on screen
            
        Returns:
            Tuple[int, int]: Client coordinates (x, y)
        """
        try:
            if not self.find_window():
                logger.warning("Window not found when converting coordinates")
                return screen_x, screen_y
                
            # Get client area position
            point = POINT(screen_x, screen_y)
            if not ctypes.windll.user32.ScreenToClient(self.hwnd, ctypes.byref(point)):
                logger.error("Failed to convert screen coordinates")
                return screen_x, screen_y
                
            return point.x, point.y
            
        except Exception as e:
            logger.error(f"Error converting coordinates: {e}")
            return screen_x, screen_y

    def capture_screenshot(self) -> Optional[np.ndarray]:
        """
        Capture a screenshot of the game window.
        
        Returns:
            Optional[np.ndarray]: Screenshot as numpy array in BGR format, or None if failed
        """
        try:
            logger.debug("Attempting to capture screenshot...")
            
            if not self.find_window():
                logger.warning("Window not found when capturing screenshot")
                logger.debug(f"Looking for window with title containing: {self.window_title}")
                return None
                
            logger.debug(f"Found window with handle: {self.hwnd}")
            
            # Get window position and size
            if pos := self.get_window_position():
                x, y, width, height = pos
                logger.debug(f"Window position: x={x}, y={y}, width={width}, height={height}")
                
                # Take screenshot using mss
                try:
                    with mss.mss() as sct:
                        monitor = {"top": y, "left": x, "width": width, "height": height}
                        logger.debug(f"Attempting to capture with monitor settings: {monitor}")
                        screenshot = np.array(sct.grab(monitor))
                        
                        if screenshot is None:
                            logger.error("mss.grab returned None")
                            return None
                            
                        logger.debug(f"Captured image shape before conversion: {screenshot.shape}")
                        
                        # Convert from BGRA to BGR
                        screenshot = cv2.cvtColor(screenshot, cv2.COLOR_BGRA2BGR)
                        logger.debug(f"Converted image shape: {screenshot.shape}")
                        
                        return screenshot
                except Exception as mss_error:
                    logger.error(f"Error during mss capture: {mss_error}", exc_info=True)
                    return None
            else:
                logger.warning("Failed to get window position")
                return None
            
        except Exception as e:
            logger.error(f"Error capturing screenshot: {e}", exc_info=True)
            return None 