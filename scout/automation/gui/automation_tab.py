"""
Automation Tab

This module provides the main automation tab in the GUI.
It contains:
- Position list and management
- Sequence builder and editor
- Import/export functionality
- Execution controls
"""

from typing import Dict, Optional, List
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QListWidget, QListWidgetItem, QLineEdit, QSpinBox,
    QDoubleSpinBox, QComboBox, QMessageBox, QFileDialog,
    QGroupBox, QScrollArea, QFrame, QCheckBox, QSlider
)
from PyQt6.QtCore import Qt, pyqtSignal
import logging
import json
from pathlib import Path
from scout.automation.core import AutomationPosition, AutomationSequence
from scout.automation.actions import ActionType, AutomationAction, ActionParamsCommon
from scout.automation.gui.position_marker import PositionMarker
from scout.automation.gui.action_params import create_params_widget, BaseParamsWidget, DragParamsWidget
from scout.automation.executor import SequenceExecutor, ExecutionContext
from scout.config_manager import ConfigManager

logger = logging.getLogger(__name__)

class PositionList(QWidget):
    """
    Widget for managing marked positions.
    
    Features:
    - List of all marked positions
    - Add/remove positions
    - Edit position properties
    - Position selection for actions
    """
    
    position_selected = pyqtSignal(str)  # Emits position name
    positions_changed = pyqtSignal(dict)  # Emits updated positions dictionary
    
    def __init__(self, sequence_builder=None):
        """Initialize the position list widget."""
        super().__init__()
        self.sequence_builder = sequence_builder
        
        layout = QVBoxLayout()
        self.setLayout(layout)
        
        # Create position list
        self.list_widget = QListWidget()
        self.list_widget.itemClicked.connect(self._on_position_selected)
        layout.addWidget(QLabel("Marked Positions:"))
        layout.addWidget(self.list_widget)
        
        # Create controls
        button_layout = QHBoxLayout()
        
        self.add_button = QPushButton("Mark New Position")
        self.add_button.clicked.connect(self._on_add_clicked)
        button_layout.addWidget(self.add_button)
        
        self.remove_button = QPushButton("Remove Position")
        self.remove_button.clicked.connect(self._on_remove_clicked)
        self.remove_button.setEnabled(False)
        button_layout.addWidget(self.remove_button)
        
        layout.addLayout(button_layout)
        
        # Add position details
        details_group = QGroupBox("Position Details")
        details_layout = QVBoxLayout()
        
        self.name_edit = QLineEdit()
        self.name_edit.setPlaceholderText("Position Name")
        self.name_edit.textChanged.connect(self._on_details_changed)
        details_layout.addWidget(self.name_edit)
        
        coord_layout = QHBoxLayout()
        self.x_spin = QSpinBox()
        self.x_spin.setRange(-10000, 10000)
        self.x_spin.valueChanged.connect(self._on_details_changed)
        coord_layout.addWidget(QLabel("X:"))
        coord_layout.addWidget(self.x_spin)
        
        self.y_spin = QSpinBox()
        self.y_spin.setRange(-10000, 10000)
        self.y_spin.valueChanged.connect(self._on_details_changed)
        coord_layout.addWidget(QLabel("Y:"))
        coord_layout.addWidget(self.y_spin)
        
        details_layout.addLayout(coord_layout)
        
        self.description_edit = QLineEdit()
        self.description_edit.setPlaceholderText("Description (optional)")
        self.description_edit.textChanged.connect(self._on_details_changed)
        details_layout.addWidget(self.description_edit)
        
        details_group.setLayout(details_layout)
        layout.addWidget(details_group)
        
        # Initialize state
        self.positions: Dict[str, AutomationPosition] = {}
        self._updating_details = False
        self._current_item: Optional[QListWidgetItem] = None
        
    def set_sequence_builder(self, sequence_builder) -> None:
        """Set the sequence builder reference."""
        self.sequence_builder = sequence_builder
        
    def update_positions(self, positions: Dict[str, AutomationPosition]) -> None:
        """Update the position list with new positions."""
        self._updating_details = True  # Prevent feedback loops
        self.positions = positions.copy()  # Make a copy to prevent reference issues
        self.list_widget.clear()
        for name in sorted(positions.keys()):  # Sort names for consistent display
            self.list_widget.addItem(name)
        self._updating_details = False
        
    def _on_position_selected(self, item: QListWidgetItem) -> None:
        """Handle position selection."""
        name = item.text()
        self.remove_button.setEnabled(True)
        self.position_selected.emit(name)
        self._current_item = item
        
        # Update details
        if name in self.positions:
            pos = self.positions[name]
            self._updating_details = True
            self.name_edit.setText(name)
            self.x_spin.setValue(pos.x)
            self.y_spin.setValue(pos.y)
            self.description_edit.setText(pos.description or "")
            self._updating_details = False
            
    def _on_add_clicked(self) -> None:
        """Handle add button click."""
        # Signal that we want to start marking a position
        # The actual implementation will be in the parent widget
        self.add_button.setEnabled(False)
        
    def _on_remove_clicked(self) -> None:
        """Handle remove button click."""
        current = self.list_widget.currentItem()
        if current:
            name = current.text()
            if name in self.positions:
                del self.positions[name]
                self.update_positions(self.positions)
                self.remove_button.setEnabled(False)
                
    def _on_details_changed(self) -> None:
        """Handle changes to position details."""
        if self._updating_details:
            return
            
        current = self.list_widget.currentItem()
        if not current:
            return
            
        old_name = current.text()
        new_name = self.name_edit.text().strip()  # Strip whitespace from name
        
        if not new_name:  # Don't allow empty names
            return
            
        if old_name in self.positions:
            pos = self.positions[old_name]
            # Update position details
            pos.x = self.x_spin.value()
            pos.y = self.y_spin.value()
            pos.description = self.description_edit.text()
            
            needs_save = True
            if new_name != old_name:
                # Check if new name already exists
                if new_name in self.positions and new_name != old_name:
                    logger.warning(f"Position name '{new_name}' already exists")
                    # Revert name change
                    self._updating_details = True
                    self.name_edit.setText(old_name)
                    self._updating_details = False
                    return
                    
                # Rename position
                self.positions[new_name] = pos
                del self.positions[old_name]
                
                # Update list item text without triggering a full refresh
                self._updating_details = True
                current.setText(new_name)
                self._updating_details = False
            
            # Save positions to disk after any change
            if needs_save:
                try:
                    positions_file = Path('config/actions/positions.json')
                    positions_data = {
                        name: pos.to_dict() for name, pos in self.positions.items()
                    }
                    positions_file.parent.mkdir(parents=True, exist_ok=True)
                    with open(positions_file, 'w') as f:
                        json.dump(positions_data, f, indent=4)
                    logger.debug(f"Position details updated and saved for '{new_name}'")
                    
                    # Update sequence builder's position list
                    if self.sequence_builder:
                        self.sequence_builder.update_positions(self.positions.copy())
                    
                    # Emit positions changed signal
                    self.positions_changed.emit(self.positions.copy())
                    
                except Exception as e:
                    logger.error(f"Failed to save positions: {e}")
                    QMessageBox.critical(None, "Error", f"Failed to save position changes: {str(e)}")

class ActionListItem(QListWidgetItem):
    """List item representing an action in a sequence."""
    
    def __init__(self, action: AutomationAction):
        """Initialize the action list item."""
        super().__init__()
        self.action = action
        self.update_text()
        
    def update_text(self) -> None:
        """Update the item's display text."""
        params = self.action.params
        text = f"{self.action.action_type.name}"
        if params.position_name:
            text += f" @ {params.position_name}"
        if params.description:
            text += f" - {params.description}"
        self.setText(text)

class SequenceBuilder(QWidget):
    """
    Widget for building and editing action sequences.
    
    Features:
    - List of actions in sequence
    - Add/remove actions
    - Configure action parameters
    - Import/export sequences
    """
    
    sequence_changed = pyqtSignal()  # Emitted when sequence is modified
    sequence_execution = pyqtSignal(object, bool, float)  # sequence, simulation, delay
    execution_paused = pyqtSignal()
    execution_step = pyqtSignal()
    execution_stopped = pyqtSignal()
    
    def __init__(self):
        """Initialize the sequence builder widget."""
        super().__init__()
        
        layout = QVBoxLayout()
        self.setLayout(layout)
        
        # Add sequence name
        name_layout = QHBoxLayout()
        name_layout.addWidget(QLabel("Sequence Name:"))
        self.name_edit = QLineEdit()
        # Disconnect any existing connections first
        self.name_edit.textChanged.disconnect() if self.name_edit.receivers(self.name_edit.textChanged) > 0 else None
        # Connect with the full text, not just the changed part
        self.name_edit.textChanged.connect(lambda: self._on_sequence_changed())
        name_layout.addWidget(self.name_edit)
        layout.addLayout(name_layout)
        
        # Create sequence list
        self.list_widget = QListWidget()
        self.list_widget.currentItemChanged.connect(self._on_action_selected)
        
        # Add loop toggle button
        self.loop_btn = QPushButton("Loop Sequence: OFF")
        self.loop_btn.setCheckable(True)
        self.loop_btn.clicked.connect(self._toggle_loop)
        self.loop_btn.setStyleSheet("background-color: #8B0000; color: white; padding: 8px; font-weight: bold;")
        layout.addWidget(self.loop_btn)
        
        layout.addWidget(QLabel("Action Sequence:"))
        layout.addWidget(self.list_widget)
        
        # Create action controls
        button_layout = QHBoxLayout()
        
        self.add_button = QPushButton("Add Action")
        self.add_button.clicked.connect(self._on_add_clicked)
        button_layout.addWidget(self.add_button)
        
        self.remove_button = QPushButton("Remove Action")
        self.remove_button.clicked.connect(self._on_remove_clicked)
        self.remove_button.setEnabled(False)
        button_layout.addWidget(self.remove_button)
        
        self.move_up_button = QPushButton("Move Up")
        self.move_up_button.clicked.connect(self._on_move_up_clicked)
        self.move_up_button.setEnabled(False)
        button_layout.addWidget(self.move_up_button)
        
        self.move_down_button = QPushButton("Move Down")
        self.move_down_button.clicked.connect(self._on_move_down_clicked)
        self.move_down_button.setEnabled(False)
        button_layout.addWidget(self.move_down_button)
        
        layout.addLayout(button_layout)
        
        # Add action configuration
        config_group = QGroupBox("Action Configuration")
        config_layout = QVBoxLayout()
        
        # Action type selection
        type_layout = QHBoxLayout()
        self.type_combo = QComboBox()
        for action_type in ActionType:
            self.type_combo.addItem(action_type.name)
        self.type_combo.currentTextChanged.connect(self._on_type_changed)
        type_layout.addWidget(QLabel("Type:"))
        type_layout.addWidget(self.type_combo)
        config_layout.addLayout(type_layout)
        
        # Position selection
        self.position_combo = QComboBox()
        self.position_combo.currentTextChanged.connect(self._on_position_changed)
        config_layout.addWidget(QLabel("Position:"))
        config_layout.addWidget(self.position_combo)
        
        # Parameters (will be populated based on action type)
        self.params_widget: Optional[BaseParamsWidget] = None
        self.params_container = QWidget()
        self.params_layout = QVBoxLayout()
        self.params_container.setLayout(self.params_layout)
        config_layout.addWidget(self.params_container)
        
        config_group.setLayout(config_layout)
        layout.addWidget(config_group)
        
        # Add execution controls
        exec_group = QGroupBox("Execution Controls")
        exec_layout = QVBoxLayout()
        
        # Simulation mode
        sim_layout = QHBoxLayout()
        sim_layout.addWidget(QLabel("Simulation Mode:"))
        self.simulation_check = QCheckBox()
        sim_layout.addWidget(self.simulation_check)
        exec_layout.addLayout(sim_layout)
        
        # Step delay
        delay_layout = QHBoxLayout()
        delay_layout.addWidget(QLabel("Step Delay (s):"))
        self.delay_spin = QDoubleSpinBox()
        self.delay_spin.setRange(0.1, 10.0)
        self.delay_spin.setValue(0.5)
        delay_layout.addWidget(self.delay_spin)
        exec_layout.addLayout(delay_layout)
        
        # Control buttons
        control_layout = QHBoxLayout()
        
        self.run_button = QPushButton("Run")
        self.run_button.clicked.connect(self._on_run_clicked)
        control_layout.addWidget(self.run_button)
        
        self.pause_button = QPushButton("Pause")
        self.pause_button.clicked.connect(self._on_pause_clicked)
        self.pause_button.setEnabled(False)
        control_layout.addWidget(self.pause_button)
        
        self.step_button = QPushButton("Step")
        self.step_button.clicked.connect(self._on_step_clicked)
        self.step_button.setEnabled(False)
        control_layout.addWidget(self.step_button)
        
        self.stop_button = QPushButton("Stop")
        self.stop_button.clicked.connect(self._on_stop_clicked)
        self.stop_button.setEnabled(False)
        control_layout.addWidget(self.stop_button)
        
        exec_layout.addLayout(control_layout)
        
        # Progress label
        self.progress_label = QLabel()
        exec_layout.addWidget(self.progress_label)
        
        exec_group.setLayout(exec_layout)
        layout.addWidget(exec_group)
        
        # Add import/export buttons
        io_layout = QHBoxLayout()
        
        self.import_button = QPushButton("Import Sequence")
        self.import_button.clicked.connect(self._on_import_clicked)
        io_layout.addWidget(self.import_button)
        
        self.export_button = QPushButton("Export Sequence")
        self.export_button.clicked.connect(self._on_export_clicked)
        io_layout.addWidget(self.export_button)
        
        layout.addLayout(io_layout)
        
        # Initialize state
        self.sequence: Optional[AutomationSequence] = None
        self.positions: Dict[str, AutomationPosition] = {}
        self._updating_widgets = False
        
        # Create initial sequence
        self._new_sequence()
        
        # Create initial params widget for the default action type
        self._update_params_widget(ActionType[self.type_combo.currentText()])
        
    def _new_sequence(self) -> None:
        """Create a new empty sequence."""
        self.sequence = AutomationSequence(
            name="New Sequence",
            actions=[],
            description=None
        )
        # Update name edit with blocking signals
        self.name_edit.blockSignals(True)
        self.name_edit.setText(self.sequence.name)
        self.name_edit.blockSignals(False)
        
        self.list_widget.clear()
        self._update_buttons()
        self.sequence_changed.emit()
        logger.debug("Created new empty sequence")
        
    def update_positions(self, positions: Dict[str, AutomationPosition]) -> None:
        """Update available positions."""
        self.positions = positions
        self.position_combo.clear()
        self.position_combo.addItem("")  # Empty option
        self.position_combo.addItems(sorted(positions.keys()))
        
        # Update drag parameters widget if it exists and is of type DragParamsWidget
        if self.params_widget and isinstance(self.params_widget, DragParamsWidget):
            self.params_widget.update_positions(positions)
        
    def _on_sequence_changed(self) -> None:
        """Handle sequence changes."""
        if self._updating_widgets:
            return
            
        if self.sequence:
            # Get the full new name from the line edit
            new_name = self.name_edit.text()
            # Update sequence name
            self.sequence.name = new_name
            self.sequence_changed.emit()
            logger.debug(f"Sequence name updated to: {new_name}")
            
    def _on_action_selected(self, current: ActionListItem, previous: ActionListItem) -> None:
        """Handle action selection."""
        self._updating_widgets = True
        
        if current:
            action = current.action
            self.type_combo.setCurrentText(action.action_type.name)
            self._update_params_widget(action.action_type)
            
            if hasattr(action.params, 'position_name'):
                self.position_combo.setCurrentText(action.params.position_name or "")
            else:
                self.position_combo.setCurrentText("")
                
            if self.params_widget:
                self.params_widget.set_params(action.params)
        
        self._update_buttons()
        self._updating_widgets = False
        
    def _on_add_clicked(self) -> None:
        """Handle add action button click."""
        action_type = ActionType[self.type_combo.currentText()]
        params = self.params_widget.get_params() if self.params_widget else None
        
        if not params:
            return
            
        action = AutomationAction(action_type, params)
        item = ActionListItem(action)
        self.list_widget.addItem(item)
        self.list_widget.setCurrentItem(item)
        
        if self.sequence:
            self.sequence.actions.append(action.to_dict())
            self.sequence_changed.emit()
            
    def _on_remove_clicked(self) -> None:
        """Handle remove action button click."""
        current = self.list_widget.currentItem()
        if current:
            row = self.list_widget.row(current)
            self.list_widget.takeItem(row)
            
            if self.sequence:
                del self.sequence.actions[row]
                self.sequence_changed.emit()
                
        self._update_buttons()
        
    def _on_move_up_clicked(self) -> None:
        """Handle move up button click."""
        current = self.list_widget.currentItem()
        if not current:
            return
            
        row = self.list_widget.row(current)
        if row <= 0:
            return
            
        # Move in list widget
        self.list_widget.takeItem(row)
        self.list_widget.insertItem(row - 1, current)
        self.list_widget.setCurrentItem(current)
        
        # Move in sequence
        if self.sequence:
            action = self.sequence.actions.pop(row)
            self.sequence.actions.insert(row - 1, action)
            self.sequence_changed.emit()
            
    def _on_move_down_clicked(self) -> None:
        """Handle move down button click."""
        current = self.list_widget.currentItem()
        if not current:
            return
            
        row = self.list_widget.row(current)
        if row >= self.list_widget.count() - 1:
            return
            
        # Move in list widget
        self.list_widget.takeItem(row)
        self.list_widget.insertItem(row + 1, current)
        self.list_widget.setCurrentItem(current)
        
        # Move in sequence
        if self.sequence:
            action = self.sequence.actions.pop(row)
            self.sequence.actions.insert(row + 1, action)
            self.sequence_changed.emit()
            
    def _on_type_changed(self, action_type: str) -> None:
        """Handle action type change."""
        if self._updating_widgets:
            return
            
        self._update_params_widget(ActionType[action_type])
        self._update_current_action()
        
    def _on_position_changed(self, position_name: str) -> None:
        """Handle position selection change."""
        if self._updating_widgets:
            return
            
        self._update_current_action()
        
    def _update_params_widget(self, action_type: ActionType) -> None:
        """Update the parameter widget for the current action type."""
        # Clear existing widget
        if self.params_widget:
            self.params_widget.deleteLater()
            
        # Create new widget
        self.params_widget = create_params_widget(action_type)
        self.params_widget.params_changed.connect(self._update_current_action)
        
        # Initialize positions for drag widget
        if isinstance(self.params_widget, DragParamsWidget):
            self.params_widget.update_positions(self.positions)
            
        self.params_layout.addWidget(self.params_widget)
        
        # Update position combo enabled state
        needs_position = action_type in {
            ActionType.CLICK,
            ActionType.RIGHT_CLICK,
            ActionType.DOUBLE_CLICK,
            ActionType.DRAG,
            ActionType.TYPE_TEXT
        }
        self.position_combo.setEnabled(needs_position)
        
    def _update_current_action(self) -> None:
        """Update the current action with new parameters."""
        if self._updating_widgets:
            return
            
        current = self.list_widget.currentItem()
        if not current or not self.params_widget:
            return
            
        # Update action
        action_type = ActionType[self.type_combo.currentText()]
        params = self.params_widget.get_params()
        
        if self.position_combo.isEnabled():
            params.position_name = self.position_combo.currentText() or None
            
        current.action = AutomationAction(action_type, params)
        current.update_text()
        
        # Update sequence
        if self.sequence:
            row = self.list_widget.row(current)
            self.sequence.actions[row] = current.action.to_dict()
            self.sequence_changed.emit()
            
    def _update_buttons(self) -> None:
        """Update button enabled states."""
        has_current = self.list_widget.currentItem() is not None
        has_items = self.list_widget.count() > 0
        current_row = self.list_widget.currentRow()
        
        self.remove_button.setEnabled(has_current)
        self.move_up_button.setEnabled(has_current and current_row > 0)
        self.move_down_button.setEnabled(has_current and current_row < self.list_widget.count() - 1)
        self.export_button.setEnabled(has_items)
        
    def _on_import_clicked(self) -> None:
        """Handle import button click."""
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Import Sequence", str(Path.home()), "JSON Files (*.json)"
        )
        if not file_path:
            return
            
        try:
            with open(file_path, 'r') as f:
                data = json.load(f)
                sequence = AutomationSequence.from_dict(data)
                
            # Update UI
            self._updating_widgets = True
            self.sequence = sequence
            self.name_edit.setText(sequence.name)
            
            # Clear and rebuild list
            self.list_widget.clear()
            for action_data in sequence.actions:
                action = AutomationAction.from_dict(action_data)
                item = ActionListItem(action)
                self.list_widget.addItem(item)
                
            self._updating_widgets = False
            self.sequence_changed.emit()
            
        except Exception as e:
            logger.error(f"Failed to import sequence: {e}")
            QMessageBox.critical(self, "Import Error", str(e))
            
    def _on_export_clicked(self) -> None:
        """Handle export button click."""
        if not self.sequence or not self.sequence.actions:
            QMessageBox.warning(self, "Export Error", "No sequence to export")
            return
            
        file_path, _ = QFileDialog.getSaveFileName(
            self, "Export Sequence", str(Path.home()), "JSON Files (*.json)"
        )
        if not file_path:
            return
            
        try:
            with open(file_path, 'w') as f:
                json.dump(self.sequence.to_dict(), f, indent=4)
                
        except Exception as e:
            logger.error(f"Failed to export sequence: {e}")
            QMessageBox.critical(self, "Export Error", str(e))

    def _on_run_clicked(self) -> None:
        """Handle run button click."""
        if not self.sequence or not self.sequence.actions:
            QMessageBox.warning(self, "Run Error", "No sequence to run")
            return
            
        self.run_button.setEnabled(False)
        self.pause_button.setEnabled(True)
        self.stop_button.setEnabled(True)
        self.step_button.setEnabled(False)
        
        self.sequence_execution.emit(
            self.sequence,
            self.simulation_check.isChecked(),
            self.delay_spin.value()
        )
        
    def _on_pause_clicked(self) -> None:
        """Handle pause button click."""
        self.pause_button.setEnabled(False)
        self.step_button.setEnabled(True)
        self.execution_paused.emit()
        
    def _on_step_clicked(self) -> None:
        """Handle step button click."""
        self.execution_step.emit()
        
    def _on_stop_clicked(self) -> None:
        """Handle stop button click."""
        self.run_button.setEnabled(True)
        self.pause_button.setEnabled(False)
        self.stop_button.setEnabled(False)
        self.step_button.setEnabled(False)
        self.execution_stopped.emit()
        
    def _update_progress(self, step: int) -> None:
        """Update progress display."""
        if not self.sequence:
            return
            
        total = len(self.sequence.actions)
        self.progress_label.setText(f"Step {step + 1} of {total}")
        
    def _on_sequence_completed(self) -> None:
        """Handle sequence completion."""
        self.run_button.setEnabled(True)
        self.pause_button.setEnabled(False)
        self.stop_button.setEnabled(False)
        self.step_button.setEnabled(False)
        self.progress_label.setText("Sequence completed")
        
    def _on_execution_error(self, message: str) -> None:
        """Handle execution error."""
        self.run_button.setEnabled(True)
        self.pause_button.setEnabled(False)
        self.stop_button.setEnabled(False)
        self.step_button.setEnabled(False)
        self.progress_label.setText("Error: " + message)
        QMessageBox.critical(self, "Execution Error", message)

    def load_sequence(self, sequence: AutomationSequence) -> None:
        """
        Load a sequence into the builder.
        
        Args:
            sequence: Sequence to load
        """
        try:
            self._updating_widgets = True
            
            # Update sequence
            self.sequence = sequence
            
            # Update name edit with blocking signals to prevent feedback loop
            self.name_edit.blockSignals(True)
            self.name_edit.setText(sequence.name)
            self.name_edit.blockSignals(False)
            
            # Clear and rebuild list
            self.list_widget.clear()
            for action_data in sequence.actions:
                action = AutomationAction.from_dict(action_data)
                item = ActionListItem(action)
                self.list_widget.addItem(item)
                
            self._updating_widgets = False
            self.sequence_changed.emit()
            logger.info(f"Loaded sequence: {sequence.name}")
            
        except Exception as e:
            logger.error(f"Error loading sequence: {e}", exc_info=True)
            self._updating_widgets = False

    def update_frequency_display(self, target_freq: float, actual_freq: float) -> None:
        """Update the frequency display label."""
        logger.debug(f"Updating pattern frequency display - Target: {target_freq:.1f}, Actual: {actual_freq:.1f}")
        
        self.freq_display.setText(f"Target: {target_freq:.1f} updates/sec, Actual: {actual_freq:.1f} updates/sec")
        
        # Color code the display based on performance
        if actual_freq >= target_freq * 0.9:  # Within 90% of target
            self.freq_display.setStyleSheet("color: green;")
            logger.debug("Performance good (>90%) - display green")
        elif actual_freq >= target_freq * 0.7:  # Within 70% of target
            self.freq_display.setStyleSheet("color: orange;")
            logger.debug("Performance moderate (70-90%) - display orange")
        else:  # Below 70% of target
            self.freq_display.setStyleSheet("color: red;")
            logger.debug("Performance poor (<70%) - display red")

    def _toggle_loop(self) -> None:
        """Toggle sequence looping on/off."""
        is_active = self.loop_btn.isChecked()
        self.loop_btn.setText(f"Loop Sequence: {'ON' if is_active else 'OFF'}")
        self.loop_btn.setStyleSheet(
            f"background-color: {'#228B22' if is_active else '#8B0000'}; "
            "color: white; padding: 8px; font-weight: bold;"
        )
        logger.debug(f"Sequence looping {'enabled' if is_active else 'disabled'}")

class AutomationTab(QWidget):
    """
    Main automation tab widget.
    
    This tab provides:
    - Split view with positions and sequences
    - Position marking interface
    - Sequence building and execution
    - Import/export functionality
    """
    
    def __init__(self, window_manager, template_matcher, text_ocr, game_actions):
        """Initialize the automation tab."""
        super().__init__()
        
        # Store components
        self.window_manager = window_manager
        self.template_matcher = template_matcher
        self.text_ocr = text_ocr
        self.game_actions = game_actions
        
        # Create layout
        layout = QHBoxLayout()
        self.setLayout(layout)
        
        # Create position marker
        self.position_marker = PositionMarker(window_manager)
        self.position_marker.position_marked.connect(self._on_position_marked)
        self.position_marker.marking_cancelled.connect(self._on_marking_cancelled)  # Connect cancel signal
        
        # Create sequence builder first
        self.sequence_builder = SequenceBuilder()
        
        # Create left side (positions) with sequence builder reference
        self.position_list = PositionList(self.sequence_builder)
        self.position_list.add_button.clicked.connect(self._start_position_marking)
        layout.addWidget(self.position_list, stretch=1)
        
        # Add separator
        separator = QFrame()
        separator.setFrameShape(QFrame.Shape.VLine)
        separator.setFrameShadow(QFrame.Shadow.Sunken)
        layout.addWidget(separator)
        
        # Add sequence builder to layout
        layout.addWidget(self.sequence_builder, stretch=2)
        
        # Create debug window
        from scout.automation.gui.debug_window import AutomationDebugWindow
        self.debug_window = AutomationDebugWindow()
        
        # Add debug button
        debug_button = QPushButton("Show Debug Window")
        debug_button.clicked.connect(self._on_debug_clicked)
        layout.addWidget(debug_button)
        
        # Create sequence executor
        self.executor = None  # Will be created when needed
        
        # Connect signals
        self.position_list.position_selected.connect(self._on_position_selected)
        self.sequence_builder.sequence_changed.connect(self._on_sequence_changed)
        self.sequence_builder.sequence_execution.connect(self._on_sequence_execution)
        self.sequence_builder.execution_paused.connect(self._on_execution_paused)
        self.sequence_builder.execution_step.connect(self._on_execution_step)
        self.sequence_builder.execution_stopped.connect(self._on_execution_stopped)
        
        # Load saved positions and sequences
        self._load_saved_data()
        
    def _load_saved_data(self) -> None:
        """Load saved positions and sequences from disk."""
        try:
            # Create actions directory if it doesn't exist
            actions_dir = Path('config/actions')
            actions_dir.mkdir(parents=True, exist_ok=True)
            
            # Load positions
            positions_file = actions_dir / 'positions.json'
            if positions_file.exists():
                with open(positions_file, 'r') as f:
                    positions_data = json.load(f)
                    positions = {
                        name: AutomationPosition.from_dict(data)
                        for name, data in positions_data.items()
                    }
                    self.position_list.update_positions(positions)
                    self.sequence_builder.update_positions(positions)
                    logger.info(f"Loaded {len(positions)} positions")
            
            # Load current sequence
            current_sequence_file = actions_dir / 'current_sequence.json'
            if current_sequence_file.exists():
                with open(current_sequence_file, 'r') as f:
                    sequence_data = json.load(f)
                    sequence = AutomationSequence.from_dict(sequence_data)
                    self.sequence_builder.load_sequence(sequence)
                    logger.info(f"Loaded current sequence: {sequence.name}")
                    
        except Exception as e:
            logger.error(f"Error loading saved data: {e}", exc_info=True)
            
    def _save_current_sequence(self) -> None:
        """Save the current sequence to disk."""
        try:
            if not self.sequence_builder.sequence:
                return
                
            # Ensure directory exists
            actions_dir = Path('config/actions')
            actions_dir.mkdir(parents=True, exist_ok=True)
            
            # Save current sequence
            current_sequence_file = actions_dir / 'current_sequence.json'
            with open(current_sequence_file, 'w') as f:
                json.dump(self.sequence_builder.sequence.to_dict(), f, indent=4)
                
            logger.info(f"Saved current sequence: {self.sequence_builder.sequence.name}")
            
        except Exception as e:
            logger.error(f"Error saving current sequence: {e}", exc_info=True)
            
    def _on_sequence_changed(self) -> None:
        """Handle sequence changes."""
        self._save_current_sequence()
        
    def _on_position_marked(self, point) -> None:
        """Handle new position being marked."""
        try:
            # Create new position with default name
            name = f"Position_{len(self.position_list.positions) + 1}"
            position = AutomationPosition(name, point.x(), point.y())
            
            # Add to list and update UI
            self.position_list.positions[name] = position
            self.position_list.update_positions(self.position_list.positions)
            self.sequence_builder.update_positions(self.position_list.positions)
            
            # Stop marking and re-enable button
            self.position_marker.stop_marking()
            self.position_list.add_button.setEnabled(True)
            
            # Update debug window
            self.debug_window.update_positions(self.position_list.positions)
            
            # Save positions
            positions_file = Path('config/actions/positions.json')
            positions_data = {
                name: pos.to_dict() for name, pos in self.position_list.positions.items()
            }
            positions_file.parent.mkdir(parents=True, exist_ok=True)  # Ensure directory exists
            with open(positions_file, 'w') as f:
                json.dump(positions_data, f, indent=4)
                
            logger.info(f"Saved position {name} at ({point.x()}, {point.y()})")
            
        except Exception as e:
            logger.error(f"Error saving position: {e}", exc_info=True)
            self.position_list.add_button.setEnabled(True)
            self.position_marker.stop_marking()  # Ensure overlay is cleaned up
            QMessageBox.critical(self, "Error", f"Failed to save position: {str(e)}")

    def _on_debug_clicked(self) -> None:
        """Show or hide the debug window."""
        if self.debug_window.isVisible():
            self.debug_window.hide()
        else:
            self.debug_window.show()
            
    def _on_position_selected(self, name: str) -> None:
        """Handle position selection."""
        # Update sequence builder with selected position
        pass
        
    def _on_sequence_execution(self, sequence: AutomationSequence, simulation: bool, delay: float) -> None:
        """Handle sequence execution request."""
        # Create executor if needed
        if not self.executor:
            context = ExecutionContext(
                positions=self.position_list.positions,
                window_manager=self.window_manager,
                template_matcher=self.template_matcher,
                text_ocr=self.text_ocr,
                game_actions=self.game_actions,
                debug_tab=self.debug_window.execution_tab,
                simulation_mode=simulation,
                step_delay=delay,
                loop_enabled=self.sequence_builder.loop_btn.isChecked()  # Pass loop state
            )
            self.executor = SequenceExecutor(context)
            
            # Connect signals
            self.executor.step_completed.connect(self.sequence_builder._update_progress)
            self.executor.sequence_completed.connect(self.sequence_builder._on_sequence_completed)
            self.executor.execution_error.connect(self.sequence_builder._on_execution_error)
            
            # Connect debug signals
            self.executor.step_completed.connect(self._update_debug_state)
            
        # Update executor settings
        self.executor.context.simulation_mode = simulation
        self.executor.context.step_delay = delay
        self.executor.context.loop_enabled = self.sequence_builder.loop_btn.isChecked()  # Update loop state
        
        # Clear debug window
        self.debug_window.clear_log()
        
        # Start execution
        self.executor.execute_sequence(sequence)
        
    def _on_execution_paused(self) -> None:
        """Handle execution pause request."""
        if self.executor:
            self.executor.pause_execution()
            self.debug_window.set_execution_paused(True)
            
    def _on_execution_step(self) -> None:
        """Handle execution step request."""
        if self.executor:
            self.executor.step_execution()
            
    def _on_execution_stopped(self) -> None:
        """Handle execution stop request."""
        if self.executor:
            self.executor.stop_execution()
            self.debug_window.set_execution_paused(False)
            
    def _update_debug_state(self, step: int) -> None:
        """Update debug window with current execution state."""
        if not self.executor or not self.executor.current_sequence:
            return
            
        # Take screenshot
        screenshot = self.window_manager.capture_screenshot()
        if screenshot is not None:
            self.debug_window.update_preview(screenshot)
            
        # Update status
        total_steps = len(self.executor.current_sequence.actions)
        self.debug_window.update_status(f"Step {step + 1} of {total_steps}")
        
        # Get current action
        action_data = self.executor.current_sequence.actions[step]
        action = AutomationAction.from_dict(action_data)
        
        # Update template matches if searching for templates
        if action.action_type == ActionType.TEMPLATE_SEARCH:
            if screenshot is not None:
                matches = self.template_matcher.find_all_templates(screenshot)
                self.debug_window.update_template_matches(matches)
                
        # Update OCR text if waiting for text
        elif action.action_type == ActionType.WAIT_FOR_OCR:
            if screenshot is not None:
                text = self.text_ocr.extract_text(screenshot)
                regions = self.text_ocr.get_text_regions(screenshot)
                self.debug_window.update_ocr_text(text, regions)
                
        # Update mouse position for mouse actions
        elif action.action_type in {
            ActionType.CLICK,
            ActionType.RIGHT_CLICK,
            ActionType.DOUBLE_CLICK,
            ActionType.DRAG,
            ActionType.TYPE_TEXT
        }:
            if hasattr(action.params, 'position_name'):
                position = self.position_list.positions.get(action.params.position_name)
                if position:
                    self.debug_window.update_mouse_position(position.x, position.y)

    def _start_position_marking(self) -> None:
        """Start the position marking process."""
        logger.info("Starting position marking")
        try:
            # First check if we can find the game window
            if not self.window_manager.find_window():
                logger.error("Could not find game window - aborting position marking")
                self.position_list.add_button.setEnabled(True)
                QMessageBox.warning(self, "Error", "Could not find game window")
                return
                
            # Get window position to verify we can get coordinates
            if not self.window_manager.get_window_position():
                logger.error("Could not get window position - aborting position marking")
                self.position_list.add_button.setEnabled(True)
                QMessageBox.warning(self, "Error", "Could not get window position")
                return
                
            # Show instructions before starting marking mode
            msg = QMessageBox(self)
            msg.setWindowTitle("Mark Position")
            msg.setText("Click anywhere on the game window to mark a position.\n"
                       "The overlay will show with a slight tint to help you see it.\n\n"
                       "Press ESC to cancel marking.")
            msg.setIcon(QMessageBox.Icon.Information)
            msg.setStandardButtons(QMessageBox.StandardButton.Ok | QMessageBox.StandardButton.Cancel)
            
            # Show message box and wait for response
            response = msg.exec()
            
            if response == QMessageBox.StandardButton.Ok:
                # Start marking mode after user acknowledges instructions
                self.position_marker.start_marking()
            else:
                # User closed or cancelled the message box, re-enable the button
                self.position_list.add_button.setEnabled(True)
            
        except Exception as e:
            logger.error(f"Error starting position marking: {e}", exc_info=True)
            self.position_list.add_button.setEnabled(True)
            self.position_marker.stop_marking()  # Ensure overlay is cleaned up
            QMessageBox.critical(self, "Error", f"Failed to start position marking: {str(e)}")

    def create_scan_controls(self, layout: QVBoxLayout) -> None:
        """
        Create controls for automation and OCR functionality.
        
        This method sets up:
        1. Automation controls (sequence execution)
        2. OCR controls (toggle button, frequency slider, region selection)
        
        Args:
            layout: Parent layout to add controls to
        """
        # Get OCR settings from config manager
        config = ConfigManager()
        ocr_settings = config.get_ocr_settings()
        
        # Create group box for automation
        automation_group = QGroupBox("Automation")
        automation_layout = QVBoxLayout()
        
        # Create sequence execution button
        self.sequence_btn = QPushButton("Start Sequence")
        self.sequence_btn.setCheckable(True)
        self.sequence_btn.clicked.connect(self._toggle_sequence)
        automation_layout.addWidget(self.sequence_btn)
        
        # Create sequence status label
        self.sequence_status = QLabel("Sequence: Inactive")
        automation_layout.addWidget(self.sequence_status)
        
        automation_group.setLayout(automation_layout)
        layout.addWidget(automation_group)
        
        # Create group box for OCR
        ocr_group = QGroupBox("Text OCR")
        ocr_layout = QVBoxLayout()
        
        # Create OCR toggle button
        self.ocr_btn = QPushButton("Start Text OCR")
        self.ocr_btn.setCheckable(True)
        self.ocr_btn.clicked.connect(self._toggle_ocr)
        ocr_layout.addWidget(self.ocr_btn)
        
        # Create OCR frequency controls
        freq_layout = QVBoxLayout()  # Changed to vertical layout
        
        # Create horizontal layout for slider and spinbox
        freq_controls = QHBoxLayout()
        freq_label = QLabel("OCR Frequency:")
        freq_controls.addWidget(freq_label)
        
        # Add range label
        range_label = QLabel("(0.1 - 2.0 updates/sec)")
        range_label.setStyleSheet("QLabel { color: gray; }")
        freq_controls.addWidget(range_label)
        
        # Slider for frequency
        self.ocr_freq_slider = QSlider(Qt.Orientation.Horizontal)
        self.ocr_freq_slider.setMinimum(1)  # 0.1 updates/sec
        self.ocr_freq_slider.setMaximum(20)  # 2.0 updates/sec
        self.ocr_freq_slider.setValue(int(ocr_settings['frequency'] * 10))
        self.ocr_freq_slider.valueChanged.connect(self.on_ocr_slider_change)
        freq_controls.addWidget(self.ocr_freq_slider)
        
        # Create spinbox for precise input
        self.ocr_freq_input = QDoubleSpinBox()
        self.ocr_freq_input.setMinimum(0.1)
        self.ocr_freq_input.setMaximum(2.0)
        self.ocr_freq_input.setSingleStep(0.1)
        self.ocr_freq_input.setValue(ocr_settings['frequency'])
        self.ocr_freq_input.valueChanged.connect(self.on_ocr_spinbox_change)
        freq_controls.addWidget(self.ocr_freq_input)
        
        ocr_layout.addLayout(freq_layout)
        
        # Create OCR region selection button
        self.select_ocr_region_btn = QPushButton("Select OCR Region")
        self.select_ocr_region_btn.clicked.connect(self._start_ocr_region_selection)
        ocr_layout.addWidget(self.select_ocr_region_btn)
        
        # Create OCR status label with coordinates
        self.ocr_status = QLabel("Text OCR: Inactive")
        self.ocr_coords_label = QLabel("Coordinates: None")
        self.ocr_coords_label.setStyleSheet("font-family: monospace;")  # For better alignment
        ocr_layout.addWidget(self.ocr_status)
        ocr_layout.addWidget(self.ocr_coords_label)
        
        ocr_group.setLayout(ocr_layout)
        layout.addWidget(ocr_group)

    def _toggle_sequence(self) -> None:
        """Toggle sequence execution."""
        if self.sequence_btn.isChecked():
            self.start_sequence()
        else:
            self.stop_sequence()
            
    def start_sequence(self) -> None:
        """Start sequence execution."""
        if not self.sequence_builder.sequence:
            QMessageBox.warning(self, "Error", "No sequence loaded")
            self.sequence_btn.setChecked(False)
            return
            
        self.sequence_btn.setText("Stop Sequence")
        self.sequence_status.setText("Sequence: Active")
        
        # Start sequence execution
        self.sequence_builder._on_run_clicked()
        
    def stop_sequence(self) -> None:
        """Stop sequence execution."""
        self.sequence_btn.setText("Start Sequence")
        self.sequence_status.setText("Sequence: Inactive")
        
        # Stop sequence execution
        self.sequence_builder._on_stop_clicked()

    def _on_marking_cancelled(self) -> None:
        """Handle position marking being cancelled."""
        logger.debug("Position marking cancelled")
        self.position_list.add_button.setEnabled(True)