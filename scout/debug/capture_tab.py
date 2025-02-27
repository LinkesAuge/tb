"""
Screen capture tab for debug window.

This module provides a tab for capturing and analyzing screen content in the debug window.
It integrates with the screen_capture module to provide a unified interface.
"""

from typing import Optional, Dict, Any, List, Tuple
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QSplitter, QGroupBox,
    QPushButton, QComboBox, QCheckBox, QSpinBox, QFileDialog
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QPixmap
import numpy as np
import logging
import os
from pathlib import Path
import time

from scout.screen_capture.capture_manager import CaptureManager
from scout.screen_capture.screen_list_model import ScreenListModel
from scout.screen_capture.window_list_model import WindowListModel
from scout.screen_capture.utils import numpy_to_qimage
from scout.debug.preview import ImagePreview

logger = logging.getLogger(__name__)

class CaptureTab(QWidget):
    """
    A tab for screen and window capture functionality.
    
    This widget provides:
    - Source selection (screens or windows)
    - Capture controls (single capture, continuous capture)
    - Image preview with analysis tools
    - Screenshot saving functionality
    """
    
    # Signals
    capture_taken = pyqtSignal(np.ndarray)  # Emitted when a capture is taken
    source_changed = pyqtSignal(str, str)   # Emitted when capture source changes (type, id)
    
    def __init__(self) -> None:
        """Initialize capture tab."""
        super().__init__()
        
        # Create capture manager
        self.capture_manager = CaptureManager(self)
        self.capture_manager.frame_captured.connect(self._on_frame_captured)
        self.capture_manager.error_occurred.connect(self._on_error)
        
        # Create models
        self.screen_model = ScreenListModel(self)
        self.window_model = WindowListModel(self)
        
        # Set up UI
        self._setup_ui()
        
        # Initialize with default values
        self._initialize()
        
        logger.debug("Capture tab initialized")
    
    def _setup_ui(self) -> None:
        """Set up the user interface."""
        # Main layout
        main_layout = QVBoxLayout(self)
        
        # Create splitter for resizable sections
        splitter = QSplitter(Qt.Orientation.Vertical)
        main_layout.addWidget(splitter)
        
        # Top section - Capture controls
        top_widget = QWidget()
        top_layout = QVBoxLayout(top_widget)
        
        # Capture source group
        source_group = QGroupBox("Capture Source")
        source_layout = QVBoxLayout()
        
        # Source type selection
        type_layout = QHBoxLayout()
        type_layout.addWidget(QLabel("Source Type:"))
        self.source_type_combo = QComboBox()
        self.source_type_combo.addItems(["Screen", "Window"])
        self.source_type_combo.currentTextChanged.connect(self._on_source_type_changed)
        type_layout.addWidget(self.source_type_combo)
        source_layout.addLayout(type_layout)
        
        # Source selection
        source_layout.addWidget(QLabel("Select Source:"))
        self.source_combo = QComboBox()
        self.source_combo.currentIndexChanged.connect(self._on_source_changed)
        source_layout.addWidget(self.source_combo)
        
        source_group.setLayout(source_layout)
        top_layout.addWidget(source_group)
        
        # Capture options group
        capture_group = QGroupBox("Capture Options")
        capture_layout = QVBoxLayout()
        
        # Continuous capture option
        continuous_layout = QHBoxLayout()
        self.continuous_check = QCheckBox("Continuous Capture")
        self.continuous_check.setChecked(False)
        self.continuous_check.stateChanged.connect(self._on_continuous_changed)
        continuous_layout.addWidget(self.continuous_check)
        
        # Capture interval
        continuous_layout.addWidget(QLabel("Interval (ms):"))
        self.interval_spin = QSpinBox()
        self.interval_spin.setRange(50, 5000)
        self.interval_spin.setValue(500)
        self.interval_spin.setSingleStep(50)
        self.interval_spin.valueChanged.connect(self._on_interval_changed)
        continuous_layout.addWidget(self.interval_spin)
        
        capture_layout.addLayout(continuous_layout)
        
        # Manual capture buttons
        button_layout = QHBoxLayout()
        self.capture_btn = QPushButton("Capture Now")
        self.capture_btn.clicked.connect(self._on_capture_clicked)
        button_layout.addWidget(self.capture_btn)
        
        self.save_btn = QPushButton("Save Screenshot")
        self.save_btn.clicked.connect(self._on_save_clicked)
        button_layout.addWidget(self.save_btn)
        
        capture_layout.addLayout(button_layout)
        
        capture_group.setLayout(capture_layout)
        top_layout.addWidget(capture_group)
        
        # Status label
        self.status_label = QLabel("Ready")
        top_layout.addWidget(self.status_label)
        
        # Add top widget to splitter
        splitter.addWidget(top_widget)
        
        # Bottom section - Image preview
        self.image_preview = ImagePreview()
        splitter.addWidget(self.image_preview)
        
        # Set initial splitter sizes
        splitter.setSizes([200, 400])
    
    def _initialize(self) -> None:
        """Initialize with default values."""
        # Populate source combo with screens
        self._populate_source_combo()
        
        # Select first source
        if self.source_combo.count() > 0:
            self.source_combo.setCurrentIndex(0)
            self._on_source_changed(0)
    
    def _populate_source_combo(self) -> None:
        """Populate the source combo box based on selected source type."""
        self.source_combo.clear()
        
        if self.source_type_combo.currentText() == "Screen":
            # Populate with screens
            for i in range(self.screen_model.rowCount()):
                screen_info = self.screen_model.data(self.screen_model.index(i, 0), Qt.ItemDataRole.DisplayRole)
                self.source_combo.addItem(screen_info, self.screen_model.screen_id(i))
        else:
            # Populate with windows
            for i in range(self.window_model.rowCount()):
                window_info = self.window_model.data(self.window_model.index(i, 0), Qt.ItemDataRole.DisplayRole)
                self.source_combo.addItem(window_info, self.window_model.window_id(i))
    
    def _on_source_type_changed(self, source_type: str) -> None:
        """
        Handle source type change.
        
        Args:
            source_type: New source type
        """
        # Update source combo
        self._populate_source_combo()
        
        # Select first source if available
        if self.source_combo.count() > 0:
            self.source_combo.setCurrentIndex(0)
            self._on_source_changed(0)
        
        # Update status
        self.status_label.setText(f"Source type changed to {source_type}")
    
    def _on_source_changed(self, index: int) -> None:
        """
        Handle source selection change.
        
        Args:
            index: Selected index
        """
        if index < 0 or self.source_combo.count() == 0:
            return
        
        source_id = self.source_combo.itemData(index)
        source_type = self.source_type_combo.currentText()
        
        # Update capture manager
        if source_type == "Screen":
            self.capture_manager.set_screen_source(source_id)
        else:
            self.capture_manager.set_window_source(source_id)
        
        # Emit signal
        self.source_changed.emit(source_type, source_id)
        
        # Update status
        self.status_label.setText(f"Source changed to {self.source_combo.currentText()}")
    
    def _on_continuous_changed(self, state: int) -> None:
        """
        Handle continuous capture state change.
        
        Args:
            state: Checkbox state
        """
        if state == Qt.CheckState.Checked.value:
            # Start continuous capture
            interval = self.interval_spin.value()
            self.capture_manager.start_capture(interval)
            self.status_label.setText(f"Continuous capture started (interval: {interval}ms)")
        else:
            # Stop continuous capture
            self.capture_manager.stop_capture()
            self.status_label.setText("Continuous capture stopped")
    
    def _on_interval_changed(self, value: int) -> None:
        """
        Handle capture interval change.
        
        Args:
            value: New interval value
        """
        if self.continuous_check.isChecked():
            # Update capture interval
            self.capture_manager.set_capture_interval(value)
            self.status_label.setText(f"Capture interval changed to {value}ms")
    
    def _on_capture_clicked(self) -> None:
        """Handle capture button click."""
        # Take a single capture
        self.capture_manager.capture_screenshot()
        self.status_label.setText("Screenshot captured")
    
    def _on_save_clicked(self) -> None:
        """Handle save button click."""
        if self.capture_manager.last_frame is None:
            self.status_label.setText("No screenshot to save")
            return
        
        # Get save path
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "Save Screenshot",
            os.path.join(os.path.expanduser("~"), "screenshot.png"),
            "Images (*.png *.jpg *.bmp)"
        )
        
        if not file_path:
            return
        
        # Save screenshot
        saved_path = self.capture_manager.save_screenshot(file_path)
        if saved_path:
            self.status_label.setText(f"Screenshot saved to: {saved_path}")
    
    def _on_frame_captured(self, frame: np.ndarray) -> None:
        """
        Handle captured frame.
        
        Args:
            frame: Captured frame as numpy array
        """
        # Update image preview
        self.image_preview.set_image(frame)
        
        # Emit signal
        self.capture_taken.emit(frame)
    
    def _on_error(self, error_msg: str) -> None:
        """
        Handle error from capture manager.
        
        Args:
            error_msg: Error message
        """
        self.status_label.setText(f"Error: {error_msg}")
    
    def get_capture_manager(self) -> CaptureManager:
        """
        Get the capture manager.
        
        Returns:
            The capture manager instance
        """
        return self.capture_manager
    
    def closeEvent(self, event) -> None:
        """
        Handle widget close event.
        
        Args:
            event: Close event
        """
        # Stop capture when widget is closed
        self.capture_manager.stop_capture()
        super().closeEvent(event)