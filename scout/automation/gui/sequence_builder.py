"""
Sequence Builder

This module provides a UI for building and editing automation sequences.
It allows users to create, edit, and manage actions within a sequence.
"""

import os
import json
import logging
from typing import Dict, List, Optional, Any, Tuple, Union, Callable

from PyQt6.QtCore import Qt, pyqtSignal, QModelIndex
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QListWidget, QListWidgetItem,
    QLabel, QMessageBox, QMenu, QInputDialog, QDialog, QLineEdit, QComboBox,
    QSpinBox, QDoubleSpinBox, QCheckBox, QTabWidget, QTextEdit, QFileDialog,
    QGroupBox, QFormLayout, QDialogButtonBox, QAbstractItemView, QSplitter
)
from PyQt6.QtGui import QIcon, QAction, QDrag, QPixmap, QPainter, QColor

from scout.automation.core import AutomationSequence, AutomationAction
from scout.automation.action_handlers_basic import BasicActionHandlers
from scout.automation.action_handlers_flow import FlowActionHandlers
from scout.automation.action_handlers_advanced_flow import AdvancedFlowActionHandlers
from scout.automation.action_handlers_data import DataActionHandlers
from scout.automation.action_handlers_visual import VisualActionHandlers
from scout.automation.gui.action_editor import ActionEditorDialog, ACTION_TYPES

logger = logging.getLogger(__name__)

class SequenceBuilder(QWidget):
    """
    Widget for building and editing automation sequences.
    
    This widget provides a UI for creating, editing, and managing actions
    within an automation sequence. It includes a list of actions, buttons
    for adding, editing, and removing actions, and the ability to reorder
    actions via drag and drop.
    """
    
    sequence_changed = pyqtSignal()
    
    def __init__(self, parent=None):
        """Initialize the sequence builder widget."""
        super().__init__(parent)
        self.sequence = AutomationSequence("New Sequence")
        self.init_ui()
        
    def init_ui(self):
        """Initialize the UI components."""
        # Main layout
        layout = QVBoxLayout()
        self.setLayout(layout)
        
        # Sequence name and description
        name_layout = QHBoxLayout()
        name_layout.addWidget(QLabel("Sequence Name:"))
        self.name_edit = QLineEdit(self.sequence.name)
        self.name_edit.textChanged.connect(self._on_name_changed)
        name_layout.addWidget(self.name_edit)
        layout.addLayout(name_layout)
        
        desc_layout = QHBoxLayout()
        desc_layout.addWidget(QLabel("Description:"))
        self.desc_edit = QLineEdit(self.sequence.description or "")
        self.desc_edit.textChanged.connect(self._on_description_changed)
        desc_layout.addWidget(self.desc_edit)
        layout.addLayout(desc_layout)
        
        # Actions list
        layout.addWidget(QLabel("Actions:"))
        self.actions_list = QListWidget()
        self.actions_list.setDragDropMode(QAbstractItemView.DragDropMode.InternalMove)
        self.actions_list.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.actions_list.itemSelectionChanged.connect(self._on_selection_changed)
        self.actions_list.model().rowsMoved.connect(self._on_rows_moved)
        layout.addWidget(self.actions_list)
        
        # Action buttons
        buttons_layout = QHBoxLayout()
        
        self.add_btn = QPushButton("Add Action")
        self.add_btn.clicked.connect(self._on_add_action)
        buttons_layout.addWidget(self.add_btn)
        
        self.edit_btn = QPushButton("Edit Action")
        self.edit_btn.clicked.connect(self._on_edit_action)
        self.edit_btn.setEnabled(False)
        buttons_layout.addWidget(self.edit_btn)
        
        self.remove_btn = QPushButton("Remove Action")
        self.remove_btn.clicked.connect(self._on_remove_action)
        self.remove_btn.setEnabled(False)
        buttons_layout.addWidget(self.remove_btn)
        
        layout.addLayout(buttons_layout)
        
        # Refresh the actions list
        self._refresh_actions_list()
    
    def _on_name_changed(self, name):
        """Handle sequence name changes."""
        self.sequence.name = name
        self.sequence_changed.emit()
    
    def _on_description_changed(self, description):
        """Handle sequence description changes."""
        self.sequence.description = description
        self.sequence_changed.emit()
    
    def _on_selection_changed(self):
        """Handle selection changes in the actions list."""
        selected = len(self.actions_list.selectedItems()) > 0
        self.edit_btn.setEnabled(selected)
        self.remove_btn.setEnabled(selected)
    
    def _on_rows_moved(self, parent, start, end, destination, row):
        """Handle rows being moved in the actions list."""
        # Update the sequence actions order
        actions = []
        for i in range(self.actions_list.count()):
            item = self.actions_list.item(i)
            action_index = item.data(Qt.ItemDataRole.UserRole)
            actions.append(self.sequence.actions[action_index])
        
        self.sequence.actions = actions
        self._refresh_actions_list()
        self.sequence_changed.emit()
    
    def _on_add_action(self):
        """Handle add action button click."""
        dialog = ActionEditorDialog(self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            action = dialog.get_action()
            self.sequence.actions.append(action)
            self._refresh_actions_list()
            self.sequence_changed.emit()
    
    def _on_edit_action(self):
        """Handle edit action button click."""
        selected_items = self.actions_list.selectedItems()
        if not selected_items:
            return
        
        item = selected_items[0]
        action_index = item.data(Qt.ItemDataRole.UserRole)
        action = self.sequence.actions[action_index]
        
        dialog = ActionEditorDialog(self, action)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            updated_action = dialog.get_action()
            self.sequence.actions[action_index] = updated_action
            self._refresh_actions_list()
            self.sequence_changed.emit()
    
    def _on_remove_action(self):
        """Handle remove action button click."""
        selected_items = self.actions_list.selectedItems()
        if not selected_items:
            return
        
        item = selected_items[0]
        action_index = item.data(Qt.ItemDataRole.UserRole)
        
        # Confirm deletion
        confirm = QMessageBox.question(
            self,
            "Confirm Deletion",
            "Are you sure you want to delete this action?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if confirm == QMessageBox.StandardButton.Yes:
            del self.sequence.actions[action_index]
            self._refresh_actions_list()
            self.sequence_changed.emit()
    
    def _refresh_actions_list(self):
        """Refresh the actions list with current sequence actions."""
        self.actions_list.clear()
        
        for i, action in enumerate(self.sequence.actions):
            action_type = action.action_type
            action_info = ACTION_TYPES.get(action_type, {"name": "Unknown"})
            
            # Get description if available
            description = ""
            if hasattr(action.params, "description") and action.params.description:
                description = f" - {action.params.description}"
            
            item_text = f"{i+1}. {action_info['name']}{description}"
            item = QListWidgetItem(item_text)
            item.setData(Qt.ItemDataRole.UserRole, i)
            self.actions_list.addItem(item)
    
    def set_sequence(self, sequence: AutomationSequence):
        """Set the sequence to edit."""
        self.sequence = sequence
        self.name_edit.setText(sequence.name)
        self.desc_edit.setText(sequence.description or "")
        self._refresh_actions_list()
    
    def get_sequence(self) -> AutomationSequence:
        """Get the current sequence."""
        return self.sequence


class SequenceBuilderDialog(QDialog):
    """
    Dialog for building and editing automation sequences.
    
    This dialog wraps the SequenceBuilder widget and adds OK/Cancel buttons.
    """
    
    def __init__(self, parent=None, sequence: Optional[AutomationSequence] = None):
        """
        Initialize the sequence builder dialog.
        
        Args:
            parent: Parent widget
            sequence: Optional sequence to edit
        """
        super().__init__(parent)
        self.setWindowTitle("Sequence Builder")
        self.resize(800, 600)
        
        # Main layout
        layout = QVBoxLayout()
        self.setLayout(layout)
        
        # Sequence builder widget
        self.builder = SequenceBuilder(self)
        if sequence:
            self.builder.set_sequence(sequence)
        layout.addWidget(self.builder)
        
        # Dialog buttons
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)
    
    def get_sequence(self) -> AutomationSequence:
        """Get the current sequence."""
        return self.builder.get_sequence()
