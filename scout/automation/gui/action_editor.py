"""
Action Editor

This module provides a dialog for editing automation actions.
It allows users to configure parameters for different action types.
"""

import logging
from typing import Dict, List, Optional, Any, Tuple, Union, Callable

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, 
    QComboBox, QSpinBox, QDoubleSpinBox, QCheckBox, QTabWidget, 
    QTextEdit, QDialogButtonBox, QFormLayout, QGroupBox, QWidget
)

from scout.automation.actions import (
    ActionType, AutomationAction, ClickParams, DragParams, TypeParams,
    WaitParams, TemplateSearchParams, OCRWaitParams, ConditionalParams, LoopParams,
    SwitchCaseParams, TryCatchParams, ParallelExecutionParams, BreakpointParams,
    LogParams, ScreenshotParams
)
from scout.automation.action_handlers_data import (
    VariableSetParams, VariableIncrementParams, StringOperationParams,
    ListOperationParams, DictOperationParams, MathOperationParams,
    FileOperationParams
)
from scout.utils.logging_utils import get_logger

logger = get_logger(__name__)

# Define action types with their display names and descriptions
ACTION_TYPES = {
    ActionType.CLICK: {
        "name": "Click",
        "description": "Click at a specific position",
        "category": "Basic"
    },
    ActionType.RIGHT_CLICK: {
        "name": "Right Click",
        "description": "Right-click at a specific position",
        "category": "Basic"
    },
    ActionType.DOUBLE_CLICK: {
        "name": "Double Click",
        "description": "Double-click at a specific position",
        "category": "Basic"
    },
    ActionType.DRAG: {
        "name": "Drag",
        "description": "Drag from one position to another",
        "category": "Basic"
    },
    ActionType.TYPE_TEXT: {
        "name": "Type Text",
        "description": "Type text at the current position",
        "category": "Basic"
    },
    ActionType.WAIT: {
        "name": "Wait",
        "description": "Wait for a specified time",
        "category": "Basic"
    },
    ActionType.TEMPLATE_SEARCH: {
        "name": "Template Search",
        "description": "Search for a template on screen",
        "category": "Visual"
    },
    ActionType.WAIT_FOR_OCR: {
        "name": "OCR Wait",
        "description": "Wait for text to appear on screen",
        "category": "Visual"
    },
    ActionType.CONDITIONAL: {
        "name": "Conditional",
        "description": "Execute actions if a condition is true",
        "category": "Flow"
    },
    ActionType.LOOP: {
        "name": "Loop",
        "description": "Repeat actions based on a condition or count",
        "category": "Flow"
    },
    ActionType.SWITCH_CASE: {
        "name": "Switch/Case",
        "description": "Execute different actions based on a value",
        "category": "Flow"
    },
    ActionType.TRY_CATCH: {
        "name": "Try/Catch",
        "description": "Handle errors in actions",
        "category": "Advanced Flow"
    },
    ActionType.PARALLEL_EXECUTION: {
        "name": "Parallel Execution",
        "description": "Execute multiple action groups in parallel",
        "category": "Advanced Flow"
    },
    ActionType.BREAKPOINT: {
        "name": "Breakpoint",
        "description": "Pause execution when a condition is met",
        "category": "Advanced Flow"
    },
    ActionType.VARIABLE_SET: {
        "name": "Set Variable",
        "description": "Set a variable value",
        "category": "Data"
    },
    ActionType.LOG: {
        "name": "Log Message",
        "description": "Log a message to the console",
        "category": "Data"
    },
    ActionType.SCREENSHOT: {
        "name": "Take Screenshot",
        "description": "Capture a screenshot of the game window",
        "category": "Visual"
    }
}


class ActionEditorDialog(QDialog):
    """
    Dialog for editing automation action parameters.
    """
    
    def __init__(self, action: Optional[AutomationAction] = None, parent=None):
        """
        Initialize the action editor dialog.
        
        Args:
            action: The action to edit, or None to create a new action
            parent: The parent widget
        """
        super().__init__(parent)
        self.setWindowTitle("Edit Action")
        self.resize(500, 400)
        
        self.action = action
        self.result_action = None
        
        self._init_ui()
        
        if action:
            self._load_action(action)
    
    def _init_ui(self) -> None:
        """Initialize the UI components."""
        layout = QVBoxLayout()
        
        # Action type selection
        type_layout = QHBoxLayout()
        type_layout.addWidget(QLabel("Action Type:"))
        
        self.type_combo = QComboBox()
        self._populate_action_types()
        type_layout.addWidget(self.type_combo)
        
        layout.addLayout(type_layout)
        
        # Action name
        name_layout = QHBoxLayout()
        name_layout.addWidget(QLabel("Action Name:"))
        
        self.name_edit = QLineEdit()
        name_layout.addWidget(self.name_edit)
        
        layout.addLayout(name_layout)
        
        # Description
        description_layout = QHBoxLayout()
        description_layout.addWidget(QLabel("Description:"))
        
        self.description_label = QLabel()
        description_layout.addWidget(self.description_label)
        
        layout.addLayout(description_layout)
        
        # Parameters container
        self.params_container = QWidget()
        self.params_layout = QVBoxLayout(self.params_container)
        layout.addWidget(self.params_container)
        
        # Buttons
        button_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)
        
        self.setLayout(layout)
        
        # Connect signals
        self.type_combo.currentIndexChanged.connect(self._on_type_changed)
        
        # Initialize with first type
        if self.type_combo.count() > 0:
            self._on_type_changed(0)
    
    def _populate_action_types(self) -> None:
        """Populate the action type combo box."""
        # Group action types by category
        categories = {}
        for action_type, info in ACTION_TYPES.items():
            category = info.get("category", "Other")
            if category not in categories:
                categories[category] = []
            categories[category].append((action_type, info["name"]))
        
        # Add categories as separators and items
        for category, items in sorted(categories.items()):
            self.type_combo.addItem(f"--- {category} ---")
            for action_type, name in sorted(items, key=lambda x: x[1]):
                self.type_combo.addItem(name, action_type)
    
    def _on_type_changed(self, index: int) -> None:
        """
        Handle action type change.
        
        Args:
            index: The index of the selected action type
        """
        # Skip category separators
        if "---" in self.type_combo.currentText():
            if index < self.type_combo.count() - 1:
                self.type_combo.setCurrentIndex(index + 1)
            return
        
        action_type = self.type_combo.currentData()
        if action_type is None:
            return
        
        # Update description
        if action_type in ACTION_TYPES:
            self.description_label.setText(ACTION_TYPES[action_type]["description"])
        
        # Clear existing parameters
        self._clear_params_layout()
        
        # Create parameter widgets based on action type
        self._create_param_widgets(action_type)
    
    def _clear_params_layout(self) -> None:
        """Clear the parameters layout."""
        while self.params_layout.count():
            item = self.params_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
    
    def _create_param_widgets(self, action_type: ActionType) -> None:
        """
        Create parameter widgets based on action type.
        
        Args:
            action_type: The action type
        """
        if action_type == ActionType.CLICK or action_type == ActionType.RIGHT_CLICK or action_type == ActionType.DOUBLE_CLICK:
            self._create_click_params()
        elif action_type == ActionType.DRAG:
            self._create_drag_params()
        elif action_type == ActionType.TYPE:
            self._create_type_params()
        elif action_type == ActionType.PRESS_KEY:
            self._create_key_params()
        elif action_type == ActionType.WAIT:
            self._create_wait_params()
        elif action_type == ActionType.TEMPLATE_SEARCH:
            self._create_template_search_params()
        elif action_type == ActionType.OCR_WAIT:
            self._create_ocr_wait_params()
        elif action_type == ActionType.IF_CONDITION:
            self._create_if_condition_params()
        elif action_type == ActionType.REPEAT_LOOP:
            self._create_repeat_loop_params()
        elif action_type == ActionType.WHILE_LOOP:
            self._create_while_loop_params()
        elif action_type == ActionType.RUN_SEQUENCE:
            self._create_run_sequence_params()
        elif action_type == ActionType.SWITCH_CASE:
            self._create_switch_case_params()
        elif action_type == ActionType.TRY_CATCH:
            self._create_try_catch_params()
        elif action_type == ActionType.PARALLEL:
            self._create_parallel_params()
        elif action_type == ActionType.BREAKPOINT:
            self._create_breakpoint_params()
        elif action_type == ActionType.SET_VARIABLE:
            self._create_variable_params()
        elif action_type == ActionType.LOG_MESSAGE:
            self._create_log_params()
        elif action_type == ActionType.SCREENSHOT:
            self._create_screenshot_params()
    
    def _create_click_params(self) -> None:
        """Create widgets for click parameters."""
        group = QGroupBox("Click Parameters")
        form = QFormLayout()
        
        self.position_combo = QComboBox()
        self.position_combo.setEditable(True)
        form.addRow("Position:", self.position_combo)
        
        self.offset_x_spin = QSpinBox()
        self.offset_x_spin.setRange(-1000, 1000)
        form.addRow("Offset X:", self.offset_x_spin)
        
        self.offset_y_spin = QSpinBox()
        self.offset_y_spin.setRange(-1000, 1000)
        form.addRow("Offset Y:", self.offset_y_spin)
        
        self.relative_check = QCheckBox("Use Relative Position")
        form.addRow("", self.relative_check)
        
        group.setLayout(form)
        self.params_layout.addWidget(group)
    
    def _create_drag_params(self) -> None:
        """Create widgets for drag parameters."""
        group = QGroupBox("Drag Parameters")
        form = QFormLayout()
        
        self.start_position_combo = QComboBox()
        self.start_position_combo.setEditable(True)
        form.addRow("Start Position:", self.start_position_combo)
        
        self.end_position_combo = QComboBox()
        self.end_position_combo.setEditable(True)
        form.addRow("End Position:", self.end_position_combo)
        
        self.duration_spin = QDoubleSpinBox()
        self.duration_spin.setRange(0.1, 10.0)
        self.duration_spin.setSingleStep(0.1)
        self.duration_spin.setValue(0.5)
        form.addRow("Duration (s):", self.duration_spin)
        
        group.setLayout(form)
        self.params_layout.addWidget(group)
    
    def _create_type_params(self) -> None:
        """Create widgets for type parameters."""
        group = QGroupBox("Type Parameters")
        form = QFormLayout()
        
        self.text_edit = QLineEdit()
        form.addRow("Text:", self.text_edit)
        
        self.interval_spin = QDoubleSpinBox()
        self.interval_spin.setRange(0.01, 1.0)
        self.interval_spin.setSingleStep(0.01)
        self.interval_spin.setValue(0.05)
        form.addRow("Interval (s):", self.interval_spin)
        
        group.setLayout(form)
        self.params_layout.addWidget(group)
    
    def _create_key_params(self) -> None:
        """Create widgets for key press parameters."""
        group = QGroupBox("Key Press Parameters")
        form = QFormLayout()
        
        self.key_edit = QLineEdit()
        form.addRow("Key:", self.key_edit)
        
        group.setLayout(form)
        self.params_layout.addWidget(group)
    
    def _create_wait_params(self) -> None:
        """Create widgets for wait parameters."""
        group = QGroupBox("Wait Parameters")
        form = QFormLayout()
        
        self.duration_spin = QDoubleSpinBox()
        self.duration_spin.setRange(0.1, 60.0)
        self.duration_spin.setSingleStep(0.1)
        self.duration_spin.setValue(1.0)
        form.addRow("Duration (s):", self.duration_spin)
        
        group.setLayout(form)
        self.params_layout.addWidget(group)
    
    def _create_template_search_params(self) -> None:
        """Create widgets for template search parameters."""
        group = QGroupBox("Template Search Parameters")
        form = QFormLayout()
        
        self.template_combo = QComboBox()
        self.template_combo.setEditable(True)
        form.addRow("Template:", self.template_combo)
        
        self.threshold_spin = QDoubleSpinBox()
        self.threshold_spin.setRange(0.1, 1.0)
        self.threshold_spin.setSingleStep(0.05)
        self.threshold_spin.setValue(0.8)
        form.addRow("Threshold:", self.threshold_spin)
        
        self.timeout_spin = QDoubleSpinBox()
        self.timeout_spin.setRange(0.1, 60.0)
        self.timeout_spin.setSingleStep(0.1)
        self.timeout_spin.setValue(5.0)
        form.addRow("Timeout (s):", self.timeout_spin)
        
        self.result_var_edit = QLineEdit()
        form.addRow("Result Variable:", self.result_var_edit)
        
        group.setLayout(form)
        self.params_layout.addWidget(group)
    
    def _create_ocr_wait_params(self) -> None:
        """Create widgets for OCR wait parameters."""
        group = QGroupBox("OCR Wait Parameters")
        form = QFormLayout()
        
        self.text_edit = QLineEdit()
        form.addRow("Text to Find:", self.text_edit)
        
        self.region_combo = QComboBox()
        self.region_combo.setEditable(True)
        form.addRow("Region:", self.region_combo)
        
        self.timeout_spin = QDoubleSpinBox()
        self.timeout_spin.setRange(0.1, 60.0)
        self.timeout_spin.setSingleStep(0.1)
        self.timeout_spin.setValue(5.0)
        form.addRow("Timeout (s):", self.timeout_spin)
        
        self.result_var_edit = QLineEdit()
        form.addRow("Result Variable:", self.result_var_edit)
        
        group.setLayout(form)
        self.params_layout.addWidget(group)
    
    def _create_if_condition_params(self) -> None:
        """Create widgets for if condition parameters."""
        group = QGroupBox("If Condition Parameters")
        form = QFormLayout()
        
        self.condition_edit = QLineEdit()
        form.addRow("Condition:", self.condition_edit)
        
        self.then_actions_edit = QTextEdit()
        form.addRow("Then Actions:", self.then_actions_edit)
        
        self.else_actions_edit = QTextEdit()
        form.addRow("Else Actions:", self.else_actions_edit)
        
        group.setLayout(form)
        self.params_layout.addWidget(group)
    
    def _create_repeat_loop_params(self) -> None:
        """Create widgets for repeat loop parameters."""
        group = QGroupBox("Repeat Loop Parameters")
        form = QFormLayout()
        
        self.count_spin = QSpinBox()
        self.count_spin.setRange(1, 1000)
        self.count_spin.setValue(5)
        form.addRow("Count:", self.count_spin)
        
        self.loop_actions_edit = QTextEdit()
        form.addRow("Loop Actions:", self.loop_actions_edit)
        
        group.setLayout(form)
        self.params_layout.addWidget(group)
    
    def _create_while_loop_params(self) -> None:
        """Create widgets for while loop parameters."""
        group = QGroupBox("While Loop Parameters")
        form = QFormLayout()
        
        self.condition_edit = QLineEdit()
        form.addRow("Condition:", self.condition_edit)
        
        self.max_iterations_spin = QSpinBox()
        self.max_iterations_spin.setRange(1, 1000)
        self.max_iterations_spin.setValue(100)
        form.addRow("Max Iterations:", self.max_iterations_spin)
        
        self.loop_actions_edit = QTextEdit()
        form.addRow("Loop Actions:", self.loop_actions_edit)
        
        group.setLayout(form)
        self.params_layout.addWidget(group)
    
    def _create_run_sequence_params(self) -> None:
        """Create widgets for run sequence parameters."""
        group = QGroupBox("Run Sequence Parameters")
        form = QFormLayout()
        
        self.sequence_combo = QComboBox()
        form.addRow("Sequence:", self.sequence_combo)
        
        self.wait_check = QCheckBox("Wait for Completion")
        self.wait_check.setChecked(True)
        form.addRow("", self.wait_check)
        
        group.setLayout(form)
        self.params_layout.addWidget(group)
    
    def _create_switch_case_params(self) -> None:
        """Create widgets for switch/case parameters."""
        group = QGroupBox("Switch/Case Parameters")
        form = QFormLayout()
        
        self.expression_edit = QLineEdit()
        form.addRow("Expression:", self.expression_edit)
        
        self.cases_edit = QTextEdit()
        self.cases_edit.setPlaceholderText("Format: case_value: action_id1, action_id2, ...\nOne case per line")
        form.addRow("Cases:", self.cases_edit)
        
        self.default_edit = QLineEdit()
        self.default_edit.setPlaceholderText("action_id1, action_id2, ...")
        form.addRow("Default Case:", self.default_edit)
        
        group.setLayout(form)
        self.params_layout.addWidget(group)
    
    def _create_try_catch_params(self) -> None:
        """Create widgets for try/catch parameters."""
        group = QGroupBox("Try/Catch Parameters")
        form = QFormLayout()
        
        self.try_actions_edit = QTextEdit()
        form.addRow("Try Actions:", self.try_actions_edit)
        
        self.catch_actions_edit = QTextEdit()
        form.addRow("Catch Actions:", self.catch_actions_edit)
        
        self.finally_actions_edit = QTextEdit()
        form.addRow("Finally Actions:", self.finally_actions_edit)
        
        group.setLayout(form)
        self.params_layout.addWidget(group)
    
    def _create_parallel_params(self) -> None:
        """Create widgets for parallel execution parameters."""
        group = QGroupBox("Parallel Execution Parameters")
        form = QFormLayout()
        
        self.groups_edit = QTextEdit()
        self.groups_edit.setPlaceholderText("Format: group_name: action_id1, action_id2, ...\nOne group per line")
        form.addRow("Action Groups:", self.groups_edit)
        
        self.timeout_spin = QDoubleSpinBox()
        self.timeout_spin.setRange(0.1, 300.0)
        self.timeout_spin.setSingleStep(0.1)
        self.timeout_spin.setValue(30.0)
        form.addRow("Timeout (s):", self.timeout_spin)
        
        group.setLayout(form)
        self.params_layout.addWidget(group)
    
    def _create_breakpoint_params(self) -> None:
        """Create widgets for breakpoint parameters."""
        group = QGroupBox("Breakpoint Parameters")
        form = QFormLayout()
        
        self.condition_edit = QLineEdit()
        form.addRow("Condition:", self.condition_edit)
        
        self.message_edit = QLineEdit()
        form.addRow("Message:", self.message_edit)
        
        group.setLayout(form)
        self.params_layout.addWidget(group)
    
    def _create_variable_params(self) -> None:
        """Create widgets for variable parameters."""
        group = QGroupBox("Variable Parameters")
        form = QFormLayout()
        
        self.var_name_edit = QLineEdit()
        form.addRow("Variable Name:", self.var_name_edit)
        
        self.var_value_edit = QLineEdit()
        form.addRow("Value:", self.var_value_edit)
        
        group.setLayout(form)
        self.params_layout.addWidget(group)
    
    def _create_log_params(self) -> None:
        """Create widgets for log message parameters."""
        group = QGroupBox("Log Message Parameters")
        form = QFormLayout()
        
        self.message_edit = QLineEdit()
        form.addRow("Message:", self.message_edit)
        
        self.level_combo = QComboBox()
        self.level_combo.addItems(["INFO", "DEBUG", "WARNING", "ERROR"])
        form.addRow("Level:", self.level_combo)
        
        group.setLayout(form)
        self.params_layout.addWidget(group)
    
    def _create_screenshot_params(self) -> None:
        """Create widgets for screenshot parameters."""
        group = QGroupBox("Screenshot Parameters")
        form = QFormLayout()
        
        self.filename_edit = QLineEdit()
        form.addRow("Filename:", self.filename_edit)
        
        self.region_combo = QComboBox()
        self.region_combo.setEditable(True)
        form.addRow("Region:", self.region_combo)
        
        group.setLayout(form)
        self.params_layout.addWidget(group)
    
    def _load_action(self, action: AutomationAction) -> None:
        """
        Load an existing action into the editor.
        
        Args:
            action: The action to load
        """
        # Set action type
        for i in range(self.type_combo.count()):
            if self.type_combo.itemData(i) == action.action_type:
                self.type_combo.setCurrentIndex(i)
                break
        
        # Set action name
        self.name_edit.setText(action.name)
        
        # Load parameters based on action type
        if action.action_type in [ActionType.CLICK, ActionType.RIGHT_CLICK, ActionType.DOUBLE_CLICK]:
            self._load_click_params(action.params)
        elif action.action_type == ActionType.DRAG:
            self._load_drag_params(action.params)
        elif action.action_type == ActionType.TYPE:
            self._load_type_params(action.params)
        elif action.action_type == ActionType.PRESS_KEY:
            self._load_key_params(action.params)
        elif action.action_type == ActionType.WAIT:
            self._load_wait_params(action.params)
        elif action.action_type == ActionType.TEMPLATE_SEARCH:
            self._load_template_search_params(action.params)
        elif action.action_type == ActionType.OCR_WAIT:
            self._load_ocr_wait_params(action.params)
        elif action.action_type == ActionType.IF_CONDITION:
            self._load_if_condition_params(action.params)
        elif action.action_type == ActionType.REPEAT_LOOP:
            self._load_repeat_loop_params(action.params)
        elif action.action_type == ActionType.WHILE_LOOP:
            self._load_while_loop_params(action.params)
        elif action.action_type == ActionType.RUN_SEQUENCE:
            self._load_run_sequence_params(action.params)
        elif action.action_type == ActionType.SWITCH_CASE:
            self._load_switch_case_params(action.params)
        elif action.action_type == ActionType.TRY_CATCH:
            self._load_try_catch_params(action.params)
        elif action.action_type == ActionType.PARALLEL:
            self._load_parallel_params(action.params)
        elif action.action_type == ActionType.BREAKPOINT:
            self._load_breakpoint_params(action.params)
        elif action.action_type == ActionType.SET_VARIABLE:
            self._load_variable_params(action.params)
        elif action.action_type == ActionType.LOG_MESSAGE:
            self._load_log_params(action.params)
        elif action.action_type == ActionType.SCREENSHOT:
            self._load_screenshot_params(action.params)
    
    def _load_click_params(self, params: ClickParams) -> None:
        """Load click parameters."""
        if hasattr(self, 'position_combo'):
            self.position_combo.setCurrentText(params.position)
        if hasattr(self, 'offset_x_spin'):
            self.offset_x_spin.setValue(params.offset_x)
        if hasattr(self, 'offset_y_spin'):
            self.offset_y_spin.setValue(params.offset_y)
        if hasattr(self, 'relative_check'):
            self.relative_check.setChecked(params.relative)
    
    def _load_drag_params(self, params: DragParams) -> None:
        """Load drag parameters."""
        if hasattr(self, 'start_position_combo'):
            self.start_position_combo.setCurrentText(params.start_position)
        if hasattr(self, 'end_position_combo'):
            self.end_position_combo.setCurrentText(params.end_position)
        if hasattr(self, 'duration_spin'):
            self.duration_spin.setValue(params.duration)
    
    def _load_type_params(self, params: TypeParams) -> None:
        """Load type parameters."""
        if hasattr(self, 'text_edit'):
            self.text_edit.setText(params.text)
        if hasattr(self, 'interval_spin'):
            self.interval_spin.setValue(params.interval)
    
    def _load_key_params(self, params: Any) -> None:
        """Load key press parameters."""
        if hasattr(self, 'key_edit'):
            self.key_edit.setText(params.key)
    
    def _load_wait_params(self, params: WaitParams) -> None:
        """Load wait parameters."""
        if hasattr(self, 'duration_spin'):
            self.duration_spin.setValue(params.duration)
    
    def _load_template_search_params(self, params: TemplateSearchParams) -> None:
        """Load template search parameters."""
        if hasattr(self, 'template_combo'):
            self.template_combo.setCurrentText(params.template)
        if hasattr(self, 'threshold_spin'):
            self.threshold_spin.setValue(params.threshold)
        if hasattr(self, 'timeout_spin'):
            self.timeout_spin.setValue(params.timeout)
        if hasattr(self, 'result_var_edit'):
            self.result_var_edit.setText(params.result_var)
    
    def _load_ocr_wait_params(self, params: OCRWaitParams) -> None:
        """Load OCR wait parameters."""
        if hasattr(self, 'text_edit'):
            self.text_edit.setText(params.text)
        if hasattr(self, 'region_combo'):
            self.region_combo.setCurrentText(params.region)
        if hasattr(self, 'timeout_spin'):
            self.timeout_spin.setValue(params.timeout)
        if hasattr(self, 'result_var_edit'):
            self.result_var_edit.setText(params.result_var)
    
    def _load_if_condition_params(self, params: ConditionalParams) -> None:
        """Load if condition parameters."""
        if hasattr(self, 'condition_edit'):
            self.condition_edit.setText(params.condition)
        if hasattr(self, 'then_actions_edit'):
            self.then_actions_edit.setPlainText(','.join(map(str, params.then_actions)))
        if hasattr(self, 'else_actions_edit'):
            self.else_actions_edit.setPlainText(','.join(map(str, params.else_actions)))
    
    def _load_repeat_loop_params(self, params: LoopParams) -> None:
        """Load repeat loop parameters."""
        if hasattr(self, 'count_spin'):
            self.count_spin.setValue(params.count)
        if hasattr(self, 'loop_actions_edit'):
            self.loop_actions_edit.setPlainText(','.join(map(str, params.actions)))
    
    def _load_while_loop_params(self, params: LoopParams) -> None:
        """Load while loop parameters."""
        if hasattr(self, 'condition_edit'):
            self.condition_edit.setText(params.condition)
        if hasattr(self, 'max_iterations_spin'):
            self.max_iterations_spin.setValue(params.max_iterations)
        if hasattr(self, 'description_edit'):
            self.description_edit.setText(params.description or "")
        
        # Store the nested actions for later editing
        self.nested_actions = params.actions
        
        # Update the action count label if it exists
        if hasattr(self, 'action_count_label'):
            action_count = len(params.actions)
            self.action_count_label.setText(f"{action_count} action{'s' if action_count != 1 else ''}")

    def _save_repeat_loop_params(self) -> LoopParams:
        """Save repeat loop parameters."""
        return LoopParams(
            description=self.description_edit.text() if hasattr(self, 'description_edit') else None,
            iterations=self.count_spin.value() if hasattr(self, 'count_spin') else 1,
            actions=self.nested_actions,
            break_on_failure=self.break_on_failure_check.isChecked() if hasattr(self, 'break_on_failure_check') else True
        )

    def _create_repeat_loop_ui(self) -> QWidget:
        """Create UI for repeat loop parameters."""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        # Description field
        desc_layout = QHBoxLayout()
        desc_layout.addWidget(QLabel("Description:"))
        self.description_edit = QLineEdit()
        self.description_edit.textChanged.connect(self._on_params_changed)
        desc_layout.addWidget(self.description_edit)
        layout.addLayout(desc_layout)
        
        # Count field
        count_layout = QHBoxLayout()
        count_layout.addWidget(QLabel("Iterations:"))
        self.count_spin = QSpinBox()
        self.count_spin.setRange(1, 10000)
        self.count_spin.setValue(1)
        self.count_spin.valueChanged.connect(self._on_params_changed)
        count_layout.addWidget(self.count_spin)
        layout.addLayout(count_layout)
        
        # Break on failure checkbox
        self.break_on_failure_check = QCheckBox("Break on failure")
        self.break_on_failure_check.setChecked(True)
        self.break_on_failure_check.stateChanged.connect(self._on_params_changed)
        layout.addWidget(self.break_on_failure_check)
        
        # Nested actions section
        actions_layout = QHBoxLayout()
        actions_layout.addWidget(QLabel("Nested Actions:"))
        self.action_count_label = QLabel("0 actions")
        actions_layout.addWidget(self.action_count_label)
        layout.addLayout(actions_layout)
        
        # Edit nested actions button
        self.edit_actions_btn = QPushButton("Edit Actions...")
        self.edit_actions_btn.clicked.connect(self._edit_nested_actions)
        layout.addWidget(self.edit_actions_btn)
        
        # Initialize nested actions list
        self.nested_actions = []
        
        return widget

    def _edit_nested_actions(self) -> None:
        """Open editor for nested actions."""
        from scout.automation.gui.nested_action_editor import NestedActionEditor
        
        editor = NestedActionEditor(self.nested_actions, self)
        if editor.exec() == QDialog.DialogCode.Accepted:
            self.nested_actions = editor.get_actions()
            # Update the action count label
            action_count = len(self.nested_actions)
            self.action_count_label.setText(f"{action_count} action{'s' if action_count != 1 else ''}")
            self._on_params_changed()

    def _on_params_changed(self) -> None:
        """Handle parameter changes."""
        if not self._creating_widgets and hasattr(self, 'params_changed'):
            self.params_changed.emit()

    def _create_while_loop_ui(self) -> QWidget:
        """Create UI for while loop parameters."""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        # Description field
        desc_layout = QHBoxLayout()
        desc_layout.addWidget(QLabel("Description:"))
        self.description_edit = QLineEdit()
        self.description_edit.textChanged.connect(self._on_params_changed)
        desc_layout.addWidget(self.description_edit)
        layout.addLayout(desc_layout)
        
        # Condition field
        condition_layout = QHBoxLayout()
        condition_layout.addWidget(QLabel("Condition:"))
        self.condition_edit = QLineEdit()
        self.condition_edit.setPlaceholderText("Python expression (e.g., 'loop_index < 10')")
        self.condition_edit.textChanged.connect(self._on_params_changed)
        condition_layout.addWidget(self.condition_edit)
        layout.addLayout(condition_layout)
        
        # Max iterations field
        max_iter_layout = QHBoxLayout()
        max_iter_layout.addWidget(QLabel("Max Iterations:"))
        self.max_iterations_spin = QSpinBox()
        self.max_iterations_spin.setRange(1, 10000)
        self.max_iterations_spin.setValue(100)
        self.max_iterations_spin.valueChanged.connect(self._on_params_changed)
        max_iter_layout.addWidget(self.max_iterations_spin)
        layout.addLayout(max_iter_layout)
        
        # Nested actions section
        actions_layout = QHBoxLayout()
        actions_layout.addWidget(QLabel("Nested Actions:"))
        self.action_count_label = QLabel("0 actions")
        actions_layout.addWidget(self.action_count_label)
        layout.addLayout(actions_layout)
        
        # Edit nested actions button
        self.edit_actions_btn = QPushButton("Edit Actions...")
        self.edit_actions_btn.clicked.connect(self._edit_nested_actions)
        layout.addWidget(self.edit_actions_btn)
        
        # Initialize nested actions list
        self.nested_actions = []
        
        return widget

    def _load_while_loop_params(self, params: LoopParams) -> None:
        """Load while loop parameters."""
        if hasattr(self, 'condition_edit'):
            self.condition_edit.setText(params.condition)
        if hasattr(self, 'max_iterations_spin'):
            self.max_iterations_spin.setValue(params.max_iterations)
        if hasattr(self, 'description_edit'):
            self.description_edit.setText(params.description or "")
        
        # Store the nested actions for later editing
        self.nested_actions = params.actions
        
        # Update the action count label if it exists
        if hasattr(self, 'action_count_label'):
            action_count = len(params.actions)
            self.action_count_label.setText(f"{action_count} action{'s' if action_count != 1 else ''}")

    def _save_while_loop_params(self) -> LoopParams:
        """Save while loop parameters."""
        return LoopParams(
            description=self.description_edit.text() if hasattr(self, 'description_edit') else None,
            condition=self.condition_edit.text() if hasattr(self, 'condition_edit') else "",
            max_iterations=self.max_iterations_spin.value() if hasattr(self, 'max_iterations_spin') else 100,
            actions=self.nested_actions
        )

    def _create_conditional_ui(self) -> QWidget:
        """Create UI for conditional parameters."""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        # Description field
        desc_layout = QHBoxLayout()
        desc_layout.addWidget(QLabel("Description:"))
        self.description_edit = QLineEdit()
        self.description_edit.textChanged.connect(self._on_params_changed)
        desc_layout.addWidget(self.description_edit)
        layout.addLayout(desc_layout)
        
        # Condition type field
        condition_type_layout = QHBoxLayout()
        condition_type_layout.addWidget(QLabel("Condition Type:"))
        self.condition_type_combo = QComboBox()
        self.condition_type_combo.addItems(["last_result", "last_match", "last_ocr", "expression"])
        self.condition_type_combo.currentTextChanged.connect(self._on_condition_type_changed)
        condition_type_layout.addWidget(self.condition_type_combo)
        layout.addLayout(condition_type_layout)
        
        # Condition value field (stack widget to show different inputs based on type)
        self.condition_stack = QStackedWidget()
        
        # Boolean value (for last_result)
        bool_widget = QWidget()
        bool_layout = QHBoxLayout(bool_widget)
        self.condition_bool = QComboBox()
        self.condition_bool.addItems(["True", "False"])
        bool_layout.addWidget(QLabel("Value:"))
        bool_layout.addWidget(self.condition_bool)
        self.condition_stack.addWidget(bool_widget)
        
        # Text value (for last_match, last_ocr)
        text_widget = QWidget()
        text_layout = QHBoxLayout(text_widget)
        self.condition_text = QLineEdit()
        text_layout.addWidget(QLabel("Value:"))
        text_layout.addWidget(self.condition_text)
        self.condition_stack.addWidget(text_widget)
        
        # Expression (for expression)
        expr_widget = QWidget()
        expr_layout = QHBoxLayout(expr_widget)
        self.condition_expr = QLineEdit()
        self.condition_expr.setPlaceholderText("Python expression (e.g., 'x > 10')")
        expr_layout.addWidget(QLabel("Expression:"))
        expr_layout.addWidget(self.condition_expr)
        self.condition_stack.addWidget(expr_widget)
        
        layout.addWidget(self.condition_stack)
        
        # Then actions section
        then_layout = QHBoxLayout()
        then_layout.addWidget(QLabel("Then Actions:"))
        self.then_count_label = QLabel("0 actions")
        then_layout.addWidget(self.then_count_label)
        layout.addLayout(then_layout)
        
        # Edit then actions button
        self.edit_then_btn = QPushButton("Edit Then Actions...")
        self.edit_then_btn.clicked.connect(self._edit_then_actions)
        layout.addWidget(self.edit_then_btn)
        
        # Else actions section
        else_layout = QHBoxLayout()
        else_layout.addWidget(QLabel("Else Actions:"))
        self.else_count_label = QLabel("0 actions")
        else_layout.addWidget(self.else_count_label)
        layout.addLayout(else_layout)
        
        # Edit else actions button
        self.edit_else_btn = QPushButton("Edit Else Actions...")
        self.edit_else_btn.clicked.connect(self._edit_else_actions)
        layout.addWidget(self.edit_else_btn)
        
        # Initialize nested actions lists
        self.then_actions = []
        self.else_actions = []
        
        # Connect signals
        self.condition_bool.currentTextChanged.connect(self._on_params_changed)
        self.condition_text.textChanged.connect(self._on_params_changed)
        self.condition_expr.textChanged.connect(self._on_params_changed)
        
        return widget

    def _on_condition_type_changed(self, condition_type: str) -> None:
        """Handle condition type changes."""
        if condition_type == "last_result":
            self.condition_stack.setCurrentIndex(0)  # Boolean widget
        elif condition_type in ["last_match", "last_ocr"]:
            self.condition_stack.setCurrentIndex(1)  # Text widget
        elif condition_type == "expression":
            self.condition_stack.setCurrentIndex(2)  # Expression widget
        
        self._on_params_changed()

    def _edit_then_actions(self) -> None:
        """Open editor for 'then' actions."""
        from scout.automation.gui.nested_action_editor import NestedActionEditor
        
        editor = NestedActionEditor(self.then_actions, self)
        if editor.exec() == QDialog.DialogCode.Accepted:
            self.then_actions = editor.get_actions()
            # Update the action count label
            action_count = len(self.then_actions)
            self.then_count_label.setText(f"{action_count} action{'s' if action_count != 1 else ''}")
            self._on_params_changed()

    def _edit_else_actions(self) -> None:
        """Open editor for 'else' actions."""
        from scout.automation.gui.nested_action_editor import NestedActionEditor
        
        editor = NestedActionEditor(self.else_actions, self)
        if editor.exec() == QDialog.DialogCode.Accepted:
            self.else_actions = editor.get_actions()
            # Update the action count label
            action_count = len(self.else_actions)
            self.else_count_label.setText(f"{action_count} action{'s' if action_count != 1 else ''}")
            self._on_params_changed()

    def _load_conditional_params(self, params: ConditionalParams) -> None:
        """Load conditional parameters."""
        if hasattr(self, 'description_edit'):
            self.description_edit.setText(params.description or "")
        
        if hasattr(self, 'condition_type_combo'):
            index = self.condition_type_combo.findText(params.condition_type)
            if index >= 0:
                self.condition_type_combo.setCurrentIndex(index)
        
        # Set the condition value based on type
        if params.condition_type == "last_result":
            if hasattr(self, 'condition_bool'):
                index = self.condition_bool.findText(str(params.condition_value))
                if index >= 0:
                    self.condition_bool.setCurrentIndex(index)
        elif params.condition_type in ["last_match", "last_ocr"]:
            if hasattr(self, 'condition_text'):
                self.condition_text.setText(str(params.condition_value))
        elif params.condition_type == "expression":
            if hasattr(self, 'condition_expr'):
                self.condition_expr.setText(str(params.condition_value))
        
        # Store the nested actions for later editing
        self.then_actions = params.then_actions
        self.else_actions = params.else_actions
        
        # Update the action count labels if they exist
        if hasattr(self, 'then_count_label'):
            action_count = len(params.then_actions)
            self.then_count_label.setText(f"{action_count} action{'s' if action_count != 1 else ''}")
        
        if hasattr(self, 'else_count_label'):
            action_count = len(params.else_actions)
            self.else_count_label.setText(f"{action_count} action{'s' if action_count != 1 else ''}")

    def _save_conditional_params(self) -> ConditionalParams:
        """Save conditional parameters."""
        condition_type = self.condition_type_combo.currentText() if hasattr(self, 'condition_type_combo') else "last_result"
        
        # Get condition value based on type
        if condition_type == "last_result":
            condition_value = self.condition_bool.currentText() == "True" if hasattr(self, 'condition_bool') else True
        elif condition_type in ["last_match", "last_ocr"]:
            condition_value = self.condition_text.text() if hasattr(self, 'condition_text') else ""
        elif condition_type == "expression":
            condition_value = self.condition_expr.text() if hasattr(self, 'condition_expr') else ""
        else:
            condition_value = True
        
        return ConditionalParams(
            description=self.description_edit.text() if hasattr(self, 'description_edit') else None,
            condition_type=condition_type,
            condition_value=condition_value,
            then_actions=self.then_actions,
            else_actions=self.else_actions
        )

