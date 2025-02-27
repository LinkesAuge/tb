"""
Base debug window class.

This module provides the base class for debug windows in the Scout application.
"""

from typing import Optional, Dict, Any, List, Tuple
from PyQt6.QtWidgets import (
    QMainWindow, QTabWidget, QWidget, QVBoxLayout, QLabel, 
    QStatusBar, QToolBar, QAction, QMenu
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QIcon, QKeySequence
import logging
import os
from pathlib import Path

logger = logging.getLogger(__name__)

class DebugWindowBase(QMainWindow):
    """
    Base class for debug windows in the Scout application.
    
    This class provides:
    - Common window setup (title, size, position)
    - Tab management
    - Status bar
    - Common actions (save, close)
    - Event handling
    
    Signals:
        window_closed: Emitted when the window is closed
    """
    
    # Signals
    window_closed = pyqtSignal()
    
    def __init__(self, title: str = "Debug Window", parent=None) -> None:
        """
        Initialize the debug window.
        
        Args:
            title: Window title
            parent: Parent widget
        """
        super().__init__(parent)
        
        # Set window properties
        self.setWindowTitle(title)
        self.setGeometry(100, 100, 1200, 800)
        
        # Create central widget and layout
        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        
        self.main_layout = QVBoxLayout(self.central_widget)
        self.main_layout.setContentsMargins(5, 5, 5, 5)
        
        # Create tab widget
        self.tab_widget = QTabWidget()
        self.main_layout.addWidget(self.tab_widget)
        
        # Create status bar
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.status_bar.showMessage("Ready")
        
        # Create toolbar
        self.toolbar = QToolBar("Main Toolbar")
        self.addToolBar(self.toolbar)
        
        # Add common actions
        self._create_actions()
        self._create_menus()
        
        logger.debug(f"Debug window '{title}' initialized")
    
    def _create_actions(self) -> None:
        """Create common actions for the window."""
        # Save action
        self.save_action = QAction("Save", self)
        self.save_action.setShortcut(QKeySequence.StandardKey.Save)
        self.save_action.setStatusTip("Save current view")
        self.save_action.triggered.connect(self._on_save)
        
        # Close action
        self.close_action = QAction("Close", self)
        self.close_action.setShortcut(QKeySequence.StandardKey.Close)
        self.close_action.setStatusTip("Close window")
        self.close_action.triggered.connect(self.close)
    
    def _create_menus(self) -> None:
        """Create menus for the window."""
        # File menu
        self.file_menu = self.menuBar().addMenu("&File")
        self.file_menu.addAction(self.save_action)
        self.file_menu.addSeparator()
        self.file_menu.addAction(self.close_action)
        
        # View menu
        self.view_menu = self.menuBar().addMenu("&View")
    
    def add_tab(self, widget: QWidget, name: str) -> None:
        """
        Add a tab to the window.
        
        Args:
            widget: Widget to add as a tab
            name: Tab name
        """
        self.tab_widget.addTab(widget, name)
        logger.debug(f"Added tab '{name}' to debug window")
    
    def remove_tab(self, name: str) -> None:
        """
        Remove a tab from the window.
        
        Args:
            name: Tab name
        """
        for i in range(self.tab_widget.count()):
            if self.tab_widget.tabText(i) == name:
                self.tab_widget.removeTab(i)
                logger.debug(f"Removed tab '{name}' from debug window")
                return
    
    def set_status(self, message: str) -> None:
        """
        Set status bar message.
        
        Args:
            message: Status message
        """
        self.status_bar.showMessage(message)
    
    def _on_save(self) -> None:
        """Handle save action."""
        # This should be implemented by subclasses
        self.set_status("Save not implemented for this window")
    
    def closeEvent(self, event) -> None:
        """
        Handle window close event.
        
        Args:
            event: Close event
        """
        logger.debug("Debug window closed")
        self.window_closed.emit()
        super().closeEvent(event)