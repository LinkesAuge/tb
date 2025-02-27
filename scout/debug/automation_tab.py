"""
Automation debug tab for debug window.

This module provides a tab for debugging automation sequences and actions.
"""

from typing import Optional, Dict, Any, List, Tuple
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QTableWidget, QTableWidgetItem,
    QPushButton, QTextEdit, QGroupBox, QSplitter, QComboBox, QCheckBox
)
from PyQt6.QtCore import Qt, pyqtSignal
import logging

logger = logging.getLogger(__name__)

class AutomationTab(QWidget):
    """
    A tab for debugging automation sequences and actions.
    
    This widget provides:
    - Execution control (pause, resume, step)
    - Action inspection
    - Variable inspection
    - Execution log
    """
    
    # Signals
    pause_execution = pyqtSignal()
    resume_execution = pyqtSignal()
    step_execution = pyqtSignal()
    
    def __init__(self) -> None:
        """Initialize automation tab."""
        super().__init__()
        
        # Create layout
        layout = QVBoxLayout()
        
        # Create splitter for resizable sections
        splitter = QSplitter(Qt.Orientation.Vertical)
        
        # Top section - Execution control and status
        top_widget = QWidget()
        top_layout = QVBoxLayout(top_widget)
        
        # Execution control
        control_group = QGroupBox("Execution Control")
        control_layout = QHBoxLayout()
        
        # Pause button
        self.pause_btn = QPushButton("Pause")
        self.pause_btn.setToolTip("Pause automation execution")
        self.pause_btn.clicked.connect(self._on_pause)
        control_layout.addWidget(self.pause_btn)
        
        # Resume button
        self.resume_btn = QPushButton("Resume")
        self.resume_btn.setToolTip("Resume automation execution")
        self.resume_btn.clicked.connect(self._on_resume)
        self.resume_btn.setEnabled(False)
        control_layout.addWidget(self.resume_btn)
        
        # Step button
        self.step_btn = QPushButton("Step")
        self.step_btn.setToolTip("Execute next action")
        self.step_btn.clicked.connect(self._on_step)
        self.step_btn.setEnabled(False)
        control_layout.addWidget(self.step_btn)
        
        control_group.setLayout(control_layout)
        top_layout.addWidget(control_group)
        
        # Status
        status_group = QGroupBox("Status")
        status_layout = QVBoxLayout()
        
        # Status label
        self.status_label = QLabel("Not running")
        status_layout.addWidget(self.status_label)
        
        # Current action label
        self.action_label = QLabel("Current action: None")
        status_layout.addWidget(self.action_label)
        
        status_group.setLayout(status_layout)
        top_layout.addWidget(status_group)
        
        # Add top widget to splitter
        splitter.addWidget(top_widget)
        
        # Middle section - Action and variable inspection
        middle_widget = QWidget()
        middle_layout = QHBoxLayout(middle_widget)
        
        # Action table
        action_group = QGroupBox("Actions")
        action_layout = QVBoxLayout()
        
        self.action_table = QTableWidget()
        self.action_table.setColumnCount(4)
        self.action_table.setHorizontalHeaderLabels(["ID", "Type", "Target", "Status"])
        self.action_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        action_layout.addWidget(self.action_table)
        
        action_group.setLayout(action_layout)
        middle_layout.addWidget(action_group)
        
        # Variable table
        var_group = QGroupBox("Variables")
        var_layout = QVBoxLayout()
        
        self.var_table = QTableWidget()
        self.var_table.setColumnCount(2)
        self.var_table.setHorizontalHeaderLabels(["Name", "Value"])
        var_layout.addWidget(self.var_table)
        
        var_group.setLayout(var_layout)
        middle_layout.addWidget(var_group)
        
        # Add middle widget to splitter
        splitter.addWidget(middle_widget)
        
        # Bottom section - Log
        bottom_widget = QWidget()
        bottom_layout = QVBoxLayout(bottom_widget)
        
        # Log group
        log_group = QGroupBox("Execution Log")
        log_layout = QVBoxLayout()
        
        # Log text edit
        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        log_layout.addWidget(self.log_text)
        
        log_group.setLayout(log_layout)
        bottom_layout.addWidget(log_group)
        
        # Add bottom widget to splitter
        splitter.addWidget(bottom_widget)
        
        # Add splitter to layout
        layout.addWidget(splitter)
        
        # Set layout
        self.setLayout(layout)
        
        logger.debug("Automation tab initialized")
    
    def update_status(self, status: str) -> None:
        """
        Update the status display.
        
        Args:
            status: Status text
        """
        self.status_label.setText(status)
    
    def update_current_action(self, action_id: str, action_type: str, target: str) -> None:
        """
        Update the current action display.
        
        Args:
            action_id: Action ID
            action_type: Action type
            target: Action target
        """
        self.action_label.setText(f"Current action: {action_id} ({action_type}) - {target}")
    
    def update_actions(self, actions: List[Dict[str, Any]]) -> None:
        """
        Update the action table.
        
        Args:
            actions: List of action dictionaries
        """
        self.action_table.setRowCount(len(actions))
        
        for i, action in enumerate(actions):
            # ID
            id_item = QTableWidgetItem(str(action.get("id", "")))
            self.action_table.setItem(i, 0, id_item)
            
            # Type
            type_item = QTableWidgetItem(str(action.get("type", "")))
            self.action_table.setItem(i, 1, type_item)
            
            # Target
            target_item = QTableWidgetItem(str(action.get("target", "")))
            self.action_table.setItem(i, 2, target_item)
            
            # Status
            status_item = QTableWidgetItem(str(action.get("status", "")))
            self.action_table.setItem(i, 3, status_item)
            
            # Highlight current action
            if action.get("current", False):
                for col in range(4):
                    self.action_table.item(i, col).setBackground(Qt.GlobalColor.yellow)
    
    def update_variables(self, variables: Dict[str, Any]) -> None:
        """
        Update the variable table.
        
        Args:
            variables: Dictionary of variables
        """
        self.var_table.setRowCount(len(variables))
        
        for i, (name, value) in enumerate(variables.items()):
            # Name
            name_item = QTableWidgetItem(name)
            self.var_table.setItem(i, 0, name_item)
            
            # Value
            value_item = QTableWidgetItem(str(value))
            self.var_table.setItem(i, 1, value_item)
    
    def add_log_entry(self, entry: str) -> None:
        """
        Add an entry to the log.
        
        Args:
            entry: Log entry text
        """
        self.log_text.append(entry)
    
    def clear_log(self) -> None:
        """Clear the log."""
        self.log_text.clear()
    
    def set_paused(self, paused: bool) -> None:
        """
        Set the paused state.
        
        Args:
            paused: Whether execution is paused
        """
        self.pause_btn.setEnabled(not paused)
        self.resume_btn.setEnabled(paused)
        self.step_btn.setEnabled(paused)
    
    def reset(self) -> None:
        """Reset the tab state."""
        self.status_label.setText("Not running")
        self.action_label.setText("Current action: None")
        self.action_table.setRowCount(0)
        self.var_table.setRowCount(0)
        self.log_text.clear()
        self.set_paused(False)
    
    def _on_pause(self) -> None:
        """Handle pause button click."""
        self.pause_execution.emit()
        self.set_paused(True)
        self.add_log_entry("Execution paused by user")
    
    def _on_resume(self) -> None:
        """Handle resume button click."""
        self.resume_execution.emit()
        self.set_paused(False)
        self.add_log_entry("Execution resumed by user")
    
    def _on_step(self) -> None:
        """Handle step button click."""
        self.step_execution.emit()
        self.add_log_entry("Step execution triggered by user")