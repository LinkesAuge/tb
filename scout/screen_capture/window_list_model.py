"""
Window List Model

Provides a Qt model for listing all available capturable windows in the system.
"""

import logging
import win32gui
import win32con
from PyQt6.QtCore import Qt, QAbstractListModel, QModelIndex, pyqtSlot, pyqtSignal
from PyQt6.QtGui import QIcon, QPixmap, QImage, QColor, QFont

# Configure logger
logger = logging.getLogger(__name__)

class WindowInfo:
    """
    Class to store window information.
    """
    def __init__(self, hwnd, title, rect=None):
        """
        Initialize window information.
        
        Args:
            hwnd: Window handle
            title: Window title
            rect: Window rectangle (x, y, width, height) or None
        """
        self.handle = hwnd  # Use 'handle' instead of 'hwnd' for compatibility
        self.title = title
        self.rect = rect or self._get_window_rect(hwnd)
    
    def _get_window_rect(self, hwnd):
        """
        Get the window rectangle.
        
        Args:
            hwnd: Window handle
            
        Returns:
            tuple: (x, y, width, height)
        """
        try:
            left, top, right, bottom = win32gui.GetWindowRect(hwnd)
            return (left, top, right - left, bottom - top)
        except Exception as e:
            logger.error(f"Error getting window rect for {hwnd}: {e}")
            return (0, 0, 0, 0)
    
    def __str__(self):
        """
        String representation of the window.
        
        Returns:
            str: Window title and dimensions
        """
        x, y, width, height = self.rect
        return f"{self.title} ({width}x{height})"
        
    @property
    def geometry(self):
        """Property that returns the rect for compatibility."""
        return self.rect

class WindowListModel(QAbstractListModel):
    """
    Model that lists all available capturable windows in the system.
    
    This model provides data for QListView to display available windows.
    It can be refreshed to update the list of windows.
    """
    
    # Signal emitted when the window list changes
    windowsChanged = pyqtSignal()
    
    # Custom roles for data retrieval
    WindowHandleRole = Qt.ItemDataRole.UserRole + 1
    WindowTitleRole = Qt.ItemDataRole.UserRole + 2
    WindowRectRole = Qt.ItemDataRole.UserRole + 3
    
    def __init__(self, parent=None):
        """
        Initialize the window list model.
        
        Args:
            parent: Parent QObject
        """
        super().__init__(parent)
        self._window_list = []
        self.populate()
        logger.debug(f"Initialized WindowListModel with {len(self._window_list)} windows")
    
    def rowCount(self, parent=QModelIndex()):
        """
        Return the number of rows in the model.
        
        Args:
            parent: Parent model index (unused for list models)
            
        Returns:
            int: Number of windows
        """
        if parent.isValid():
            return 0  # List models have no children
        return len(self._window_list)
    
    def data(self, index, role=Qt.ItemDataRole.DisplayRole):
        """
        Return data for the given index and role.
        
        Args:
            index: Model index
            role: Data role
            
        Returns:
            Data for the given role, or None if invalid
        """
        if not index.isValid() or index.row() >= len(self._window_list):
            return None
        
        window_info = self._window_list[index.row()]
        
        if role == Qt.ItemDataRole.DisplayRole:
            # Display name for the window
            return str(window_info)
        
        elif role == self.WindowHandleRole:
            # Return the window handle
            return window_info.handle
        
        elif role == self.WindowTitleRole:
            # Return the window title
            return window_info.title
        
        elif role == self.WindowRectRole:
            # Return the window rectangle
            return window_info.rect
        
        elif role == Qt.ItemDataRole.ToolTipRole:
            # Tooltip with detailed information
            x, y, width, height = window_info.rect
            tooltip = f"Window: {window_info.title}\n"
            tooltip += f"Handle: {window_info.handle}\n"
            tooltip += f"Position: ({x}, {y})\n"
            tooltip += f"Size: {width}x{height}"
            return tooltip
        
        return None
    
    def window(self, index):
        """
        Get the WindowInfo object for the given index.
        
        Args:
            index: Model index or row number
            
        Returns:
            WindowInfo: Window information or None if invalid
        """
        if isinstance(index, QModelIndex):
            row = index.row()
        else:
            row = index
            
        if 0 <= row < len(self._window_list):
            return self._window_list[row]
        
        return None
    
    def get_window_info(self, index):
        """
        Get the WindowInfo object for the given index.
        
        This method is an alias for window() for compatibility with code 
        that expects a get_window_info method.
        
        Args:
            index: Model index or row number
            
        Returns:
            WindowInfo: Window information or None if invalid
        """
        return self.window(index)
    
    def find_window_by_title(self, title_pattern):
        """
        Find a window by its title (partial match).
        
        Args:
            title_pattern: Title pattern to match
            
        Returns:
            int: Index of the first matching window or -1 if not found
        """
        title_pattern = title_pattern.lower()
        for i, window_info in enumerate(self._window_list):
            if title_pattern in window_info.title.lower():
                return i
        return -1
    
    def find_window_by_handle(self, hwnd):
        """
        Find a window by its handle.
        
        Args:
            hwnd: Window handle to find
            
        Returns:
            int: Index of the matching window or -1 if not found
        """
        for i, window_info in enumerate(self._window_list):
            if window_info.handle == hwnd:
                return i
        return -1
    
    @staticmethod
    def _is_capturable_window(hwnd):
        """
        Check if a window is capturable.
        
        A window is considered capturable if it:
        - Is visible
        - Has a non-empty title
        - Has a non-zero size
        - Is not a child window
        
        Args:
            hwnd: Window handle
            
        Returns:
            bool: True if the window is capturable, False otherwise
        """
        if not win32gui.IsWindowVisible(hwnd):
            return False
        
        title = win32gui.GetWindowText(hwnd)
        if not title:
            return False
        
        # Check if window has a size
        try:
            left, top, right, bottom = win32gui.GetWindowRect(hwnd)
            if right - left <= 0 or bottom - top <= 0:
                return False
        except:
            return False
        
        # Check if window has a parent (we want top-level windows)
        if win32gui.GetParent(hwnd) != 0:
            return False
        
        # Check window styles
        style = win32gui.GetWindowLong(hwnd, win32con.GWL_STYLE)
        if not (style & win32con.WS_VISIBLE):
            return False
        
        # Exclude windows with WS_EX_TOOLWINDOW style (tooltips, etc.)
        ex_style = win32gui.GetWindowLong(hwnd, win32con.GWL_EXSTYLE)
        if ex_style & win32con.WS_EX_TOOLWINDOW:
            return False
        
        return True
    
    @staticmethod
    def _enum_windows_callback(hwnd, windows):
        """
        Callback for EnumWindows.
        
        Args:
            hwnd: Window handle
            windows: List to store window information
            
        Returns:
            bool: Always True to continue enumeration
        """
        if WindowListModel._is_capturable_window(hwnd):
            title = win32gui.GetWindowText(hwnd)
            windows.append(WindowInfo(hwnd, title))
        return True
    
    @pyqtSlot()
    def populate(self):
        """
        Populate the model with available windows.
        
        This method clears the current window list and enumerates all
        capturable windows in the system.
        """
        logger.debug("Populating window list model")
        self.beginResetModel()
        self._window_list = []
        
        # Enumerate all windows
        windows = []
        win32gui.EnumWindows(self._enum_windows_callback, windows)
        
        # Sort windows by title
        self._window_list = sorted(windows, key=lambda w: w.title.lower())
        
        self.endResetModel()
        self.windowsChanged.emit()
        logger.debug(f"Window list model populated with {len(self._window_list)} windows")
    
    def refresh(self):
        """
        Refresh the window list.
        
        This method updates the list of available windows by repopulating the model.
        """
        logger.debug("Refreshing window list")
        self.populate()
        return True
    
    def roleNames(self):
        """
        Return the role names for QML integration.
        
        Returns:
            dict: Role names mapping
        """
        roles = super().roleNames()
        roles[self.WindowHandleRole] = b"windowHandle"
        roles[self.WindowTitleRole] = b"windowTitle"
        roles[self.WindowRectRole] = b"windowRect"
        return roles
