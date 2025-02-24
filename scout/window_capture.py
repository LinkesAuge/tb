from typing import Optional, Tuple, Dict, Any
import win32gui
import win32con
import win32ui
import numpy as np
import mss
import ctypes
from ctypes.wintypes import RECT, POINT
import logging

logger = logging.getLogger(__name__)

class WindowCapture:
    """
    A class for capturing and managing window content across different capture methods.
    
    This class provides unified window capture functionality with support for:
    - DPI awareness
    - Client area detection
    - Multiple capture methods (MSS, Win32 API)
    - Browser-specific adjustments
    - Multi-monitor support
    - Region-specific captures
    """
    
    def __init__(self, window_title: str = None) -> None:
        """
        Initialize window capture with optional window title.
        
        Args:
            window_title: Title or partial title of window to capture. If None, uses desktop.
        """
        # Set DPI awareness
        ctypes.windll.user32.SetProcessDPIAware()
        self.window_title = window_title
        self.hwnd = None
        self.window_rect = (0, 0, 0, 0)
        self.client_rect = RECT()
        self.dpi_scale = 1.0
        
        # Cache for window metrics
        self._client_offset_x = 0
        self._client_offset_y = 0
        self._is_browser = False
        
        # Find window if title provided
        if window_title:
            self.find_window()
        
        logger.debug(f"WindowCapture initialized for window: {window_title}")
    
    def find_window(self) -> bool:
        """
        Find window by title.
        
        Returns:
            bool: True if window found, False otherwise
        """
        if self.window_title is None:
            self.hwnd = win32gui.GetDesktopWindow()
            return True
            
        matching_windows = []
        
        def enum_windows_callback(hwnd: int, _: Any) -> bool:
            if win32gui.IsWindowVisible(hwnd):
                title = win32gui.GetWindowText(hwnd)
                # Skip our own application windows
                if title == "Total Battle Scout" or title == "TB Scout Overlay":
                    return True
                if self.window_title in title:
                    matching_windows.append((hwnd, title))
            return True
        
        win32gui.EnumWindows(enum_windows_callback, None)
        
        if matching_windows:
            self.hwnd = matching_windows[0][0]  # Use first match
            logger.info(f"Found window: {matching_windows[0][1]}")
            
            # Update window metrics
            self._update_window_metrics()
            return True
            
        logger.warning(f"No window found matching: {self.window_title}")
        return False
    
    def _update_window_metrics(self) -> None:
        """Update window position, size, and client area metrics."""
        try:
            # Get window rect
            self.window_rect = win32gui.GetWindowRect(self.hwnd)
            
            # Get client rect
            ctypes.windll.user32.GetClientRect(self.hwnd, ctypes.byref(self.client_rect))
            
            # Get client position
            client_point = POINT(0, 0)
            ctypes.windll.user32.ClientToScreen(self.hwnd, ctypes.byref(client_point))
            
            # Calculate client offset
            self._client_offset_x = client_point.x - self.window_rect[0]
            self._client_offset_y = client_point.y - self.window_rect[1]
            
            # Check if browser
            title = win32gui.GetWindowText(self.hwnd)
            self._is_browser = any(browser in title for browser in ["Chrome", "Firefox", "Edge", "Opera"])
            
            # Get DPI scale
            dc = win32gui.GetDC(self.hwnd)
            try:
                self.dpi_scale = ctypes.windll.gdi32.GetDeviceCaps(dc, 88) / 96.0  # LOGPIXELSX = 88
            finally:
                win32gui.ReleaseDC(self.hwnd, dc)
                
            logger.debug(f"Window metrics updated: offset=({self._client_offset_x}, {self._client_offset_y}), "
                        f"dpi={self.dpi_scale}, is_browser={self._is_browser}")
                        
        except Exception as e:
            logger.error(f"Error updating window metrics: {e}")
    
    def get_window_rect(self) -> Tuple[int, int, int, int]:
        """
        Get window rectangle coordinates.
        
        Returns:
            Tuple[int, int, int, int]: (left, top, right, bottom)
        """
        return self.window_rect
    
    def get_client_rect(self) -> Tuple[int, int, int, int]:
        """
        Get client area rectangle coordinates.
        
        Returns:
            Tuple[int, int, int, int]: (left, top, right, bottom)
        """
        client_left = self.window_rect[0] + self._client_offset_x
        client_top = self.window_rect[1] + self._client_offset_y
        client_right = client_left + (self.client_rect.right - self.client_rect.left)
        client_bottom = client_top + (self.client_rect.bottom - self.client_rect.top)
        return (client_left, client_top, client_right, client_bottom)
    
    def capture_screenshot(self, method: str = "mss", region: Optional[Dict[str, int]] = None) -> Optional[np.ndarray]:
        """
        Capture window screenshot using specified method.
        
        Args:
            method: Capture method ("mss" or "win32")
            region: Optional region to capture {left, top, width, height}. If None, captures entire window.
            
        Returns:
            Optional[np.ndarray]: Screenshot as numpy array or None if failed
        """
        if not region and not self.find_window():
            return None
            
        try:
            if method == "mss":
                return self._capture_mss(region)
            elif method == "win32":
                return self._capture_win32(region)
            else:
                logger.error(f"Unknown capture method: {method}")
                return None
                
        except Exception as e:
            logger.error(f"Error capturing screenshot: {e}")
            return None
    
    def _capture_mss(self, region: Optional[Dict[str, int]] = None) -> Optional[np.ndarray]:
        """
        Capture using MSS.
        
        Args:
            region: Optional region to capture. If None, captures entire window/client area.
        """
        with mss.mss() as sct:
            if region:
                monitor = region
            else:
                client_rect = self.get_client_rect()
                if not client_rect:
                    logger.error("Failed to get client rect for capture")
                    return None
                    
                monitor = {
                    "left": client_rect[0],
                    "top": client_rect[1],
                    "width": client_rect[2] - client_rect[0],
                    "height": client_rect[3] - client_rect[1],
                    "mon": 0
                }
                
            screenshot = np.array(sct.grab(monitor))
            return screenshot
    
    def _capture_win32(self, region: Optional[Dict[str, int]] = None) -> Optional[np.ndarray]:
        """
        Capture using Win32 API.
        
        Args:
            region: Optional region to capture. If None, captures entire window/client area.
        """
        if region:
            width = region["width"]
            height = region["height"]
            x_offset = region["left"]
            y_offset = region["top"]
        else:
            client_rect = self.get_client_rect()
            if not client_rect:
                return None
            x_offset = self._client_offset_x
            y_offset = self._client_offset_y
            width = client_rect[2] - client_rect[0]
            height = client_rect[3] - client_rect[1]
        
        # Create device contexts and bitmap
        wDC = win32gui.GetWindowDC(self.hwnd)
        dcObj = win32ui.CreateDCFromHandle(wDC)
        cDC = dcObj.CreateCompatibleDC()
        dataBitMap = win32ui.CreateBitmap()
        dataBitMap.CreateCompatibleBitmap(dcObj, width, height)
        cDC.SelectObject(dataBitMap)
        
        try:
            # Copy window content
            cDC.BitBlt((0, 0), (width, height), 
                      dcObj, 
                      (x_offset, y_offset), 
                      win32con.SRCCOPY)
            
            # Convert to numpy array
            signedIntsArray = dataBitMap.GetBitmapBits(True)
            img = np.frombuffer(signedIntsArray, dtype='uint8')
            img.shape = (height, width, 4)
            
            # Remove alpha channel
            return img[..., :3]
            
        finally:
            # Clean up
            dcObj.DeleteDC()
            cDC.DeleteDC()
            win32gui.ReleaseDC(self.hwnd, wDC)
            win32gui.DeleteObject(dataBitMap.GetHandle())
    
    def convert_to_client_coords(self, screen_x: int, screen_y: int) -> Tuple[int, int]:
        """
        Convert screen coordinates to client area coordinates.
        
        Args:
            screen_x: Screen X coordinate
            screen_y: Screen Y coordinate
            
        Returns:
            Tuple[int, int]: (client_x, client_y)
        """
        client_x = screen_x - (self.window_rect[0] + self._client_offset_x)
        client_y = screen_y - (self.window_rect[1] + self._client_offset_y)
        return (client_x, client_y)
    
    def convert_to_screen_coords(self, client_x: int, client_y: int) -> Tuple[int, int]:
        """
        Convert client area coordinates to screen coordinates.
        
        Args:
            client_x: Client area X coordinate
            client_y: Client area Y coordinate
            
        Returns:
            Tuple[int, int]: (screen_x, screen_y)
        """
        screen_x = client_x + (self.window_rect[0] + self._client_offset_x)
        screen_y = client_y + (self.window_rect[1] + self._client_offset_y)
        return (screen_x, screen_y) 