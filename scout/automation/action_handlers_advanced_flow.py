"""
Advanced Flow Control Action Handlers

This module implements handlers for advanced flow control automation actions:
- Switch/case statements
- Try/catch error handling
- Parallel execution
- Conditional breakpoints

These handlers provide more complex flow control capabilities beyond
the basic conditionals and loops.
"""

import time
import logging
from typing import Dict, Optional, List, Callable, Tuple, Any, Union
import re
import concurrent.futures

from scout.automation.core import ExecutionContext
from scout.automation.actions import (
    ActionType, AutomationAction, ActionParamsCommon,
    SwitchCaseParams, TryCatchParams, ParallelExecutionParams, BreakpointParams
)

logger = logging.getLogger(__name__)

class AdvancedFlowActionHandlers:
    """
    Handlers for advanced flow control automation actions like switch/case,
    try/catch, parallel execution, and conditional breakpoints.
    """
    
    def __init__(self, context: ExecutionContext, log_callback: Callable[[str], None],
                execute_action_callback: Callable[[AutomationAction, bool, Dict[str, Any]], bool]):
        """
        Initialize the advanced flow control action handlers.
        
        Args:
            context: Execution context with required components
            log_callback: Function to call for debug logging
            execute_action_callback: Function to call to execute nested actions
        """
        self.context = context
        self.log_callback = log_callback
        self.execute_action_callback = execute_action_callback
        self.variable_pattern = re.compile(r'\${([^}]+)}')
    
    def handle_switch_case(self, params: SwitchCaseParams, simulate: bool, 
                          variable_store: Optional[Dict[str, Any]] = None) -> bool:
        """
        Handle a switch/case action.
        
        Args:
            params: Switch/case parameters
            simulate: Whether to simulate the action
            variable_store: Store for variables
            
        Returns:
            True if the switch/case execution succeeded, False otherwise
        """
        try:
            expression = params.expression
            cases = params.cases
            default_actions = params.default_actions
            
            # Replace variables in expression if variable store is provided
            if variable_store and isinstance(expression, str):
                expression = self._replace_variables(expression, variable_store)
            
            # Log the action
            self.log_callback(
                f"{'Simulating' if simulate else 'Executing'} switch/case on expression: '{expression}'"
            )
            
            # Evaluate the expression
            expression_value = self._evaluate_expression(expression, variable_store)
            self.log_callback(f"Expression evaluated to: {expression_value}")
            
            # Find matching case
            matched_case = None
            for case in cases:
                case_value = case.value
                
                # Replace variables in case value if it's a string
                if variable_store and isinstance(case_value, str):
                    case_value = self._replace_variables(case_value, variable_store)
                
                # Try to convert case value to same type as expression value for comparison
                try:
                    if isinstance(expression_value, (int, float)) and isinstance(case_value, str):
                        if case_value.isdigit():
                            case_value = int(case_value)
                        elif case_value.replace('.', '', 1).isdigit():
                            case_value = float(case_value)
                except (ValueError, TypeError):
                    pass
                
                # Check for match
                if case_value == expression_value:
                    matched_case = case
                    self.log_callback(f"Found matching case: {case_value}")
                    break
            
            # Execute matching case actions or default actions
            if matched_case and matched_case.actions:
                self.log_callback(f"Executing actions for case: {matched_case.value}")
                return self._execute_action_list(matched_case.actions, simulate, variable_store)
            elif default_actions:
                self.log_callback("No matching case found, executing default actions")
                return self._execute_action_list(default_actions, simulate, variable_store)
            else:
                self.log_callback("No matching case found and no default actions specified")
                return True  # No actions to execute is still a success
            
        except Exception as e:
            logger.exception(f"Error in switch/case action: {e}")
            self.log_callback(f"Switch/case action failed: {e}")
            return False
    
    def handle_try_catch(self, params: TryCatchParams, simulate: bool, 
                        variable_store: Optional[Dict[str, Any]] = None) -> bool:
        """
        Handle a try/catch error handling action.
        
        Args:
            params: Try/catch parameters
            simulate: Whether to simulate the action
            variable_store: Store for variables
            
        Returns:
            True if the try/catch execution succeeded, False otherwise
        """
        try:
            try_actions = params.try_actions
            catch_actions = params.catch_actions
            finally_actions = params.finally_actions
            store_error_variable = params.store_error_variable
            
            # Log the action
            self.log_callback(
                f"{'Simulating' if simulate else 'Executing'} try/catch block"
            )
            
            # Create a copy of the variable store
            local_vars = variable_store.copy() if variable_store else {}
            
            # Execute try block
            self.log_callback("Executing 'try' block")
            try_success = True
            error_message = None
            
            try:
                try_success = self._execute_action_list(try_actions, simulate, local_vars)
            except Exception as e:
                try_success = False
                error_message = str(e)
                logger.exception(f"Error in try block: {e}")
                self.log_callback(f"Error in try block: {e}")
            
            # Execute catch block if try failed
            if not try_success and catch_actions:
                self.log_callback("Executing 'catch' block")
                
                # Store error message in variable if requested
                if store_error_variable and variable_store is not None:
                    variable_store[store_error_variable] = error_message or "Unknown error"
                    self.log_callback(f"Stored error message in variable '${store_error_variable}'")
                
                catch_success = self._execute_action_list(catch_actions, simulate, local_vars)
                if not catch_success:
                    self.log_callback("Catch block execution failed")
            
            # Execute finally block
            if finally_actions:
                self.log_callback("Executing 'finally' block")
                finally_success = self._execute_action_list(finally_actions, simulate, local_vars)
                if not finally_success:
                    self.log_callback("Finally block execution failed")
                    return False
            
            # Update the original variable store with any changes
            if variable_store:
                for key, value in local_vars.items():
                    variable_store[key] = value
            
            # Return success if either try succeeded or catch was executed
            return try_success or (not try_success and catch_actions)
            
        except Exception as e:
            logger.exception(f"Error in try/catch action: {e}")
            self.log_callback(f"Try/catch action failed: {e}")
            return False
    
    def handle_parallel_execution(self, params: ParallelExecutionParams, simulate: bool, 
                                 variable_store: Optional[Dict[str, Any]] = None) -> bool:
        """
        Handle parallel execution of multiple action groups.
        
        Args:
            params: Parallel execution parameters
            simulate: Whether to simulate the action
            variable_store: Store for variables
            
        Returns:
            True if all parallel executions succeeded, False otherwise
        """
        try:
            action_groups = params.action_groups
            max_workers = params.max_workers or 4  # Default to 4 workers
            wait_for_all = params.wait_for_all
            
            # Log the action
            self.log_callback(
                f"{'Simulating' if simulate else 'Executing'} parallel execution "
                f"with {len(action_groups)} action groups (max workers: {max_workers})"
            )
            
            # In simulation mode, we just execute the first group
            if simulate:
                self.log_callback("Simulation: Executing only the first action group")
                if action_groups:
                    return self._execute_action_list(action_groups[0].actions, simulate, variable_store)
                return True
            
            # Create a thread-safe copy of the variable store for each group
            # Each group gets its own copy to avoid conflicts
            group_variable_stores = []
            for _ in action_groups:
                group_variable_stores.append(variable_store.copy() if variable_store else {})
            
            # Function to execute a single action group
            def execute_group(group_index):
                group = action_groups[group_index]
                group_vars = group_variable_stores[group_index]
                
                self.log_callback(f"Starting execution of parallel group {group_index+1}")
                success = self._execute_action_list(group.actions, simulate, group_vars)
                self.log_callback(f"Parallel group {group_index+1} completed with success={success}")
                
                return success, group_vars
            
            # Execute action groups in parallel
            results = []
            with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
                futures = [executor.submit(execute_group, i) for i in range(len(action_groups))]
                
                # Wait for all futures to complete if wait_for_all is True
                if wait_for_all:
                    for future in concurrent.futures.as_completed(futures):
                        success, group_vars = future.result()
                        results.append(success)
                        
                        # Merge variables back into the main store
                        # Note: This can cause conflicts if multiple groups modify the same variables
                        if variable_store:
                            for key, value in group_vars.items():
                                variable_store[key] = value
                else:
                    # Just wait for the first one to complete
                    done, not_done = concurrent.futures.wait(
                        futures, return_when=concurrent.futures.FIRST_COMPLETED
                    )
                    
                    # Get result from the first completed future
                    for future in done:
                        success, group_vars = future.result()
                        results.append(success)
                        
                        # Merge variables back into the main store
                        if variable_store:
                            for key, value in group_vars.items():
                                variable_store[key] = value
                        
                        # Cancel remaining futures
                        for future in not_done:
                            future.cancel()
                        
                        break
            
            # Check if all required executions succeeded
            if wait_for_all:
                all_succeeded = all(results)
                self.log_callback(f"All parallel groups completed with overall success={all_succeeded}")
                return all_succeeded
            else:
                any_succeeded = any(results)
                self.log_callback(f"At least one parallel group completed with success={any_succeeded}")
                return any_succeeded
            
        except Exception as e:
            logger.exception(f"Error in parallel execution action: {e}")
            self.log_callback(f"Parallel execution action failed: {e}")
            return False
    
    def handle_breakpoint(self, params: BreakpointParams, simulate: bool, 
                         variable_store: Optional[Dict[str, Any]] = None) -> bool:
        """
        Handle a conditional breakpoint action.
        
        Args:
            params: Breakpoint parameters
            simulate: Whether to simulate the action
            variable_store: Store for variables
            
        Returns:
            True if the breakpoint was handled successfully, False otherwise
        """
        try:
            condition = params.condition
            message = params.message or "Breakpoint reached"
            
            # Replace variables in condition and message
            if variable_store:
                if condition:
                    condition = self._replace_variables(condition, variable_store)
                message = self._replace_variables(message, variable_store)
            
            # Log the action
            self.log_callback(
                f"{'Simulating' if simulate else 'Executing'} breakpoint "
                f"with condition: '{condition or 'None'}'"
            )
            
            # Check if breakpoint should be triggered
            should_break = True
            if condition:
                should_break = self._evaluate_condition(condition, variable_store)
                self.log_callback(f"Breakpoint condition evaluated to: {should_break}")
            
            if should_break:
                self.log_callback(f"Breakpoint triggered: {message}")
                
                if not simulate:
                    # Notify the execution context that a breakpoint was hit
                    if hasattr(self.context, 'on_breakpoint_hit'):
                        self.context.on_breakpoint_hit(message, variable_store)
                    
                    # Pause execution
                    if hasattr(self.context, 'pause_execution'):
                        self.context.pause_execution()
            else:
                self.log_callback("Breakpoint condition not met, continuing execution")
            
            return True
            
        except Exception as e:
            logger.exception(f"Error in breakpoint action: {e}")
            self.log_callback(f"Breakpoint action failed: {e}")
            return False
    
    def _execute_action_list(self, actions: List[AutomationAction], simulate: bool, 
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
            # Execute the action
            success = self.execute_action_callback(action, simulate, variable_store)
            if not success:
                return False
            
            # Check if we should stop execution
            if self.context.should_stop():
                self.log_callback("Execution stopped by user")
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
            if variable_store:
                condition = self._replace_variables(condition, variable_store)
            
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
            elif " and " in condition.lower():
                left, right = condition.lower().split(" and ", 1)
                return self._evaluate_condition(left.strip(), variable_store) and \
                       self._evaluate_condition(right.strip(), variable_store)
            elif " or " in condition.lower():
                left, right = condition.lower().split(" or ", 1)
                return self._evaluate_condition(left.strip(), variable_store) or \
                       self._evaluate_condition(right.strip(), variable_store)
            elif condition.lower() == "true":
                return True
            elif condition.lower() == "false":
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
    
    def _evaluate_expression(self, expression: Any, variable_store: Optional[Dict[str, Any]] = None) -> Any:
        """
        Evaluate an expression, which could be a variable reference or a literal value.
        
        Args:
            expression: Expression to evaluate
            variable_store: Store for variables
            
        Returns:
            The evaluated expression value
        """
        # If expression is not a string, return it as is
        if not isinstance(expression, str):
            return expression
            
        # If it's a variable reference, get the value from the variable store
        if expression.startswith("${") and expression.endswith("}"):
            var_name = expression[2:-1]
            if variable_store and var_name in variable_store:
                return variable_store[var_name]
            return None
            
        # Otherwise, parse it as a value
        return self._parse_value(expression)
    
    def _parse_value(self, value_str: str) -> Any:
        """
        Parse a string value into the appropriate Python type.
        
        Args:
            value_str: String value to parse
            
        Returns:
            Parsed value
        """
        if not isinstance(value_str, str):
            return value_str
            
        # Try to parse as integer
        try:
            if value_str.isdigit():
                return int(value_str)
        except Exception:
            pass
            
        # Try to parse as float
        try:
            return float(value_str)
        except Exception:
            pass
            
        # Try to parse as boolean
        if value_str.lower() == "true":
            return True
        if value_str.lower() == "false":
            return False
            
        # Try to parse as list
        if value_str.startswith("[") and value_str.endswith("]"):
            try:
                items = value_str[1:-1].split(",")
                return [self._parse_value(item.strip()) for item in items]
            except Exception:
                pass
        
        # Default to string
        return value_str
    
    def _replace_variables(self, text: str, variable_store: Dict[str, Any]) -> str:
        """
        Replace variables in text with their values from the variable store.
        
        Args:
            text: Text containing variables in the format ${variable_name}
            variable_store: Dictionary of variable names to values
            
        Returns:
            Text with variables replaced by their values
        """
        def replace_match(match):
            var_name = match.group(1)
            if var_name in variable_store:
                return str(variable_store[var_name])
            return match.group(0)  # Keep original if variable not found
        
        return self.variable_pattern.sub(replace_match, text)