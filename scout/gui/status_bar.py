"""
Status Bar Module

This module provides a status bar component for the TB Scout application.
The status bar displays application status, messages, and indicators.
"""

from PyQt6.QtWidgets import QStatusBar, QLabel, QProgressBar, QHBoxLayout, QWidget
from PyQt6.QtCore import Qt, pyqtSlot
from PyQt6.QtGui import QIcon, QPixmap

from scout.signals import signal_bus
from scout.utils.logging_utils import get_logger

logger = get_logger(__name__)


class StatusBar(QStatusBar):
    """
    Status bar for the main application window.
    
    Displays:
    - Status messages
    - Progress indicators
    - Connection status
    - Automation status
    """
    
    def __init__(self, parent=None):
        """Initialize the status bar with all components."""
        super().__init__(parent)
        
        # Create status components
        self._setup_ui()
        
        # Connect signals
        self._connect_signals()
        
        # Set initial status
        self.set_status("Ready")
        
    def _setup_ui(self):
        """Set up the UI components of the status bar."""
        # Main status message label
        self.status_label = QLabel("Ready")
        self.status_label.setMinimumWidth(200)
        
        # Progress bar for operations
        self.progress_bar = QProgressBar()
        self.progress_bar.setMaximumWidth(150)
        self.progress_bar.setMaximumHeight(15)
        self.progress_bar.setVisible(False)
        
        # Window connection status
        self.window_status = QLabel("No window")
        self.window_status.setStyleSheet("color: #888;")
        
        # Automation status
        self.automation_status = QLabel("Idle")
        self.automation_status.setStyleSheet("color: #888;")
        
        # Add permanent widgets to the status bar
        self.addWidget(self.status_label, 1)
        self.addWidget(self.progress_bar)
        self.addPermanentWidget(self.window_status)
        self.addPermanentWidget(self.automation_status)
        
    def _connect_signals(self):
        """Connect to application signals."""
        # Status message updates
        signal_bus.status_message.connect(self.set_status)
        
        # Window status updates
        signal_bus.window_selected.connect(self.on_window_selected)
        signal_bus.window_lost.connect(self.on_window_lost)
        
        # Automation status updates
        signal_bus.automation_started.connect(self.on_automation_started)
        signal_bus.automation_paused.connect(self.on_automation_paused)
        signal_bus.automation_resumed.connect(self.on_automation_resumed)
        signal_bus.automation_stopped.connect(self.on_automation_stopped)
        signal_bus.automation_step_complete.connect(self.on_automation_progress)
        signal_bus.automation_sequence_complete.connect(self.on_automation_complete)
        
    @pyqtSlot(str)
    def set_status(self, message):
        """Set the main status message."""
        self.status_label.setText(message)
        logger.debug(f"Status: {message}")
        
    @pyqtSlot(int, int)
    def on_automation_progress(self, current, total):
        """Update progress bar for automation."""
        if not self.progress_bar.isVisible():
            self.progress_bar.setVisible(True)
        
        self.progress_bar.setMaximum(total)
        self.progress_bar.setValue(current)
        
        # Update percentage in automation status
        percent = int((current / total) * 100) if total > 0 else 0
        self.automation_status.setText(f"Running: {percent}%")
        
    @pyqtSlot(str)
    def on_automation_started(self, sequence_name):
        """Handle automation start event."""
        self.automation_status.setText(f"Running: {sequence_name}")
        self.automation_status.setStyleSheet("color: green;")
        self.progress_bar.setVisible(True)
        self.progress_bar.setValue(0)
        self.set_status(f"Automation started: {sequence_name}")
        
    @pyqtSlot()
    def on_automation_paused(self):
        """Handle automation pause event."""
        self.automation_status.setText("Paused")
        self.automation_status.setStyleSheet("color: orange;")
        self.set_status("Automation paused")
        
    @pyqtSlot()
    def on_automation_resumed(self):
        """Handle automation resume event."""
        self.automation_status.setText("Running")
        self.automation_status.setStyleSheet("color: green;")
        self.set_status("Automation resumed")
        
    @pyqtSlot()
    def on_automation_stopped(self):
        """Handle automation stop event."""
        self.automation_status.setText("Idle")
        self.automation_status.setStyleSheet("color: #888;")
        self.progress_bar.setVisible(False)
        self.set_status("Automation stopped")
        
    @pyqtSlot(str)
    def on_automation_complete(self, sequence_name):
        """Handle automation completion event."""
        self.automation_status.setText("Completed")
        self.automation_status.setStyleSheet("color: blue;")
        self.progress_bar.setVisible(False)
        self.set_status(f"Automation completed: {sequence_name}")
        
    @pyqtSlot(int)
    def on_window_selected(self, window_handle):
        """Handle window selection event."""
        self.window_status.setText("Window connected")
        self.window_status.setStyleSheet("color: green;")
        self.set_status("Game window connected")
        
    @pyqtSlot()
    def on_window_lost(self):
        """Handle window lost event."""
        self.window_status.setText("Window lost")
        self.window_status.setStyleSheet("color: red;")
        self.set_status("Game window connection lost")
        
    def set_window_status(self, connected: bool, title: str = ""):
        """
        Set the window connection status.
        
        Args:
            connected: Whether a window is connected
            title: The title of the connected window (if connected)
        """
        if connected:
            self.window_status.setText(f"Window: {title}" if title else "Window connected")
            self.window_status.setStyleSheet("color: green;")
        else:
            self.window_status.setText("No window")
            self.window_status.setStyleSheet("color: #888;")
            
    def set_scanning_status(self, is_scanning: bool):
        """
        Set the scanning status indicator.
        
        Args:
            is_scanning: Whether scanning is active
        """
        if is_scanning:
            self.automation_status.setText("Scanning")
            self.automation_status.setStyleSheet("color: green;")
            self.set_status("Scanning active")
        else:
            self.automation_status.setText("Idle")
            self.automation_status.setStyleSheet("color: #888;")
            self.set_status("Scanning stopped")
            
    def update_coordinates(self, x: int, y: int):
        """
        Update the coordinates display in the status bar.
        
        Args:
            x: X coordinate
            y: Y coordinate
        """
        # Create or update the coordinates label if it doesn't exist
        if not hasattr(self, 'coordinates_label'):
            self.coordinates_label = QLabel()
            self.addPermanentWidget(self.coordinates_label)
            
        # Update the coordinates text
        self.coordinates_label.setText(f"Position: ({x}, {y})")
        self.coordinates_label.setStyleSheet("color: #444;")
        
    def set_automation_status(self, active: bool, sequence_name: str = ""):
        """
        Set the automation status.
        
        Args:
            active: Whether automation is active
            sequence_name: Name of the running sequence (if active)
        """
        if active:
            self.automation_status.setText(f"Executing: {sequence_name}")
            self.automation_status.setStyleSheet("color: green;")
            self.set_status(f"Executing sequence: {sequence_name}")
        else:
            self.automation_status.setText("Idle")
            self.automation_status.setStyleSheet("color: #888;")
            self.set_status("Automation inactive")