"""
Automation Debug Tab

This module provides a debug tab for the automation system in the debug window.
It shows:
- Currently marked positions
- Active sequences
- Execution status
- Debug logs
"""

from typing import Dict, Optional
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
    QTextEdit, QPushButton, QTableWidget, QTableWidgetItem
)
from PyQt6.QtCore import Qt, pyqtSignal
import logging
from scout.automation.core import AutomationPosition, AutomationSequence

logger = logging.getLogger(__name__)

class AutomationDebugTab(QWidget):
    """
    Debug tab for automation system.
    
    Shows:
    - Position list with coordinates
    - Sequence execution status
    - Debug log viewer
    - Controls for step-by-step execution
    """
    
    # Signals for controlling execution
    pause_execution = pyqtSignal()
    resume_execution = pyqtSignal()
    step_execution = pyqtSignal()
    
    def __init__(self):
        """Initialize the automation debug tab."""
        super().__init__()
        
        # Create layout
        layout = QVBoxLayout()
        self.setLayout(layout)
        
        # Create position table
        self.position_table = QTableWidget()
        self.position_table.setColumnCount(3)
        self.position_table.setHorizontalHeaderLabels(['Name', 'X', 'Y'])
        layout.addWidget(QLabel("Marked Positions:"))
        layout.addWidget(self.position_table)
        
        # Create execution controls
        control_layout = QHBoxLayout()
        
        self.pause_button = QPushButton("Pause")
        self.pause_button.clicked.connect(self.pause_execution.emit)
        control_layout.addWidget(self.pause_button)
        
        self.resume_button = QPushButton("Resume")
        self.resume_button.clicked.connect(self.resume_execution.emit)
        control_layout.addWidget(self.resume_button)
        
        self.step_button = QPushButton("Step")
        self.step_button.clicked.connect(self.step_execution.emit)
        control_layout.addWidget(self.step_button)
        
        layout.addLayout(control_layout)
        
        # Create status display
        self.status_label = QLabel("Status: Idle")
        layout.addWidget(self.status_label)
        
        # Create log viewer
        self.log_viewer = QTextEdit()
        self.log_viewer.setReadOnly(True)
        layout.addWidget(QLabel("Debug Log:"))
        layout.addWidget(self.log_viewer)
        
        # Initialize state
        self.resume_button.setEnabled(False)
        self.step_button.setEnabled(False)
        
    def update_positions(self, positions: Dict[str, AutomationPosition]) -> None:
        """
        Update the position table.
        
        Args:
            positions: Dictionary of position name to AutomationPosition
        """
        self.position_table.setRowCount(len(positions))
        for i, (name, pos) in enumerate(positions.items()):
            self.position_table.setItem(i, 0, QTableWidgetItem(name))
            self.position_table.setItem(i, 1, QTableWidgetItem(str(pos.x)))
            self.position_table.setItem(i, 2, QTableWidgetItem(str(pos.y)))
            
    def update_status(self, status: str) -> None:
        """
        Update the execution status display.
        
        Args:
            status: Status message to display
        """
        self.status_label.setText(f"Status: {status}")
        
    def set_execution_paused(self, paused: bool) -> None:
        """
        Update the execution control buttons.
        
        Args:
            paused: Whether execution is paused
        """
        self.pause_button.setEnabled(not paused)
        self.resume_button.setEnabled(paused)
        self.step_button.setEnabled(paused)
        
    def add_log_message(self, message: str) -> None:
        """
        Add a message to the debug log.
        
        Args:
            message: Log message to add
        """
        self.log_viewer.append(message)
        
    def clear_log(self) -> None:
        """Clear the debug log."""
        self.log_viewer.clear() 