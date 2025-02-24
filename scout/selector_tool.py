from typing import Dict, Optional
from PyQt6.QtWidgets import QWidget, QLabel, QMessageBox, QApplication
from PyQt6.QtCore import Qt, QTimer, pyqtSignal
from PyQt6.QtGui import QPainter, QPen, QColor, QBrush, QPaintEvent, QMouseEvent
import logging
import win32gui
import win32con
import ctypes
from ctypes.wintypes import RECT, POINT
from scout.window_capture import WindowCapture
from scout.window_manager import WindowManager

logger = logging.getLogger(__name__)

class SelectorTool(QWidget):
    """
    A widget for selecting a region of the screen.
    
    This tool creates a transparent overlay over the game window
    and allows users to click and drag to select a rectangular region.
    It uses the same window manager as the main overlay to ensure
    consistent coordinate handling across the application.
    
    Signals:
        region_selected: Emits a dict containing the selected region coordinates
        selection_cancelled: Emits when selection is cancelled
    """
    
    region_selected = pyqtSignal(dict)  # Emits region as dict (left, top, width, height)
    selection_cancelled = pyqtSignal()  # Emits when selection is cancelled
    
    def __init__(self, window_manager: WindowManager, instruction_text: str = "Click and drag to select a region") -> None:
        """
        Initialize the selector tool.
        
        Args:
            window_manager: The window manager instance for coordinate handling
            instruction_text: Text to display as instructions for the user
        """
        super().__init__()
        logger.info("Initializing selector tool")
        
        self.window_manager = window_manager
        
        # Set window flags for a fullscreen overlay
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.WindowStaysOnTopHint
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setCursor(Qt.CursorShape.CrossCursor)
        
        # Initialize selection variables
        self.start_pos = None
        self.current_pos = None
        self.is_selecting = False
        
        # Get the game window position
        if not self.window_manager.find_window():
            logger.error("Game window not found")
            return
            
        window_pos = self.window_manager.get_window_position()
        if not window_pos:
            logger.error("Could not get window position")
            return
            
        x, y, width, height = window_pos
        logger.debug(f"Setting selector to cover game window: pos=({x}, {y}), size={width}x{height}")
        self.setGeometry(x, y, width, height)
        
        # Add instruction label
        self.instruction_label = QLabel(instruction_text, self)
        self.instruction_label.setStyleSheet("""
            QLabel {
                color: white;
                background-color: rgba(0, 0, 0, 150);
                padding: 10px;
                border-radius: 5px;
            }
        """)
        self.instruction_label.adjustSize()
        self.instruction_label.move(20, 20)
        logger.debug("Instruction label created and positioned")
        
    def paintEvent(self, event: QPaintEvent) -> None:
        """Draw the selection overlay."""
        painter = QPainter(self)
        
        # Draw semi-transparent background
        painter.fillRect(self.rect(), QColor(0, 0, 0, 1))  # Almost transparent black
        
        if self.is_selecting and self.start_pos and self.current_pos:
            # Draw selection rectangle
            painter.setPen(QPen(QColor(0, 255, 0), 2))  # Green border
            color = QColor(0, 255, 0, 50)  # Green with 50/255 alpha
            painter.setBrush(QBrush(color))
            
            x = min(self.start_pos.x(), self.current_pos.x())
            y = min(self.start_pos.y(), self.current_pos.y())
            width = abs(self.current_pos.x() - self.start_pos.x())
            height = abs(self.current_pos.y() - self.start_pos.y())
            
            painter.drawRect(x, y, width, height)
            
            # Draw size info
            size_text = f"{width}x{height}"
            painter.setPen(QPen(QColor(255, 255, 255)))  # White text
            painter.drawText(x + 5, y - 5, size_text)
            logger.debug(f"Drawing selection rectangle: pos=({x}, {y}), size={width}x{height}")
            
    def mousePressEvent(self, event: QMouseEvent) -> None:
        """Handle mouse press event to start selection."""
        if event.button() == Qt.MouseButton.LeftButton:
            self.start_pos = event.pos()
            self.current_pos = event.pos()
            self.is_selecting = True
            logger.debug(f"Started selection at: ({event.pos().x()}, {event.pos().y()})")
            
    def mouseMoveEvent(self, event: QMouseEvent) -> None:
        """Handle mouse move event to update selection."""
        if self.is_selecting:
            self.current_pos = event.pos()
            logger.debug(f"Updated selection to: ({event.pos().x()}, {event.pos().y()})")
            self.update()  # Trigger repaint
            
    def mouseReleaseEvent(self, event: QMouseEvent) -> None:
        """Handle mouse release event to complete selection."""
        if event.button() == Qt.MouseButton.LeftButton and self.is_selecting:
            self.is_selecting = False
            if self.start_pos and self.current_pos:
                # Calculate region in logical coordinates (relative to game window)
                x1, y1 = self.start_pos.x(), self.start_pos.y()
                x2, y2 = self.current_pos.x(), self.current_pos.y()
                left = min(x1, x2)
                top = min(y1, y2)
                width = abs(x2 - x1)
                height = abs(y2 - y1)
                
                # Get screen info for DPI scaling
                screen = QApplication.screenAt(event.pos())
                if not screen:
                    logger.warning("Could not determine screen for selection")
                    screen = QApplication.primaryScreen()
                
                dpi_scale = screen.devicePixelRatio()
                logger.debug(f"Selection on screen with DPI scale: {dpi_scale}")
                
                # Convert to physical coordinates using DPI scale
                physical_left = int(left * dpi_scale)
                physical_top = int(top * dpi_scale)
                physical_width = int(width * dpi_scale)
                physical_height = int(height * dpi_scale)
                
                # Get window position to make coordinates relative to screen
                window_pos = self.window_manager.get_window_position()
                if window_pos:
                    window_x, window_y, _, _ = window_pos
                    physical_left += window_x
                    physical_top += window_y
                
                logger.debug(f"Coordinate conversion:")
                logger.debug(f"Window-relative coords: ({left}, {top})")
                logger.debug(f"Screen coords: ({physical_left}, {physical_top})")
                logger.debug(f"Physical size: {physical_width}x{physical_height}")
                
                region = {
                    'left': physical_left,
                    'top': physical_top,
                    'width': physical_width,
                    'height': physical_height,
                    'dpi_scale': dpi_scale,
                    'logical_coords': {
                        'left': left,
                        'top': top,
                        'width': width,
                        'height': height
                    }
                }
                
                logger.info(f"Selection completed: Physical={region}, Logical={region['logical_coords']}")
                
                # Emit the region
                self.region_selected.emit(region)
            else:
                logger.warning("Invalid selection - missing start or end position")
                self.selection_cancelled.emit()
            self.close()
        elif event.button() == Qt.MouseButton.RightButton:
            logger.info("Selection cancelled by right click")
            self.selection_cancelled.emit()
            self.close() 