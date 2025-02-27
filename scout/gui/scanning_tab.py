"""
Scanning Tab for TB Scout

This module provides the scanning tab functionality for the TB Scout application.
It contains controls for scanning the game world and displaying results.
"""

from typing import Optional
import logging

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QCheckBox,
    QGroupBox, QLabel, QComboBox, QSlider, QSpinBox
)
from PyQt6.QtCore import Qt, pyqtSignal, pyqtSlot

from scout.window_manager import WindowManager
from scout.overlay import Overlay
from scout.template_matcher import TemplateMatcher
from scout.world_scanner import WorldScanner
from scout.utils.logging_utils import get_logger

logger = get_logger(__name__)

class ScanningTab(QWidget):
    """
    Tab for scanning functionality.
    
    This tab provides:
    - Controls for starting/stopping scanning
    - Options for overlay display
    - Controls for scan parameters
    """
    
    # Signals
    scan_toggled = pyqtSignal(bool)
    overlay_toggled = pyqtSignal(bool)
    
    def __init__(
        self,
        window_manager: WindowManager,
        overlay: Overlay,
        template_matcher: TemplateMatcher,
        world_scanner: WorldScanner,
        parent: Optional[QWidget] = None
    ):
        """
        Initialize the scanning tab.
        
        Args:
            window_manager: Window manager instance
            overlay: Overlay instance
            template_matcher: Template matcher instance
            world_scanner: World scanner instance
            parent: Parent widget
        """
        super().__init__(parent)
        
        # Store component references
        self.window_manager = window_manager
        self.overlay = overlay
        self.template_matcher = template_matcher
        self.world_scanner = world_scanner
        
        # Setup UI
        self._setup_ui()
        
        # Connect signals
        self._connect_signals()
        
        logger.debug("Scanning tab initialized")
    
    def _setup_ui(self) -> None:
        """Set up the user interface."""
        # Create main layout
        main_layout = QVBoxLayout(self)
        
        # Add scanning controls
        controls_group = QGroupBox("Scanning Controls")
        controls_layout = QHBoxLayout(controls_group)
        
        # Add scan button
        self.scan_button = QPushButton("Start Scanning")
        self.scan_button.clicked.connect(self._toggle_scanning)
        controls_layout.addWidget(self.scan_button)
        
        # Add overlay toggle
        self.overlay_toggle = QCheckBox("Show Overlay")
        self.overlay_toggle.setChecked(True)
        self.overlay_toggle.stateChanged.connect(self._toggle_overlay)
        controls_layout.addWidget(self.overlay_toggle)
        
        # Add clear button
        self.clear_button = QPushButton("Clear Overlay")
        self.clear_button.clicked.connect(self._clear_overlay)
        controls_layout.addWidget(self.clear_button)
        
        # Add controls group to main layout
        main_layout.addWidget(controls_group)
        
        # Add scan options
        options_group = QGroupBox("Scan Options")
        options_layout = QVBoxLayout(options_group)
        
        # Add scan type selection
        scan_type_layout = QHBoxLayout()
        scan_type_label = QLabel("Scan Type:")
        self.scan_type_combo = QComboBox()
        self.scan_type_combo.addItems(["Full Scan", "Quick Scan", "Resource Scan", "Enemy Scan"])
        scan_type_layout.addWidget(scan_type_label)
        scan_type_layout.addWidget(self.scan_type_combo)
        options_layout.addLayout(scan_type_layout)
        
        # Add scan interval
        interval_layout = QHBoxLayout()
        interval_label = QLabel("Scan Interval (s):")
        self.interval_spin = QSpinBox()
        self.interval_spin.setRange(1, 60)
        self.interval_spin.setValue(5)
        interval_layout.addWidget(interval_label)
        interval_layout.addWidget(self.interval_spin)
        options_layout.addLayout(interval_layout)
        
        # Add confidence threshold slider
        confidence_layout = QHBoxLayout()
        confidence_label = QLabel("Match Confidence:")
        self.confidence_slider = QSlider(Qt.Orientation.Horizontal)
        self.confidence_slider.setRange(50, 100)
        self.confidence_slider.setValue(int(self.template_matcher.confidence_threshold * 100))
        self.confidence_slider.valueChanged.connect(self._update_confidence)
        self.confidence_value_label = QLabel(f"{self.template_matcher.confidence_threshold:.2f}")
        confidence_layout.addWidget(confidence_label)
        confidence_layout.addWidget(self.confidence_slider)
        confidence_layout.addWidget(self.confidence_value_label)
        options_layout.addLayout(confidence_layout)
        
        # Add options group to main layout
        main_layout.addWidget(options_group)
        
        # Add results area
        results_group = QGroupBox("Scan Results")
        results_layout = QVBoxLayout(results_group)
        
        # Add results label
        self.results_label = QLabel("No scan results yet")
        results_layout.addWidget(self.results_label)
        
        # Add results group to main layout
        main_layout.addWidget(results_group)
        
        # Add stretch to push everything to the top
        main_layout.addStretch()
    
    def _connect_signals(self) -> None:
        """Connect signals to slots."""
        # Connect world scanner signals
        self.world_scanner.scanning_started.connect(self._on_scanning_started)
        self.world_scanner.scanning_stopped.connect(self._on_scanning_stopped)
        self.world_scanner.scan_results_updated.connect(self._on_scan_results_updated)
    
    def _toggle_scanning(self) -> None:
        """Toggle scanning state."""
        if self.world_scanner.is_scanning:
            self.world_scanner.stop_scanning()
            self.scan_button.setText("Start Scanning")
        else:
            self.world_scanner.start_scanning()
            self.scan_button.setText("Stop Scanning")
        
        # Emit signal
        self.scan_toggled.emit(self.world_scanner.is_scanning)
    
    def _toggle_overlay(self, state: int) -> None:
        """
        Toggle overlay visibility.
        
        Args:
            state: Checkbox state
        """
        is_checked = state == Qt.CheckState.Checked.value
        self.overlay.set_visible(is_checked)
        
        # Emit signal
        self.overlay_toggled.emit(is_checked)
    
    def _clear_overlay(self) -> None:
        """Clear the overlay."""
        self.overlay.clear()
    
    def _update_confidence(self, value: int) -> None:
        """
        Update confidence threshold.
        
        Args:
            value: Slider value (50-100)
        """
        confidence = value / 100.0
        self.template_matcher.set_confidence_threshold(confidence)
        self.confidence_value_label.setText(f"{confidence:.2f}")
    
    @pyqtSlot()
    def _on_scanning_started(self) -> None:
        """Handle scanning started event."""
        self.scan_button.setText("Stop Scanning")
    
    @pyqtSlot()
    def _on_scanning_stopped(self) -> None:
        """Handle scanning stopped event."""
        self.scan_button.setText("Start Scanning")
    
    @pyqtSlot(dict)
    def _on_scan_results_updated(self, results: dict) -> None:
        """
        Handle scan results updated event.
        
        Args:
            results: Scan results dictionary
        """
        # Update results display
        if results:
            result_text = "Scan Results:\n"
            for key, value in results.items():
                result_text += f"- {key}: {value}\n"
            self.results_label.setText(result_text)
        else:
            self.results_label.setText("No scan results")
