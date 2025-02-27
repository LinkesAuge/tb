"""
Screen List Model

Provides a Qt model for listing all available screens/monitors in the system.
"""

import logging
from PyQt6.QtCore import Qt, QAbstractListModel, QModelIndex, pyqtSlot, pyqtSignal
from PyQt6.QtGui import QGuiApplication

# Configure logger
logger = logging.getLogger(__name__)

class ScreenInfo:
    """
    Class to store screen information.
    """
    def __init__(self, screen, index):
        """
        Initialize screen information.
        
        Args:
            screen: QScreen object
            index: Screen index
        """
        self.screen = screen
        self.index = index
        self.name = screen.name()
        self.geometry = screen.geometry()
        self.is_primary = screen.virtualGeometry().topLeft() == screen.geometry().topLeft()
        self.manufacturer = screen.manufacturer() if hasattr(screen, 'manufacturer') else ""
        self.model = screen.model() if hasattr(screen, 'model') else ""
        self.serial_number = screen.serialNumber() if hasattr(screen, 'serialNumber') else ""
        self.dpi = screen.physicalDotsPerInch()
    
    def __str__(self):
        """
        String representation of the screen.
        
        Returns:
            str: Screen name and dimensions
        """
        width = self.geometry.width()
        height = self.geometry.height()
        primary_text = " (Primary)" if self.is_primary else ""
        return f"Screen {self.index}: {width}x{height}{primary_text}"

class ScreenListModel(QAbstractListModel):
    """
    Model that lists all available screens/monitors in the system.
    
    This model provides data for QListView to display available screens.
    It automatically updates when screens are added or removed.
    """
    
    # Signal emitted when the screen list changes
    screensChanged = pyqtSignal()
    
    # Custom roles for data retrieval
    ScreenIndexRole = Qt.ItemDataRole.UserRole + 1
    ScreenNameRole = Qt.ItemDataRole.UserRole + 2
    ScreenGeometryRole = Qt.ItemDataRole.UserRole + 3
    IsPrimaryRole = Qt.ItemDataRole.UserRole + 4
    
    def __init__(self, parent=None):
        """
        Initialize the screen list model.
        
        Args:
            parent: Parent QObject
        """
        super().__init__(parent)
        self._screen_list = []
        
        # Connect to screen change signals
        app = QGuiApplication.instance()
        app.screenAdded.connect(self.screens_changed)
        app.screenRemoved.connect(self.screens_changed)
        app.primaryScreenChanged.connect(self.screens_changed)
        
        # Initial population
        self._populate_screens()
        logger.debug(f"Initialized ScreenListModel with {len(self._screen_list)} screens")
    
    def rowCount(self, parent=QModelIndex()):
        """
        Return the number of rows in the model.
        
        Args:
            parent: Parent model index (unused for list models)
            
        Returns:
            int: Number of screens
        """
        if parent.isValid():
            return 0  # List models have no children
        return len(self._screen_list)
    
    def data(self, index, role=Qt.ItemDataRole.DisplayRole):
        """
        Return data for the given index and role.
        
        Args:
            index: Model index
            role: Data role
            
        Returns:
            Data for the given role, or None if invalid
        """
        if not index.isValid() or index.row() >= len(self._screen_list):
            return None
        
        screen_info = self._screen_list[index.row()]
        
        if role == Qt.ItemDataRole.DisplayRole:
            # Display name for the screen
            return str(screen_info)
        
        elif role == self.ScreenIndexRole:
            # Return the screen index
            return screen_info.index
        
        elif role == self.ScreenNameRole:
            # Return the screen name
            return screen_info.name
        
        elif role == self.ScreenGeometryRole:
            # Return the screen geometry
            return screen_info.geometry
        
        elif role == self.IsPrimaryRole:
            # Return whether this is the primary screen
            return screen_info.is_primary
        
        elif role == Qt.ItemDataRole.ToolTipRole:
            # Tooltip with detailed information
            tooltip = f"Screen: {screen_info.name}\n"
            tooltip += f"Resolution: {screen_info.geometry.width()}x{screen_info.geometry.height()}\n"
            tooltip += f"Position: ({screen_info.geometry.x()}, {screen_info.geometry.y()})\n"
            tooltip += f"DPI: {screen_info.dpi:.1f}\n"
            
            if screen_info.manufacturer or screen_info.model:
                tooltip += f"Manufacturer: {screen_info.manufacturer}\n"
                tooltip += f"Model: {screen_info.model}\n"
            
            if screen_info.is_primary:
                tooltip += "Primary Display"
            
            return tooltip
        
        return None
    
    def screen(self, index):
        """
        Get the ScreenInfo object for the given index.
        
        Args:
            index: Model index or row number
            
        Returns:
            ScreenInfo: Screen information or None if invalid
        """
        if isinstance(index, QModelIndex):
            row = index.row()
        else:
            row = index
            
        if 0 <= row < len(self._screen_list):
            return self._screen_list[row]
        
        return None
    
    def get_screen(self, index):
        """
        Get the ScreenInfo object for the given index.
        
        This method is an alias for screen() for compatibility with code 
        that expects a get_screen method.
        
        Args:
            index: Model index or row number
            
        Returns:
            ScreenInfo: Screen information or None if invalid
        """
        return self.screen(index)
    
    def get_primary_screen_index(self):
        """
        Get the index of the primary screen.
        
        Returns:
            int: Index of the primary screen or 0 if not found
        """
        for i, screen_info in enumerate(self._screen_list):
            if screen_info.is_primary:
                return i
        return 0  # Default to first screen if primary not found
    
    def _populate_screens(self):
        """
        Populate the model with all available screens.
        """
        # Begin model reset
        self.beginResetModel()
        
        # Clear the current list
        self._screen_list = []
        
        # Get all screens
        app = QGuiApplication.instance()
        screens = app.screens()
        
        # Create ScreenInfo objects
        for i, screen in enumerate(screens):
            self._screen_list.append(ScreenInfo(screen, i))
        
        # End model reset
        self.endResetModel()
        
        logger.debug(f"Populated screen list with {len(self._screen_list)} screens")
    
    @pyqtSlot()
    def screens_changed(self):
        """
        Handle screen changes (added, removed, primary changed).
        """
        logger.debug("Screen configuration changed, updating model")
        self._populate_screens()
        self.screensChanged.emit()
    
    def roleNames(self):
        """
        Return the role names for QML integration.
        
        Returns:
            dict: Role names mapping
        """
        roles = super().roleNames()
        roles[self.ScreenIndexRole] = b"screenIndex"
        roles[self.ScreenNameRole] = b"screenName"
        roles[self.ScreenGeometryRole] = b"screenGeometry"
        roles[self.IsPrimaryRole] = b"isPrimary"
        return roles
