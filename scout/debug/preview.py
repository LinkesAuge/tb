"""
Image preview widget for debug windows.

This module provides a widget for displaying images with overlays for:
- Positions
- Template matches
- OCR regions
- Mouse position
- Grid
"""

from typing import Optional, Dict, List, Tuple
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QLabel
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QImage, QPixmap, QPainter, QPen, QColor, QMouseEvent
import numpy as np
import cv2
import logging
from scout.automation.core import AutomationPosition

logger = logging.getLogger(__name__)

class PreviewWidget(QWidget):
    """
    Widget for displaying images with overlays.
    
    Features:
    - Display images with various overlays
    - Show/hide different overlay types
    - Grid display
    - Mouse position tracking
    - Zoom control
    
    Signals:
        mouse_moved: Emitted when mouse moves over the image (x, y)
        mouse_clicked: Emitted when mouse is clicked on the image (x, y, button)
    """
    
    # Signals
    mouse_moved = pyqtSignal(int, int)
    mouse_clicked = pyqtSignal(int, int, int)  # x, y, button
    
    def __init__(self) -> None:
        """Initialize the preview widget."""
        super().__init__()
        
        # Create layout
        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        
        # Create image label
        self.image_label = QLabel()
        self.image_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.image_label)
        
        # Set layout
        self.setLayout(layout)
        
        # Enable mouse tracking
        self.setMouseTracking(True)
        self.image_label.setMouseTracking(True)
        
        # Current state
        self.current_image: Optional[np.ndarray] = None
        self.display_image: Optional[QPixmap] = None
        self.positions: Dict[str, AutomationPosition] = {}
        self.template_matches: List[Tuple] = []  # [(name, x, y, w, h, conf)]
        self.ocr_regions: List[Tuple] = []  # [(text, x, y, w, h)]
        self.mouse_position: Optional[Tuple[int, int]] = None
        
        # Display options
        self.show_positions = True
        self.show_templates = True
        self.show_ocr = True
        self.show_mouse = True
        self.show_grid = False
        self.grid_size = 50
        self.zoom_level = 1.0
        
        logger.debug("Preview widget initialized")
    
    def update_image(self, image: np.ndarray) -> None:
        """
        Update the displayed image.
        
        Args:
            image: Image as numpy array
        """
        if image is None:
            return
            
        self.current_image = image.copy()
        self._update_display()
    
    def update_positions(self, positions: Dict[str, AutomationPosition]) -> None:
        """
        Update marked positions.
        
        Args:
            positions: Dictionary of named positions
        """
        self.positions = positions
        self._update_display()
    
    def update_template_matches(self, matches: List[Tuple]) -> None:
        """
        Update template matches.
        
        Args:
            matches: List of template matches (name, x, y, w, h, conf)
        """
        self.template_matches = matches
        self._update_display()
    
    def update_ocr_regions(self, regions: List[Tuple]) -> None:
        """
        Update OCR regions.
        
        Args:
            regions: List of OCR regions (text, x, y, w, h)
        """
        self.ocr_regions = regions
        self._update_display()
    
    def update_mouse_position(self, x: int, y: int) -> None:
        """
        Update mouse cursor position.
        
        Args:
            x: X coordinate
            y: Y coordinate
        """
        self.mouse_position = (x, y)
        self._update_display()
    
    def toggle_grid(self, show: bool) -> None:
        """
        Toggle grid display.
        
        Args:
            show: Whether to show the grid
        """
        self.show_grid = show
        self._update_display()
    
    def set_grid_size(self, size: int) -> None:
        """
        Set grid size.
        
        Args:
            size: Grid size in pixels
        """
        self.grid_size = size
        if self.show_grid:
            self._update_display()
    
    def set_zoom(self, zoom: float) -> None:
        """
        Set zoom level.
        
        Args:
            zoom: Zoom level (1.0 = 100%)
        """
        self.zoom_level = max(0.1, min(5.0, zoom))
        self._update_display()
    
    def _update_display(self) -> None:
        """Update the display with current image and overlays."""
        if self.current_image is None:
            return
            
        try:
            # Convert image to RGB for Qt
            if len(self.current_image.shape) == 2:  # Grayscale
                display = cv2.cvtColor(self.current_image, cv2.COLOR_GRAY2RGB)
            else:  # Color (assume BGR)
                display = cv2.cvtColor(self.current_image, cv2.COLOR_BGR2RGB)
            
            # Create QImage
            h, w = display.shape[:2]
            bytes_per_line = 3 * w
            q_img = QImage(display.data, w, h, bytes_per_line, QImage.Format.Format_RGB888)
            
            # Create pixmap for drawing
            pixmap = QPixmap.fromImage(q_img)
            
            # Apply zoom
            if self.zoom_level != 1.0:
                new_w = int(w * self.zoom_level)
                new_h = int(h * self.zoom_level)
                pixmap = pixmap.scaled(new_w, new_h, Qt.AspectRatioMode.KeepAspectRatio, 
                                     Qt.TransformationMode.SmoothTransformation)
            
            # Create painter for overlays
            painter = QPainter(pixmap)
            
            # Draw grid if enabled
            if self.show_grid:
                self._draw_grid(painter, pixmap.width(), pixmap.height())
            
            # Draw positions if enabled
            if self.show_positions:
                self._draw_positions(painter)
            
            # Draw template matches if enabled
            if self.show_templates:
                self._draw_template_matches(painter)
            
            # Draw OCR regions if enabled
            if self.show_ocr:
                self._draw_ocr_regions(painter)
            
            # Draw mouse position if enabled
            if self.show_mouse and self.mouse_position:
                self._draw_mouse_position(painter)
            
            # End painting
            painter.end()
            
            # Update display
            self.display_image = pixmap
            self.image_label.setPixmap(pixmap)
            
        except Exception as e:
            logger.error(f"Error updating preview display: {e}")
    
    def _draw_grid(self, painter: QPainter, width: int, height: int) -> None:
        """
        Draw grid on the image.
        
        Args:
            painter: QPainter to use
            width: Image width
            height: Image height
        """
        # Set pen for grid
        pen = QPen(QColor(100, 100, 100, 100))
        pen.setWidth(1)
        painter.setPen(pen)
        
        # Calculate grid size based on zoom
        grid_size = int(self.grid_size * self.zoom_level)
        
        # Draw vertical lines
        for x in range(0, width, grid_size):
            painter.drawLine(x, 0, x, height)
        
        # Draw horizontal lines
        for y in range(0, height, grid_size):
            painter.drawLine(0, y, width, y)
    
    def _draw_positions(self, painter: QPainter) -> None:
        """
        Draw marked positions on the image.
        
        Args:
            painter: QPainter to use
        """
        for name, pos in self.positions.items():
            # Calculate position with zoom
            x = int(pos.x * self.zoom_level)
            y = int(pos.y * self.zoom_level)
            
            # Set pen for position
            pen = QPen(QColor(0, 255, 0))
            pen.setWidth(2)
            painter.setPen(pen)
            
            # Draw crosshair
            size = 10
            painter.drawLine(x - size, y, x + size, y)
            painter.drawLine(x, y - size, x, y + size)
            
            # Draw name
            painter.drawText(x + 5, y - 5, name)
    
    def _draw_template_matches(self, painter: QPainter) -> None:
        """
        Draw template matches on the image.
        
        Args:
            painter: QPainter to use
        """
        for name, x, y, w, h, conf in self.template_matches:
            # Calculate position with zoom
            x = int(x * self.zoom_level)
            y = int(y * self.zoom_level)
            w = int(w * self.zoom_level)
            h = int(h * self.zoom_level)
            
            # Set pen color based on confidence
            if conf > 0.9:
                color = QColor(0, 255, 0)  # Green for high confidence
            elif conf > 0.7:
                color = QColor(255, 255, 0)  # Yellow for medium confidence
            else:
                color = QColor(255, 0, 0)  # Red for low confidence
            
            pen = QPen(color)
            pen.setWidth(2)
            painter.setPen(pen)
            
            # Draw rectangle
            painter.drawRect(x, y, w, h)
            
            # Draw name and confidence
            painter.drawText(x, y - 5, f"{name} ({conf:.2f})")
    
    def _draw_ocr_regions(self, painter: QPainter) -> None:
        """
        Draw OCR regions on the image.
        
        Args:
            painter: QPainter to use
        """
        for text, x, y, w, h in self.ocr_regions:
            # Calculate position with zoom
            x = int(x * self.zoom_level)
            y = int(y * self.zoom_level)
            w = int(w * self.zoom_level)
            h = int(h * self.zoom_level)
            
            # Set pen for OCR region
            pen = QPen(QColor(0, 0, 255))
            pen.setWidth(2)
            painter.setPen(pen)
            
            # Draw rectangle
            painter.drawRect(x, y, w, h)
            
            # Draw text
            painter.drawText(x, y - 5, text)
    
    def _draw_mouse_position(self, painter: QPainter) -> None:
        """
        Draw mouse position on the image.
        
        Args:
            painter: QPainter to use
        """
        x, y = self.mouse_position
        
        # Calculate position with zoom
        x = int(x * self.zoom_level)
        y = int(y * self.zoom_level)
        
        # Set pen for mouse position
        pen = QPen(QColor(255, 0, 255))
        pen.setWidth(2)
        painter.setPen(pen)
        
        # Draw crosshair
        size = 15
        painter.drawLine(x - size, y, x + size, y)
        painter.drawLine(x, y - size, x, y + size)
        
        # Draw coordinates
        painter.drawText(x + 10, y + 10, f"({int(x / self.zoom_level)}, {int(y / self.zoom_level)})")
    
    def mouseMoveEvent(self, event: QMouseEvent) -> None:
        """
        Handle mouse move event.
        
        Args:
            event: Mouse event
        """
        if self.display_image and self.image_label.rect().contains(event.pos()):
            # Calculate position relative to image
            pos = event.pos() - self.image_label.pos()
            
            # Convert to original image coordinates
            x = int(pos.x() / self.zoom_level)
            y = int(pos.y() / self.zoom_level)
            
            # Emit signal
            self.mouse_moved.emit(x, y)
        
        super().mouseMoveEvent(event)
    
    def mousePressEvent(self, event: QMouseEvent) -> None:
        """
        Handle mouse press event.
        
        Args:
            event: Mouse event
        """
        if self.display_image and self.image_label.rect().contains(event.pos()):
            # Calculate position relative to image
            pos = event.pos() - self.image_label.pos()
            
            # Convert to original image coordinates
            x = int(pos.x() / self.zoom_level)
            y = int(pos.y() / self.zoom_level)
            
            # Emit signal
            self.mouse_clicked.emit(x, y, event.button())
        
        super().mousePressEvent(event)
    
    def clear(self) -> None:
        """Clear all content."""
        self.current_image = None
        self.positions = {}
        self.template_matches = []
        self.ocr_regions = []
        self.mouse_position = None
        self.image_label.clear()