"""
Scanning Tab for TB Scout

This module provides the scanning tab functionality for the TB Scout application.
It contains controls for scanning the game world and displaying results.
"""

from typing import Optional
import logging
import time
from pathlib import Path

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QCheckBox,
    QGroupBox, QLabel, QComboBox, QSlider, QSpinBox, QLineEdit, QFileDialog, QMessageBox
)
from PyQt6.QtCore import Qt, pyqtSignal, pyqtSlot, QTimer

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
        
        # Enable debug mode by default
        if hasattr(self.template_matcher, 'set_debug_mode'):
            self.template_matcher.set_debug_mode(True)
            logger.info("Debug mode enabled by default in template matcher")
        
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
        
        # Simplified scan type selection - removed coordinate-based options
        scan_type_layout = QHBoxLayout()
        scan_type_label = QLabel("Scan Mode:")
        self.scan_type_combo = QComboBox()
        self.scan_type_combo.addItems(["Full Window Scan", "Template Test Mode"])
        scan_type_layout.addWidget(scan_type_label)
        scan_type_layout.addWidget(self.scan_type_combo)
        options_layout.addLayout(scan_type_layout)
        
        # Add scan interval
        interval_layout = QHBoxLayout()
        interval_label = QLabel("Scan Interval (s):")
        self.interval_spin = QSpinBox()
        self.interval_spin.setRange(1, 10)
        self.interval_spin.setValue(1)
        self.interval_spin.valueChanged.connect(self._update_scan_interval)
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
        
        # Add debug controls
        debug_group = QGroupBox("Debug Tools")
        debug_layout = QVBoxLayout(debug_group)
        
        # Add debug mode toggle
        debug_mode_layout = QHBoxLayout()
        self.debug_mode_checkbox = QCheckBox("Enable Debug Mode")
        self.debug_mode_checkbox.setChecked(True)
        self.debug_mode_checkbox.stateChanged.connect(self._toggle_debug_mode)
        debug_mode_layout.addWidget(self.debug_mode_checkbox)
        
        # Add explanation label
        debug_mode_explanation = QLabel("Debug mode enables test templates and additional logging")
        debug_mode_layout.addWidget(debug_mode_explanation)
        debug_mode_layout.addStretch()
        debug_layout.addLayout(debug_mode_layout)
        
        # Add debug button for testing
        debug_btn_layout = QHBoxLayout()
        self.debug_btn = QPushButton("Create Test Matches")
        self.debug_btn.clicked.connect(self._create_test_matches)
        self.test_templates_btn = QPushButton("Test All Templates")
        self.test_templates_btn.clicked.connect(self._test_all_templates)
        debug_btn_layout.addWidget(self.debug_btn)
        debug_btn_layout.addWidget(self.test_templates_btn)
        debug_layout.addLayout(debug_btn_layout)
        
        # Add debug visuals toggle
        debug_visuals_layout = QHBoxLayout()
        self.debug_visuals_btn = QPushButton("Toggle Debug Visuals")
        self.debug_visuals_btn.clicked.connect(self._toggle_debug_visuals)
        self.debug_info_btn = QPushButton("Toggle Debug Info")
        self.debug_info_btn.clicked.connect(self._toggle_debug_info)
        debug_visuals_layout.addWidget(self.debug_visuals_btn)
        debug_visuals_layout.addWidget(self.debug_info_btn)
        debug_layout.addLayout(debug_visuals_layout)
        
        # Add template tester
        template_test_layout = QHBoxLayout()
        template_test_label = QLabel("Test Template:")
        self.template_input = QLineEdit()
        self.template_input.setPlaceholderText("Enter template name")
        self.test_template_btn = QPushButton("Test Specific Template")
        self.test_template_btn.clicked.connect(self._test_specific_template)
        
        # Add template list button
        list_templates_btn = QPushButton("List Templates")
        list_templates_btn.clicked.connect(self._list_available_templates)
        
        # Add template folder selection button
        custom_templates_btn = QPushButton("Select Templates Folder")
        custom_templates_btn.clicked.connect(self._select_templates_folder)
        custom_templates_btn.setToolTip("Select a folder containing custom template images")
        
        template_test_layout.addWidget(template_test_label)
        template_test_layout.addWidget(self.template_input)
        template_test_layout.addWidget(self.test_template_btn)
        template_test_layout.addWidget(list_templates_btn)
        template_test_layout.addWidget(custom_templates_btn)
        
        # Add this layout to the debug layout
        debug_layout.addLayout(template_test_layout)
        
        # Add debug group to main layout
        main_layout.addWidget(debug_group)
        
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
        try:
            # Get the current state before toggling
            was_scanning = self.world_scanner.is_scanning
            
            # Log the current state
            logger.debug(f"Toggle scanning called. Current state: is_scanning={was_scanning}")
            
            # Update scan interval before starting
            if not was_scanning:
                self._update_scan_interval(self.interval_spin.value())
                
                # Enable debug mode in template matcher for scanning
                if hasattr(self.template_matcher, 'set_debug_mode'):
                    self.template_matcher.set_debug_mode(True)
                    logger.info("Enabled debug mode in template matcher for scanning")
                else:
                    logger.warning("Template matcher doesn't have set_debug_mode method")
            
            # Toggle the scanning state
            if was_scanning:
                logger.debug("Stopping scanning...")
                self.world_scanner.stop_scanning()
                self.scan_button.setText("Start Scanning")
                
                # Disable debug mode when scanning stops
                if hasattr(self.template_matcher, 'set_debug_mode'):
                    self.template_matcher.set_debug_mode(False)
                    logger.info("Disabled debug mode in template matcher")
            else:
                logger.debug("Starting scanning...")
                self.world_scanner.start_scanning()
                self.scan_button.setText("Stop Scanning")
            
            # Verify that the state actually changed
            if was_scanning == self.world_scanner.is_scanning:
                logger.warning(f"World scanner state did not change! Forcing state to {not was_scanning}")
                # Force the state to change
                self.world_scanner.is_scanning = not was_scanning
            
            # Emit signal with the new state
            logger.debug(f"Emitting scan_toggled signal with state: {self.world_scanner.is_scanning}")
            self.scan_toggled.emit(self.world_scanner.is_scanning)
            
        except Exception as e:
            logger.error(f"Error in _toggle_scanning: {e}", exc_info=True)
    
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
        
        # Update template matcher confidence
        if hasattr(self.template_matcher, 'set_confidence_threshold'):
            self.template_matcher.set_confidence_threshold(confidence)
            logger.info(f"Updated template matcher confidence threshold to {confidence:.2f}")
        
        # Update the confidence label
        self.confidence_value_label.setText(f"{confidence:.2f}")
        
        # Force clearing the overlay cache to ensure only matches meeting the new threshold are shown
        if hasattr(self.overlay, 'clear'):
            self.overlay.clear()
            logger.info(f"Cleared overlay cache after confidence threshold change to {confidence:.2f}")
            
        # Update configuration to save the setting
        if hasattr(self, 'config_manager'):
            self.config_manager.set("templates.confidence", str(confidence))
            self.config_manager.save_config()
            logger.debug(f"Saved confidence threshold {confidence:.2f} to configuration")
            
        # Force a new template scan to apply the new threshold immediately
        if hasattr(self.world_scanner, 'is_scanning') and self.world_scanner.is_scanning:
            # Force an immediate update if currently scanning
            if hasattr(self.overlay, '_update_template_matching'):
                logger.info(f"Forcing template matching update with new threshold: {confidence:.2f}")
                
                # Force multiple updates to ensure the new confidence is applied
                QTimer.singleShot(100, self.overlay._update_template_matching)
                QTimer.singleShot(300, self.overlay._update_template_matching)
                QTimer.singleShot(500, self.overlay._update_template_matching)
    
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
            
            # First display the most important information
            for key in ["status", "matches_found", "templates_checked", "screenshots_taken"]:
                if key in results:
                    result_text += f"- {key}: {results[key]}\n"
            
            # Then display timing information
            for key in ["elapsed_time_str", "start_time_str", "last_update"]:
                if key in results:
                    result_text += f"- {key}: {results[key]}\n"
            
            # Display any remaining information
            for key, value in results.items():
                if key not in ["status", "matches_found", "templates_checked", "screenshots_taken", 
                              "elapsed_time_str", "start_time_str", "last_update"]:
                    result_text += f"- {key}: {value}\n"
                    
            self.results_label.setText(result_text)
        else:
            self.results_label.setText("No scan results")
    
    def _create_test_matches(self) -> None:
        """Create fake template matches for debugging purposes."""
        try:
            logger.info("Creating test template matches")
            
            if not hasattr(self.overlay, 'cached_matches'):
                logger.error("Overlay has no cached_matches attribute")
                return
                
            # Clear any existing matches
            self.overlay.cached_matches = []
            
            # Create some fake match tuples (template_name, x, y, w, h, confidence)
            test_matches = [
                ('test_template1', 400, 300, 50, 50, 0.95),
                ('test_template2', 600, 400, 80, 60, 0.87),
                ('test_template3', 800, 500, 40, 40, 0.78)
            ]
            
            # Add to overlay's cached matches
            self.overlay.cached_matches.extend(test_matches)
            logger.info(f"Added {len(test_matches)} test matches to overlay")
            
            # Update scan results if world scanner is available
            if hasattr(self.world_scanner, 'scan_results'):
                self.world_scanner.scan_results.update({
                    "matches_found": len(test_matches),
                    "templates_checked": 3,
                    "status": "Testing",
                    "test_mode": True
                })
                self.world_scanner.scan_results_updated.emit(self.world_scanner.scan_results)
                logger.info("Updated scan results with test data")
            
            # Force overlay to redraw
            if hasattr(self.overlay, '_draw_overlay'):
                self.overlay._draw_overlay()
                logger.info("Forced overlay redraw with test matches")
            
            # Show message in results area
            self.results_label.setText(f"Test matches created: {len(test_matches)}")
            
        except Exception as e:
            logger.error(f"Error creating test matches: {e}", exc_info=True)

    def _test_all_templates(self) -> None:
        """Test all templates at different confidence thresholds."""
        try:
            logger.info("Running template test with different thresholds")
            
            if not hasattr(self.template_matcher, 'test_all_templates'):
                logger.error("Template matcher has no test_all_templates method")
                return
                
            # Make sure the overlay is visible
            if hasattr(self.overlay, 'set_visible'):
                self.overlay.set_visible(True)
                
            # Make sure template matching is active
            if hasattr(self.overlay, 'template_matching_active'):
                self.overlay.template_matching_active = True
                
            # Run the test
            test_matches = self.template_matcher.test_all_templates()
            
            # Update overlay with test matches
            if test_matches:
                if hasattr(self.overlay, 'cached_matches'):
                    self.overlay.cached_matches = test_matches
                    logger.info(f"Added {len(test_matches)} test matches to overlay")
                    
                    # Force overlay to redraw
                    if hasattr(self.overlay, '_draw_overlay'):
                        self.overlay._draw_overlay()
                        logger.info("Forced overlay redraw with test matches")
                        
                    # Show message in results area
                    self.results_label.setText(f"Template test found {len(test_matches)} matches")
                    
                    # Update scan results if world scanner is available
                    if hasattr(self.world_scanner, 'scan_results'):
                        self.world_scanner.scan_results.update({
                            "matches_found": len(test_matches),
                            "templates_checked": len(self.template_matcher.templates),
                            "status": "Testing",
                            "test_mode": True,
                            "threshold": "variable"
                        })
                        self.world_scanner.scan_results_updated.emit(self.world_scanner.scan_results)
            else:
                logger.warning("No matches found in template test")
                self.results_label.setText("No matches found in template test")
            
        except Exception as e:
            logger.error(f"Error testing templates: {e}", exc_info=True)

    def _test_specific_template(self):
        """Test a specific template with progressively lower thresholds."""
        try:
            template_name = self.template_input.text().strip()
            if not template_name:
                self.results_label.setText("Please enter a template name to test")
                return
                
            self.results_label.setText(f"Testing template: {template_name}")
            
            # Check if template matcher is available
            if not hasattr(self, 'template_matcher') or not self.template_matcher:
                self.results_label.setText("Template matcher not available")
                logger.error("Template matcher not available for testing")
                return
                
            # Make overlay visible if it isn't already
            if hasattr(self, 'overlay') and self.overlay:
                self.overlay.set_visible(True)
                self.overlay.active = True
                
            # Test the template
            if hasattr(self.template_matcher, 'find_template_with_progressively_lower_threshold'):
                # Get the template matches
                matches = self.template_matcher.find_template_with_progressively_lower_threshold(template_name)
                match_count = len(matches)
                
                if match_count > 0:
                    # Update the overlay with these matches
                    if hasattr(self, 'overlay') and self.overlay:
                        self.overlay.cached_matches = matches
                        # Force redraw
                        if hasattr(self.overlay, '_draw_overlay'):
                            self.overlay._draw_overlay()
                            
                    # Display results
                    result_text = f"Found {match_count} matches for {template_name}\n"
                    for i, match in enumerate(matches[:5]):
                        name, x, y, w, h, conf = match
                        result_text += f"Match {i+1}: ({x}, {y}) size {w}x{h} confidence={conf:.4f}\n"
                    self.results_label.setText(result_text)
                    
                    # Update world scanner if available
                    if hasattr(self, 'world_scanner') and self.world_scanner:
                        scan_results = {
                            'status': 'Debug',
                            'matches_found': match_count,
                            'templates_checked': 1,
                            'last_update': time.strftime("%H:%M:%S")
                        }
                        self.world_scanner.scan_results.update(scan_results)
                        self.world_scanner.scan_results_updated.emit(scan_results)
                else:
                    self.results_label.setText(f"No matches found for template: {template_name}")
            else:
                self.results_label.setText("Template matcher does not support progressive threshold testing")
                
        except Exception as e:
            error_msg = f"Error testing template: {str(e)}"
            logger.error(error_msg, exc_info=True)
            self.results_label.setText(error_msg)

    def _list_available_templates(self):
        """List all available templates in the results area."""
        try:
            if not hasattr(self, 'template_matcher') or not self.template_matcher:
                self.results_label.setText("Template matcher not available")
                return
                
            # Check if templates are available
            if not hasattr(self.template_matcher, 'templates'):
                self.results_label.setText("No templates dictionary available")
                return
                
            templates = self.template_matcher.templates
            if not templates:
                self.results_label.setText("No templates loaded")
                logger.warning("No templates loaded in template matcher")
                return
                
            # Display template list
            template_names = list(templates.keys())
            template_names.sort()
            
            result_text = f"Available Templates ({len(template_names)}):\n"
            
            # Display details about each template
            for name in template_names:
                template = templates[name]
                # Get template dimensions
                h, w = template.shape[:2]
                result_text += f"• {name} ({w}x{h})\n"
                
            self.results_label.setText(result_text)
            logger.info(f"Listed {len(template_names)} available templates")
            
        except Exception as e:
            error_msg = f"Error listing templates: {str(e)}"
            logger.error(error_msg, exc_info=True)
            self.results_label.setText(error_msg)

    def _toggle_debug_visuals(self) -> None:
        """Toggle debug visualizations on/off."""
        try:
            if hasattr(self.overlay, 'toggle_debug_visuals'):
                self.overlay.toggle_debug_visuals()
                logger.info("Toggled debug visuals")
            else:
                logger.error("Overlay object does not have toggle_debug_visuals method")
        except Exception as e:
            logger.error(f"Error toggling debug visuals: {e}")
    
    def _toggle_debug_info(self) -> None:
        """Toggle debug information display on/off."""
        try:
            if hasattr(self.overlay, 'toggle_debug_info'):
                self.overlay.toggle_debug_info()
                logger.info("Toggled debug info")
            else:
                logger.error("Overlay object does not have toggle_debug_info method")
        except Exception as e:
            logger.error(f"Error toggling debug info: {e}")

    def _update_scan_interval(self, value: int) -> None:
        """
        Update scan interval.
        
        Args:
            value: Interval in seconds
        """
        # Set the scan interval on the WorldScanner
        if hasattr(self.world_scanner, 'set_scan_interval'):
            self.world_scanner.set_scan_interval(float(value))
            logger.info(f"Updated scan interval to {value} seconds")
        else:
            logger.warning("WorldScanner doesn't have a set_scan_interval method")

    def _toggle_debug_mode(self, state: int) -> None:
        """
        Toggle debug mode in the template matcher.
        
        Args:
            state: Checkbox state
        """
        try:
            is_checked = state == Qt.CheckState.Checked.value
            if not hasattr(self.template_matcher, 'set_debug_mode'):
                logger.warning("Template matcher doesn't have set_debug_mode method")
                return
            
            self.template_matcher.set_debug_mode(is_checked)
            logger.info(f"Debug mode {'enabled' if is_checked else 'disabled'}")
            
            # If debug mode is enabled, clear the overlay and force an update
            if is_checked and hasattr(self.overlay, 'clear'):
                self.overlay.clear()
                
                # If we're scanning, force an immediate update
                if hasattr(self.world_scanner, 'is_scanning') and self.world_scanner.is_scanning:
                    # Force an immediate scan update
                    if hasattr(self.world_scanner, '_update_scan_results'):
                        self.world_scanner._update_scan_results()
                        logger.info("Forced scan update after enabling debug mode")
        except Exception as e:
            logger.error(f"Error toggling debug mode: {e}", exc_info=True)

    def _select_templates_folder(self) -> None:
        """Open a folder dialog to select and load templates from a custom folder."""
        try:
            # Open folder selection dialog
            folder_path = QFileDialog.getExistingDirectory(
                self, "Select Templates Folder", "D:/OneDrive/AI/Projekte/Scout/tb",
                QFileDialog.Option.ShowDirsOnly
            )
            
            if not folder_path:
                # User cancelled the dialog
                return
            
            # Convert to Path object
            folder_path = Path(folder_path)
            
            # Check if the folder exists
            if not folder_path.exists() or not folder_path.is_dir():
                QMessageBox.warning(
                    self, "Invalid Folder",
                    f"The selected path {folder_path} is not a valid directory."
                )
                return
            
            # Check if there are PNG files in the folder
            png_files = list(folder_path.glob("*.png"))
            if not png_files:
                result = QMessageBox.question(
                    self, "No Templates Found",
                    f"No PNG files found in {folder_path}. Do you want to continue anyway?",
                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
                )
                if result == QMessageBox.StandardButton.No:
                    return
            
            # Update template matcher's templates directory
            if not hasattr(self.template_matcher, 'templates_dir'):
                QMessageBox.warning(
                    self, "Error",
                    "Template matcher doesn't have a templates_dir attribute."
                )
                return
            
            # Store original directory for logging
            original_dir = self.template_matcher.templates_dir
            
            # Update template matcher's directory and reload templates
            self.template_matcher.templates_dir = folder_path
            
            # Try to reload templates from the new directory
            original_count = len(self.template_matcher.templates) if hasattr(self.template_matcher, 'templates') else 0
            self.template_matcher.reload_templates()
            new_count = len(self.template_matcher.templates) if hasattr(self.template_matcher, 'templates') else 0
            
            # Report results
            if new_count > 0:
                QMessageBox.information(
                    self, "Templates Loaded",
                    f"Successfully loaded {new_count} templates from {folder_path}."
                )
                logger.info(f"Changed templates directory from {original_dir} to {folder_path} and loaded {new_count} templates")
                
                # Update the results label with template information
                template_names = list(self.template_matcher.templates.keys())
                template_names.sort()
                result_text = f"Templates Loaded from {folder_path}:\n"
                for name in template_names:
                    template = self.template_matcher.templates[name]
                    h, w = template.shape[:2]
                    result_text += f"• {name} ({w}x{h})\n"
                self.results_label.setText(result_text)
                
                # If scanning is active, force a redraw
                if hasattr(self.world_scanner, 'is_scanning') and self.world_scanner.is_scanning:
                    # Force a fresh scan
                    logger.info("Forcing scan update after template reload")
                    if hasattr(self.world_scanner, '_update_scan_results'):
                        self.world_scanner._update_scan_results()
            else:
                # If no templates were loaded, go back to the original directory
                self.template_matcher.templates_dir = original_dir
                self.template_matcher.reload_templates()
                
                QMessageBox.warning(
                    self, "No Templates Loaded",
                    f"Failed to load any templates from {folder_path}. Reverted to original templates."
                )
                logger.warning(f"Failed to load templates from {folder_path}, reverted to {original_dir}")
            
        except Exception as e:
            error_msg = f"Error selecting templates folder: {str(e)}"
            logger.error(error_msg, exc_info=True)
            QMessageBox.critical(
                self, "Error",
                error_msg
            )
