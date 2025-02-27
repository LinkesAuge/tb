"""
OCR tab for debug window.

This module provides a tab for visualizing and debugging OCR (Optical Character Recognition)
results in the debug window.
"""

from typing import Optional, Dict, Any, List, Tuple
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QSplitter, QGroupBox,
    QPushButton, QComboBox, QCheckBox, QSpinBox, QFileDialog, QTextEdit,
    QTableWidget, QTableWidgetItem, QHeaderView
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QPixmap, QFont
import numpy as np
import logging
import os
from pathlib import Path
import time
import cv2

from scout.debug.preview import ImagePreview

logger = logging.getLogger(__name__)

class OCRTab(QWidget):
    """
    A tab for visualizing and debugging OCR results.
    
    This widget provides:
    - Display of original image and processed image for OCR
    - Text extraction results with confidence scores
    - Region selection and visualization
    - OCR parameter adjustment
    """
    
    # Signals
    region_selected = pyqtSignal(tuple)  # Emitted when a region is selected (x, y, w, h)
    parameters_changed = pyqtSignal(dict)  # Emitted when OCR parameters are changed
    
    def __init__(self) -> None:
        """Initialize OCR tab."""
        super().__init__()
        
        # Set up UI
        self._setup_ui()
        
        # Initialize state
        self.current_image = None
        self.current_regions = []
        self.current_text = {}
        
        logger.debug("OCR tab initialized")
    
    def _setup_ui(self) -> None:
        """Set up the user interface."""
        # Main layout
        main_layout = QVBoxLayout(self)
        
        # Create splitter for resizable sections
        splitter = QSplitter(Qt.Orientation.Vertical)
        main_layout.addWidget(splitter)
        
        # Top section - Image preview and controls
        top_widget = QWidget()
        top_layout = QHBoxLayout(top_widget)
        
        # Image preview
        self.image_preview = ImagePreview()
        top_layout.addWidget(self.image_preview, 2)
        
        # Controls
        controls_widget = QWidget()
        controls_layout = QVBoxLayout(controls_widget)
        
        # OCR settings group
        settings_group = QGroupBox("OCR Settings")
        settings_layout = QVBoxLayout()
        
        # Language selection
        lang_layout = QHBoxLayout()
        lang_layout.addWidget(QLabel("Language:"))
        self.lang_combo = QComboBox()
        self.lang_combo.addItems(["eng", "rus", "deu", "fra", "spa", "ita"])
        self.lang_combo.currentTextChanged.connect(self._on_parameter_changed)
        lang_layout.addWidget(self.lang_combo)
        settings_layout.addLayout(lang_layout)
        
        # Page segmentation mode
        psm_layout = QHBoxLayout()
        psm_layout.addWidget(QLabel("Page Mode:"))
        self.psm_combo = QComboBox()
        self.psm_combo.addItems([
            "0 - OSD Only",
            "1 - Auto with OSD",
            "3 - Auto without OSD",
            "4 - Single column",
            "6 - Single block",
            "7 - Single line",
            "8 - Single word",
            "10 - Single char",
            "11 - Sparse text",
            "13 - Raw line"
        ])
        self.psm_combo.setCurrentIndex(3)  # Default to "3 - Auto without OSD"
        self.psm_combo.currentIndexChanged.connect(self._on_parameter_changed)
        psm_layout.addWidget(self.psm_combo)
        settings_layout.addLayout(psm_layout)
        
        # Preprocessing options
        preproc_layout = QVBoxLayout()
        preproc_layout.addWidget(QLabel("Preprocessing:"))
        
        # Grayscale
        self.gray_check = QCheckBox("Convert to grayscale")
        self.gray_check.setChecked(True)
        self.gray_check.stateChanged.connect(self._on_parameter_changed)
        preproc_layout.addWidget(self.gray_check)
        
        # Thresholding
        thresh_layout = QHBoxLayout()
        self.thresh_check = QCheckBox("Apply threshold")
        self.thresh_check.setChecked(True)
        self.thresh_check.stateChanged.connect(self._on_parameter_changed)
        thresh_layout.addWidget(self.thresh_check)
        
        thresh_layout.addWidget(QLabel("Value:"))
        self.thresh_spin = QSpinBox()
        self.thresh_spin.setRange(0, 255)
        self.thresh_spin.setValue(127)
        self.thresh_spin.valueChanged.connect(self._on_parameter_changed)
        thresh_layout.addWidget(self.thresh_spin)
        preproc_layout.addLayout(thresh_layout)
        
        # Noise reduction
        noise_layout = QHBoxLayout()
        self.noise_check = QCheckBox("Noise reduction")
        self.noise_check.setChecked(False)
        self.noise_check.stateChanged.connect(self._on_parameter_changed)
        noise_layout.addWidget(self.noise_check)
        
        noise_layout.addWidget(QLabel("Kernel:"))
        self.noise_spin = QSpinBox()
        self.noise_spin.setRange(1, 9)
        self.noise_spin.setValue(3)
        self.noise_spin.setSingleStep(2)  # Only odd values
        self.noise_spin.valueChanged.connect(self._on_parameter_changed)
        noise_layout.addWidget(self.noise_spin)
        preproc_layout.addLayout(noise_layout)
        
        settings_layout.addLayout(preproc_layout)
        
        # Action buttons
        button_layout = QHBoxLayout()
        
        self.process_btn = QPushButton("Process Image")
        self.process_btn.clicked.connect(self._on_process_clicked)
        button_layout.addWidget(self.process_btn)
        
        self.save_btn = QPushButton("Save Results")
        self.save_btn.clicked.connect(self._on_save_clicked)
        button_layout.addWidget(self.save_btn)
        
        settings_layout.addLayout(button_layout)
        
        settings_group.setLayout(settings_layout)
        controls_layout.addWidget(settings_group)
        
        # Status label
        self.status_label = QLabel("Ready")
        controls_layout.addWidget(self.status_label)
        
        top_layout.addWidget(controls_widget, 1)
        
        # Add top widget to splitter
        splitter.addWidget(top_widget)
        
        # Bottom section - Results
        bottom_widget = QWidget()
        bottom_layout = QHBoxLayout(bottom_widget)
        
        # Text results
        text_group = QGroupBox("Extracted Text")
        text_layout = QVBoxLayout()
        
        self.text_edit = QTextEdit()
        self.text_edit.setReadOnly(True)
        self.text_edit.setFont(QFont("Courier New", 10))
        text_layout.addWidget(self.text_edit)
        
        text_group.setLayout(text_layout)
        bottom_layout.addWidget(text_group)
        
        # Region details
        region_group = QGroupBox("Region Details")
        region_layout = QVBoxLayout()
        
        self.region_table = QTableWidget(0, 5)  # Rows will be added dynamically
        self.region_table.setHorizontalHeaderLabels(["Region", "Text", "Confidence", "Coordinates", "Size"])
        self.region_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
        self.region_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        region_layout.addWidget(self.region_table)
        
        region_group.setLayout(region_layout)
        bottom_layout.addWidget(region_group)
        
        # Add bottom widget to splitter
        splitter.addWidget(bottom_widget)
        
        # Set initial splitter sizes
        splitter.setSizes([400, 200])
    
    def set_image(self, image: np.ndarray) -> None:
        """
        Set the current image for OCR processing.
        
        Args:
            image: Image as numpy array
        """
        self.current_image = image.copy()
        self.image_preview.set_image(image)
        self.status_label.setText("Image loaded. Press 'Process Image' to perform OCR.")
    
    def set_regions(self, regions: List[Tuple[int, int, int, int]], 
                   texts: Optional[List[str]] = None,
                   confidences: Optional[List[float]] = None) -> None:
        """
        Set regions of interest with optional text and confidence values.
        
        Args:
            regions: List of regions as (x, y, w, h) tuples
            texts: Optional list of extracted text for each region
            confidences: Optional list of confidence scores for each region
        """
        self.current_regions = regions
        
        # Create a copy of the image for visualization
        if self.current_image is not None:
            vis_image = self.current_image.copy()
            
            # Draw regions
            for i, (x, y, w, h) in enumerate(regions):
                # Draw rectangle
                cv2.rectangle(vis_image, (x, y), (x + w, y + h), (0, 255, 0), 2)
                
                # Draw region number
                cv2.putText(vis_image, str(i + 1), (x, y - 5),
                           cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
            
            # Update image preview
            self.image_preview.set_image(vis_image)
        
        # Update region table
        self.region_table.setRowCount(len(regions))
        
        for i, (x, y, w, h) in enumerate(regions):
            # Region number
            self.region_table.setItem(i, 0, QTableWidgetItem(str(i + 1)))
            
            # Text (if available)
            if texts and i < len(texts):
                self.region_table.setItem(i, 1, QTableWidgetItem(texts[i]))
            else:
                self.region_table.setItem(i, 1, QTableWidgetItem(""))
            
            # Confidence (if available)
            if confidences and i < len(confidences):
                conf_item = QTableWidgetItem(f"{confidences[i]:.2f}%")
                self.region_table.setItem(i, 2, conf_item)
            else:
                self.region_table.setItem(i, 2, QTableWidgetItem(""))
            
            # Coordinates
            coord_item = QTableWidgetItem(f"({x}, {y})")
            self.region_table.setItem(i, 3, coord_item)
            
            # Size
            size_item = QTableWidgetItem(f"{w} × {h}")
            self.region_table.setItem(i, 4, size_item)
    
    def set_text_results(self, text: str, regions_text: Dict[int, str] = None) -> None:
        """
        Set the OCR text results.
        
        Args:
            text: Full extracted text
            regions_text: Optional dictionary mapping region indices to extracted text
        """
        # Update text display
        self.text_edit.setText(text)
        
        # Update region table if region-specific text is provided
        if regions_text and self.region_table.rowCount() > 0:
            for region_idx, region_text in regions_text.items():
                if 0 <= region_idx < self.region_table.rowCount():
                    self.region_table.setItem(region_idx, 1, QTableWidgetItem(region_text))
    
    def get_ocr_parameters(self) -> Dict[str, Any]:
        """
        Get current OCR parameters.
        
        Returns:
            Dictionary of OCR parameters
        """
        # Extract PSM value from the combo box text (format: "3 - Auto without OSD")
        psm_text = self.psm_combo.currentText()
        psm_value = int(psm_text.split(" ")[0])
        
        return {
            "language": self.lang_combo.currentText(),
            "psm": psm_value,
            "preprocessing": {
                "grayscale": self.gray_check.isChecked(),
                "threshold": {
                    "enabled": self.thresh_check.isChecked(),
                    "value": self.thresh_spin.value()
                },
                "noise_reduction": {
                    "enabled": self.noise_check.isChecked(),
                    "kernel_size": self.noise_spin.value()
                }
            }
        }
    
    def _on_parameter_changed(self) -> None:
        """Handle OCR parameter changes."""
        params = self.get_ocr_parameters()
        self.parameters_changed.emit(params)
        self.status_label.setText("Parameters updated. Press 'Process Image' to apply.")
    
    def _on_process_clicked(self) -> None:
        """Handle process button click."""
        if self.current_image is None:
            self.status_label.setText("No image loaded. Capture or load an image first.")
            return
        
        # In a real implementation, this would call the OCR engine
        # For now, we'll just update the status
        self.status_label.setText("Processing image... (OCR engine integration pending)")
        
        # This would be replaced with actual OCR processing
        # For demonstration, we'll just show a placeholder
        self.text_edit.setText("OCR processing would happen here.\n\nThis is placeholder text.")
        
        # Example regions for demonstration
        example_regions = [
            (100, 100, 200, 50),
            (100, 200, 300, 50),
            (400, 150, 150, 100)
        ]
        example_texts = [
            "Sample text region 1",
            "Sample text region 2",
            "Region 3"
        ]
        example_confidences = [98.5, 87.2, 65.9]
        
        self.set_regions(example_regions, example_texts, example_confidences)
    
    def _on_save_clicked(self) -> None:
        """Handle save button click."""
        if not self.text_edit.toPlainText():
            self.status_label.setText("No OCR results to save.")
            return
        
        try:
            # Create debug directory if it doesn't exist
            debug_dir = Path("scout/debug_output")
            os.makedirs(debug_dir, exist_ok=True)
            
            # Generate filename with timestamp
            timestamp = time.strftime("%Y%m%d-%H%M%S")
            filename = f"ocr_results_{timestamp}.txt"
            filepath = debug_dir / filename
            
            # Save text
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(self.text_edit.toPlainText())
            
            # Update status
            self.status_label.setText(f"Results saved to {filepath}")
            
        except Exception as e:
            logger.error(f"Error saving OCR results: {e}")
            self.status_label.setText(f"Error saving results: {str(e)}")