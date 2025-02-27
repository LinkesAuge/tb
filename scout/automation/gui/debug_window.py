"""
Automation Debug Window

This module provides a debug window for the automation system, featuring:
- Detailed execution logs
- Position visualization
- Pattern match preview
- OCR text display
- Step-by-step execution controls
- Variable monitoring
- Action history tracking
"""

from typing import Dict, Optional, List, Any, Tuple
from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QTextEdit, QTableWidget, QTableWidgetItem,
    QGroupBox, QSplitter, QTabWidget, QCheckBox, QSpinBox,
    QDoubleSpinBox, QComboBox, QFileDialog, QMessageBox,
    QStatusBar, QToolBar, QAction
)
from PyQt6.QtCore import Qt, pyqtSignal, QTimer
from PyQt6.QtGui import QImage, QPixmap, QIcon, QAction
import cv2
import numpy as np
import logging
import os
from datetime import datetime
from scout.automation.core import AutomationPosition
from scout.automation.actions import ActionType
from scout.automation.gui.debug_tab import AutomationDebugTab

logger = logging.getLogger(__name__)

class ImagePreview(QLabel):
    """
    Widget for displaying image previews with overlays.
    
    Features:
    - Template match visualization
    - OCR text highlighting
    - Position markers
    - Mouse movement preview
    - Grid overlay option
    - Zoom and pan capabilities
    """
    
    def __init__(self):
        """Initialize the image preview widget."""
        super().__init__()
        self.setMinimumSize(400, 300)
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setText("No preview available")
        
        # Display settings
        self.show_positions = True
        self.show_templates = True
        self.show_ocr = True
        self.show_mouse = True
        self.show_grid = False
        self.grid_size = 50
        self.zoom_level = 1.0
        
        # Current state
        self.current_image: Optional[np.ndarray] = None
        self.positions: Dict[str, AutomationPosition] = {}
        self.template_matches: List[tuple] = []  # [(name, x, y, w, h, conf)]
        self.ocr_regions: List[tuple] = []  # [(text, x, y, w, h)]
        self.mouse_position: Optional[tuple] = None  # (x, y)
        
        # Enable mouse tracking for coordinate display
        self.setMouseTracking(True)
        
    def update_image(self, image: np.ndarray) -> None:
        """Update the displayed image."""
        if image is None:
            return
            
        self.current_image = image.copy()
        self._update_display()
        
    def update_positions(self, positions: Dict[str, AutomationPosition]) -> None:
        """Update marked positions."""
        self.positions = positions
        self._update_display()
        
    def update_pattern_matches(self, matches: List[tuple]) -> None:
        """Update pattern match regions."""
        self.template_matches = matches
        self._update_display()
        
    def update_ocr_regions(self, regions: List[tuple]) -> None:
        """Update OCR text regions."""
        self.ocr_regions = regions
        self._update_display()
        
    def update_mouse_position(self, x: int, y: int) -> None:
        """Update mouse cursor position."""
        self.mouse_position = (x, y)
        self._update_display()
        
    def set_zoom(self, zoom_level: float) -> None:
        """Set the zoom level for the preview."""
        self.zoom_level = max(0.1, min(5.0, zoom_level))
        self._update_display()
        
    def toggle_grid(self, show: bool) -> None:
        """Toggle grid overlay."""
        self.show_grid = show
        self._update_display()
        
    def set_grid_size(self, size: int) -> None:
        """Set grid size."""
        self.grid_size = max(10, min(200, size))
        if self.show_grid:
            self._update_display()
            
    def mouseMoveEvent(self, event):
        """Handle mouse movement to show coordinates."""
        if self.current_image is not None:
            # Calculate actual image coordinates based on display scaling
            pixmap_rect = self.pixmap().rect()
            widget_rect = self.rect()
            
            # Calculate scaling factors
            scale_x = pixmap_rect.width() / self.current_image.shape[1]
            scale_y = pixmap_rect.height() / self.current_image.shape[0]
            
            # Calculate image coordinates
            x = int(event.position().x() / scale_x)
            y = int(event.position().y() / scale_y)
            
            # Ensure coordinates are within image bounds
            if 0 <= x < self.current_image.shape[1] and 0 <= y < self.current_image.shape[0]:
                # Get pixel color at cursor position
                if len(self.current_image.shape) == 3:  # Color image
                    b, g, r = self.current_image[y, x]
                    self.setToolTip(f"Position: ({x}, {y}) | RGB: ({r}, {g}, {b})")
                else:  # Grayscale
                    v = self.current_image[y, x]
                    self.setToolTip(f"Position: ({x}, {y}) | Value: {v}")
            
        super().mouseMoveEvent(event)
            
    def _update_display(self) -> None:
        """Update the display with current overlays."""
        if self.current_image is None:
            return
            
        # Create copy for drawing
        display = self.current_image.copy()
        
        # Draw positions
        if self.show_positions:
            for name, pos in self.positions.items():
                cv2.drawMarker(
                    display,
                    (pos.x, pos.y),
                    (255, 165, 0),  # Orange
                    cv2.MARKER_CROSS,
                    20,
                    2
                )
                cv2.putText(
                    display,
                    name,
                    (pos.x + 10, pos.y + 10),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.5,
                    (255, 165, 0),
                    1
                )
                
        # Draw template matches
        if self.show_templates:
            for name, x, y, w, h, conf in self.template_matches:
                cv2.rectangle(
                    display,
                    (x, y),
                    (x + w, y + h),
                    (0, 255, 0),  # Green
                    2
                )
                cv2.putText(
                    display,
                    f"{name} ({conf:.2f})",
                    (x, y - 5),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.5,
                    (0, 255, 0),
                    1
                )
                
        # Draw OCR regions
        if self.show_ocr:
            for text, x, y, w, h in self.ocr_regions:
                cv2.rectangle(
                    display,
                    (x, y),
                    (x + w, y + h),
                    (0, 0, 255),  # Red
                    2
                )
                cv2.putText(
                    display,
                    text,
                    (x, y - 5),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.5,
                    (0, 0, 255),
                    1
                )
                
        # Draw mouse position
        if self.show_mouse and self.mouse_position:
            x, y = self.mouse_position
            cv2.circle(
                display,
                (x, y),
                5,
                (255, 255, 255),  # White
                -1
            )
            
        # Draw grid
        if self.show_grid:
            h, w = display.shape[:2]
            # Draw vertical lines
            for x in range(0, w, self.grid_size):
                cv2.line(display, (x, 0), (x, h), (128, 128, 128), 1)
            # Draw horizontal lines
            for y in range(0, h, self.grid_size):
                cv2.line(display, (0, y), (w, y), (128, 128, 128), 1)
            
        # Apply zoom if needed
        if self.zoom_level != 1.0:
            h, w = display.shape[:2]
            new_h, new_w = int(h * self.zoom_level), int(w * self.zoom_level)
            display = cv2.resize(display, (new_w, new_h), interpolation=cv2.INTER_AREA if self.zoom_level < 1.0 else cv2.INTER_LINEAR)
            
        # Convert to Qt image and display
        if len(display.shape) == 3:  # Color image
            height, width, channels = display.shape
            bytes_per_line = channels * width
            # Convert BGR to RGB
            display_rgb = cv2.cvtColor(display, cv2.COLOR_BGR2RGB)
            qt_image = QImage(
                display_rgb.data,
                width,
                height,
                bytes_per_line,
                QImage.Format.Format_RGB888
            )
        else:  # Grayscale
            height, width = display.shape
            bytes_per_line = width
            qt_image = QImage(
                display.data,
                width,
                height,
                bytes_per_line,
                QImage.Format.Format_Grayscale8
            )
            
        self.setPixmap(QPixmap.fromImage(qt_image))

class AutomationDebugWindow(QMainWindow):
    """
    Debug window for automation system.
    
    Features:
    - Execution log viewer
    - Image preview with overlays
    - Template visualization
    - OCR text display
    - Execution controls
    - Variable monitoring
    - Action history tracking
    - Screenshot saving
    """
    
    # Signals for execution control
    pause_execution = pyqtSignal()
    resume_execution = pyqtSignal()
    step_execution = pyqtSignal()
    
    def __init__(self):
        """Initialize the debug window."""
        super().__init__()
        self.setWindowTitle("Automation Debug")
        self.resize(1200, 800)
        
        # Create central widget and layout
        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout()
        central.setLayout(layout)
        
        # Create toolbar
        self.create_toolbar()
        
        # Create status bar
        self.statusBar = QStatusBar()
        self.setStatusBar(self.statusBar)
        self.statusBar.showMessage("Ready")
        
        # Create splitter for preview and controls
        splitter = QSplitter(Qt.Orientation.Horizontal)
        layout.addWidget(splitter)
        
        # Left side - Image preview
        preview_group = QGroupBox("Preview")
        preview_layout = QVBoxLayout()
        preview_group.setLayout(preview_layout)
        
        # Preview controls
        control_layout = QHBoxLayout()
        
        self.show_positions_check = QCheckBox("Show Positions")
        self.show_positions_check.setChecked(True)
        self.show_positions_check.stateChanged.connect(self._on_preview_options_changed)
        control_layout.addWidget(self.show_positions_check)
        
        self.show_templates_check = QCheckBox("Show Templates")
        self.show_templates_check.setChecked(True)
        self.show_templates_check.stateChanged.connect(self._on_preview_options_changed)
        control_layout.addWidget(self.show_templates_check)
        
        self.show_ocr_check = QCheckBox("Show OCR")
        self.show_ocr_check.setChecked(True)
        self.show_ocr_check.stateChanged.connect(self._on_preview_options_changed)
        control_layout.addWidget(self.show_ocr_check)
        
        self.show_mouse_check = QCheckBox("Show Mouse")
        self.show_mouse_check.setChecked(True)
        self.show_mouse_check.stateChanged.connect(self._on_preview_options_changed)
        control_layout.addWidget(self.show_mouse_check)
        
        self.show_grid_check = QCheckBox("Show Grid")
        self.show_grid_check.setChecked(False)
        self.show_grid_check.stateChanged.connect(self._on_preview_options_changed)
        control_layout.addWidget(self.show_grid_check)
        
        preview_layout.addLayout(control_layout)
        
        # Zoom controls
        zoom_layout = QHBoxLayout()
        
        zoom_label = QLabel("Zoom:")
        zoom_layout.addWidget(zoom_label)
        
        self.zoom_spinner = QDoubleSpinBox()
        self.zoom_spinner.setRange(0.1, 5.0)
        self.zoom_spinner.setSingleStep(0.1)
        self.zoom_spinner.setValue(1.0)
        self.zoom_spinner.valueChanged.connect(self._on_zoom_changed)
        zoom_layout.addWidget(self.zoom_spinner)
        
        zoom_layout.addStretch()
        
        grid_label = QLabel("Grid Size:")
        zoom_layout.addWidget(grid_label)
        
        self.grid_spinner = QSpinBox()
        self.grid_spinner.setRange(10, 200)
        self.grid_spinner.setSingleStep(10)
        self.grid_spinner.setValue(50)
        self.grid_spinner.valueChanged.connect(self._on_grid_size_changed)
        zoom_layout.addWidget(self.grid_spinner)
        
        preview_layout.addLayout(zoom_layout)
        
        # Preview widget
        self.preview = ImagePreview()
        preview_layout.addWidget(self.preview)
        
        splitter.addWidget(preview_group)
        
        # Right side - Debug tabs
        tabs = QTabWidget()
        
        # Execution tab
        self.execution_tab = AutomationDebugTab()
        self.execution_tab.pause_execution.connect(self.pause_execution)
        self.execution_tab.resume_execution.connect(self.resume_execution)
        self.execution_tab.step_execution.connect(self.step_execution)
        tabs.addTab(self.execution_tab, "Execution")
        
        # Template tab
        template_tab = QWidget()
        template_layout = QVBoxLayout()
        template_tab.setLayout(template_layout)
        
        self.template_table = QTableWidget()
        self.template_table.setColumnCount(4)
        self.template_table.setHorizontalHeaderLabels(['Template', 'Position', 'Confidence', 'Status'])
        template_layout.addWidget(self.template_table)
        
        tabs.addTab(template_tab, "Templates")
        
        # OCR tab
        ocr_tab = QWidget()
        ocr_layout = QVBoxLayout()
        ocr_tab.setLayout(ocr_layout)
        
        self.ocr_text = QTextEdit()
        self.ocr_text.setReadOnly(True)
        ocr_layout.addWidget(self.ocr_text)
        
        tabs.addTab(ocr_tab, "OCR")
        
        splitter.addWidget(tabs)
        
        # Set initial splitter sizes
        splitter.setSizes([600, 600])
        
        # Setup timer for execution time updates
        self.timer = QTimer(self)
        self.timer.timeout.connect(self._update_execution_time)
        self.timer.start(100)  # Update every 100ms
        
    def create_toolbar(self):
        """Create the toolbar with actions."""
        toolbar = QToolBar("Debug Controls")
        self.addToolBar(toolbar)
        
        # Save screenshot action
        save_action = QAction("Save Screenshot", self)
        save_action.triggered.connect(self._save_screenshot)
        toolbar.addAction(save_action)
        
        # Clear logs action
        clear_action = QAction("Clear Logs", self)
        clear_action.triggered.connect(self._clear_all_logs)
        toolbar.addAction(clear_action)
        
        toolbar.addSeparator()
        
        # Reset view action
        reset_view_action = QAction("Reset View", self)
        reset_view_action.triggered.connect(self._reset_view)
        toolbar.addAction(reset_view_action)
        
    def _on_preview_options_changed(self) -> None:
        """Handle changes to preview display options."""
        self.preview.show_positions = self.show_positions_check.isChecked()
        self.preview.show_templates = self.show_templates_check.isChecked()
        self.preview.show_ocr = self.show_ocr_check.isChecked()
        self.preview.show_mouse = self.show_mouse_check.isChecked()
        self.preview.toggle_grid(self.show_grid_check.isChecked())
        self.preview._update_display()
        
    def _on_zoom_changed(self, value: float) -> None:
        """Handle zoom level changes."""
        self.preview.set_zoom(value)
        
    def _on_grid_size_changed(self, value: int) -> None:
        """Handle grid size changes."""
        self.preview.set_grid_size(value)
        
    def _save_screenshot(self) -> None:
        """Save the current preview as an image file."""
        if self.preview.current_image is None:
            QMessageBox.warning(self, "Save Failed", "No image available to save.")
            return
            
        # Get save path from user
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename, _ = QFileDialog.getSaveFileName(
            self, "Save Screenshot", 
            f"automation_debug_{timestamp}.png",
            "Images (*.png *.jpg)"
        )
        
        if filename:
            try:
                # Save the image with overlays
                if self.preview.pixmap():
                    self.preview.pixmap().save(filename)
                    self.statusBar.showMessage(f"Screenshot saved to {filename}", 3000)
                    logger.info(f"Debug screenshot saved to {filename}")
                else:
                    # Fall back to saving the raw image
                    cv2.imwrite(filename, self.preview.current_image)
                    self.statusBar.showMessage(f"Raw screenshot saved to {filename}", 3000)
                    logger.info(f"Raw debug screenshot saved to {filename}")
            except Exception as e:
                QMessageBox.critical(self, "Save Failed", f"Failed to save screenshot: {str(e)}")
                logger.error(f"Failed to save debug screenshot: {e}")
                
    def _clear_all_logs(self) -> None:
        """Clear all logs and history."""
        self.execution_tab.clear_log()
        self.ocr_text.clear()
        self.statusBar.showMessage("All logs cleared", 3000)
        
    def _reset_view(self) -> None:
        """Reset view settings to defaults."""
        self.zoom_spinner.setValue(1.0)
        self.grid_spinner.setValue(50)
        self.show_positions_check.setChecked(True)
        self.show_templates_check.setChecked(True)
        self.show_ocr_check.setChecked(True)
        self.show_mouse_check.setChecked(True)
        self.show_grid_check.setChecked(False)
        
    def _update_execution_time(self) -> None:
        """Update the execution time display."""
        self.execution_tab.update_execution_time()
        
    def update_preview(self, image: np.ndarray) -> None:
        """Update the preview image."""
        self.preview.update_image(image)
        
    def update_positions(self, positions: Dict[str, AutomationPosition]) -> None:
        """Update marked positions."""
        self.preview.update_positions(positions)
        self.execution_tab.update_positions(positions)
        
    def update_template_matches(self, matches: List[tuple]) -> None:
        """Update template match information."""
        self.preview.update_pattern_matches(matches)
        
        # Update template table
        self.template_table.setRowCount(len(matches))
        for i, (name, x, y, w, h, conf) in enumerate(matches):
            self.template_table.setItem(i, 0, QTableWidgetItem(name))
            self.template_table.setItem(i, 1, QTableWidgetItem(f"({x}, {y})"))
            self.template_table.setItem(i, 2, QTableWidgetItem(f"{conf:.2f}"))
            self.template_table.setItem(i, 3, QTableWidgetItem("Found"))
            
    def update_ocr_text(self, text: str, regions: List[tuple]) -> None:
        """Update OCR text and regions."""
        self.preview.update_ocr_regions(regions)
        self.ocr_text.setText(text)
        
    def update_mouse_position(self, x: int, y: int) -> None:
        """Update mouse cursor position."""
        self.preview.update_mouse_position(x, y)
        
    def add_log_message(self, message: str) -> None:
        """Add a message to the execution log."""
        self.execution_tab.add_log_message(message)
        
    def clear_log(self) -> None:
        """Clear the execution log."""
        self.execution_tab.clear_log()
        
    def set_execution_paused(self, paused: bool) -> None:
        """Update execution control button states."""
        self.execution_tab.set_execution_paused(paused)
        
    def update_status(self, status: str) -> None:
        """Update execution status display."""
        self.execution_tab.update_status(status)
        self.statusBar.showMessage(f"Automation: {status}")
        
    def update_current_action(self, action_description: str) -> None:
        """Update the current action display."""
        self.execution_tab.update_current_action(action_description)
        
    def add_action_to_history(self, action_type: str, status: str, duration: float) -> None:
        """Add an action to the history."""
        self.execution_tab.add_action_to_history(action_type, status, duration)
        
    def update_variables(self, variables: Dict[str, Any]) -> None:
        """Update the variables display."""
        self.execution_tab.update_variables(variables)
        
    def reset(self) -> None:
        """Reset the debug window state."""
        self._reset_view()
        self.execution_tab.reset()
        self.template_table.setRowCount(0)
        self.ocr_text.clear()
        self.preview.current_image = None
        self.preview.positions = {}
        self.preview.template_matches = []
        self.preview.ocr_regions = []
        self.preview.mouse_position = None
        self.execution_tab.update_status("Idle")  # Use "Idle" as the default status
