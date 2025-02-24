from typing import Optional, Dict, Any, List, Tuple
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QLabel, QTabWidget, QScrollArea
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QImage, QPixmap
import numpy as np
import cv2
from pathlib import Path
import logging
from datetime import datetime
from scout.config_manager import ConfigManager

logger = logging.getLogger(__name__)

class ImageTab(QWidget):
    """
    A tab for displaying a single image with metadata.
    
    This widget provides:
    - Image display with automatic scaling
    - Metadata display (dimensions, type, etc.)
    - Optional overlay information
    """
    
    def __init__(self, name: str) -> None:
        """
        Initialize image tab.
        
        Args:
            name: Name of the tab
        """
        super().__init__()
        self.name = name
        
        # Create layout
        layout = QVBoxLayout()
        
        # Create scroll area for image
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        
        # Create image label
        self.image_label = QLabel()
        self.image_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        scroll.setWidget(self.image_label)
        
        # Create info label
        self.info_label = QLabel()
        self.info_label.setStyleSheet("QLabel { background-color: rgba(0, 0, 0, 50); padding: 5px; }")
        
        # Add widgets to layout
        layout.addWidget(scroll)
        layout.addWidget(self.info_label)
        self.setLayout(layout)
        
    def update_image(self, image: np.ndarray, metadata: Optional[Dict[str, Any]] = None) -> None:
        """
        Update the displayed image and metadata.
        
        Args:
            image: Image as numpy array
            metadata: Optional metadata to display
        """
        try:
            # Convert image for display
            if len(image.shape) == 2:  # Grayscale
                h, w = image.shape
                bytes_per_line = w
                q_img = QImage(image.data, w, h, bytes_per_line, QImage.Format.Format_Grayscale8)
            else:  # Color (assume BGR)
                h, w, c = image.shape
                bytes_per_line = 3 * w
                rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
                q_img = QImage(rgb.data, w, h, bytes_per_line, QImage.Format.Format_RGB888)
            
            # Scale image while preserving aspect ratio
            pixmap = QPixmap.fromImage(q_img)
            scaled = pixmap.scaled(800, 600, Qt.AspectRatioMode.KeepAspectRatio, 
                                 Qt.TransformationMode.SmoothTransformation)
            
            # Update image
            self.image_label.setPixmap(scaled)
            
            # Update info
            info_text = f"Size: {w}x{h}"
            if metadata:
                info_text += " | " + " | ".join(f"{k}: {v}" for k, v in metadata.items())
            self.info_label.setText(info_text)
            
        except Exception as e:
            logger.error(f"Error updating image in tab {self.name}: {e}")
            self.info_label.setText(f"Error: {str(e)}")

class DebugWindow(QWidget):
    """
    Debug visualization window supporting multiple image sources.
    
    Features:
    - Multiple tabs for different image sources
    - Automatic image scaling and format conversion
    - Metadata display
    - Image saving functionality
    - Support for overlays and annotations
    
    Signals:
        window_closed: Emitted when the debug window is closed by the user
    """
    
    # Add signal for window close
    window_closed = pyqtSignal()
    
    def __init__(self) -> None:
        """Initialize debug window."""
        super().__init__()
        self.setWindowTitle("Debug Viewer")
        self.setGeometry(100, 100, 900, 700)
        
        # Load config
        self.config_manager = ConfigManager()
        debug_settings = self.config_manager.get_debug_settings()
        
        # Initialize debug directory path from config
        self.debug_dir = Path(debug_settings["debug_screenshots_dir"])
        self.debug_dir.mkdir(exist_ok=True)
        
        # Create main layout
        layout = QVBoxLayout()
        
        # Create tab widget
        self.tabs = QTabWidget()
        self.tabs.setTabPosition(QTabWidget.TabPosition.North)
        layout.addWidget(self.tabs)
        
        # Initialize tab dictionary
        self.image_tabs: Dict[str, ImageTab] = {}
        
        # Set layout
        self.setLayout(layout)
        
        logger.debug("Debug window initialized")
    
    def closeEvent(self, event) -> None:
        """Handle window close event."""
        logger.debug("Debug window closed by user")
        self.window_closed.emit()
        super().closeEvent(event)
    
    def update_image(self, name: str, image: np.ndarray, 
                    metadata: Optional[Dict[str, Any]] = None,
                    save: bool = False) -> None:
        """
        Update or create an image tab.
        
        Args:
            name: Name/identifier for the image tab
            image: Image data as numpy array
            metadata: Optional metadata to display
            save: Whether to save the image to disk
        """
        try:
            # Create tab if it doesn't exist
            if name not in self.image_tabs:
                tab = ImageTab(name)
                self.image_tabs[name] = tab
                self.tabs.addTab(tab, name)
            
            # Update tab
            self.image_tabs[name].update_image(image, metadata)
            
            # Save image if requested
            if save:
                save_path = self.debug_dir / f"{name}.png"
                cv2.imwrite(str(save_path), image)
                logger.debug(f"Saved debug image to {save_path}")
            
        except Exception as e:
            logger.error(f"Error updating debug image '{name}': {e}")
    
    def update_region(self, name: str, image: np.ndarray, 
                     regions: List[Tuple[int, int, int, int]],
                     labels: Optional[List[str]] = None,
                     colors: Optional[List[Tuple[int, int, int]]] = None) -> None:
        """
        Update image with highlighted regions.
        
        Args:
            name: Name/identifier for the image tab
            image: Base image
            regions: List of (x, y, w, h) regions to highlight
            labels: Optional list of labels for regions
            colors: Optional list of BGR colors for regions
        """
        try:
            # Create copy of image
            display = image.copy()
            
            # Default color if none provided
            if not colors:
                colors = [(0, 255, 0)] * len(regions)  # Green
            elif len(colors) < len(regions):
                colors.extend([(0, 255, 0)] * (len(regions) - len(colors)))
            
            # Draw regions
            for i, (x, y, w, h) in enumerate(regions):
                color = colors[i]
                cv2.rectangle(display, (x, y), (x + w, y + h), color, 2)
                
                if labels and i < len(labels):
                    cv2.putText(display, labels[i], (x, y - 5),
                              cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 1)
            
            # Update display
            self.update_image(name, display, 
                            metadata={"regions": len(regions)},
                            save=True)
            
        except Exception as e:
            logger.error(f"Error updating region display '{name}': {e}")
    
    def clear(self) -> None:
        """Clear all tabs."""
        for _ in range(self.tabs.count()):
            self.tabs.removeTab(0)
        self.image_tabs.clear()
        
    def show_tab(self, name: str) -> None:
        """
        Show specific tab.
        
        Args:
            name: Name of tab to show
        """
        if name in self.image_tabs:
            index = self.tabs.indexOf(self.image_tabs[name])
            if index >= 0:
                self.tabs.setCurrentIndex(index)
                
    def remove_tab(self, name: str) -> None:
        """
        Remove a specific tab.
        
        Args:
            name: Name of tab to remove
        """
        if name in self.image_tabs:
            index = self.tabs.indexOf(self.image_tabs[name])
            if index >= 0:
                self.tabs.removeTab(index)
                del self.image_tabs[name] 