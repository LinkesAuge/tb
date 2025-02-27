"""
Image tab for debug window.

This module provides a tab for displaying and analyzing images in the debug window.
"""

from typing import Optional, Dict, Any, List, Tuple
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QLabel, QScrollArea, QHBoxLayout, QPushButton, QComboBox, QCheckBox
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QImage, QPixmap
import numpy as np
import cv2
import logging
from pathlib import Path
import os
import time

logger = logging.getLogger(__name__)

class ImageTab(QWidget):
    """
    A tab for displaying a single image with metadata.
    
    This widget provides:
    - Image display with automatic scaling
    - Metadata display (dimensions, type, etc.)
    - Optional overlay information
    - Image saving functionality
    """
    
    # Signals
    image_saved = pyqtSignal(str)  # Emitted when an image is saved (path)
    
    def __init__(self, name: str) -> None:
        """
        Initialize image tab.
        
        Args:
            name: Name of the tab
        """
        super().__init__()
        self.name = name
        self.current_image = None
        self.metadata = None
        
        # Create layout
        layout = QVBoxLayout()
        
        # Create toolbar
        toolbar_layout = QHBoxLayout()
        
        # Save button
        self.save_btn = QPushButton("Save Image")
        self.save_btn.setToolTip("Save current image to file")
        self.save_btn.clicked.connect(self._on_save_image)
        toolbar_layout.addWidget(self.save_btn)
        
        # Display options
        self.display_combo = QComboBox()
        self.display_combo.addItems(["Normal", "Grayscale", "Edges", "Thresholded"])
        self.display_combo.setToolTip("Select display mode")
        self.display_combo.currentIndexChanged.connect(self._update_display)
        toolbar_layout.addWidget(self.display_combo)
        
        # Show grid checkbox
        self.show_grid = QCheckBox("Show Grid")
        self.show_grid.setToolTip("Show grid overlay")
        self.show_grid.stateChanged.connect(self._update_display)
        toolbar_layout.addWidget(self.show_grid)
        
        # Add stretch to push buttons to the left
        toolbar_layout.addStretch()
        
        # Add toolbar to layout
        layout.addLayout(toolbar_layout)
        
        # Create scroll area for image
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        
        # Create image label
        self.image_label = QLabel()
        self.image_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.image_label.setMinimumSize(400, 300)
        scroll_area.setWidget(self.image_label)
        
        # Create info label
        self.info_label = QLabel()
        
        # Add widgets to layout
        layout.addWidget(scroll_area)
        layout.addWidget(self.info_label)
        
        # Set layout
        self.setLayout(layout)
        
        logger.debug(f"Image tab '{name}' initialized")
    
    def update_image(self, image: np.ndarray, metadata: Optional[Dict[str, Any]] = None) -> None:
        """
        Update the displayed image and metadata.
        
        Args:
            image: Image as numpy array
            metadata: Optional metadata to display
        """
        try:
            # Store image and metadata
            self.current_image = image.copy() if image is not None else None
            self.metadata = metadata
            
            # Update display
            self._update_display()
            
        except Exception as e:
            logger.error(f"Error updating image in tab {self.name}: {e}")
            self.info_label.setText(f"Error: {str(e)}")
    
    def _update_display(self) -> None:
        """Update the displayed image based on current settings."""
        if self.current_image is None:
            self.image_label.clear()
            self.info_label.clear()
            return
        
        try:
            # Get display mode
            mode = self.display_combo.currentText()
            
            # Process image based on mode
            display_image = self.current_image.copy()
            
            if mode == "Grayscale" and len(display_image.shape) == 3:
                display_image = cv2.cvtColor(display_image, cv2.COLOR_BGR2GRAY)
            elif mode == "Edges" and len(display_image.shape) == 3:
                gray = cv2.cvtColor(display_image, cv2.COLOR_BGR2GRAY)
                display_image = cv2.Canny(gray, 100, 200)
            elif mode == "Thresholded" and len(display_image.shape) == 3:
                gray = cv2.cvtColor(display_image, cv2.COLOR_BGR2GRAY)
                _, display_image = cv2.threshold(gray, 127, 255, cv2.THRESH_BINARY)
            
            # Add grid if requested
            if self.show_grid.isChecked():
                display_image = self._add_grid(display_image)
            
            # Convert image for display
            if len(display_image.shape) == 2:  # Grayscale
                h, w = display_image.shape
                bytes_per_line = w
                q_img = QImage(display_image.data, w, h, bytes_per_line, QImage.Format.Format_Grayscale8)
            else:  # Color (assume BGR)
                h, w, c = display_image.shape
                bytes_per_line = 3 * w
                rgb = cv2.cvtColor(display_image, cv2.COLOR_BGR2RGB)
                q_img = QImage(rgb.data, w, h, bytes_per_line, QImage.Format.Format_RGB888)
            
            # Scale image while preserving aspect ratio
            pixmap = QPixmap.fromImage(q_img)
            scaled = pixmap.scaled(800, 600, Qt.AspectRatioMode.KeepAspectRatio, 
                                 Qt.TransformationMode.SmoothTransformation)
            
            # Update image
            self.image_label.setPixmap(scaled)
            
            # Update info
            if self.current_image is not None:
                if len(self.current_image.shape) == 3:
                    h, w, c = self.current_image.shape
                    info_text = f"Size: {w}x{h}, Channels: {c}"
                else:
                    h, w = self.current_image.shape
                    info_text = f"Size: {w}x{h}, Grayscale"
                
                if self.metadata:
                    info_text += " | " + " | ".join(f"{k}: {v}" for k, v in self.metadata.items())
                self.info_label.setText(info_text)
            
        except Exception as e:
            logger.error(f"Error updating display in tab {self.name}: {e}")
            self.info_label.setText(f"Error: {str(e)}")
    
    def _add_grid(self, image: np.ndarray) -> np.ndarray:
        """
        Add a grid overlay to the image.
        
        Args:
            image: Image to add grid to
            
        Returns:
            Image with grid overlay
        """
        # Create a copy of the image
        result = image.copy()
        
        # Get image dimensions
        if len(result.shape) == 3:
            h, w, _ = result.shape
        else:
            h, w = result.shape
        
        # Define grid spacing (every 50 pixels)
        spacing = 50
        
        # Define grid color
        color = (0, 255, 0) if len(result.shape) == 3 else 255
        
        # Draw horizontal lines
        for y in range(0, h, spacing):
            if len(result.shape) == 3:
                cv2.line(result, (0, y), (w, y), color, 1)
            else:
                cv2.line(result, (0, y), (w, y), color, 1)
        
        # Draw vertical lines
        for x in range(0, w, spacing):
            if len(result.shape) == 3:
                cv2.line(result, (x, 0), (x, h), color, 1)
            else:
                cv2.line(result, (x, 0), (x, h), color, 1)
        
        return result
    
    def _on_save_image(self) -> None:
        """Save the current image to a file."""
        if self.current_image is None:
            logger.warning(f"No image to save in tab {self.name}")
            return
        
        try:
            # Create debug directory if it doesn't exist
            debug_dir = Path("scout/debug_output")
            os.makedirs(debug_dir, exist_ok=True)
            
            # Generate filename with timestamp
            timestamp = time.strftime("%Y%m%d-%H%M%S")
            filename = f"{self.name}_{timestamp}.png"
            filepath = debug_dir / filename
            
            # Save image
            cv2.imwrite(str(filepath), self.current_image)
            
            # Update info
            self.info_label.setText(f"Image saved to {filepath}")
            
            # Emit signal
            self.image_saved.emit(str(filepath))
            
            logger.debug(f"Image saved to {filepath}")
            
        except Exception as e:
            logger.error(f"Error saving image in tab {self.name}: {e}")
            self.info_label.setText(f"Error saving image: {str(e)}")
    
    def clear(self) -> None:
        """Clear the image and metadata."""
        self.current_image = None
        self.metadata = None
        self.image_label.clear()
        self.info_label.clear()