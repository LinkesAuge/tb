"""
Automation Tab

This module provides the main tab interface for the automation system in the Scout application.
It allows users to create, edit, run, and manage automation sequences.
"""

import logging
import os
import time  # Add import for time module
from typing import Dict, List, Optional, Tuple, Any, Callable

from PyQt6.QtCore import Qt, pyqtSignal, QTimer
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, 
    QComboBox, QListWidget, QListWidgetItem, QSplitter, 
    QCheckBox, QSpinBox, QGroupBox, QMessageBox, QFileDialog
)

from scout.automation.core import AutomationCore
from scout.automation.sequence import AutomationSequence, SequenceManager
from scout.automation.executor import SequenceExecutor
from scout.automation.progress_tracker import ExecutionStats
from scout.automation.gui.sequence_builder import SequenceBuilderDialog
from scout.utils.logging_utils import get_logger

logger = get_logger(__name__)

class AutomationTab(QWidget):
    """
    Main tab for automation functionality.
    
    This tab provides a user interface for:
    - Selecting and running automation sequences
    - Creating and editing sequences
    - Monitoring execution progress
    - Importing and exporting sequences
    """
    
    # Signals
    sequence_selected = pyqtSignal(str)
    sequence_started = pyqtSignal(str)
    sequence_stopped = pyqtSignal()
    
    def __init__(
        self, 
        automation_core: AutomationCore,
        executor: SequenceExecutor,
        parent: Optional[QWidget] = None
    ):
        """
        Initialize the automation tab.
        
        Args:
            automation_core: The automation core instance
            executor: The sequence executor instance
            parent: Parent widget
        """
        super().__init__(parent)
        self.automation_core = automation_core
        self.sequence_manager = automation_core.sequence_manager
        self.executor = executor
        
        # Connect to executor signals
        self.executor.step_completed.connect(self._on_step_completed)
        self.executor.sequence_completed.connect(self._on_execution_completed)
        self.executor.execution_progress.connect(self._on_execution_progress)
        
        # Setup UI
        self._setup_ui()
        
        # Refresh sequence list
        self._refresh_sequence_list()
        
        # Setup timer for periodic UI updates
        self.update_timer = QTimer(self)
        self.update_timer.timeout.connect(self._update_status)
        self.update_timer.start(500)  # Update every 500ms
    
    def _setup_ui(self) -> None:
        """Set up the user interface."""
        main_layout = QVBoxLayout(self)
        
        # Create splitter for resizable sections
        splitter = QSplitter(Qt.Orientation.Vertical)
        main_layout.addWidget(splitter)
        
        # Top section - Sequence selection and controls
        top_widget = QWidget()
        top_layout = QVBoxLayout(top_widget)
        
        # Sequence selection
        sequence_group = QGroupBox("Automation Sequences")
        sequence_layout = QVBoxLayout(sequence_group)
        
        # Sequence list
        self.sequence_list = QListWidget()
        self.sequence_list.setMinimumHeight(150)
        self.sequence_list.itemSelectionChanged.connect(self._on_sequence_selected)
        sequence_layout.addWidget(self.sequence_list)
        
        # Sequence buttons
        sequence_buttons = QHBoxLayout()
        
        self.new_btn = QPushButton("New")
        self.new_btn.clicked.connect(self._on_new_sequence)
        sequence_buttons.addWidget(self.new_btn)
        
        self.edit_btn = QPushButton("Edit")
        self.edit_btn.clicked.connect(self._on_edit_sequence)
        self.edit_btn.setEnabled(False)
        sequence_buttons.addWidget(self.edit_btn)
        
        self.delete_btn = QPushButton("Delete")
        self.delete_btn.clicked.connect(self._on_delete_sequence)
        self.delete_btn.setEnabled(False)
        sequence_buttons.addWidget(self.delete_btn)
        
        self.duplicate_btn = QPushButton("Duplicate")
        self.duplicate_btn.clicked.connect(self._on_duplicate_sequence)
        self.duplicate_btn.setEnabled(False)
        sequence_buttons.addWidget(self.duplicate_btn)
        
        sequence_layout.addLayout(sequence_buttons)
        
        # Import/Export buttons
        import_export_layout = QHBoxLayout()
        
        self.import_btn = QPushButton("Import")
        self.import_btn.clicked.connect(self._on_import_sequences)
        import_export_layout.addWidget(self.import_btn)
        
        self.export_btn = QPushButton("Export")
        self.export_btn.clicked.connect(self._on_export_sequences)
        import_export_layout.addWidget(self.export_btn)
        
        sequence_layout.addLayout(import_export_layout)
        
        top_layout.addWidget(sequence_group)
        
        # Execution controls
        execution_group = QGroupBox("Execution Controls")
        execution_layout = QVBoxLayout(execution_group)
        
        # Execution options
        options_layout = QHBoxLayout()
        
        self.loop_checkbox = QCheckBox("Loop Sequence")
        options_layout.addWidget(self.loop_checkbox)
        
        delay_layout = QHBoxLayout()
        delay_layout.addWidget(QLabel("Step Delay:"))
        self.delay_spinbox = QSpinBox()
        self.delay_spinbox.setRange(0, 5000)
        self.delay_spinbox.setSingleStep(50)
        self.delay_spinbox.setValue(200)
        self.delay_spinbox.setSuffix(" ms")
        delay_layout.addWidget(self.delay_spinbox)
        options_layout.addLayout(delay_layout)
        
        execution_layout.addLayout(options_layout)
        
        # Execution buttons
        execution_buttons = QHBoxLayout()
        
        self.run_btn = QPushButton("Run")
        self.run_btn.clicked.connect(self._on_run_sequence)
        self.run_btn.setEnabled(False)
        execution_buttons.addWidget(self.run_btn)
        
        self.pause_btn = QPushButton("Pause")
        self.pause_btn.clicked.connect(self._on_pause_sequence)
        self.pause_btn.setEnabled(False)
        execution_buttons.addWidget(self.pause_btn)
        
        self.step_btn = QPushButton("Step")
        self.step_btn.clicked.connect(self._on_step_sequence)
        self.step_btn.setEnabled(False)
        execution_buttons.addWidget(self.step_btn)
        
        self.stop_btn = QPushButton("Stop")
        self.stop_btn.clicked.connect(self._on_stop_sequence)
        self.stop_btn.setEnabled(False)
        execution_buttons.addWidget(self.stop_btn)
        
        execution_layout.addLayout(execution_buttons)
        
        top_layout.addWidget(execution_group)
        
        # Add top widget to splitter
        splitter.addWidget(top_widget)
        
        # Bottom section - Execution status and logs
        bottom_widget = QWidget()
        bottom_layout = QVBoxLayout(bottom_widget)
        
        # Status section
        status_group = QGroupBox("Execution Status")
        status_layout = QVBoxLayout(status_group)
        
        # Status labels
        self.status_label = QLabel("Ready")
        status_layout.addWidget(self.status_label)
        
        self.progress_label = QLabel("No sequence running")
        status_layout.addWidget(self.progress_label)
        
        self.stats_label = QLabel("")
        status_layout.addWidget(self.stats_label)
        
        bottom_layout.addWidget(status_group)
        
        # Log section
        log_group = QGroupBox("Execution Log")
        log_layout = QVBoxLayout(log_group)
        
        self.log_list = QListWidget()
        self.log_list.setMinimumHeight(150)
        log_layout.addWidget(self.log_list)
        
        clear_log_btn = QPushButton("Clear Log")
        clear_log_btn.clicked.connect(self.log_list.clear)
        log_layout.addWidget(clear_log_btn)
        
        bottom_layout.addWidget(log_group)
        
        # Add bottom widget to splitter
        splitter.addWidget(bottom_widget)
        
        # Set initial splitter sizes
        splitter.setSizes([300, 200])
    
    def _refresh_sequence_list(self) -> None:
        """Refresh the list of available sequences."""
        self.sequence_list.clear()
        
        sequences = self.sequence_manager.get_all_sequences()
        for sequence in sorted(sequences, key=lambda s: s.name):
            item = QListWidgetItem(sequence.name)
            item.setData(Qt.ItemDataRole.UserRole, sequence.name)
            self.sequence_list.addItem(item)
    
    def _on_sequence_selected(self) -> None:
        """Handle sequence selection."""
        selected_items = self.sequence_list.selectedItems()
        has_selection = len(selected_items) > 0
        
        self.edit_btn.setEnabled(has_selection)
        self.delete_btn.setEnabled(has_selection)
        self.duplicate_btn.setEnabled(has_selection)
        self.run_btn.setEnabled(has_selection and not self.executor.is_running)
        
        if has_selection:
            sequence_name = selected_items[0].data(Qt.ItemDataRole.UserRole)
            self.sequence_selected.emit(sequence_name)
    
    def _on_new_sequence(self) -> None:
        """Create a new sequence."""
        dialog = SequenceBuilderDialog(self.sequence_manager, parent=self)
        if dialog.exec():
            self._refresh_sequence_list()
    
    def _on_edit_sequence(self) -> None:
        """Edit the selected sequence."""
        selected_items = self.sequence_list.selectedItems()
        if not selected_items:
            return
            
        sequence_name = selected_items[0].data(Qt.ItemDataRole.UserRole)
        sequence = self.sequence_manager.get_sequence(sequence_name)
        
        if not sequence:
            QMessageBox.warning(self, "Error", f"Sequence '{sequence_name}' not found.")
            return
            
        dialog = SequenceBuilderDialog(
            self.sequence_manager, 
            sequence_name=sequence_name,
            parent=self
        )
        if dialog.exec():
            self._refresh_sequence_list()
    
    def _on_delete_sequence(self) -> None:
        """Delete the selected sequence."""
        selected_items = self.sequence_list.selectedItems()
        if not selected_items:
            return
            
        sequence_name = selected_items[0].data(Qt.ItemDataRole.UserRole)
        
        reply = QMessageBox.question(
            self, 
            "Confirm Deletion",
            f"Are you sure you want to delete the sequence '{sequence_name}'?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            self.sequence_manager.delete_sequence(sequence_name)
            self._refresh_sequence_list()
    
    def _on_duplicate_sequence(self) -> None:
        """Duplicate the selected sequence."""
        selected_items = self.sequence_list.selectedItems()
        if not selected_items:
            return
            
        sequence_name = selected_items[0].data(Qt.ItemDataRole.UserRole)
        sequence = self.sequence_manager.get_sequence(sequence_name)
        
        if not sequence:
            QMessageBox.warning(self, "Error", f"Sequence '{sequence_name}' not found.")
            return
            
        # Create a new name for the duplicated sequence
        new_name = f"{sequence_name} (Copy)"
        i = 1
        while self.sequence_manager.get_sequence(new_name):
            i += 1
            new_name = f"{sequence_name} (Copy {i})"
        
        # Create a duplicate sequence
        new_sequence = AutomationSequence(
            name=new_name,
            actions=sequence.actions.copy()
        )
        
        # Add the new sequence
        self.sequence_manager.add_sequence(new_sequence)
        self._refresh_sequence_list()
        
        # Select the new sequence
        for i in range(self.sequence_list.count()):
            item = self.sequence_list.item(i)
            if item.data(Qt.ItemDataRole.UserRole) == new_name:
                self.sequence_list.setCurrentItem(item)
                break
    
    def _on_import_sequences(self) -> None:
        """Import sequences from a file."""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Import Sequences",
            "",
            "JSON Files (*.json);;All Files (*)"
        )
        
        if not file_path:
            return
            
        try:
            success = self.sequence_manager.load_from_file(file_path)
            if success:
                self._refresh_sequence_list()
                QMessageBox.information(
                    self,
                    "Import Successful",
                    "Sequences imported successfully."
                )
            else:
                QMessageBox.warning(
                    self,
                    "Import Failed",
                    "Failed to import sequences from the selected file."
                )
        except Exception as e:
            QMessageBox.critical(
                self,
                "Import Error",
                f"An error occurred while importing sequences: {str(e)}"
            )
    
    def _on_export_sequences(self) -> None:
        """Export sequences to a file."""
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "Export Sequences",
            "",
            "JSON Files (*.json);;All Files (*)"
        )
        
        if not file_path:
            return
            
        # Add .json extension if not present
        if not file_path.lower().endswith('.json'):
            file_path += '.json'
            
        try:
            success = self.sequence_manager.save_to_file(file_path)
            if success:
                QMessageBox.information(
                    self,
                    "Export Successful",
                    "Sequences exported successfully."
                )
            else:
                QMessageBox.warning(
                    self,
                    "Export Failed",
                    "Failed to export sequences to the selected file."
                )
        except Exception as e:
            QMessageBox.critical(
                self,
                "Export Error",
                f"An error occurred while exporting sequences: {str(e)}"
            )
    
    def _on_run_sequence(self) -> None:
        """Run the selected sequence."""
        selected_items = self.sequence_list.selectedItems()
        if not selected_items:
            return
            
        sequence_name = selected_items[0].data(Qt.ItemDataRole.UserRole)
        
        # Configure execution options
        self.executor.context.loop_enabled = self.loop_checkbox.isChecked()
        self.executor.context.step_delay = self.delay_spinbox.value() / 1000.0  # Convert ms to seconds
        
        # Start execution
        success = self.executor.execute_sequence(sequence_name)
        
        if success:
            self.sequence_started.emit(sequence_name)
            self._update_ui_for_running_state()
            self._add_log_message(f"Started execution of sequence '{sequence_name}'")
        else:
            QMessageBox.warning(
                self,
                "Execution Failed",
                f"Failed to start execution of sequence '{sequence_name}'."
            )
    
    def _on_pause_sequence(self) -> None:
        """Pause or resume the current sequence."""
        if not self.executor.is_running:
            return
            
        if self.executor.is_paused:
            # Resume execution
            self.executor.resume_execution()
            self.pause_btn.setText("Pause")
            self._add_log_message("Resumed execution")
        else:
            # Pause execution
            self.executor.pause_execution()
            self.pause_btn.setText("Resume")
            self._add_log_message("Paused execution")
            
        self._update_ui_for_running_state()
    
    def _on_step_sequence(self) -> None:
        """Execute a single step while paused."""
        if not self.executor.is_running or not self.executor.is_paused:
            return
            
        self.executor.step_execution()
        self._add_log_message("Executed single step")
    
    def _on_stop_sequence(self) -> None:
        """Stop the current sequence."""
        if not self.executor.is_running:
            return
            
        self.executor.stop_execution()
        self.sequence_stopped.emit()
        self._update_ui_for_stopped_state()
        self._add_log_message("Stopped execution")
    
    def _on_step_completed(self, step_index: int) -> None:
        """
        Handle step completion.
        
        Args:
            step_index: Index of the completed step
        """
        # This method is called when a step is completed
        # We'll update the UI in the _update_status method
        pass
    
    def _on_execution_completed(self) -> None:
        """
        Handle sequence completion.
        """
        if not self.executor.context.loop_enabled:
            self._update_ui_for_stopped_state()
            
        self._add_log_message(f"Sequence completed")
    
    def _on_execution_progress(self, current_step: int, total_steps: int) -> None:
        """
        Handle execution progress updates.
        
        Args:
            current_step: Current step index (1-based)
            total_steps: Total number of steps
        """
        # This method is called when execution progress is updated
        # We'll update the UI in the _update_status method
        pass
    
    def _update_ui_for_running_state(self) -> None:
        """Update UI elements for the running state."""
        is_running = self.executor.is_running
        is_paused = self.executor.is_paused
        
        # Update button states
        self.run_btn.setEnabled(not is_running)
        self.pause_btn.setEnabled(is_running)
        self.step_btn.setEnabled(is_running and is_paused)
        self.stop_btn.setEnabled(is_running)
        
        # Update other UI elements
        self.new_btn.setEnabled(not is_running)
        self.edit_btn.setEnabled(not is_running and len(self.sequence_list.selectedItems()) > 0)
        self.delete_btn.setEnabled(not is_running and len(self.sequence_list.selectedItems()) > 0)
        self.duplicate_btn.setEnabled(not is_running and len(self.sequence_list.selectedItems()) > 0)
        self.import_btn.setEnabled(not is_running)
        self.export_btn.setEnabled(not is_running)
        
        # Update pause button text
        self.pause_btn.setText("Resume" if is_paused else "Pause")
    
    def _update_ui_for_stopped_state(self) -> None:
        """Update UI elements for the stopped state."""
        # Update button states
        self.run_btn.setEnabled(len(self.sequence_list.selectedItems()) > 0)
        self.pause_btn.setEnabled(False)
        self.step_btn.setEnabled(False)
        self.stop_btn.setEnabled(False)
        
        # Update other UI elements
        self.new_btn.setEnabled(True)
        self.edit_btn.setEnabled(len(self.sequence_list.selectedItems()) > 0)
        self.delete_btn.setEnabled(len(self.sequence_list.selectedItems()) > 0)
        self.duplicate_btn.setEnabled(len(self.sequence_list.selectedItems()) > 0)
        self.import_btn.setEnabled(True)
        self.export_btn.setEnabled(True)
        
        # Reset pause button text
        self.pause_btn.setText("Pause")
    
    def _update_status(self) -> None:
        """Update status display with current execution information."""
        if not self.executor.is_running:
            self.status_label.setText("Ready")
            self.progress_label.setText("No sequence running")
            self.stats_label.setText("")
            return
            
        # Get current sequence and step
        sequence_name = self.executor.current_sequence.name if self.executor.current_sequence else "Unknown"
        current_step = self.executor.current_step + 1  # Convert to 1-based index
        total_steps = len(self.executor.current_sequence.actions) if self.executor.current_sequence else 0
        
        # Update status label
        status = "Paused" if self.executor.is_paused else "Running"
        self.status_label.setText(f"Status: {status}")
        
        # Update progress label
        self.progress_label.setText(
            f"Executing: {sequence_name} - Step {current_step}/{total_steps} "
            f"({current_step/total_steps*100:.1f}%)"
        )
        
        # Update stats if available
        stats = self.executor.progress_tracker.current_stats
        if stats:
            elapsed = time.time() - stats.start_time
            self.stats_label.setText(
                f"Elapsed: {elapsed:.1f}s - "
                f"Success: {stats.success_count}/{stats.completed_actions} "
                f"({stats.success_rate:.1f}%)"
            )
    
    def _add_log_message(self, message: str) -> None:
        """
        Add a message to the log list.
        
        Args:
            message: Message to add
        """
        self.log_list.addItem(message)







