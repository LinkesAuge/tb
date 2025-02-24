"""
Automation Debug Window

This module provides a debug window for the automation system, featuring:
- Detailed execution logs
- Position visualization
- Pattern match preview
- OCR text display
- Step-by-step execution controls
"""

from typing import Dict, Optional, List
from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QTextEdit, QTableWidget, QTableWidgetItem,
    QGroupBox, QSplitter, QTabWidget, QCheckBox, QSpinBox,
    QDoubleSpinBox, QComboBox
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QImage, QPixmap
import cv2
import numpy as np
import logging
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
        
        # Current state
        self.current_image: Optional[np.ndarray] = None
        self.positions: Dict[str, AutomationPosition] = {}
        self.template_matches: List[tuple] = []  # [(name, x, y, w, h, conf)]
        self.ocr_regions: List[tuple] = []  # [(text, x, y, w, h)]
        self.mouse_position: Optional[tuple] = None  # (x, y)
        
    def update_image(self, image: np.ndarray) -> None:
        """Update the displayed image."""
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
            
        # Convert to Qt image and display
        height, width = display.shape[:2]
        bytes_per_line = 3 * width
        qt_image = QImage(
            display.data,
            width,
            height,
            bytes_per_line,
            QImage.Format.Format_RGB888
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
    """
    
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
        
        preview_layout.addLayout(control_layout)
        
        # Preview widget
        self.preview = ImagePreview()
        preview_layout.addWidget(self.preview)
        
        splitter.addWidget(preview_group)
        
        # Right side - Debug tabs
        tabs = QTabWidget()
        
        # Execution tab
        self.execution_tab = AutomationDebugTab()
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
        
    def _on_preview_options_changed(self) -> None:
        """Handle changes to preview display options."""
        self.preview.show_positions = self.show_positions_check.isChecked()
        self.preview.show_templates = self.show_templates_check.isChecked()
        self.preview.show_ocr = self.show_ocr_check.isChecked()
        self.preview.show_mouse = self.show_mouse_check.isChecked()
        self.preview._update_display()
        
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