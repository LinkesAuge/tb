"""
Settings Tab for TB Scout

This module provides the settings tab interface for the TB Scout application.
It allows users to configure various application settings.
"""

from typing import Optional, Dict, Any, Callable
import os
import logging

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, 
    QCheckBox, QGroupBox, QLabel, QComboBox, QSlider,
    QSpinBox, QDoubleSpinBox, QLineEdit, QScrollArea,
    QFileDialog
)
from PyQt6.QtCore import Qt, pyqtSignal

from scout.config_manager import ConfigManager
from scout.overlay import Overlay
from scout.template_matcher import TemplateMatcher
from scout.text_ocr import TextOCR
from scout.sound_manager import SoundManager
from scout.utils.logging_utils import get_logger

logger = get_logger(__name__)

class SettingsTab(QWidget):
    """
    Tab for application settings.
    
    This tab provides controls for configuring:
    - General application settings
    - Overlay appearance and behavior
    - Template matching parameters
    - OCR settings
    - Sound settings
    """
    
    # Signals
    settings_saved = pyqtSignal()
    settings_reset = pyqtSignal()
    
    def __init__(
        self,
        config_manager: ConfigManager,
        overlay: Optional[Overlay] = None,
        template_matcher: Optional[TemplateMatcher] = None,
        text_ocr: Optional[TextOCR] = None,
        sound_manager: Optional[SoundManager] = None,
        parent: Optional[QWidget] = None
    ):
        """Initialize the settings tab."""
        super().__init__(parent)
        
        # Store component references
        self.config_manager = config_manager
        self.overlay = overlay
        self.template_matcher = template_matcher
        self.text_ocr = text_ocr
        self.sound_manager = sound_manager
        
        # Setup UI
        self._setup_ui()
        
        # Load current settings
        self._load_settings()
    
    def _setup_ui(self) -> None:
        """Set up the user interface."""
        layout = QVBoxLayout(self)
        
        # Create scroll area for settings
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_content = QWidget()
        scroll_layout = QVBoxLayout(scroll_content)
        scroll_area.setWidget(scroll_content)
        
        # Add settings groups
        self._add_general_settings(scroll_layout)
        self._add_overlay_settings(scroll_layout)
        self._add_template_settings(scroll_layout)
        self._add_ocr_settings(scroll_layout)
        self._add_sound_settings(scroll_layout)
        
        # Add save/reset buttons
        buttons_layout = QHBoxLayout()
        
        # Add save button
        self.save_settings_button = QPushButton("Save Settings")
        self.save_settings_button.clicked.connect(self._save_settings)
        buttons_layout.addWidget(self.save_settings_button)
        
        # Add reset button
        self.reset_settings_button = QPushButton("Reset to Defaults")
        self.reset_settings_button.clicked.connect(self._reset_settings)
        buttons_layout.addWidget(self.reset_settings_button)
        
        # Add scroll area and buttons to layout
        layout.addWidget(scroll_area)
        layout.addLayout(buttons_layout)
    
    def _add_general_settings(self, parent_layout: QVBoxLayout) -> None:
        """Add general settings to the settings tab."""
        # Create group
        group = QGroupBox("General Settings")
        layout = QVBoxLayout(group)
        
        # Add startup options
        startup_layout = QHBoxLayout()
        startup_label = QLabel("On Startup:")
        self.startup_combo = QComboBox()
        self.startup_combo.addItems(["Show Main Window", "Minimize to Tray", "Start Scanning"])
        startup_layout.addWidget(startup_label)
        startup_layout.addWidget(self.startup_combo)
        layout.addLayout(startup_layout)
        
        # Add minimize to tray option
        self.minimize_to_tray_check = QCheckBox("Minimize to Tray Instead of Taskbar")
        layout.addWidget(self.minimize_to_tray_check)
        
        # Add auto-update check
        self.auto_update_check = QCheckBox("Check for Updates on Startup")
        layout.addWidget(self.auto_update_check)
        
        # Add to parent layout
        parent_layout.addWidget(group)
    
    def _add_overlay_settings(self, parent_layout: QVBoxLayout) -> None:
        """Add overlay settings to the settings tab."""
        # Create group
        group = QGroupBox("Overlay Settings")
        layout = QVBoxLayout(group)
        
        # Add opacity slider
        opacity_layout = QHBoxLayout()
        opacity_label = QLabel("Opacity:")
        self.opacity_slider = QSlider(Qt.Orientation.Horizontal)
        self.opacity_slider.setMinimum(10)
        self.opacity_slider.setMaximum(100)
        self.opacity_slider.setValue(50)
        self.opacity_value_label = QLabel("50%")
        self.opacity_slider.valueChanged.connect(self._on_opacity_changed)
        opacity_layout.addWidget(opacity_label)
        opacity_layout.addWidget(self.opacity_slider)
        opacity_layout.addWidget(self.opacity_value_label)
        layout.addLayout(opacity_layout)
        
        # Add color selection
        color_layout = QHBoxLayout()
        color_label = QLabel("Highlight Color:")
        self.color_combo = QComboBox()
        self.color_combo.addItems(["Red", "Green", "Blue", "Yellow", "Cyan", "Magenta"])
        color_layout.addWidget(color_label)
        color_layout.addWidget(self.color_combo)
        layout.addLayout(color_layout)
        
        # Add display options group
        display_group = QGroupBox("Display Options")
        display_layout = QVBoxLayout(display_group)
        
        # Add show labels option
        self.show_labels_check = QCheckBox("Show Labels")
        display_layout.addWidget(self.show_labels_check)
        
        # Add show confidence option
        self.show_confidence_check = QCheckBox("Show Confidence Values")
        display_layout.addWidget(self.show_confidence_check)
        
        # Add show coordinates option
        self.show_coordinates_check = QCheckBox("Show Coordinates")
        display_layout.addWidget(self.show_coordinates_check)
        
        layout.addWidget(display_group)
        
        # Add to parent layout
        parent_layout.addWidget(group)
    
    def _add_template_settings(self, parent_layout: QVBoxLayout) -> None:
        """Add template matching settings to the settings tab."""
        # Create group
        group = QGroupBox("Template Matching Settings")
        layout = QVBoxLayout(group)
        
        # Add method selection
        method_layout = QHBoxLayout()
        method_label = QLabel("Matching Method:")
        self.method_combo = QComboBox()
        self.method_combo.addItems(["TM_CCOEFF_NORMED", "TM_CCORR_NORMED", "TM_SQDIFF_NORMED"])
        method_layout.addWidget(method_label)
        method_layout.addWidget(self.method_combo)
        layout.addLayout(method_layout)
        
        # Add confidence threshold
        confidence_layout = QHBoxLayout()
        confidence_label = QLabel("Confidence Threshold:")
        self.confidence_spin = QDoubleSpinBox()
        self.confidence_spin.setMinimum(0.1)
        self.confidence_spin.setMaximum(1.0)
        self.confidence_spin.setSingleStep(0.05)
        self.confidence_spin.setValue(0.7)
        confidence_layout.addWidget(confidence_label)
        confidence_layout.addWidget(self.confidence_spin)
        layout.addLayout(confidence_layout)
        
        # Add template directory setting
        template_dir_layout = QHBoxLayout()
        template_dir_label = QLabel("Template Directory:")
        self.template_dir_edit = QLineEdit()
        self.template_dir_edit.setReadOnly(True)
        self.template_dir_browse_button = QPushButton("Browse...")
        self.template_dir_browse_button.clicked.connect(self._browse_template_dir)
        template_dir_layout.addWidget(template_dir_label)
        template_dir_layout.addWidget(self.template_dir_edit)
        template_dir_layout.addWidget(self.template_dir_browse_button)
        layout.addLayout(template_dir_layout)
        
        # Add to parent layout
        parent_layout.addWidget(group)
    
    def _add_ocr_settings(self, parent_layout: QVBoxLayout) -> None:
        """Add OCR settings to the settings tab."""
        # Create group
        group = QGroupBox("OCR Settings")
        layout = QVBoxLayout(group)
        
        # Add language selection
        language_layout = QHBoxLayout()
        language_label = QLabel("Language:")
        self.language_combo = QComboBox()
        self.language_combo.addItems(["English", "German", "French", "Spanish", "Russian"])
        language_layout.addWidget(language_label)
        language_layout.addWidget(self.language_combo)
        layout.addLayout(language_layout)
        
        # Add OCR frequency
        freq_layout = QHBoxLayout()
        freq_label = QLabel("Update Frequency:")
        self.ocr_freq_slider = QSlider(Qt.Orientation.Horizontal)
        self.ocr_freq_slider.setMinimum(1)
        self.ocr_freq_slider.setMaximum(20)
        self.ocr_freq_slider.setValue(5)
        self.ocr_freq_input = QDoubleSpinBox()
        self.ocr_freq_input.setMinimum(0.1)
        self.ocr_freq_input.setMaximum(2.0)
        self.ocr_freq_input.setSingleStep(0.1)
        self.ocr_freq_input.setValue(0.5)
        self.ocr_freq_slider.valueChanged.connect(self._on_ocr_slider_change)
        self.ocr_freq_input.valueChanged.connect(self._on_ocr_spinbox_change)
        freq_layout.addWidget(freq_label)
        freq_layout.addWidget(self.ocr_freq_slider)
        freq_layout.addWidget(self.ocr_freq_input)
        layout.addLayout(freq_layout)
        
        # Add preprocessing options
        preprocessing_group = QGroupBox("Preprocessing")
        preprocessing_layout = QVBoxLayout(preprocessing_group)
        
        # Add threshold option
        threshold_layout = QHBoxLayout()
        threshold_label = QLabel("Threshold:")
        self.threshold_slider = QSlider(Qt.Orientation.Horizontal)
        self.threshold_slider.setMinimum(0)
        self.threshold_slider.setMaximum(255)
        self.threshold_slider.setValue(127)
        self.threshold_value_label = QLabel("127")
        self.threshold_slider.valueChanged.connect(self._on_threshold_changed)
        threshold_layout.addWidget(threshold_label)
        threshold_layout.addWidget(self.threshold_slider)
        threshold_layout.addWidget(self.threshold_value_label)
        preprocessing_layout.addLayout(threshold_layout)
        
        # Add blur option
        blur_layout = QHBoxLayout()
        blur_label = QLabel("Blur:")
        self.blur_slider = QSlider(Qt.Orientation.Horizontal)
        self.blur_slider.setMinimum(0)
        self.blur_slider.setMaximum(10)
        self.blur_slider.setValue(0)
        self.blur_value_label = QLabel("0")
        self.blur_slider.valueChanged.connect(self._on_blur_changed)
        blur_layout.addWidget(blur_label)
        blur_layout.addWidget(self.blur_slider)
        blur_layout.addWidget(self.blur_value_label)
        preprocessing_layout.addLayout(blur_layout)
        
        layout.addWidget(preprocessing_group)
        
        # Add to parent layout
        parent_layout.addWidget(group)
    
    def _add_sound_settings(self, parent_layout: QVBoxLayout) -> None:
        """Add sound settings to the settings tab."""
        # Create group
        group = QGroupBox("Sound Settings")
        layout = QVBoxLayout(group)
        
        # Add enable sounds option
        self.sound_toggle = QCheckBox("Enable Sounds")
        self.sound_toggle.setChecked(True)
        layout.addWidget(self.sound_toggle)
        
        # Add volume slider
        volume_layout = QHBoxLayout()
        volume_label = QLabel("Volume:")
        self.volume_slider = QSlider(Qt.Orientation.Horizontal)
        self.volume_slider.setMinimum(0)
        self.volume_slider.setMaximum(100)
        self.volume_slider.setValue(50)
        self.volume_value_label = QLabel("50%")
        self.volume_slider.valueChanged.connect(self._on_volume_changed)
        volume_layout.addWidget(volume_label)
        volume_layout.addWidget(self.volume_slider)
        volume_layout.addWidget(self.volume_value_label)
        layout.addLayout(volume_layout)
        
        # Add to parent layout
        parent_layout.addWidget(group)
    
    def _load_settings(self) -> None:
        """Load settings from config manager."""
        if not self.config_manager:
            logger.warning("No config manager available to load settings")
            return
        
        # Load general settings
        startup_option = self.config_manager.get("startup_option", "Show Main Window")
        self.startup_combo.setCurrentText(startup_option)
        
        minimize_to_tray = self.config_manager.get("minimize_to_tray", False)
        self.minimize_to_tray_check.setChecked(minimize_to_tray)
        
        auto_update = self.config_manager.get("auto_update", True)
        self.auto_update_check.setChecked(auto_update)
        
        # Load overlay settings
        if self.overlay:
            opacity = int(self.overlay.opacity * 100)
            self.opacity_slider.setValue(opacity)
            self.opacity_value_label.setText(f"{opacity}%")
            
            highlight_color = self.overlay.highlight_color_name
            self.color_combo.setCurrentText(highlight_color)
            
            show_labels = self.config_manager.get("overlay_show_labels", True)
            self.show_labels_check.setChecked(show_labels)
            
            show_confidence = self.config_manager.get("overlay_show_confidence", False)
            self.show_confidence_check.setChecked(show_confidence)
            
            show_coordinates = self.config_manager.get("overlay_show_coordinates", False)
            self.show_coordinates_check.setChecked(show_coordinates)
        
        # Load template matching settings
        if self.template_matcher:
            method = self.template_matcher.method_name
            self.method_combo.setCurrentText(method)
            
            confidence = self.template_matcher.confidence_threshold
            self.confidence_spin.setValue(confidence)
            
            template_dir = self.config_manager.get("template_directory", "")
            self.template_dir_edit.setText(template_dir)
        
        # Load OCR settings
        if self.text_ocr:
            language = self.text_ocr.language
            self.language_combo.setCurrentText(language)
            
            frequency = self.text_ocr.frequency
            self.ocr_freq_input.setValue(frequency)
            self.ocr_freq_slider.setValue(int(frequency * 10))
            
            threshold = self.config_manager.get("ocr_threshold", 127)
            self.threshold_slider.setValue(threshold)
            self.threshold_value_label.setText(str(threshold))
            
            blur = self.config_manager.get("ocr_blur", 0)
            self.blur_slider.setValue(blur)
            self.blur_value_label.setText(str(blur))
        
        # Load sound settings
        if self.sound_manager:
            enabled = self.sound_manager.enabled
            self.sound_toggle.setChecked(enabled)
            
            volume = int(self.sound_manager.volume * 100)
            self.volume_slider.setValue(volume)
            self.volume_value_label.setText(f"{volume}%")
    
    def _save_settings(self) -> None:
        """Save settings to config manager."""
        if not self.config_manager:
            logger.warning("No config manager available to save settings")
            return
        
        try:
            # Save general settings
            self.config_manager.set("startup_option", self.startup_combo.currentText())
            self.config_manager.set("minimize_to_tray", self.minimize_to_tray_check.isChecked())
            self.config_manager.set("auto_update", self.auto_update_check.isChecked())
            
            # Save overlay settings
            opacity = self.opacity_slider.value() / 100.0
            self.config_manager.set("overlay_opacity", opacity)
            if self.overlay:
                self.overlay.set_opacity(opacity)
            
            highlight_color = self.color_combo.currentText()
            self.config_manager.set("overlay_highlight_color", highlight_color)
            if self.overlay:
                self.overlay.set_highlight_color(highlight_color)
            
            self.config_manager.set("overlay_show_labels", self.show_labels_check.isChecked())
            self.config_manager.set("overlay_show_confidence", self.show_confidence_check.isChecked())
            self.config_manager.set("overlay_show_coordinates", self.show_coordinates_check.isChecked())
            
            # Save template matching settings
            method = self.method_combo.currentText()
            self.config_manager.set("template_matching_method", method)
            if self.template_matcher:
                self.template_matcher.set_method(method)
            
            confidence = self.confidence_spin.value()
            self.config_manager.set("confidence_threshold", confidence)
            if self.template_matcher:
                self.template_matcher.set_confidence_threshold(confidence)
            
            template_dir = self.template_dir_edit.text()
            self.config_manager.set("template_directory", template_dir)
            
            # Save OCR settings
            language = self.language_combo.currentText()
            self.config_manager.set("ocr_language", language)
            if self.text_ocr:
                self.text_ocr.set_language(language)
            
            frequency = self.ocr_freq_input.value()
            self.config_manager.set("ocr_frequency", frequency)
            if self.text_ocr:
                self.text_ocr.set_frequency(frequency)
            
            threshold = self.threshold_slider.value()
            self.config_manager.set("ocr_threshold", threshold)
            
            blur = self.blur_slider.value()
            self.config_manager.set("ocr_blur", blur)
            
            # Save sound settings
            enabled = self.sound_toggle.isChecked()
            self.config_manager.set("sound_enabled", enabled)
            if self.sound_manager:
                self.sound_manager.set_enabled(enabled)
            
            volume = self.volume_slider.value() / 100.0
            self.config_manager.set("sound_volume", volume)
            if self.sound_manager:
                self.sound_manager.set_volume(volume)
            
            # Save all settings
            self.config_manager.save()
            
            # Emit signal
            self.settings_saved.emit()
            
            logger.info("Settings saved successfully")
        
        except Exception as e:
            logger.error(f"Error saving settings: {e}", exc_info=True)
    
    def _reset_settings(self) -> None:
        """Reset settings to defaults."""
        if not self.config_manager:
            logger.warning("No config manager available to reset settings")
            return
        
        try:
            # Reset to defaults
            self.config_manager.reset_to_defaults()
            
            # Reload settings
            self._load_settings()
            
            # Apply settings to components
            if self.overlay:
                self.overlay.set_opacity(self.config_manager.get("overlay_opacity", 0.5))
                self.overlay.set_highlight_color(self.config_manager.get("overlay_highlight_color", "Red"))
            
            if self.template_matcher:
                self.template_matcher.set_method(self.config_manager.get("template_matching_method", "TM_CCOEFF_NORMED"))
                self.template_matcher.set_confidence_threshold(self.config_manager.get("confidence_threshold", 0.7))
            
            if self.text_ocr:
                self.text_ocr.set_language(self.config_manager.get("ocr_language", "English"))
                self.text_ocr.set_frequency(self.config_manager.get("ocr_frequency", 0.5))
            
            if self.sound_manager:
                self.sound_manager.set_enabled(self.config_manager.get("sound_enabled", True))
                self.sound_manager.set_volume(self.config_manager.get("sound_volume", 0.5))
            
            # Emit signal
            self.settings_reset.emit()
            
            logger.info("Settings reset to defaults")
        
        except Exception as e:
            logger.error(f"Error resetting settings: {e}", exc_info=True)
    
    def _browse_template_dir(self) -> None:
        """Open file dialog to browse for template directory."""
        current_dir = self.template_dir_edit.text() or os.path.expanduser("~")
        
        directory = QFileDialog.getExistingDirectory(
            self,
            "Select Template Directory",
            current_dir,
            QFileDialog.Option.ShowDirsOnly
        )
        
        if directory:
            self.template_dir_edit.setText(directory)
    
    def _on_opacity_changed(self, value: int) -> None:
        """
        Handle opacity slider change.
        
        Args:
            value: Opacity value (10-100)
        """
        self.opacity_value_label.setText(f"{value}%")
        
        # Update overlay if available
        if self.overlay:
            opacity = value / 100.0
            self.overlay.set_opacity(opacity)
    
    def _on_threshold_changed(self, value: int) -> None:
        """
        Handle threshold slider change.
        
        Args:
            value: Threshold value (0-255)
        """
        self.threshold_value_label.setText(str(value))
    
    def _on_blur_changed(self, value: int) -> None:
        """
        Handle blur slider change.
        
        Args:
            value: Blur value (0-10)
        """
        self.blur_value_label.setText(str(value))
    
    def _on_volume_changed(self, value: int) -> None:
        """
        Handle volume slider change.
        
        Args:
            value: Volume value (0-100)
        """
        self.volume_value_label.setText(f"{value}%")
        
        # Update sound manager if available
        if self.sound_manager:
            volume = value / 100.0
            self.sound_manager.set_volume(volume)
    
    def _on_ocr_slider_change(self, value: int) -> None:
        """
        Handle OCR frequency slider change.
        
        Args:
            value: Slider value (1-20)
        """
        # Convert to frequency (0.1-2.0)
        freq = value / 10.0
        
        # Update spinbox without triggering its valueChanged signal
        self.ocr_freq_input.blockSignals(True)
        self.ocr_freq_input.setValue(freq)
        self.ocr_freq_input.blockSignals(False)
        
        # Update OCR frequency if available
        if self.text_ocr:
            self.text_ocr.set_frequency(freq)
    
    def _on_ocr_spinbox_change(self, value: float) -> None:
        """
        Handle OCR frequency spinbox change.
        
        Args:
            value: The frequency value in updates per second (0.1-2.0)
        """
        # Update slider without triggering its valueChanged signal
        slider_value = int(value * 10)
        self.ocr_freq_slider.blockSignals(True)
        self.ocr_freq_slider.setValue(slider_value)
        self.ocr_freq_slider.blockSignals(False)
        
        # Update OCR frequency if available
        if self.text_ocr:
            self.text_ocr.set_frequency(value)