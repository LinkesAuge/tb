"""
Action Parameter Widgets

This module provides specialized widgets for configuring different types of action parameters.
Each action type has its own parameter widget that shows relevant configuration options.
"""

from typing import Dict, Any, Optional, List
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QLineEdit, QSpinBox, QDoubleSpinBox, QCheckBox,
    QComboBox, QListWidget, QListWidgetItem, QTextEdit,
    QGroupBox, QRadioButton, QPushButton, QTabWidget,
    QFileDialog, QScrollArea
)
from PyQt6.QtCore import Qt, pyqtSignal
import logging
from pathlib import Path
from scout.automation.actions import (
    ActionType, ActionParamsCommon, ClickParams, DragParams,
    TypeParams, WaitParams, TemplateSearchParams, OCRWaitParams,
    ConditionalParams, LoopParams, SwitchCaseParams, TryCatchParams,
    ParallelExecutionParams, BreakpointParams
)
from scout.automation.action_handlers_data import (
    VariableSetParams, VariableIncrementParams, StringOperationParams,
    ListOperationParams, DictOperationParams, MathOperationParams,
    FileOperationParams
)
from scout.config_manager import ConfigManager

logger = logging.getLogger(__name__)

class BaseParamsWidget(QWidget):
    """Base class for all parameter widgets."""
    
    params_changed = pyqtSignal()
    
    def __init__(self):
        """Initialize the base parameters widget."""
        super().__init__()
        self._creating_widgets = False
        
    def get_params(self) -> ActionParamsCommon:
        """
        Get the current parameters.
        
        Returns:
            Current parameters
        """
        raise NotImplementedError("Subclasses must implement get_params")
        
    def set_params(self, params: ActionParamsCommon) -> None:
        """
        Set the parameters.
        
        Args:
            params: Parameters to set
        """
        raise NotImplementedError("Subclasses must implement set_params")

class CommonParamsWidget(QWidget):
    """Widget for common action parameters."""
    
    params_changed = pyqtSignal()
    
    def __init__(self):
        """Initialize the common parameters widget."""
        super().__init__()
        layout = QVBoxLayout()
        self.setLayout(layout)
        
        # Name field
        name_layout = QHBoxLayout()
        name_layout.addWidget(QLabel("Name:"))
        self.name_edit = QLineEdit()
        self.name_edit.textChanged.connect(self.params_changed.emit)
        name_layout.addWidget(self.name_edit)
        layout.addLayout(name_layout)
        
        # Description field
        desc_layout = QHBoxLayout()
        desc_layout.addWidget(QLabel("Description:"))
        self.description_edit = QLineEdit()
        self.description_edit.textChanged.connect(self.params_changed.emit)
        desc_layout.addWidget(self.description_edit)
        layout.addLayout(desc_layout)
        
        # Enabled checkbox
        enabled_layout = QHBoxLayout()
        enabled_layout.addWidget(QLabel("Enabled:"))
        self.enabled_check = QCheckBox()
        self.enabled_check.setChecked(True)
        self.enabled_check.stateChanged.connect(self.params_changed.emit)
        enabled_layout.addWidget(self.enabled_check)
        layout.addLayout(enabled_layout)
        
        # Timeout field
        timeout_layout = QHBoxLayout()
        timeout_layout.addWidget(QLabel("Timeout (s):"))
        self.timeout_spin = QDoubleSpinBox()
        self.timeout_spin.setRange(0.01, 999)
        self.timeout_spin.setValue(30.0)
        self.timeout_spin.valueChanged.connect(self.params_changed.emit)
        timeout_layout.addWidget(self.timeout_spin)
        layout.addLayout(timeout_layout)
        
        # Retry count
        retry_layout = QHBoxLayout()
        retry_layout.addWidget(QLabel("Retry Count:"))
        self.retry_spin = QSpinBox()
        self.retry_spin.setRange(0, 10)
        self.retry_spin.setValue(0)
        self.retry_spin.valueChanged.connect(self.params_changed.emit)
        retry_layout.addWidget(self.retry_spin)
        layout.addLayout(retry_layout)
        
        # Retry interval
        interval_layout = QHBoxLayout()
        interval_layout.addWidget(QLabel("Retry Interval (s):"))
        self.interval_spin = QDoubleSpinBox()
        self.interval_spin.setRange(0.1, 60)
        self.interval_spin.setValue(1.0)
        self.interval_spin.valueChanged.connect(self.params_changed.emit)
        interval_layout.addWidget(self.interval_spin)
        layout.addLayout(interval_layout)
        
        # On failure
        failure_layout = QHBoxLayout()
        failure_layout.addWidget(QLabel("On Failure:"))
        self.failure_combo = QComboBox()
        self.failure_combo.addItems(["stop", "continue", "retry"])
        self.failure_combo.currentTextChanged.connect(self.params_changed.emit)
        failure_layout.addWidget(self.failure_combo)
        layout.addLayout(failure_layout)
        
        # Failure message
        message_layout = QHBoxLayout()
        message_layout.addWidget(QLabel("Failure Message:"))
        self.message_edit = QLineEdit()
        self.message_edit.textChanged.connect(self.params_changed.emit)
        message_layout.addWidget(self.message_edit)
        layout.addLayout(message_layout)
    
    def get_common_params(self) -> Dict[str, Any]:
        """
        Get the common parameters.
        
        Returns:
            Dictionary of common parameters
        """
        return {
            "name": self.name_edit.text(),
            "description": self.description_edit.text(),
            "enabled": self.enabled_check.isChecked(),
            "timeout": self.timeout_spin.value(),
            "retry_count": self.retry_spin.value(),
            "retry_interval": self.interval_spin.value(),
            "on_failure": self.failure_combo.currentText(),
            "failure_message": self.message_edit.text()
        }
    
    def set_common_params(self, params: ActionParamsCommon) -> None:
        """
        Set the common parameters.
        
        Args:
            params: Parameters to set
        """
        self.name_edit.setText(params.name)
        self.description_edit.setText(params.description)
        self.enabled_check.setChecked(params.enabled)
        self.timeout_spin.setValue(params.timeout)
        self.retry_spin.setValue(params.retry_count)
        self.interval_spin.setValue(params.retry_interval)
        
        # Find and select the on_failure option
        index = self.failure_combo.findText(params.on_failure)
        if index >= 0:
            self.failure_combo.setCurrentIndex(index)
            
        self.message_edit.setText(params.failure_message)

class ClickParamsWidget(BaseParamsWidget):
    """Widget for configuring click action parameters."""
    
    def __init__(self):
        """Initialize the click parameters widget."""
        super().__init__()
        layout = QVBoxLayout()
        self.setLayout(layout)
        
        # Common parameters
        self.common_widget = CommonParamsWidget()
        self.common_widget.params_changed.connect(self.params_changed.emit)
        layout.addWidget(self.common_widget)
        
        # Click coordinates
        coords_layout = QHBoxLayout()
        coords_layout.addWidget(QLabel("Coordinates:"))
        
        x_layout = QHBoxLayout()
        x_layout.addWidget(QLabel("X:"))
        self.x_spin = QSpinBox()
        self.x_spin.setRange(-9999, 9999)
        self.x_spin.setValue(0)
        self.x_spin.valueChanged.connect(self.params_changed.emit)
        x_layout.addWidget(self.x_spin)
        
        y_layout = QHBoxLayout()
        y_layout.addWidget(QLabel("Y:"))
        self.y_spin = QSpinBox()
        self.y_spin.setRange(-9999, 9999)
        self.y_spin.setValue(0)
        self.y_spin.valueChanged.connect(self.params_changed.emit)
        y_layout.addWidget(self.y_spin)
        
        coords_layout.addLayout(x_layout)
        coords_layout.addLayout(y_layout)
        layout.addLayout(coords_layout)
        
        # Relative to
        relative_layout = QHBoxLayout()
        relative_layout.addWidget(QLabel("Relative To:"))
        self.relative_combo = QComboBox()
        self.relative_combo.addItems(["window", "screen", "last_match"])
        self.relative_combo.currentTextChanged.connect(self.params_changed.emit)
        relative_layout.addWidget(self.relative_combo)
        layout.addLayout(relative_layout)
        
        # Duration
        duration_layout = QHBoxLayout()
        duration_layout.addWidget(QLabel("Duration (s):"))
        self.duration_spin = QDoubleSpinBox()
        self.duration_spin.setRange(0.01, 10.0)
        self.duration_spin.setValue(0.5)
        self.duration_spin.valueChanged.connect(self.params_changed.emit)
        duration_layout.addWidget(self.duration_spin)
        layout.addLayout(duration_layout)
        
    def get_params(self) -> ClickParams:
        """Get the current click parameters."""
        common_params = self.common_widget.get_common_params()
        return ClickParams(
            **common_params,
            x=self.x_spin.value(),
            y=self.y_spin.value(),
            relative_to=self.relative_combo.currentText(),
            duration=self.duration_spin.value()
        )
        
    def set_params(self, params: ClickParams) -> None:
        """Set the click parameters."""
        self._creating_widgets = True
        self.common_widget.set_common_params(params)
        self.x_spin.setValue(params.x)
        self.y_spin.setValue(params.y)
        
        # Find and select the relative_to option
        index = self.relative_combo.findText(params.relative_to)
        if index >= 0:
            self.relative_combo.setCurrentIndex(index)
            
        self.duration_spin.setValue(params.duration)
        self._creating_widgets = False

class DragParamsWidget(BaseParamsWidget):
    """Widget for configuring drag action parameters."""
    
    def __init__(self):
        """Initialize the drag parameters widget."""
        super().__init__()
        layout = QVBoxLayout()
        self.setLayout(layout)
        
        # Common parameters
        self.common_widget = CommonParamsWidget()
        self.common_widget.params_changed.connect(self.params_changed.emit)
        layout.addWidget(self.common_widget)
        
        # Start coordinates
        start_layout = QHBoxLayout()
        start_layout.addWidget(QLabel("Start Coordinates:"))
        
        start_x_layout = QHBoxLayout()
        start_x_layout.addWidget(QLabel("X:"))
        self.start_x_spin = QSpinBox()
        self.start_x_spin.setRange(-9999, 9999)
        self.start_x_spin.setValue(0)
        self.start_x_spin.valueChanged.connect(self.params_changed.emit)
        start_x_layout.addWidget(self.start_x_spin)
        
        start_y_layout = QHBoxLayout()
        start_y_layout.addWidget(QLabel("Y:"))
        self.start_y_spin = QSpinBox()
        self.start_y_spin.setRange(-9999, 9999)
        self.start_y_spin.setValue(0)
        self.start_y_spin.valueChanged.connect(self.params_changed.emit)
        start_y_layout.addWidget(self.start_y_spin)
        
        start_layout.addLayout(start_x_layout)
        start_layout.addLayout(start_y_layout)
        layout.addLayout(start_layout)
        
        # End coordinates
        end_layout = QHBoxLayout()
        end_layout.addWidget(QLabel("End Coordinates:"))
        
        end_x_layout = QHBoxLayout()
        end_x_layout.addWidget(QLabel("X:"))
        self.end_x_spin = QSpinBox()
        self.end_x_spin.setRange(-9999, 9999)
        self.end_x_spin.setValue(0)
        self.end_x_spin.valueChanged.connect(self.params_changed.emit)
        end_x_layout.addWidget(self.end_x_spin)
        
        end_y_layout = QHBoxLayout()
        end_y_layout.addWidget(QLabel("Y:"))
        self.end_y_spin = QSpinBox()
        self.end_y_spin.setRange(-9999, 9999)
        self.end_y_spin.setValue(0)
        self.end_y_spin.valueChanged.connect(self.params_changed.emit)
        end_y_layout.addWidget(self.end_y_spin)
        
        end_layout.addLayout(end_x_layout)
        end_layout.addLayout(end_y_layout)
        layout.addLayout(end_layout)
        
        # Relative to
        relative_layout = QHBoxLayout()
        relative_layout.addWidget(QLabel("Relative To:"))
        self.relative_combo = QComboBox()
        self.relative_combo.addItems(["window", "screen", "last_match"])
        self.relative_combo.currentTextChanged.connect(self.params_changed.emit)
        relative_layout.addWidget(self.relative_combo)
        layout.addLayout(relative_layout)
        
        # Duration
        duration_layout = QHBoxLayout()
        duration_layout.addWidget(QLabel("Duration (s):"))
        self.duration_spin = QDoubleSpinBox()
        self.duration_spin.setRange(0.1, 10.0)
        self.duration_spin.setValue(0.5)
        self.duration_spin.valueChanged.connect(self.params_changed.emit)
        duration_layout.addWidget(self.duration_spin)
        layout.addLayout(duration_layout)
        
    def get_params(self) -> DragParams:
        """Get the current drag parameters."""
        common_params = self.common_widget.get_common_params()
        return DragParams(
            **common_params,
            start_x=self.start_x_spin.value(),
            start_y=self.start_y_spin.value(),
            end_x=self.end_x_spin.value(),
            end_y=self.end_y_spin.value(),
            relative_to=self.relative_combo.currentText(),
            duration=self.duration_spin.value()
        )
        
    def set_params(self, params: DragParams) -> None:
        """Set the drag parameters."""
        self._creating_widgets = True
        self.common_widget.set_common_params(params)
        self.start_x_spin.setValue(params.start_x)
        self.start_y_spin.setValue(params.start_y)
        self.end_x_spin.setValue(params.end_x)
        self.end_y_spin.setValue(params.end_y)
        
        # Find and select the relative_to option
        index = self.relative_combo.findText(params.relative_to)
        if index >= 0:
            self.relative_combo.setCurrentIndex(index)
            
        self.duration_spin.setValue(params.duration)
        self._creating_widgets = False

class TypeParamsWidget(BaseParamsWidget):
    """Widget for configuring type action parameters."""
    
    def __init__(self):
        """Initialize the type parameters widget."""
        super().__init__()
        layout = QVBoxLayout()
        self.setLayout(layout)
        
        # Common parameters
        self.common_widget = CommonParamsWidget()
        self.common_widget.params_changed.connect(self.params_changed.emit)
        layout.addWidget(self.common_widget)
        
        # Text field
        text_layout = QHBoxLayout()
        text_layout.addWidget(QLabel("Text:"))
        self.text_edit = QLineEdit()
        self.text_edit.textChanged.connect(self.params_changed.emit)
        text_layout.addWidget(self.text_edit)
        layout.addLayout(text_layout)
        
        # Delay field
        delay_layout = QHBoxLayout()
        delay_layout.addWidget(QLabel("Delay (s):"))
        self.delay_spin = QDoubleSpinBox()
        self.delay_spin.setRange(0.01, 1.0)
        self.delay_spin.setValue(0.05)
        self.delay_spin.setSingleStep(0.01)
        self.delay_spin.valueChanged.connect(self.params_changed.emit)
        delay_layout.addWidget(self.delay_spin)
        layout.addLayout(delay_layout)
        
        # Use clipboard
        clipboard_layout = QHBoxLayout()
        clipboard_layout.addWidget(QLabel("Use Clipboard:"))
        self.clipboard_check = QCheckBox()
        self.clipboard_check.stateChanged.connect(self.params_changed.emit)
        clipboard_layout.addWidget(self.clipboard_check)
        layout.addLayout(clipboard_layout)
        
    def get_params(self) -> TypeParams:
        """Get the current type parameters."""
        common_params = self.common_widget.get_common_params()
        return TypeParams(
            **common_params,
            text=self.text_edit.text(),
            delay=self.delay_spin.value(),
            use_clipboard=self.clipboard_check.isChecked()
        )
        
    def set_params(self, params: TypeParams) -> None:
        """Set the type parameters."""
        self._creating_widgets = True
        self.common_widget.set_common_params(params)
        self.text_edit.setText(params.text)
        self.delay_spin.setValue(params.delay)
        self.clipboard_check.setChecked(params.use_clipboard)
        self._creating_widgets = False

class WaitParamsWidget(BaseParamsWidget):
    """Widget for configuring wait action parameters."""
    
    def __init__(self):
        """Initialize the wait parameters widget."""
        super().__init__()
        layout = QVBoxLayout()
        self.setLayout(layout)
        
        # Common parameters
        self.common_widget = CommonParamsWidget()
        self.common_widget.params_changed.connect(self.params_changed.emit)
        layout.addWidget(self.common_widget)
        
        # Duration field
        duration_layout = QHBoxLayout()
        duration_layout.addWidget(QLabel("Duration (s):"))
        self.duration_spin = QDoubleSpinBox()
        self.duration_spin.setRange(0.1, 3600.0)
        self.duration_spin.setValue(1.0)
        self.duration_spin.valueChanged.connect(self.params_changed.emit)
        duration_layout.addWidget(self.duration_spin)
        layout.addLayout(duration_layout)
        
        # Random variation
        variation_layout = QHBoxLayout()
        variation_layout.addWidget(QLabel("Random Variation (s):"))
        self.variation_spin = QDoubleSpinBox()
        self.variation_spin.setRange(0.0, 10.0)
        self.variation_spin.setValue(0.0)
        self.variation_spin.valueChanged.connect(self.params_changed.emit)
        variation_layout.addWidget(self.variation_spin)
        layout.addLayout(variation_layout)
        
    def get_params(self) -> WaitParams:
        """Get the current wait parameters."""
        common_params = self.common_widget.get_common_params()
        return WaitParams(
            **common_params,
            duration=self.duration_spin.value(),
            random_variation=self.variation_spin.value()
        )
        
    def set_params(self, params: WaitParams) -> None:
        """Set the wait parameters."""
        self._creating_widgets = True
        self.common_widget.set_common_params(params)
        self.duration_spin.setValue(params.duration)
        self.variation_spin.setValue(params.random_variation)
        self._creating_widgets = False

class TemplateSearchParamsWidget(BaseParamsWidget):
    """Widget for configuring template search action parameters."""
    
    def __init__(self):
        """Initialize the template search parameters widget."""
        super().__init__()
        layout = QVBoxLayout()
        self.setLayout(layout)
        
        # Common parameters
        self.common_widget = CommonParamsWidget()
        self.common_widget.params_changed.connect(self.params_changed.emit)
        layout.addWidget(self.common_widget)
        
        # Template path
        template_layout = QHBoxLayout()
        template_layout.addWidget(QLabel("Template:"))
        self.template_edit = QLineEdit()
        self.template_edit.textChanged.connect(self.params_changed.emit)
        template_layout.addWidget(self.template_edit)
        
        self.browse_button = QPushButton("Browse...")
        self.browse_button.clicked.connect(self._browse_template)
        template_layout.addWidget(self.browse_button)
        
        layout.addLayout(template_layout)
        
        # Confidence threshold
        confidence_layout = QHBoxLayout()
        confidence_layout.addWidget(QLabel("Confidence:"))
        self.confidence_spin = QDoubleSpinBox()
        self.confidence_spin.setRange(0.1, 1.0)
        self.confidence_spin.setValue(0.8)
        self.confidence_spin.setSingleStep(0.05)
        self.confidence_spin.valueChanged.connect(self.params_changed.emit)
        confidence_layout.addWidget(self.confidence_spin)
        layout.addLayout(confidence_layout)
        
        # Search region
        region_group = QGroupBox("Search Region")
        region_layout = QVBoxLayout()
        region_group.setLayout(region_layout)
        
        self.region_check = QCheckBox("Specify Search Region")
        self.region_check.stateChanged.connect(self._toggle_region)
        region_layout.addWidget(self.region_check)
        
        region_coords = QHBoxLayout()
        
        x_layout = QHBoxLayout()
        x_layout.addWidget(QLabel("X:"))
        self.region_x_spin = QSpinBox()
        self.region_x_spin.setRange(0, 9999)
        self.region_x_spin.setValue(0)
        self.region_x_spin.valueChanged.connect(self.params_changed.emit)
        self.region_x_spin.setEnabled(False)
        x_layout.addWidget(self.region_x_spin)
        
        y_layout = QHBoxLayout()
        y_layout.addWidget(QLabel("Y:"))
        self.region_y_spin = QSpinBox()
        self.region_y_spin.setRange(0, 9999)
        self.region_y_spin.setValue(0)
        self.region_y_spin.valueChanged.connect(self.params_changed.emit)
        self.region_y_spin.setEnabled(False)
        y_layout.addWidget(self.region_y_spin)
        
        region_coords.addLayout(x_layout)
        region_coords.addLayout(y_layout)
        region_layout.addLayout(region_coords)
        
        region_size = QHBoxLayout()
        
        width_layout = QHBoxLayout()
        width_layout.addWidget(QLabel("Width:"))
        self.region_width_spin = QSpinBox()
        self.region_width_spin.setRange(1, 9999)
        self.region_width_spin.setValue(100)
        self.region_width_spin.valueChanged.connect(self.params_changed.emit)
        self.region_width_spin.setEnabled(False)
        width_layout.addWidget(self.region_width_spin)
        
        height_layout = QHBoxLayout()
        height_layout.addWidget(QLabel("Height:"))
        self.region_height_spin = QSpinBox()
        self.region_height_spin.setRange(1, 9999)
        self.region_height_spin.setValue(100)
        self.region_height_spin.valueChanged.connect(self.params_changed.emit)
        self.region_height_spin.setEnabled(False)
        height_layout.addWidget(self.region_height_spin)
        
        region_size.addLayout(width_layout)
        region_size.addLayout(height_layout)
        region_layout.addLayout(region_size)
        
        layout.addWidget(region_group)
        
        # Max matches
        matches_layout = QHBoxLayout()
        matches_layout.addWidget(QLabel("Max Matches:"))
        self.matches_spin = QSpinBox()
        self.matches_spin.setRange(1, 100)
        self.matches_spin.setValue(1)
        self.matches_spin.valueChanged.connect(self.params_changed.emit)
        matches_layout.addWidget(self.matches_spin)
        layout.addLayout(matches_layout)
        
        # Save to variable
        variable_layout = QHBoxLayout()
        variable_layout.addWidget(QLabel("Save to Variable:"))
        self.variable_edit = QLineEdit()
        self.variable_edit.textChanged.connect(self.params_changed.emit)
        variable_layout.addWidget(self.variable_edit)
        layout.addLayout(variable_layout)
        
    def _browse_template(self) -> None:
        """Open a file dialog to browse for a template image."""
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Select Template Image", "", "Images (*.png *.jpg *.jpeg *.bmp)"
        )
        if file_path:
            self.template_edit.setText(file_path)
            
    def _toggle_region(self, state: int) -> None:
        """Toggle the search region controls."""
        enabled = state == Qt.CheckState.Checked
        self.region_x_spin.setEnabled(enabled)
        self.region_y_spin.setEnabled(enabled)
        self.region_width_spin.setEnabled(enabled)
        self.region_height_spin.setEnabled(enabled)
        self.params_changed.emit()
        
    def get_params(self) -> TemplateSearchParams:
        """Get the current template search parameters."""
        common_params = self.common_widget.get_common_params()
        
        # Get search region if enabled
        search_region = None
        if self.region_check.isChecked():
            search_region = [
                self.region_x_spin.value(),
                self.region_y_spin.value(),
                self.region_width_spin.value(),
                self.region_height_spin.value()
            ]
            
        return TemplateSearchParams(
            **common_params,
            template_path=self.template_edit.text(),
            confidence=self.confidence_spin.value(),
            search_region=search_region,
            max_matches=self.matches_spin.value(),
            save_to_variable=self.variable_edit.text()
        )
        
    def set_params(self, params: TemplateSearchParams) -> None:
        """Set the template search parameters."""
        self._creating_widgets = True
        self.common_widget.set_common_params(params)
        self.template_edit.setText(params.template_path)
        self.confidence_spin.setValue(params.confidence)
        
        # Set search region if provided
        if params.search_region:
            self.region_check.setChecked(True)
            self.region_x_spin.setValue(params.search_region[0])
            self.region_y_spin.setValue(params.search_region[1])
            self.region_width_spin.setValue(params.search_region[2])
            self.region_height_spin.setValue(params.search_region[3])
        else:
            self.region_check.setChecked(False)
            
        self.matches_spin.setValue(params.max_matches)
        self.variable_edit.setText(params.save_to_variable)
        self._creating_widgets = False

class OCRWaitParamsWidget(BaseParamsWidget):
    """Widget for configuring OCR wait action parameters."""
    
    def __init__(self):
        """Initialize the OCR wait parameters widget."""
        super().__init__()
        layout = QVBoxLayout()
        self.setLayout(layout)
        
        # Common parameters
        self.common_widget = CommonParamsWidget()
        self.common_widget.params_changed.connect(self.params_changed.emit)
        layout.addWidget(self.common_widget)
        
        # Text to find
        text_layout = QHBoxLayout()
        text_layout.addWidget(QLabel("Text to Find:"))
        self.text_edit = QLineEdit()
        self.text_edit.textChanged.connect(self.params_changed.emit)
        text_layout.addWidget(self.text_edit)
        layout.addLayout(text_layout)
        
        # Search region
        region_group = QGroupBox("Search Region")
        region_layout = QVBoxLayout()
        region_group.setLayout(region_layout)
        
        self.region_check = QCheckBox("Specify Region")
        self.region_check.stateChanged.connect(self._on_region_check_changed)
        self.region_check.stateChanged.connect(self.params_changed.emit)
        region_layout.addWidget(self.region_check)
        
        region_coords_layout = QHBoxLayout()
        
        # X coordinate
        x_layout = QHBoxLayout()
        x_layout.addWidget(QLabel("X:"))
        self.region_x_spin = QSpinBox()
        self.region_x_spin.setRange(0, 9999)
        self.region_x_spin.setValue(0)
        self.region_x_spin.valueChanged.connect(self.params_changed.emit)
        x_layout.addWidget(self.region_x_spin)
        region_coords_layout.addLayout(x_layout)
        
        # Y coordinate
        y_layout = QHBoxLayout()
        y_layout.addWidget(QLabel("Y:"))
        self.region_y_spin = QSpinBox()
        self.region_y_spin.setRange(0, 9999)
        self.region_y_spin.setValue(0)
        self.region_y_spin.valueChanged.connect(self.params_changed.emit)
        y_layout.addWidget(self.region_y_spin)
        region_coords_layout.addLayout(y_layout)
        
        # Width
        width_layout = QHBoxLayout()
        width_layout.addWidget(QLabel("Width:"))
        self.region_width_spin = QSpinBox()
        self.region_width_spin.setRange(1, 9999)
        self.region_width_spin.setValue(100)
        self.region_width_spin.valueChanged.connect(self.params_changed.emit)
        width_layout.addWidget(self.region_width_spin)
        region_coords_layout.addLayout(width_layout)
        
        # Height
        height_layout = QHBoxLayout()
        height_layout.addWidget(QLabel("Height:"))
        self.region_height_spin = QSpinBox()
        self.region_height_spin.setRange(1, 9999)
        self.region_height_spin.setValue(100)
        self.region_height_spin.valueChanged.connect(self.params_changed.emit)
        height_layout.addWidget(self.region_height_spin)
        region_coords_layout.addLayout(height_layout)
        
        region_layout.addLayout(region_coords_layout)
        layout.addWidget(region_group)
        
        # Timeout
        timeout_layout = QHBoxLayout()
        timeout_layout.addWidget(QLabel("Timeout (ms):"))
        self.timeout_spin = QSpinBox()
        self.timeout_spin.setRange(100, 60000)
        self.timeout_spin.setValue(5000)
        self.timeout_spin.setSingleStep(100)
        self.timeout_spin.valueChanged.connect(self.params_changed.emit)
        timeout_layout.addWidget(self.timeout_spin)
        layout.addLayout(timeout_layout)
        
        # Case sensitivity
        case_layout = QHBoxLayout()
        case_layout.addWidget(QLabel("Case Sensitive:"))
        self.case_check = QCheckBox()
        self.case_check.setChecked(False)
        self.case_check.stateChanged.connect(self.params_changed.emit)
        case_layout.addWidget(self.case_check)
        layout.addLayout(case_layout)
        
        # Store variable
        store_layout = QHBoxLayout()
        store_layout.addWidget(QLabel("Store Result In:"))
        self.store_edit = QLineEdit()
        self.store_edit.textChanged.connect(self.params_changed.emit)
        store_layout.addWidget(self.store_edit)
        layout.addLayout(store_layout)
        
        # OCR Parameters
        ocr_group = QGroupBox("OCR Parameters")
        ocr_layout = QVBoxLayout()
        ocr_group.setLayout(ocr_layout)
        
        # Language
        lang_layout = QHBoxLayout()
        lang_layout.addWidget(QLabel("Language:"))
        self.lang_combo = QComboBox()
        self.lang_combo.addItems(["eng", "deu", "fra", "spa", "ita", "por", "rus", "jpn", "kor", "chi_sim", "chi_tra"])
        self.lang_combo.currentTextChanged.connect(self.params_changed.emit)
        lang_layout.addWidget(self.lang_combo)
        ocr_layout.addLayout(lang_layout)
        
        # PSM mode
        psm_layout = QHBoxLayout()
        psm_layout.addWidget(QLabel("Page Segmentation Mode:"))
        self.psm_combo = QComboBox()
        self.psm_combo.addItems([
            "0 - Orientation and script detection only",
            "1 - Automatic page segmentation with OSD",
            "2 - Automatic page segmentation, but no OSD or OCR",
            "3 - Fully automatic page segmentation, but no OSD",
            "4 - Assume a single column of text of variable sizes",
            "5 - Assume a single uniform block of vertically aligned text",
            "6 - Assume a single uniform block of text",
            "7 - Treat the image as a single text line",
            "8 - Treat the image as a single word",
            "9 - Treat the image as a single word in a circle",
            "10 - Treat the image as a single character",
            "11 - Sparse text. Find as much text as possible in no particular order",
            "12 - Sparse text with OSD",
            "13 - Raw line. Treat the image as a single text line"
        ])
        self.psm_combo.setCurrentIndex(3)  # Default to "3 - Fully automatic page segmentation, but no OSD"
        self.psm_combo.currentIndexChanged.connect(self.params_changed.emit)
        psm_layout.addWidget(self.psm_combo)
        ocr_layout.addLayout(psm_layout)
        
        # Confidence threshold
        conf_layout = QHBoxLayout()
        conf_layout.addWidget(QLabel("Confidence Threshold:"))
        self.conf_spin = QDoubleSpinBox()
        self.conf_spin.setRange(0.0, 1.0)
        self.conf_spin.setValue(0.6)
        self.conf_spin.setSingleStep(0.05)
        self.conf_spin.valueChanged.connect(self.params_changed.emit)
        conf_layout.addWidget(self.conf_spin)
        ocr_layout.addLayout(conf_layout)
        
        layout.addWidget(ocr_group)
        
        # Initialize region widgets state
        self._on_region_check_changed(self.region_check.checkState())
    
    def _on_region_check_changed(self, state):
        """Enable or disable region input fields based on checkbox state."""
        enabled = state == Qt.CheckState.Checked
        self.region_x_spin.setEnabled(enabled)
        self.region_y_spin.setEnabled(enabled)
        self.region_width_spin.setEnabled(enabled)
        self.region_height_spin.setEnabled(enabled)
    
    def get_params(self) -> OCRWaitParams:
        """Get the current OCR wait parameters."""
        common_params = self.common_widget.get_common_params()
        
        # Extract PSM value from the combo box text (format: "3 - Fully automatic...")
        psm_text = self.psm_combo.currentText()
        psm_value = int(psm_text.split(" ")[0])
        
        # Get search region if specified
        search_region = None
        if self.region_check.isChecked():
            search_region = [
                self.region_x_spin.value(),
                self.region_y_spin.value(),
                self.region_width_spin.value(),
                self.region_height_spin.value()
            ]
        
        return OCRWaitParams(
            **common_params,
            text=self.text_edit.text(),
            search_region=search_region,
            timeout_ms=self.timeout_spin.value(),
            case_sensitive=self.case_check.isChecked(),
            store_variable=self.store_edit.text(),
            language=self.lang_combo.currentText(),
            psm=psm_value,
            confidence_threshold=self.conf_spin.value()
        )
    
    def set_params(self, params: OCRWaitParams) -> None:
        """Set the OCR wait parameters."""
        self._creating_widgets = True
        self.common_widget.set_common_params(params)
        self.text_edit.setText(params.text)
        
        # Set search region if provided
        if params.search_region:
            self.region_check.setChecked(True)
            self.region_x_spin.setValue(params.search_region[0])
            self.region_y_spin.setValue(params.search_region[1])
            self.region_width_spin.setValue(params.search_region[2])
            self.region_height_spin.setValue(params.search_region[3])
        else:
            self.region_check.setChecked(False)
        
        self.timeout_spin.setValue(params.timeout_ms)
        self.case_check.setChecked(params.case_sensitive)
        self.store_edit.setText(params.store_variable)
        
        # Set language
        index = self.lang_combo.findText(params.language)
        if index >= 0:
            self.lang_combo.setCurrentIndex(index)
        
        # Set PSM mode
        for i in range(self.psm_combo.count()):
            item_text = self.psm_combo.itemText(i)
            if item_text.startswith(f"{params.psm} -"):
                self.psm_combo.setCurrentIndex(i)
                break
        
        self.conf_spin.setValue(params.confidence_threshold)
        self._creating_widgets = False

class ConditionalParamsWidget(BaseParamsWidget):
    """Widget for configuring conditional action parameters."""
    
    def __init__(self):
        """Initialize the conditional parameters widget."""
        super().__init__()
        layout = QVBoxLayout()
        self.setLayout(layout)
        
        # Description field
        desc_layout = QHBoxLayout()
        desc_layout.addWidget(QLabel("Description:"))
        self.description_edit = QLineEdit()
        self.description_edit.textChanged.connect(self.params_changed.emit)
        desc_layout.addWidget(self.description_edit)
        layout.addLayout(desc_layout)
        
        # Condition type
        condition_type_layout = QHBoxLayout()
        condition_type_layout.addWidget(QLabel("Condition Type:"))
        self.condition_type_combo = QComboBox()
        self.condition_type_combo.addItems(["last_result", "last_match", "last_ocr", "expression"])
        self.condition_type_combo.currentTextChanged.connect(self._on_condition_type_changed)
        condition_type_layout.addWidget(self.condition_type_combo)
        layout.addLayout(condition_type_layout)
        
        # Condition value - stacked based on type
        self.condition_value_layout = QVBoxLayout()
        layout.addLayout(self.condition_value_layout)
        
        # Boolean value (for last_result)
        self.bool_group = QWidget()
        bool_layout = QHBoxLayout(self.bool_group)
        self.true_radio = QRadioButton("True")
        self.false_radio = QRadioButton("False")
        self.true_radio.setChecked(True)
        bool_layout.addWidget(self.true_radio)
        bool_layout.addWidget(self.false_radio)
        
        # Text value (for last_match, last_ocr)
        self.text_group = QWidget()
        text_layout = QHBoxLayout(self.text_group)
        text_layout.addWidget(QLabel("Contains Text:"))
        self.text_value_edit = QLineEdit()
        text_layout.addWidget(self.text_value_edit)
        
        # Expression value
        self.expr_group = QWidget()
        expr_layout = QHBoxLayout(self.expr_group)
        expr_layout.addWidget(QLabel("Expression:"))
        self.expr_value_edit = QLineEdit()
        expr_layout.addWidget(self.expr_value_edit)
        
        # Add initial condition value widget
        self.condition_value_layout.addWidget(self.bool_group)
        
        # Note about nested actions
        note_label = QLabel("Note: Nested actions (Then/Else) are configured in the action editor dialog")
        note_label.setStyleSheet("color: gray; font-style: italic;")
        layout.addWidget(note_label)
        
        # Connect signals
        self.true_radio.toggled.connect(self.params_changed.emit)
        self.false_radio.toggled.connect(self.params_changed.emit)
        self.text_value_edit.textChanged.connect(self.params_changed.emit)
        self.expr_value_edit.textChanged.connect(self.params_changed.emit)
        
    def _on_condition_type_changed(self, condition_type: str) -> None:
        """Handle change in condition type."""
        # Clear current condition value widget
        while self.condition_value_layout.count():
            item = self.condition_value_layout.takeAt(0)
            if item.widget():
                item.widget().hide()
        
        # Add appropriate condition value widget
        if condition_type == "last_result":
            self.condition_value_layout.addWidget(self.bool_group)
            self.bool_group.show()
        elif condition_type in ["last_match", "last_ocr"]:
            self.condition_value_layout.addWidget(self.text_group)
            self.text_group.show()
        elif condition_type == "expression":
            self.condition_value_layout.addWidget(self.expr_group)
            self.expr_group.show()
            
        self.params_changed.emit()
        
    def get_params(self) -> ConditionalParams:
        """Get the current conditional parameters."""
        condition_type = self.condition_type_combo.currentText()
        
        # Get condition value based on type
        if condition_type == "last_result":
            condition_value = self.true_radio.isChecked()
        elif condition_type in ["last_match", "last_ocr"]:
            condition_value = self.text_value_edit.text()
        elif condition_type == "expression":
            condition_value = self.expr_value_edit.text()
        else:
            condition_value = True
            
        return ConditionalParams(
            description=self.description_edit.text() or None,
            condition_type=condition_type,
            condition_value=condition_value,
            then_actions=[],  # These are set in the action editor
            else_actions=[]   # These are set in the action editor
        )
        
    def set_params(self, params: ConditionalParams) -> None:
        """Set the conditional parameters."""
        self._creating_widgets = True
        
        self.description_edit.setText(params.description or "")
        
        # Set condition type
        index = self.condition_type_combo.findText(params.condition_type)
        if index >= 0:
            self.condition_type_combo.setCurrentIndex(index)
            
        # Set condition value based on type
        if params.condition_type == "last_result":
            self.true_radio.setChecked(params.condition_value)
            self.false_radio.setChecked(not params.condition_value)
        elif params.condition_type in ["last_match", "last_ocr"]:
            self.text_value_edit.setText(str(params.condition_value))
        elif params.condition_type == "expression":
            self.expr_value_edit.setText(str(params.condition_value))
            
        self._creating_widgets = False

class LoopParamsWidget(BaseParamsWidget):
    """Widget for configuring loop action parameters."""
    
    def __init__(self):
        """Initialize the loop parameters widget."""
        super().__init__()
        layout = QVBoxLayout()
        self.setLayout(layout)
        
        # Description field
        desc_layout = QHBoxLayout()
        desc_layout.addWidget(QLabel("Description:"))
        self.description_edit = QLineEdit()
        self.description_edit.textChanged.connect(self.params_changed.emit)
        desc_layout.addWidget(self.description_edit)
        layout.addLayout(desc_layout)
        
        # Iterations field
        iterations_layout = QHBoxLayout()
        iterations_layout.addWidget(QLabel("Iterations:"))
        self.iterations_spin = QSpinBox()
        self.iterations_spin.setRange(0, 9999)
        self.iterations_spin.setValue(1)
        self.iterations_spin.setSpecialValueText("Infinite")  # 0 means infinite
        self.iterations_spin.valueChanged.connect(self.params_changed.emit)
        iterations_layout.addWidget(self.iterations_spin)
        layout.addLayout(iterations_layout)
        
        # Break condition
        break_layout = QHBoxLayout()
        break_layout.addWidget(QLabel("Break Condition:"))
        self.break_condition_edit = QLineEdit()
        self.break_condition_edit.setPlaceholderText("Expression to evaluate after each iteration")
        self.break_condition_edit.textChanged.connect(self.params_changed.emit)
        break_layout.addWidget(self.break_condition_edit)
        layout.addLayout(break_layout)
        
        # Break on failure
        self.break_on_failure_check = QCheckBox("Break on Failure")
        self.break_on_failure_check.setChecked(True)
        self.break_on_failure_check.stateChanged.connect(self.params_changed.emit)
        layout.addWidget(self.break_on_failure_check)
        
        # Note about nested actions
        note_label = QLabel("Note: Nested actions (Loop Body) are configured in the action editor dialog")
        note_label.setStyleSheet("color: gray; font-style: italic;")
        layout.addWidget(note_label)
        
        # Action count display
        self.action_count_layout = QHBoxLayout()
        self.action_count_layout.addWidget(QLabel("Actions in Loop:"))
        self.action_count_label = QLabel("0 actions")
        self.action_count_layout.addWidget(self.action_count_label)
        layout.addLayout(self.action_count_layout)
        
    def get_params(self) -> LoopParams:
        """Get the current loop parameters."""
        return LoopParams(
            description=self.description_edit.text() or None,
            iterations=self.iterations_spin.value(),
            break_condition=self.break_condition_edit.text() or None,
            break_on_failure=self.break_on_failure_check.isChecked(),
            actions=[]  # This is set in the action editor
        )
        
    def set_params(self, params: LoopParams) -> None:
        """Set the loop parameters."""
        self._creating_widgets = True
        
        self.description_edit.setText(params.description or "")
        self.iterations_spin.setValue(params.iterations)
        self.break_condition_edit.setText(params.break_condition or "")
        self.break_on_failure_check.setChecked(params.break_on_failure)
        
        # Update the action count label
        action_count = len(params.actions) if hasattr(params, 'actions') else 0
        self.action_count_label.setText(f"{action_count} action{'s' if action_count != 1 else ''}")
        
        self._creating_widgets = False

class VariableSetParamsWidget(BaseParamsWidget):
    """Widget for configuring variable set action parameters."""
    
    def __init__(self):
        """Initialize the variable set parameters widget."""
        super().__init__()
        layout = QVBoxLayout()
        self.setLayout(layout)
        
        # Description field
        desc_layout = QHBoxLayout()
        desc_layout.addWidget(QLabel("Description:"))
        self.description_edit = QLineEdit()
        self.description_edit.textChanged.connect(self.params_changed.emit)
        desc_layout.addWidget(self.description_edit)
        layout.addLayout(desc_layout)
        
        # Variable name field
        var_name_layout = QHBoxLayout()
        var_name_layout.addWidget(QLabel("Variable Name:"))
        self.var_name_edit = QLineEdit()
        self.var_name_edit.textChanged.connect(self.params_changed.emit)
        var_name_layout.addWidget(self.var_name_edit)
        layout.addLayout(var_name_layout)
        
        # Value field
        value_layout = QHBoxLayout()
        value_layout.addWidget(QLabel("Value:"))
        self.value_edit = QLineEdit()
        self.value_edit.textChanged.connect(self.params_changed.emit)
        value_layout.addWidget(self.value_edit)
        layout.addLayout(value_layout)
        
        # Value type field
        type_layout = QHBoxLayout()
        type_layout.addWidget(QLabel("Value Type:"))
        self.type_combo = QComboBox()
        self.type_combo.addItems(["string", "integer", "float", "boolean", "expression"])
        self.type_combo.currentTextChanged.connect(self.params_changed.emit)
        type_layout.addWidget(self.type_combo)
        layout.addLayout(type_layout)
        
    def get_params(self) -> VariableSetParams:
        """Get the current variable set parameters."""
        return VariableSetParams(
            description=self.description_edit.text() or None,
            variable_name=self.var_name_edit.text(),
            value=self.value_edit.text(),
            value_type=self.type_combo.currentText()
        )
        
    def set_params(self, params: VariableSetParams) -> None:
        """Set the variable set parameters."""
        self._creating_widgets = True
        
        self.description_edit.setText(params.description or "")
        self.var_name_edit.setText(params.variable_name)
        self.value_edit.setText(str(params.value))
        
        # Set value type
        index = self.type_combo.findText(params.value_type)
        if index >= 0:
            self.type_combo.setCurrentIndex(index)
            
        self._creating_widgets = False

class VariableIncrementParamsWidget(BaseParamsWidget):
    """Widget for configuring variable increment action parameters."""
    
    def __init__(self):
        """Initialize the variable increment parameters widget."""
        super().__init__()
        layout = QVBoxLayout()
        self.setLayout(layout)
        
        # Description field
        desc_layout = QHBoxLayout()
        desc_layout.addWidget(QLabel("Description:"))
        self.description_edit = QLineEdit()
        self.description_edit.textChanged.connect(self.params_changed.emit)
        desc_layout.addWidget(self.description_edit)
        layout.addLayout(desc_layout)
        
        # Variable name field
        var_name_layout = QHBoxLayout()
        var_name_layout.addWidget(QLabel("Variable Name:"))
        self.var_name_edit = QLineEdit()
        self.var_name_edit.textChanged.connect(self.params_changed.emit)
        var_name_layout.addWidget(self.var_name_edit)
        layout.addLayout(var_name_layout)
        
        # Increment value field
        increment_layout = QHBoxLayout()
        increment_layout.addWidget(QLabel("Increment By:"))
        self.increment_spin = QDoubleSpinBox()
        self.increment_spin.setRange(-1000, 1000)
        self.increment_spin.setValue(1)
        self.increment_spin.valueChanged.connect(self.params_changed.emit)
        increment_layout.addWidget(self.increment_spin)
        layout.addLayout(increment_layout)
        
    def get_params(self) -> VariableIncrementParams:
        """Get the current variable increment parameters."""
        return VariableIncrementParams(
            description=self.description_edit.text() or None,
            variable_name=self.var_name_edit.text(),
            increment_by=self.increment_spin.value()
        )
        
    def set_params(self, params: VariableIncrementParams) -> None:
        """Set the variable increment parameters."""
        self._creating_widgets = True
        
        self.description_edit.setText(params.description or "")
        self.var_name_edit.setText(params.variable_name)
        self.increment_spin.setValue(params.increment_by)
        
        self._creating_widgets = False

def create_params_widget(action_type: ActionType) -> BaseParamsWidget:
    """
    Create a parameter widget for the given action type.
    
    Args:
        action_type: Type of action to create parameters for
        
    Returns:
        Parameter widget instance
    """
    widget_map = {
        ActionType.CLICK: ClickParamsWidget,
        ActionType.RIGHT_CLICK: ClickParamsWidget,
        ActionType.DOUBLE_CLICK: ClickParamsWidget,
        ActionType.DRAG: DragParamsWidget,
        ActionType.TYPE_TEXT: TypeParamsWidget,
        ActionType.WAIT: WaitParamsWidget,
        ActionType.TEMPLATE_SEARCH: TemplateSearchParamsWidget,
        ActionType.WAIT_FOR_OCR: OCRWaitParamsWidget,
        ActionType.CONDITIONAL: ConditionalParamsWidget,
        ActionType.LOOP: LoopParamsWidget,
        ActionType.VARIABLE_SET: VariableSetParamsWidget,
        ActionType.VARIABLE_INCREMENT: VariableIncrementParamsWidget
    }
    
    widget_class = widget_map.get(action_type)
    if not widget_class:
        raise ValueError(f"No parameter widget for action type: {action_type}")
        
    return widget_class() 
