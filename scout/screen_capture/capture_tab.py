"""
Screen capture tab UI component.

This module provides the CaptureTab class which implements the UI for
selecting and capturing screens and windows.
"""

from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QPixmap, QImage, QPainter, QColor, QGuiApplication
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QComboBox, 
    QPushButton, QCheckBox, QSpinBox, QGroupBox, QSplitter,
    QFileDialog
)

import numpy as np
import cv2

from scout.screen_capture.capture_manager import CaptureManager
from scout.screen_capture.screen_list_model import ScreenListModel
from scout.screen_capture.window_list_model import WindowListModel
from scout.screen_capture.utils import numpy_to_qimage


class ImageViewer(QLabel):
    """
    Widget for displaying captured images with optional overlays.
    """
    
    def __init__(self, parent=None):
        """Initialize the image viewer."""
        super().__init__(parent)
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setMinimumSize(320, 240)
        self.setStyleSheet("background-color: #222; border: 1px solid #444;")
        self.setText("No image captured")
        self._pixmap = None
    
    def set_image(self, image: np.ndarray) -> None:
        """
        Set the image to display.
        
        Args:
            image: Numpy array containing the image
        """
        if image is None:
            self.clear()
            return
            
        # Convert numpy array to QImage
        qimage = numpy_to_qimage(image)
        
        # Convert to pixmap and set
        self._pixmap = QPixmap.fromImage(qimage)
        self._update_display()
    
    def clear(self) -> None:
        """Clear the displayed image."""
        self._pixmap = None
        self.setText("No image captured")
    
    def _update_display(self) -> None:
        """Update the display with the current pixmap."""
        if self._pixmap is None:
            return
            
        # Scale pixmap to fit the label while maintaining aspect ratio
        scaled_pixmap = self._pixmap.scaled(
            self.width(), self.height(),
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation
        )
        
        self.setPixmap(scaled_pixmap)
    
    def resizeEvent(self, event) -> None:
        """Handle resize events to update the displayed image."""
        super().resizeEvent(event)
        if self._pixmap is not None:
            self._update_display()


class CaptureTab(QWidget):
    """
    Tab widget for screen and window capture functionality.
    
    This widget provides UI controls for selecting capture sources,
    viewing captured images, and saving screenshots.
    """
    
    def __init__(self, parent=None):
        """Initialize the capture tab."""
        super().__init__(parent)
        
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
        
        # Source selection group
        source_group = QGroupBox("Capture Source")
        source_layout = QVBoxLayout(source_group)
        
        # Screen selection
        screen_layout = QHBoxLayout()
        screen_layout.addWidget(QLabel("Screen:"))
        self.screen_combo = QComboBox()
        self.screen_combo.setModel(self.screen_model)
        self.screen_combo.currentIndexChanged.connect(self._on_screen_selected)
        screen_layout.addWidget(self.screen_combo)
        source_layout.addLayout(screen_layout)
        
        # Window selection
        window_layout = QHBoxLayout()
        window_layout.addWidget(QLabel("Window:"))
        self.window_combo = QComboBox()
        self.window_combo.setModel(self.window_model)
        self.window_combo.currentIndexChanged.connect(self._on_window_selected)
        window_layout.addWidget(self.window_combo)
        self.refresh_windows_btn = QPushButton("Refresh")
        self.refresh_windows_btn.clicked.connect(self._refresh_windows)
        window_layout.addWidget(self.refresh_windows_btn)
        source_layout.addLayout(window_layout)
        
        top_layout.addWidget(source_group)
        
        # Capture controls group
        capture_group = QGroupBox("Capture Controls")
        capture_layout = QVBoxLayout(capture_group)
        
        # Auto-capture settings
        auto_capture_layout = QHBoxLayout()
        self.auto_capture_cb = QCheckBox("Auto Capture")
        self.auto_capture_cb.toggled.connect(self._on_auto_capture_toggled)
        auto_capture_layout.addWidget(self.auto_capture_cb)
        
        auto_capture_layout.addWidget(QLabel("Interval (ms):"))
        self.interval_spin = QSpinBox()
        self.interval_spin.setRange(10, 10000)
        self.interval_spin.setValue(100)
        self.interval_spin.setSingleStep(10)
        auto_capture_layout.addWidget(self.interval_spin)
        
        capture_layout.addLayout(auto_capture_layout)
        
        # Manual capture buttons
        button_layout = QHBoxLayout()
        self.capture_btn = QPushButton("Capture Now")
        self.capture_btn.clicked.connect(self._on_capture_clicked)
        button_layout.addWidget(self.capture_btn)
        
        self.save_btn = QPushButton("Save Screenshot")
        self.save_btn.clicked.connect(self._on_save_clicked)
        button_layout.addWidget(self.save_btn)
        
        capture_layout.addLayout(button_layout)
        
        top_layout.addWidget(capture_group)
        
        # Status label
        self.status_label = QLabel("Ready")
        top_layout.addWidget(self.status_label)
        
        # Add top widget to splitter
        splitter.addWidget(top_widget)
        
        # Bottom section - Image viewer
        bottom_widget = QWidget()
        bottom_layout = QVBoxLayout(bottom_widget)
        
        # Image viewer
        self.image_viewer = ImageViewer()
        bottom_layout.addWidget(self.image_viewer)
        
        # Add bottom widget to splitter
        splitter.addWidget(bottom_widget)
        
        # Set initial splitter sizes
        splitter.setSizes([200, 400])
    
    def _initialize(self) -> None:
        """Initialize with default values."""
        # Select primary screen by default
        primary_idx = self.screen_model.get_primary_screen_index()
        if primary_idx >= 0:
            self.screen_combo.setCurrentIndex(primary_idx)
    
    def _on_screen_selected(self, index: int) -> None:
        """
        Handle screen selection change.
        
        Args:
            index: Index of the selected screen
        """
        if index < 0:
            return
            
        # Get selected screen
        screen = self.screen_model.get_screen(index)
        if screen:
            # Update capture manager
            self.capture_manager.set_screen(screen)
            self.window_combo.setCurrentIndex(-1)
            self.status_label.setText(f"Selected screen: {screen.name()}")
    
    def _on_window_selected(self, index: int) -> None:
        """
        Handle window selection change.
        
        Args:
            index: Index of the selected window
        """
        if index < 0:
            return
            
        # Get selected window
        window_info = self.window_model.get_window_info(index)
        if window_info:
            # Update capture manager
            self.capture_manager.set_window(window_info.handle, window_info.geometry)
            self.screen_combo.setCurrentIndex(-1)
            self.status_label.setText(f"Selected window: {window_info.title}")
    
    def _refresh_windows(self) -> None:
        """Refresh the list of available windows."""
        self.window_model.refresh()
        self.status_label.setText("Window list refreshed")
    
    def _on_auto_capture_toggled(self, checked: bool) -> None:
        """
        Handle auto-capture checkbox toggle.
        
        Args:
            checked: Whether auto-capture is enabled
        """
        if checked:
            interval = self.interval_spin.value()
            self.capture_manager.start_capture(interval)
            self.status_label.setText(f"Auto-capture started ({interval} ms)")
        else:
            self.capture_manager.stop_capture()
            self.status_label.setText("Auto-capture stopped")
    
    def _on_capture_clicked(self) -> None:
        """Handle capture button click."""
        frame = self.capture_manager.take_screenshot()
        if frame is not None:
            self.status_label.setText("Screenshot captured")
    
    def _on_save_clicked(self) -> None:
        """Handle save button click."""
        # Get file path from user
        file_path, _ = QFileDialog.getSaveFileName(
            self, "Save Screenshot", "", "Images (*.png *.jpg *.bmp)"
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
        self.image_viewer.set_image(frame)
    
    def _on_error(self, error_msg: str) -> None:
        """
        Handle error from capture manager.
        
        Args:
            error_msg: Error message
        """
        self.status_label.setText(f"Error: {error_msg}")
    
    def closeEvent(self, event):
        """
        Handle widget close event.
        
        Args:
            event: Close event
        """
        # Stop capture when widget is closed
        self._capture_manager.stop_capture()
        super().closeEvent(event)
