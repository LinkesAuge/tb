"""
Flow Control Action Handlers

This module implements handlers for flow control automation actions:
- Conditional execution (if/else)
- Loops (repeat, while)
- Sequence execution

These handlers control the flow of automation sequences based on conditions
and iteration requirements.
"""

import time
import logging
from typing import Dict, Optional, List, Callable, Tuple, Any, Union
import re

from scout.automation.core import ExecutionContext
from scout.automation.actions import (
    ActionType, AutomationAction, ActionParamsCommon,
    ConditionalParams, LoopParams
)

logger = logging.getLogger(__name__)

class FlowActionHandlers:
    """
    Handlers for flow control automation actions like conditionals and loops.
    """
    
    def __init__(self, context: ExecutionContext, log_callback: Callable[[str], None],
                execute_action_callback: Callable[[AutomationAction, bool, Dict[str, Any]], bool]):
        """
        Initialize the flow control action handlers.
        
        Args:
            context: Execution context with required components
            log_callback: Function to call for debug logging
            execute_action_callback: Function to call to execute nested actions
        """
        self.context = context
        self.log_callback = log_callback
        self.execute_action_callback = execute_action_callback
        self.variable_pattern = re.compile(r'\${([^}]+)}')
    
    def handle_if_condition(self, params: ConditionalParams, simulate: bool, 
                           variable_store: Optional[Dict[str, Any]] = None) -> bool:
        """
        Handle a conditional (if/else) action.
        
        Args:
            params: If condition parameters
            simulate: Whether to simulate the action
            variable_store: Store for variables
            
        Returns:
            True if the condition execution succeeded, False otherwise
        """
        try:
            condition = params.condition
            then_actions = params.then_actions
            else_actions = params.else_actions
            
            # Log the action
            self.log_callback(
                f"{'Simulating' if simulate else 'Executing'} if condition: '{condition}'"
            )
            
            # Evaluate the condition
            condition_result = self._evaluate_condition(condition, variable_store)
            self.log_callback(f"Condition evaluated to: {condition_result}")
            
            # Execute the appropriate branch
            if condition_result:
                self.log_callback("Executing 'then' branch")
                if then_actions:
                    return self._execute_action_list(then_actions, simulate, variable_store)
            else:
                self.log_callback("Executing 'else' branch")
                if else_actions:
                    return self._execute_action_list(else_actions, simulate, variable_store)
            
            # If we get here, either the condition was false and there were no else actions,
            # or the condition was true and there were no then actions
            return True
            
        except Exception as e:
            logger.exception(f"Error in if condition action: {e}")
            self.log_callback(f"If condition action failed: {e}")
            return False
    
    def handle_repeat_loop(self, params: LoopParams, simulate: bool, 
                          variable_store: Optional[Dict[str, Any]] = None) -> bool:
        """
        Handle a repeat loop action.
        
        Args:
            params: Repeat loop parameters
            simulate: Whether to simulate the action
            variable_store: Store for variables
            
        Returns:
            True if the loop execution succeeded, False otherwise
        """
        try:
            # Extract parameters
            count = params.count if hasattr(params, 'count') else 1
            actions = params.actions if hasattr(params, 'actions') else []
            
            # Log the action
            self.log_callback(
                f"{'Simulating' if simulate else 'Executing'} repeat loop: {count} iterations"
            )
            
            # Execute the loop
            for i in range(count):
                self.log_callback(f"Loop iteration {i+1}/{count}")
                
                # Execute the actions
                if actions:
                    result = self._execute_action_list(actions, simulate, variable_store)
                    if not result:
                        self.log_callback(f"Loop iteration {i+1} failed, breaking loop")
                        return False
                
                # Check if we should continue
                if self.context.should_stop():
                    self.log_callback("Execution stopped, breaking loop")
                    return False
            
            return True
            
        except Exception as e:
            logger.exception(f"Error in repeat loop action: {e}")
            self.log_callback(f"Repeat loop action failed: {e}")
            return False
    
    def handle_while_loop(self, params: LoopParams, simulate: bool, 
                         variable_store: Optional[Dict[str, Any]] = None) -> bool:
        """
        Handle a while loop action.
        
        Args:
            params: While loop parameters
            simulate: Whether to simulate the action
            variable_store: Store for variables
            
        Returns:
            True if the loop execution succeeded, False otherwise
        """
        try:
            # Extract parameters
            condition = params.condition if hasattr(params, 'condition') else "False"
            actions = params.actions if hasattr(params, 'actions') else []
            max_iterations = params.max_iterations if hasattr(params, 'max_iterations') else 100
            
            # Log the action
            self.log_callback(
                f"{'Simulating' if simulate else 'Executing'} while loop: condition '{condition}'"
            )
            
            # Execute the loop
            iteration = 0
            while self._evaluate_condition(condition, variable_store):
                iteration += 1
                self.log_callback(f"Loop iteration {iteration}")
                
                # Check max iterations
                if iteration > max_iterations:
                    self.log_callback(f"Reached maximum iterations ({max_iterations}), breaking loop")
                    return False
                
                # Execute the actions
                if actions:
                    result = self._execute_action_list(actions, simulate, variable_store)
                    if not result:
                        self.log_callback(f"Loop iteration {iteration} failed, breaking loop")
                        return False
                
                # Check if we should continue
                if self.context.should_stop():
                    self.log_callback("Execution stopped, breaking loop")
                    return False
            
            return True
            
        except Exception as e:
            logger.exception(f"Error in while loop action: {e}")
            self.log_callback(f"While loop action failed: {e}")
            return False
    
    def handle_sequence(self, params: Dict[str, Any], simulate: bool, 
                       variable_store: Optional[Dict[str, Any]] = None) -> bool:
        """
        Handle a sequence action.
        
        Args:
            params: Sequence parameters
            simulate: Whether to simulate the action
            variable_store: Store for variables
            
        Returns:
            True if the sequence execution succeeded, False otherwise
        """
        try:
            # Extract parameters
            actions = params.get('actions', [])
            
            # Log the action
            self.log_callback(
                f"{'Simulating' if simulate else 'Executing'} sequence with {len(actions)} actions"
            )
            
            # Execute the sequence
            if actions:
                return self._execute_action_list(actions, simulate, variable_store)
            
            return True
            
        except Exception as e:
            logger.exception(f"Error in sequence action: {e}")
            self.log_callback(f"Sequence action failed: {e}")
            return False
    
    def _execute_action_list(self, actions: List[Any], simulate: bool, 
                            variable_store: Optional[Dict[str, Any]] = None) -> bool:
        """
        Execute a list of actions.
        
        Args:
            actions: List of actions to execute
            simulate: Whether to simulate the actions
            variable_store: Store for variables
            
        Returns:
            True if all actions succeeded, False otherwise
        """
        for action in actions:
            # Convert action dict to AutomationAction if needed
            if isinstance(action, dict):
                from scout.automation.actions import create_action_from_dict
                action = create_action_from_dict(action)
            
            # Execute the action
            result = self.execute_action_callback(action, simulate, variable_store)
            if not result:
                return False
            
            # Check if we should continue
            if self.context.should_stop():
                return False
        
        return True
    
    def _evaluate_condition(self, condition: str, variable_store: Optional[Dict[str, Any]] = None) -> bool:
        """
        Evaluate a condition string.
        
        Args:
            condition: Condition string to evaluate
            variable_store: Store for variables
            
        Returns:
            True if the condition evaluates to true, False otherwise
        """
        try:
            # Replace variables in the condition
            if variable_store and '${' in condition:
                for match in self.variable_pattern.finditer(condition):
                    var_name = match.group(1)
                    if var_name in variable_store:
                        var_value = variable_store[var_name]
                        # Handle different types of values
                        if isinstance(var_value, str):
                            replacement = f"'{var_value}'"
                        else:
                            replacement = str(var_value)
                        condition = condition.replace(f"${{{var_name}}}", replacement)
            
            # Check for comparison operators
            if " == " in condition:
                left, right = condition.split(" == ", 1)
                return self._parse_value(left.strip()) == self._parse_value(right.strip())
            elif " != " in condition:
                left, right = condition.split(" != ", 1)
                return self._parse_value(left.strip()) != self._parse_value(right.strip())
            elif " > " in condition:
                left, right = condition.split(" > ", 1)
                return self._parse_value(left.strip()) > self._parse_value(right.strip())
            elif " >= " in condition:
                left, right = condition.split(" >= ", 1)
                return self._parse_value(left.strip()) >= self._parse_value(right.strip())
            elif " < " in condition:
                left, right = condition.split(" < ", 1)
                return self._parse_value(left.strip()) < self._parse_value(right.strip())
            elif " <= " in condition:
                left, right = condition.split(" <= ", 1)
                return self._parse_value(left.strip()) <= self._parse_value(right.strip())
            
            # Check for boolean value
            if condition.lower() == "true":
                return True
            if condition.lower() == "false":
                return False
            
            # If it's just a variable name, check if it exists and is truthy
            if variable_store and condition in variable_store:
                return bool(variable_store[condition])
            
            # Default to false for unknown conditions
            self.log_callback(f"Unknown condition format: {condition}")
            return False
            
        except Exception as e:
            logger.exception(f"Error evaluating condition '{condition}': {e}")
            self.log_callback(f"Condition evaluation failed: {e}")
            return False
    
    def _parse_value(self, value_str: str) -> Any:
        """
        Parse a string value into the appropriate Python type.
        
        Args:
            value_str: String value to parse
            
        Returns:
            Parsed value
        """
        # Remove quotes from string literals
        if (value_str.startswith("'") and value_str.endswith("'")) or \
           (value_str.startswith('"') and value_str.endswith('"')):
            return value_str[1:-1]
        
        # Try to parse as number
        try:
            if '.' in value_str:
                return float(value_str)
            else:
                return int(value_str)
        except ValueError:
            # Not a number, return as is
            return value_str
