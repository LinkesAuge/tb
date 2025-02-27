"""
Automation Debug Tab

This module provides a debug tab for the automation system in the debug window.
It shows:
- Currently marked positions
- Active sequences
- Execution status
- Debug logs
- Variable values
- Action execution history
"""

from typing import Dict, Optional, TYPE_CHECKING, List, Any, Tuple
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
    QTextEdit, QPushButton, QTableWidget, QTableWidgetItem,
    QSplitter, QTabWidget, QCheckBox, QComboBox, QSpinBox,
    QGroupBox, QHeaderView
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QColor, QBrush
import logging
import time
from datetime import datetime

# Use TYPE_CHECKING to avoid circular imports
if TYPE_CHECKING:
    from scout.automation.core import AutomationPosition, AutomationSequence, AutomationAction

logger = logging.getLogger(__name__)

class AutomationDebugTab(QWidget):
    """
    Debug tab for automation system.
    
    Shows:
    - Position list with coordinates
    - Sequence execution status
    - Debug log viewer
    - Controls for step-by-step execution
    - Variable inspector
    - Action history
    """
    
    # Signals for controlling execution
    pause_execution = pyqtSignal()
    resume_execution = pyqtSignal()
    step_execution = pyqtSignal()
    
    def __init__(self):
        """Initialize the automation debug tab."""
        super().__init__()
        
        # Create layout
        main_layout = QVBoxLayout()
        self.setLayout(main_layout)
        
        # Create splitter for top and bottom sections
        main_splitter = QSplitter(Qt.Orientation.Vertical)
        main_layout.addWidget(main_splitter)
        
        # Top section - Controls and status
        top_widget = QWidget()
        top_layout = QVBoxLayout()
        top_widget.setLayout(top_layout)
        
        # Create execution controls
        control_group = QGroupBox("Execution Controls")
        control_layout = QHBoxLayout()
        control_group.setLayout(control_layout)
        
        self.pause_button = QPushButton("Pause")
        self.pause_button.clicked.connect(self.pause_execution.emit)
        control_layout.addWidget(self.pause_button)
        
        self.resume_button = QPushButton("Resume")
        self.resume_button.clicked.connect(self.resume_execution.emit)
        control_layout.addWidget(self.resume_button)
        
        self.step_button = QPushButton("Step")
        self.step_button.clicked.connect(self.step_execution.emit)
        control_layout.addWidget(self.step_button)
        
        self.clear_log_button = QPushButton("Clear Log")
        self.clear_log_button.clicked.connect(self.clear_log)
        control_layout.addWidget(self.clear_log_button)
        
        top_layout.addWidget(control_group)
        
        # Create status display
        status_group = QGroupBox("Execution Status")
        status_layout = QVBoxLayout()
        status_group.setLayout(status_layout)
        
        self.status_label = QLabel("Status: Idle")
        self.status_label.setStyleSheet("font-weight: bold;")
        status_layout.addWidget(self.status_label)
        
        self.current_action_label = QLabel("Current Action: None")
        status_layout.addWidget(self.current_action_label)
        
        self.execution_time_label = QLabel("Execution Time: 0.00s")
        status_layout.addWidget(self.execution_time_label)
        
        top_layout.addWidget(status_group)
        
        # Bottom section - Tabs for different debug views
        bottom_widget = QWidget()
        bottom_layout = QVBoxLayout()
        bottom_widget.setLayout(bottom_layout)
        
        # Create tabs
        self.tabs = QTabWidget()
        bottom_layout.addWidget(self.tabs)
        
        # Positions tab
        positions_tab = QWidget()
        positions_layout = QVBoxLayout()
        positions_tab.setLayout(positions_layout)
        
        self.position_table = QTableWidget()
        self.position_table.setColumnCount(3)
        self.position_table.setHorizontalHeaderLabels(['Name', 'X', 'Y'])
        self.position_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        positions_layout.addWidget(self.position_table)
        
        self.tabs.addTab(positions_tab, "Positions")
        
        # Variables tab
        variables_tab = QWidget()
        variables_layout = QVBoxLayout()
        variables_tab.setLayout(variables_layout)
        
        self.variables_table = QTableWidget()
        self.variables_table.setColumnCount(3)
        self.variables_table.setHorizontalHeaderLabels(['Name', 'Value', 'Type'])
        self.variables_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.variables_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        variables_layout.addWidget(self.variables_table)
        
        self.tabs.addTab(variables_tab, "Variables")
        
        # Action history tab
        history_tab = QWidget()
        history_layout = QVBoxLayout()
        history_tab.setLayout(history_layout)
        
        self.history_table = QTableWidget()
        self.history_table.setColumnCount(4)
        self.history_table.setHorizontalHeaderLabels(['Time', 'Action', 'Status', 'Duration'])
        self.history_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        history_layout.addWidget(self.history_table)
        
        self.tabs.addTab(history_tab, "Action History")
        
        # Log tab
        log_tab = QWidget()
        log_layout = QVBoxLayout()
        log_tab.setLayout(log_layout)
        
        self.log_viewer = QTextEdit()
        self.log_viewer.setReadOnly(True)
        log_layout.addWidget(self.log_viewer)
        
        self.tabs.addTab(log_tab, "Debug Log")
        
        # Add widgets to main splitter
        main_splitter.addWidget(top_widget)
        main_splitter.addWidget(bottom_widget)
        main_splitter.setSizes([200, 600])  # Set initial sizes
        
        # Initialize state
        self.resume_button.setEnabled(False)
        self.step_button.setEnabled(False)
        self.execution_start_time = None
        self.action_history = []
        
    def update_positions(self, positions: Dict[str, 'AutomationPosition']) -> None:
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
            
    def update_variables(self, variables: Dict[str, Any]) -> None:
        """
        Update the variables table.
        
        Args:
            variables: Dictionary of variable name to value
        """
        self.variables_table.setRowCount(len(variables))
        for i, (name, value) in enumerate(variables.items()):
            self.variables_table.setItem(i, 0, QTableWidgetItem(name))
            self.variables_table.setItem(i, 1, QTableWidgetItem(str(value)))
            self.variables_table.setItem(i, 2, QTableWidgetItem(type(value).__name__))
            
    def update_status(self, status: str) -> None:
        """
        Update the execution status display.
        
        Args:
            status: Status message to display
        """
        self.status_label.setText(f"Status: {status}")
        
        # Start timing if execution begins
        if status == "Running" and self.execution_start_time is None:
            self.execution_start_time = time.time()
            self.update_execution_time()
        
        # Stop timing if execution ends
        if status in ["Idle", "Completed", "Failed"]:
            self.execution_start_time = None
            
    def update_current_action(self, action_description: str) -> None:
        """
        Update the current action display.
        
        Args:
            action_description: Description of the current action
        """
        self.current_action_label.setText(f"Current Action: {action_description}")
        
    def update_execution_time(self) -> None:
        """Update the execution time display."""
        if self.execution_start_time is not None:
            elapsed = time.time() - self.execution_start_time
            self.execution_time_label.setText(f"Execution Time: {elapsed:.2f}s")
            
    def add_action_to_history(self, action_type: str, status: str, duration: float) -> None:
        """
        Add an action to the history table.
        
        Args:
            action_type: Type of action
            status: Execution status (Success, Failed, etc.)
            duration: Execution duration in seconds
        """
        # Add to internal history
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.action_history.append((timestamp, action_type, status, duration))
        
        # Limit history size
        if len(self.action_history) > 100:
            self.action_history = self.action_history[-100:]
            
        # Update table
        self.update_action_history()
        
    def update_action_history(self) -> None:
        """Update the action history table from internal history."""
        self.history_table.setRowCount(len(self.action_history))
        
        for i, (timestamp, action_type, status, duration) in enumerate(reversed(self.action_history)):
            self.history_table.setItem(i, 0, QTableWidgetItem(timestamp))
            self.history_table.setItem(i, 1, QTableWidgetItem(action_type))
            
            status_item = QTableWidgetItem(status)
            if status == "Success":
                status_item.setBackground(QBrush(QColor(200, 255, 200)))  # Light green
            elif status == "Failed":
                status_item.setBackground(QBrush(QColor(255, 200, 200)))  # Light red
            self.history_table.setItem(i, 2, status_item)
            
            self.history_table.setItem(i, 3, QTableWidgetItem(f"{duration:.2f}s"))
        
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
        timestamp = datetime.now().strftime("%H:%M:%S.%f")[:-3]
        self.log_viewer.append(f"[{timestamp}] {message}")
        
    def clear_log(self) -> None:
        """Clear the debug log."""
        self.log_viewer.clear()
        
    def reset(self) -> None:
        """Reset the debug tab state."""
        self.execution_start_time = None
        self.execution_time_label.setText("Execution Time: 0.00s")
        self.current_action_label.setText("Current Action: None")
        self.status_label.setText("Status: Idle")
        self.log_viewer.clear() 
