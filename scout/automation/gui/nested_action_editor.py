"""
Nested Action Editor

This module provides a dialog for editing nested actions in flow control actions.
"""

from typing import List, Dict, Any, Optional
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QPushButton,
    QListWidget, QListWidgetItem, QMenu, QMessageBox
)
from PyQt6.QtCore import Qt, pyqtSignal
import logging
from scout.automation.actions import ActionType

logger = logging.getLogger(__name__)

class NestedActionEditor(QDialog):
    """Dialog for editing nested actions."""
    
    def __init__(self, actions: List[Dict[str, Any]], parent=None):
        """
        Initialize the nested action editor.
        
        Args:
            actions: List of action dictionaries
            parent: Parent widget
        """
        super().__init__(parent)
        self.actions = actions.copy() if actions else []
        
        self.setWindowTitle("Edit Nested Actions")
        self.resize(600, 400)
        
        self.setup_ui()
    
    def setup_ui(self):
        """Set up the dialog UI."""
        layout = QVBoxLayout(self)
        
        # Action list
        self.action_list = QListWidget()
        self.action_list.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.action_list.customContextMenuRequested.connect(self._show_context_menu)
        layout.addWidget(self.action_list)
        
        # Refresh the action list
        self._refresh_action_list()
        
        # Buttons
        button_layout = QHBoxLayout()
        
        # Add action button
        self.add_btn = QPushButton("Add Action")
        self.add_btn.clicked.connect(self._add_action)
        button_layout.addWidget(self.add_btn)
        
        # Edit action button
        self.edit_btn = QPushButton("Edit Action")
        self.edit_btn.clicked.connect(self._edit_action)
        button_layout.addWidget(self.edit_btn)
        
        # Remove action button
        self.remove_btn = QPushButton("Remove Action")
        self.remove_btn.clicked.connect(self._remove_action)
        button_layout.addWidget(self.remove_btn)
        
        # Move up button
        self.up_btn = QPushButton("Move Up")
        self.up_btn.clicked.connect(self._move_up)
        button_layout.addWidget(self.up_btn)
        
        # Move down button
        self.down_btn = QPushButton("Move Down")
        self.down_btn.clicked.connect(self._move_down)
        button_layout.addWidget(self.down_btn)
        
        layout.addLayout(button_layout)
        
        # Dialog buttons
        dialog_buttons = QHBoxLayout()
        
        # OK button
        self.ok_btn = QPushButton("OK")
        self.ok_btn.clicked.connect(self.accept)
        dialog_buttons.addWidget(self.ok_btn)
        
        # Cancel button
        self.cancel_btn = QPushButton("Cancel")
        self.cancel_btn.clicked.connect(self.reject)
        dialog_buttons.addWidget(self.cancel_btn)
        
        layout.addLayout(dialog_buttons)
    
    def _refresh_action_list(self):
        """Refresh the action list."""
        self.action_list