"""
Automation Core

This module serves as the central component of the automation system,
integrating position management, sequence handling, execution context,
progress tracking, and action execution.
"""

import logging
import time
import json
from typing import Dict, List, Optional, Tuple, Any, Callable

from .position import Position, PositionManager
from .sequence import AutomationSequence, SequenceManager
from .context import ExecutionContext
from .progress_tracker import ProgressTracker
from .actions import (
    ActionType, AutomationAction
)
from .action_handlers_basic import BasicActionHandlers
from .action_handlers_flow import FlowActionHandlers
from .action_handlers_advanced_flow import AdvancedFlowActionHandlers
from .action_handlers_data import DataActionHandlers
from .action_handlers_visual import VisualActionHandlers

logger = logging.getLogger(__name__)

class AutomationCore:
    """
    Core automation system that integrates all automation components.
    
    This class serves as the main interface for the automation system,
    providing methods for managing positions, sequences, and execution.
    """
    
    def __init__(self, window_manager, template_matcher, text_ocr,
                game_actions, template_search, signal_bus):
        """
        Initialize the automation core.
        
        Args:
            window_manager: Window manager to get window information
            template_matcher: Template matcher for visual recognition
            text_ocr: Text OCR for text recognition
            game_actions: Game-specific action implementation
            template_search: Template search functionality
            signal_bus: Signal bus for event communication
        """
        logger.info("Initializing automation core")
        
        # Store provided components
        self.window_manager = window_manager
        self.template_matcher = template_matcher
        self.text_ocr = text_ocr
        self.game_actions = game_actions
        self.template_search = template_search
        self.signal_bus = signal_bus
        
        # Initialize managers
        self.position_manager = PositionManager()
        self.sequence_manager = SequenceManager()
        self.progress_tracker = ProgressTracker()
        
        # Create a log callback function
        def log_callback(message):
            """Callback function for action handlers to log messages"""
            logger.info(f"Automation: {message}")
        
        # Create an execute action callback function for nested actions
        def execute_action_callback(action, simulate, variable_store):
            """Callback function for executing nested actions"""
            logger.debug(f"Executing nested action: {action.action_type}")
            return self.execute_action(action, simulate, variable_store)
            
        # Initialize action handlers
        self.basic_handlers = BasicActionHandlers(self, log_callback)
        self.flow_handlers = FlowActionHandlers(self, log_callback, execute_action_callback)
        self.advanced_flow_handlers = AdvancedFlowActionHandlers(self, log_callback, execute_action_callback)
        self.data_handlers = DataActionHandlers(self, log_callback)
        self.visual_handlers = VisualActionHandlers(self, log_callback)
        
        # Execution state
        self.is_executing = False
        self.current_sequence = None
        self.execution_context = None
        self.pause_requested = False
        self.stop_requested = False
        
        # Event handlers
        self._on_sequence_complete_handlers = []
        self._on_progress_handlers = []
        
        logger.info("Automation core initialized")
    
    def _log_callback(self, message: str) -> None:
        """
        Log a message to the debug tab if available.
        
        Args:
            message: Message to log
        """
        logger.debug(message)
        if self.debug_tab:
            self.debug_tab.log_message(message)
    
    def register_on_sequence_complete(self, handler: Callable[[str, bool], None]) -> None:
        """
        Register a handler for sequence completion events.
        
        Args:
            handler: Function to call when a sequence completes.
                     Takes sequence_name and success flag as arguments.
        """
        self._on_sequence_complete_handlers.append(handler)
    
    def _on_sequence_complete(self, sequence_name: str, success: bool) -> None:
        """
        Call all registered sequence completion handlers.
        
        Args:
            sequence_name: Name of the completed sequence
            success: Whether the sequence completed successfully
        """
        for handler in self._on_sequence_complete_handlers:
            try:
                handler(sequence_name, success)
            except Exception as e:
                logger.error(f"Error in sequence completion handler: {e}")
    
    def register_on_progress(self, handler: Callable[[int, int], None]) -> None:
        """
        Register a handler for progress events.
        
        Args:
            handler: Function to call when progress is made.
                     Takes current_step and total_steps as arguments.
        """
        self._on_progress_handlers.append(handler)
    
    def _on_progress(self, current_step: int, total_steps: int) -> None:
        """
        Call all registered progress handlers.
        
        Args:
            current_step: Current step number
            total_steps: Total number of steps
        """
        for handler in self._on_progress_handlers:
            try:
                handler(current_step, total_steps)
            except Exception as e:
                logger.error(f"Error in progress handler: {e}")
    
    # Position management methods
    
    def create_position(self, name: str, x: int, y: int, description: Optional[str] = None) -> Position:
        """
        Create a new position.
        
        Args:
            name: Unique name for the position
            x: X coordinate
            y: Y coordinate
            description: Optional description of the position
            
        Returns:
            Newly created Position object
        """
        position = Position(name, x, y, description)
        self.position_manager.add_position(position)
        return position
    
    def get_position(self, name: str) -> Optional[Position]:
        """
        Get a position by name.
        
        Args:
            name: Name of the position to retrieve
            
        Returns:
            Position object or None if not found
        """
        return self.position_manager.get_position(name)
    
    def remove_position(self, name: str) -> bool:
        """
        Remove a position by name.
        
        Args:
            name: Name of the position to remove
            
        Returns:
            True if position was removed, False if not found
        """
        return self.position_manager.remove_position(name)
    
    def get_all_positions(self) -> List[Position]:
        """
        Get all registered positions.
        
        Returns:
            List of all Position objects
        """
        return self.position_manager.get_all_positions()
    
    # Sequence management methods
    
    def create_sequence(self, name: str, description: Optional[str] = None) -> AutomationSequence:
        """
        Create a new automation sequence.
        
        Args:
            name: Unique name for the sequence
            description: Optional description of the sequence
            
        Returns:
            Newly created AutomationSequence object
        """
        sequence = AutomationSequence(name, [], description)
        self.sequence_manager.add_sequence(sequence)
        return sequence
    
    def get_sequence(self, name: str) -> Optional[AutomationSequence]:
        """
        Get a sequence by name.
        
        Args:
            name: Name of the sequence to retrieve
            
        Returns:
            AutomationSequence object or None if not found
        """
        return self.sequence_manager.get_sequence(name)
    
    def remove_sequence(self, name: str) -> bool:
        """
        Remove a sequence by name.
        
        Args:
            name: Name of the sequence to remove
            
        Returns:
            True if sequence was removed, False if not found
        """
        return self.sequence_manager.remove_sequence(name)
    
    def get_all_sequences(self) -> List[AutomationSequence]:
        """
        Get all registered sequences.
        
        Returns:
            List of all AutomationSequence objects
        """
        return self.sequence_manager.get_all_sequences()
    
    def add_action_to_sequence(self, sequence_name: str, action: AutomationAction) -> bool:
        """
        Add an action to a sequence.
        
        Args:
            sequence_name: Name of the sequence to add to
            action: AutomationAction to add
            
        Returns:
            True if action was added, False if sequence not found
        """
        sequence = self.get_sequence(sequence_name)
        if not sequence:
            logger.error(f"Cannot add action: sequence '{sequence_name}' not found")
            return False
        
        sequence.add_action(action)
        return True
    
    # Helper methods for creating actions
    
    def create_click_action(self, position_name: str, offset_x: int = 0, offset_y: int = 0,
                           right_click: bool = False, double_click: bool = False,
                           description: Optional[str] = None) -> AutomationAction:
        """
        Create a click action.
        
        Args:
            position_name: Name of the position to click
            offset_x: X offset from the position
            offset_y: Y offset from the position
            right_click: Whether to perform a right click
            double_click: Whether to perform a double click
            description: Optional description of the action
            
        Returns:
            AutomationAction configured for clicking
        """
        from .actions import ClickParams, ActionType
        
        action_type = ActionType.CLICK
        if right_click:
            action_type = ActionType.RIGHT_CLICK
        elif double_click:
            action_type = ActionType.DOUBLE_CLICK
        
        params = ClickParams(
            description=description,
            position_name=position_name,
            offset_x=offset_x,
            offset_y=offset_y
        )
        return AutomationAction(action_type, params)
    
    def create_drag_action(self, start_position_name: str, end_position_name: str,
                          start_offset_x: int = 0, start_offset_y: int = 0,
                          end_offset_x: int = 0, end_offset_y: int = 0,
                          duration: float = 0.5,
                          description: Optional[str] = None) -> AutomationAction:
        """
        Create a drag action.
        
        Args:
            start_position_name: Name of the starting position
            end_position_name: Name of the ending position
            start_offset_x: X offset from the starting position
            start_offset_y: Y offset from the starting position
            end_offset_x: X offset from the ending position
            end_offset_y: Y offset from the ending position
            duration: Duration of the drag in seconds
            description: Optional description of the action
            
        Returns:
            AutomationAction configured for dragging
        """
        from .actions import DragParams, ActionType
        
        params = DragParams(
            description=description,
            start_position_name=start_position_name,
            end_position_name=end_position_name,
            start_offset_x=start_offset_x,
            start_offset_y=start_offset_y,
            end_offset_x=end_offset_x,
            end_offset_y=end_offset_y,
            duration=duration
        )
        return AutomationAction(ActionType.DRAG, params)
    
    def create_type_action(self, text: str, delay: float = 0.05,
                          description: Optional[str] = None) -> AutomationAction:
        """
        Create a typing action.
        
        Args:
            text: Text to type
            delay: Delay between keystrokes in seconds
            description: Optional description of the action
            
        Returns:
            AutomationAction configured for typing
        """
        from .actions import TypeParams, ActionType
        
        params = TypeParams(
            description=description,
            text=text,
            delay=delay
        )
        return AutomationAction(ActionType.TYPE_TEXT, params)
    
    def create_wait_action(self, duration: float = 1.0,
                          description: Optional[str] = None) -> AutomationAction:
        """
        Create a wait action.
        
        Args:
            duration: Duration to wait in seconds
            description: Optional description of the action
            
        Returns:
            AutomationAction configured for waiting
        """
        from .actions import WaitParams, ActionType
        
        params = WaitParams(
            description=description,
            duration=duration
        )
        return AutomationAction(ActionType.WAIT, params)
    
    def create_template_search_action(self, template_name: str, threshold: float = 0.8,
                                     result_variable: str = "template_result",
                                     description: Optional[str] = None) -> AutomationAction:
        """
        Create a template search action.
        
        Args:
            template_name: Name of the template to search for
            threshold: Matching threshold (0.0 to 1.0)
            result_variable: Variable to store the result
            description: Optional description of the action
            
        Returns:
            AutomationAction configured for template searching
        """
        from .actions import TemplateSearchParams, ActionType
        
        params = TemplateSearchParams(
            description=description,
            template_name=template_name,
            threshold=threshold,
            result_variable=result_variable
        )
        return AutomationAction(ActionType.TEMPLATE_SEARCH, params)
    
    def create_ocr_wait_action(self, text: str, region: Optional[List[int]] = None,
                              timeout: float = 10.0, result_variable: str = "ocr_result",
                              description: Optional[str] = None) -> AutomationAction:
        """
        Create an OCR wait action.
        
        Args:
            text: Text to wait for
            region: Region to search in [x, y, width, height]
            timeout: Timeout in seconds
            result_variable: Variable to store the result
            description: Optional description of the action
            
        Returns:
            AutomationAction configured for OCR waiting
        """
        from .actions import OCRWaitParams, ActionType
        
        params = OCRWaitParams(
            description=description,
            text=text,
            region=region,
            timeout=timeout,
            result_variable=result_variable
        )
        return AutomationAction(ActionType.WAIT_FOR_OCR, params)
    
    def create_conditional_action(self, condition: str, then_actions: List[AutomationAction],
                                 else_actions: Optional[List[AutomationAction]] = None,
                                 description: Optional[str] = None) -> AutomationAction:
        """
        Create a conditional action.
        
        Args:
            condition: Condition to evaluate
            then_actions: Actions to execute if condition is true
            else_actions: Actions to execute if condition is false
            description: Optional description of the action
            
        Returns:
            AutomationAction configured for conditional execution
        """
        from .actions import ConditionalParams, ActionType
        
        params = ConditionalParams(
            description=description,
            condition=condition,
            then_actions=then_actions,
            else_actions=else_actions or []
        )
        return AutomationAction(ActionType.CONDITIONAL, params)
    
    def create_loop_action(self, iterations: int, actions: List[AutomationAction],
                          break_on_failure: bool = False,
                          description: Optional[str] = None) -> AutomationAction:
        """
        Create a loop action.
        
        Args:
            iterations: Number of iterations
            actions: Actions to execute in the loop
            break_on_failure: Whether to break the loop on action failure
            description: Optional description of the action
            
        Returns:
            AutomationAction configured for looping
        """
        from .actions import LoopParams, ActionType
        
        # Convert actions to dictionaries for storage
        action_dicts = [action.to_dict() for action in actions]
        
        params = LoopParams(
            description=description,
            iterations=iterations,
            actions=action_dicts,
            break_on_failure=break_on_failure
        )
        return AutomationAction(ActionType.LOOP, params)
    
    # Execution methods
    
    def execute_sequence(self, sequence_name: str) -> bool:
        """
        Execute a sequence by name.
        
        This method delegates to the executor component to run the sequence.
        
        Args:
            sequence_name: Name of the sequence to execute
            
        Returns:
            True if sequence executed successfully, False otherwise
        """
        sequence = self.get_sequence(sequence_name)
        if not sequence:
            logger.error(f"Cannot execute sequence: '{sequence_name}' not found")
            return False
        
        if self.is_executing:
            logger.error(f"Cannot execute sequence: Another sequence is already running")
            return False
        
        try:
            self.is_executing = True
            self.current_sequence = sequence
            self.execution_context = ExecutionContext(
                positions={pos.name: pos for pos in self.get_all_positions()},
                window_manager=self.window_manager,
                template_matcher=self.template_matcher,
                text_ocr=self.text_ocr,
                game_actions=self.game_actions,
                variables={},
                overlay=self.overlay
            )
            
            logger.info(f"Executing sequence: {sequence_name}")
            
            # Reset progress tracker
            self.progress_tracker.reset(len(sequence.actions))
            
            # Execute each action in the sequence
            success = self._execute_actions(sequence.actions)
            
            logger.info(f"Sequence {sequence_name} completed with {'success' if success else 'failure'}")
            
            # Notify sequence completion
            self._on_sequence_complete(sequence_name, success)
            
            return success
        except Exception as e:
            logger.error(f"Error executing sequence {sequence_name}: {e}")
            self._on_sequence_complete(sequence_name, False)
            return False
        finally:
            self.is_executing = False
            self.current_sequence = None
            self.execution_context = None
            self.pause_requested = False
            self.stop_requested = False
    
    def _execute_actions(self, actions: List[AutomationAction]) -> bool:
        """
        Execute a list of actions.
        
        Args:
            actions: List of actions to execute
            
        Returns:
            True if all actions executed successfully, False otherwise
        """
        for i, action in enumerate(actions):
            if self.stop_requested:
                logger.info("Execution stopped by user")
                return False
            
            while self.pause_requested:
                time.sleep(0.1)
                if self.stop_requested:
                    logger.info("Execution stopped by user during pause")
                    return False
            
            # Update progress
            self.progress_tracker.set_current_action(i + 1)
            progress_data = self.progress_tracker.get_progress()
            self._on_progress_update(progress_data)
            
            # Find a handler for this action type
            handler = None
            for h in self.action_handlers:
                if h.can_handle(action.action_type):
                    handler = h
                    break
            
            if not handler:
                logger.error(f"No handler found for action type: {action.action_type}")
                return False
            
            # Execute the action
            try:
                success = handler.handle(action, self.execution_context)
                if not success:
                    logger.error(f"Action failed: {action.action_type}")
                    return False
            except Exception as e:
                logger.error(f"Error executing action {action.action_type}: {e}")
                return False
        
        return True
    
    def pause_execution(self) -> None:
        """
        Pause the current sequence execution.
        """
        if self.is_executing:
            self.pause_requested = True
            logger.info("Execution pause requested")
    
    def resume_execution(self) -> None:
        """
        Resume the paused sequence execution.
        """
        if self.is_executing and self.pause_requested:
            self.pause_requested = False
            logger.info("Execution resumed")
    
    def stop_execution(self) -> None:
        """
        Stop the current sequence execution.
        """
        if self.is_executing:
            self.stop_requested = True
            logger.info("Execution stop requested")
    
    def save_to_file(self, filename: str) -> bool:
        """
        Save all positions and sequences to a file.
        
        Args:
            filename: Path to the file to save to
            
        Returns:
            True if saved successfully, False otherwise
        """
        try:
            data = {
                'positions': [pos.to_dict() for pos in self.get_all_positions()],
                'sequences': [seq.to_dict() for seq in self.get_all_sequences()]
            }
            
            with open(filename, 'w') as f:
                json.dump(data, f, indent=2)
            
            logger.info(f"Saved automation data to {filename}")
            return True
        except Exception as e:
            logger.error(f"Failed to save automation data: {e}")
            return False
    
    def load_from_file(self, filename: str) -> bool:
        """
        Load positions and sequences from a file.
        
        Args:
            filename: Path to the file to load from
            
        Returns:
            True if loaded successfully, False otherwise
        """
        try:
            with open(filename, 'r') as f:
                data = json.load(f)
            
            # Clear existing data
            self.position_manager.clear()
            self.sequence_manager.clear()
            
            # Load positions
            for pos_data in data.get('positions', []):
                position = Position.from_dict(pos_data)
                self.position_manager.add_position(position)
            
            # Load sequences
            for seq_data in data.get('sequences', []):
                sequence = Sequence.from_dict(seq_data)
                self.sequence_manager.add_sequence(sequence)
            
            logger.info(f"Loaded automation data from {filename}")
            return True
        except Exception as e:
            logger.error(f"Failed to load automation data: {e}")
            return False
