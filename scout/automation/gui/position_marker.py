"""
Position Marker Overlay

This module provides a transparent overlay for marking and visualizing positions
in the game window. It allows users to:
- Click to mark new positions
- See existing marked positions
- Get visual feedback during position selection
"""

from typing import Optional, Tuple, Dict, List
from PyQt6.QtWidgets import QWidget, QLabel, QToolTip
from PyQt6.QtCore import Qt, pyqtSignal, QPoint, QRect
from PyQt6.QtGui import QPainter, QPen, QColor, QMouseEvent, QPaintEvent, QFont, QBrush
import logging
from scout.window_manager import WindowManager
from scout.automation.core import AutomationPosition

logger = logging.getLogger(__name__)

class PositionMarker(QWidget):
    """
    Transparent overlay for marking and displaying positions.
    
    This widget creates a transparent overlay that:
    - Shows marked positions with crosses
    - Allows clicking to mark new positions
    - Provides visual feedback during marking
    - Updates position coordinates relative to game window
    """
    
    # Signal emitted when a new position is marked
    position_marked = pyqtSignal(QPoint)
    # Signal emitted when marking is cancelled
    marking_cancelled = pyqtSignal()
    # Signal emitted when a position is selected from existing positions
    position_selected = pyqtSignal(str)
    
    def __init__(self, window_manager: WindowManager):
        """Initialize the position marker overlay."""
        super().__init__(None)  # No parent widget
        self.window_manager = window_manager
        
        # Configure window properties for click-through when not marking
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.WindowStaysOnTopHint |
            Qt.WindowType.Tool |
            Qt.WindowType.NoDropShadowWindowHint |
            Qt.WindowType.WindowTransparentForInput  # Allow click-through by default
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating)
        self.setAttribute(Qt.WidgetAttribute.WA_MouseTracking)  # Enable mouse tracking
        
        # Visual settings
        self.cross_size = 20
        self.cross_color = QColor(255, 165, 0)  # Orange
        self.cross_width = 2
        self.font_color = QColor(255, 255, 255)  # White
        self.font_size = 10
        self.hover_color = QColor(0, 255, 0, 100)  # Semi-transparent green
        self.selection_radius = 15  # Radius for position selection
        
        # State
        self.marked_positions: Dict[str, AutomationPosition] = {}
        self.current_position: Optional[QPoint] = None
        self.mouse_position: Optional[QPoint] = None  # Track current mouse position
        self.is_marking = False
        self.is_selecting = False  # Mode for selecting existing positions
        self.hovered_position: Optional[str] = None  # Currently hovered position name
        
        # Set cursor to crosshair
        self.setCursor(Qt.CursorShape.CrossCursor)
        
        logger.debug("Position marker initialized")
        
    def start_marking(self) -> None:
        """Enter position marking mode."""
        logger.debug("Starting position marking mode")
        
        # First find the game window
        if not self.window_manager.find_window():
            logger.error("Could not find game window")
            return
            
        # Get window position and size
        if pos := self.window_manager.get_window_position():
            x, y, width, height = pos
            logger.debug(f"Game window found at ({x}, {y}) with size {width}x{height}")
            
            # Enable mouse events by removing the transparent input flag
            self.setWindowFlags(
                self.windowFlags() & ~Qt.WindowType.WindowTransparentForInput
            )
            self.is_marking = True
            self.is_selecting = False
            self.mouse_position = None  # Reset mouse position
            
            # Set overlay size and position
            self.setGeometry(x, y, width, height)
            
            # Show and raise overlay
            self.show()
            self.raise_()
            self.activateWindow()  # Make sure our window gets focus
            
            logger.debug("Position marker overlay shown and activated")
        else:
            logger.error("Could not get window position")
            return
            
        self.update()
        
    def start_selecting(self) -> None:
        """Enter position selection mode."""
        logger.debug("Starting position selection mode")
        
        # First find the game window
        if not self.window_manager.find_window():
            logger.error("Could not find game window")
            return
            
        # Get window position and size
        if pos := self.window_manager.get_window_position():
            x, y, width, height = pos
            logger.debug(f"Game window found at ({x}, {y}) with size {width}x{height}")
            
            # Enable mouse events by removing the transparent input flag
            self.setWindowFlags(
                self.windowFlags() & ~Qt.WindowType.WindowTransparentForInput
            )
            self.is_marking = False
            self.is_selecting = True
            self.mouse_position = None  # Reset mouse position
            self.hovered_position = None
            
            # Set overlay size and position
            self.setGeometry(x, y, width, height)
            
            # Show and raise overlay
            self.show()
            self.raise_()
            self.activateWindow()  # Make sure our window gets focus
            
            logger.debug("Position selection overlay shown and activated")
        else:
            logger.error("Could not get window position")
            return
            
        self.update()
        
    def stop_marking(self) -> None:
        """Exit position marking mode."""
        logger.debug("Stopping position marking mode")
        self.is_marking = False
        self.is_selecting = False
        self.mouse_position = None  # Clear mouse position
        self.hovered_position = None
        
        # Restore click-through by adding back the transparent input flag
        self.setWindowFlags(
            self.windowFlags() | Qt.WindowType.WindowTransparentForInput
        )
        self.hide()
        self.current_position = None
        self.update()
        
    def update_positions(self, positions: Dict[str, AutomationPosition]) -> None:
        """
        Update the displayed positions.
        
        Args:
            positions: Dictionary of position name to AutomationPosition
        """
        self.marked_positions = positions
        self.update()
        
    def mousePressEvent(self, event: QMouseEvent) -> None:
        """Handle mouse press events for position marking."""
        if not self.is_marking and not self.is_selecting:
            logger.debug(f"Mouse press ignored - not in marking or selecting mode")
            return
            
        if event.button() != Qt.MouseButton.LeftButton:
            logger.debug(f"Mouse press ignored - not left button: {event.button()}")
            return
            
        try:
            # Get click position relative to widget
            pos = event.pos()
            window_x, window_y = pos.x(), pos.y()
            
            # Validate coordinates
            if window_x < 0 or window_y < 0:
                logger.warning(f"Invalid position coordinates: ({window_x}, {window_y})")
                return
            
            if self.is_marking:
                logger.debug(f"Position marked at window coordinates: ({window_x}, {window_y})")
                self.current_position = QPoint(window_x, window_y)
                self.position_marked.emit(self.current_position)
                self.stop_marking()  # Automatically stop marking after a position is marked
            
            elif self.is_selecting and self.hovered_position:
                logger.debug(f"Position selected: {self.hovered_position}")
                self.position_selected.emit(self.hovered_position)
                self.stop_marking()  # Stop selecting mode
                
        except Exception as e:
            logger.error(f"Error handling mouse press: {e}", exc_info=True)
            self.stop_marking()  # Ensure we stop marking on error
            
    def keyPressEvent(self, event) -> None:
        """Handle key press events."""
        if event.key() == Qt.Key.Key_Escape and (self.is_marking or self.is_selecting):
            logger.debug("ESC pressed - canceling position marking/selection")
            self.stop_marking()
            self.marking_cancelled.emit()  # Emit signal when cancelled
            event.accept()
        else:
            super().keyPressEvent(event)

    def mouseMoveEvent(self, event: QMouseEvent) -> None:
        """Handle mouse movement to update the display."""
        if self.is_marking or self.is_selecting:
            self.mouse_position = event.pos()
            
            # Check if mouse is hovering over any position in selection mode
            if self.is_selecting:
                self._update_hovered_position()
                
            self.update()  # Trigger repaint to update display
            
        super().mouseMoveEvent(event)
        
    def _update_hovered_position(self) -> None:
        """Update the currently hovered position."""
        if not self.mouse_position:
            self.hovered_position = None
            return
            
        mouse_x, mouse_y = self.mouse_position.x(), self.mouse_position.y()
        
        # Check if mouse is near any position
        for name, pos in self.marked_positions.items():
            distance = ((pos.x - mouse_x) ** 2 + (pos.y - mouse_y) ** 2) ** 0.5
            if distance <= self.selection_radius:
                if self.hovered_position != name:
                    self.hovered_position = name
                    # Show tooltip with position info
                    QToolTip.showText(
                        self.mapToGlobal(self.mouse_position),
                        f"{name}: ({pos.x}, {pos.y})\n{pos.description or ''}",
                        self
                    )
                return
                
        # No position hovered
        self.hovered_position = None

    def paintEvent(self, event: QPaintEvent) -> None:
        """Paint the overlay with crosses and coordinates."""
        if not self.is_marking and not self.is_selecting and not self.marked_positions:
            return
            
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        # Set font for text
        font = QFont()
        font.setPointSize(self.font_size)
        painter.setFont(font)
        
        # Only draw background when marking or selecting
        if self.is_marking or self.is_selecting:
            # Draw semi-transparent background to make overlay visible
            painter.fillRect(self.rect(), QColor(0, 0, 0, 15))  # Very light tint
            
            # Draw crosshair at current mouse position
            if self.mouse_position:
                x, y = self.mouse_position.x(), self.mouse_position.y()
                
                # Draw crosshair lines
                pen = QPen(self.cross_color)
                pen.setWidth(1)
                painter.setPen(pen)
                painter.drawLine(x, 0, x, self.height())
                painter.drawLine(0, y, self.width(), y)
                
                # Draw coordinates near cursor with shadow for better visibility
                text = f"({x}, {y})"
                
                # Draw text shadow
                painter.setPen(QPen(QColor(0, 0, 0)))
                for dx in [-1, 1]:
                    for dy in [-1, 1]:
                        painter.drawText(x + 15 + dx, y - 5 + dy, text)
                
                # Draw main text
                painter.setPen(QPen(self.font_color))
                painter.drawText(x + 15, y - 5, text)
        
        # Draw existing positions
        for name, pos in self.marked_positions.items():
            # Highlight hovered position in selection mode
            is_hovered = (self.is_selecting and self.hovered_position == name)
            self._draw_position(painter, pos.x, pos.y, name, is_hovered, pos.description)
            
        # Draw current position if marking
        if self.is_marking and self.current_position:
            self._draw_position(painter, self.current_position.x(), self.current_position.y(), "Current")
            
    def _draw_position(self, painter: QPainter, x: int, y: int, label: str, 
                      is_hovered: bool = False, description: Optional[str] = None) -> None:
        """
        Draw a position marker with coordinates.
        
        Args:
            painter: QPainter instance
            x: X coordinate
            y: Y coordinate
            label: Label to display
            is_hovered: Whether this position is being hovered over
            description: Optional description to display
        """
        # Draw highlight circle for hovered positions
        if is_hovered:
            painter.setBrush(QBrush(self.hover_color))
            painter.setPen(Qt.PenStyle.NoPen)
            painter.drawEllipse(QPoint(x, y), self.selection_radius, self.selection_radius)
        
        # Draw cross
        pen = QPen(self.cross_color)
        pen.setWidth(self.cross_width)
        painter.setPen(pen)
        
        half_size = self.cross_size // 2
        # Horizontal line
        painter.drawLine(x - half_size, y, x + half_size, y)
        # Vertical line
        painter.drawLine(x, y - half_size, x, y + half_size)
        
        # Prepare display text
        display_text = f"{label} ({x}, {y})"
        if description and is_hovered:
            display_text += f" - {description}"
        
        # Draw text shadow for better contrast
        painter.setPen(QPen(QColor(0, 0, 0)))
        for dx in [-1, 1]:
            for dy in [-1, 1]:
                painter.drawText(x + half_size + 5 + dx, y + dy, display_text)
        
        # Draw main text
        painter.setPen(QPen(self.font_color))
        painter.drawText(x + half_size + 5, y, display_text)
        
    def get_position_at(self, point: QPoint) -> Optional[str]:
        """
        Get the name of the position at the given point.
        
        Args:
            point: Point to check
            
        Returns:
            Name of the position if found, None otherwise
        """
        for name, pos in self.marked_positions.items():
            distance = ((pos.x - point.x()) ** 2 + (pos.y - point.y()) ** 2) ** 0.5
            if distance <= self.selection_radius:
                return name
        return None
        
    def get_all_position_names(self) -> List[str]:
        """
        Get a list of all position names.
        
        Returns:
            List of position names
        """
        painter.drawText(x + half_size + 5, y, label + f" ({x}, {y})") 
