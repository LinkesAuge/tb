"""
Data Manipulation Action Handlers

This module implements handlers for data manipulation automation actions:
- Variable operations (set, increment, decrement)
- String operations (concat, substring, replace)
- List operations (create, append, get item)
- Dictionary operations (create, set key, get value)
- Math operations (calculate, random)
- File operations (read, write)

These handlers provide capabilities for manipulating data during automation sequences.
"""

import logging
import random
import re
import json
import os
from typing import Dict, Optional, List, Callable, Any, Union
from dataclasses import dataclass, field

from scout.automation.core import ExecutionContext
from scout.automation.actions import ActionType, AutomationAction, ActionParamsCommon

logger = logging.getLogger(__name__)

# Define parameter classes for data manipulation actions

@dataclass
class VariableSetParams(ActionParamsCommon):
    """
    Parameters for setting a variable.
    
    Attributes:
        variable_name: Name of the variable to set
        value: Value to assign to the variable
        value_type: Type of the value (string, number, boolean, expression)
    """
    variable_name: str = ""
    value: Any = ""
    value_type: str = "string"  # string, number, boolean, expression


@dataclass
class VariableIncrementParams(ActionParamsCommon):
    """
    Parameters for incrementing a numeric variable.
    
    Attributes:
        variable_name: Name of the variable to increment
        increment_by: Amount to increment by
    """
    variable_name: str = ""
    increment_by: float = 1.0


@dataclass
class StringOperationParams(ActionParamsCommon):
    """
    Parameters for string operations.
    
    Attributes:
        operation: Type of string operation (concat, substring, replace, length, etc.)
        input_variables: List of input variable names
        output_variable: Name of the variable to store the result
        parameters: Additional parameters for the operation
    """
    operation: str = "concat"  # concat, substring, replace, length, etc.
    input_variables: List[str] = field(default_factory=list)
    output_variable: str = ""
    parameters: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ListOperationParams(ActionParamsCommon):
    """
    Parameters for list operations.
    
    Attributes:
        operation: Type of list operation (create, append, get, length, etc.)
        list_variable: Name of the list variable
        input_value: Input value for the operation
        output_variable: Name of the variable to store the result
        index: Index for operations that require it
    """
    operation: str = "create"  # create, append, get, length, etc.
    list_variable: str = ""
    input_value: Any = None
    output_variable: str = ""
    index: int = 0


@dataclass
class DictOperationParams(ActionParamsCommon):
    """
    Parameters for dictionary operations.
    
    Attributes:
        operation: Type of dictionary operation (create, set, get, keys, etc.)
        dict_variable: Name of the dictionary variable
        key: Key for the operation
        value: Value for the operation
        output_variable: Name of the variable to store the result
    """
    operation: str = "create"  # create, set, get, keys, etc.
    dict_variable: str = ""
    key: str = ""
    value: Any = None
    output_variable: str = ""


@dataclass
class MathOperationParams(ActionParamsCommon):
    """
    Parameters for math operations.
    
    Attributes:
        operation: Type of math operation (add, subtract, multiply, divide, etc.)
        operands: List of operands
        output_variable: Name of the variable to store the result
    """
    operation: str = "add"  # add, subtract, multiply, divide, etc.
    operands: List[Any] = field(default_factory=list)
    output_variable: str = ""


@dataclass
class RandomValueParams(ActionParamsCommon):
    """
    Parameters for generating random values.
    
    Attributes:
        value_type: Type of random value (int, float, choice)
        min_value: Minimum value for numeric types
        max_value: Maximum value for numeric types
        choices: List of choices for choice type
        output_variable: Name of the variable to store the result
    """
    value_type: str = "int"  # int, float, choice
    min_value: float = 0
    max_value: float = 100
    choices: List[str] = field(default_factory=list)
    output_variable: str = ""


@dataclass
class FileOperationParams(ActionParamsCommon):
    """
    Parameters for file operations.
    
    Attributes:
        operation: Type of file operation (read, write, append)
        file_path: Path to the file
        content: Content to write (for write and append)
        output_variable: Name of the variable to store the result (for read)
        format: File format (text, json, csv)
    """
    operation: str = "read"  # read, write, append
    file_path: str = ""
    content: str = ""
    output_variable: str = ""
    format: str = "text"  # text, json, csv


class DataActionHandlers:
    """
    Handlers for data manipulation automation actions.
    """
    
    def __init__(self, context: ExecutionContext, log_callback: Callable[[str], None]):
        """
        Initialize the data action handlers.
        
        Args:
            context: Execution context with required components
            log_callback: Function to call for debug logging
        """
        self.context = context
        self.log_callback = log_callback
        self.variable_pattern = re.compile(r'\${([^}]+)}')
    
    def handle_variable_set(self, params: VariableSetParams, simulate: bool, 
                           variable_store: Dict[str, Any]) -> bool:
        """
        Handle setting a variable.
        
        Args:
            params: Variable set parameters
            simulate: Whether to simulate the action
            variable_store: Store for variables
            
        Returns:
            True if the action was successful, False otherwise
        """
        try:
            variable_name = params.variable_name
            value = params.value
            value_type = params.value_type
            
            # Log the action
            self.log_callback(f"{'Simulating' if simulate else 'Setting'} variable '{variable_name}'")
            
            # Process the value based on its type
            if value_type == "expression":
                # Evaluate the expression
                try:
                    # Replace variables in the expression
                    expr = self._replace_variables(str(value), variable_store)
                    # Safely evaluate the expression
                    result = eval(expr, {"__builtins__": {}}, variable_store)
                    value = result
                except Exception as e:
                    self.log_callback(f"Error evaluating expression: {e}")
                    return False
            elif value_type == "number":
                try:
                    value = float(value)
                    # Convert to int if it's a whole number
                    if value.is_integer():
                        value = int(value)
                except ValueError:
                    self.log_callback(f"Error converting '{value}' to number")
                    return False
            elif value_type == "boolean":
                if isinstance(value, str):
                    value = value.lower() in ("true", "yes", "1", "y")
            elif value_type == "string":
                # Replace variables in the string
                if isinstance(value, str):
                    value = self._replace_variables(value, variable_store)
            
            # Set the variable in the store
            if not simulate:
                variable_store[variable_name] = value
                self.log_callback(f"Set variable '{variable_name}' to {value} ({type(value).__name__})")
            
            return True
            
        except Exception as e:
            logger.exception(f"Error in variable set action: {e}")
            self.log_callback(f"Variable set action failed: {e}")
            return False
    
    def handle_variable_increment(self, params: VariableIncrementParams, simulate: bool, 
                                 variable_store: Dict[str, Any]) -> bool:
        """
        Handle incrementing a numeric variable.
        
        Args:
            params: Variable increment parameters
            simulate: Whether to simulate the action
            variable_store: Store for variables
            
        Returns:
            True if the action was successful, False otherwise
        """
        try:
            variable_name = params.variable_name
            increment_by = params.increment_by
            
            # Log the action
            self.log_callback(f"{'Simulating' if simulate else 'Incrementing'} variable '{variable_name}' by {increment_by}")
            
            # Check if the variable exists
            if variable_name not in variable_store:
                self.log_callback(f"Variable '{variable_name}' not found, initializing to 0")
                if not simulate:
                    variable_store[variable_name] = 0
            
            # Check if the variable is numeric
            current_value = variable_store.get(variable_name, 0)
            if not isinstance(current_value, (int, float)):
                self.log_callback(f"Variable '{variable_name}' is not numeric")
                return False
            
            # Increment the variable
            if not simulate:
                new_value = current_value + increment_by
                variable_store[variable_name] = new_value
                self.log_callback(f"Incremented '{variable_name}' from {current_value} to {new_value}")
            
            return True
            
        except Exception as e:
            logger.exception(f"Error in variable increment action: {e}")
            self.log_callback(f"Variable increment action failed: {e}")
            return False
    
    def handle_string_operation(self, params: StringOperationParams, simulate: bool, 
                               variable_store: Dict[str, Any]) -> bool:
        """
        Handle string operations.
        
        Args:
            params: String operation parameters
            simulate: Whether to simulate the action
            variable_store: Store for variables
            
        Returns:
            True if the action was successful, False otherwise
        """
        try:
            operation = params.operation
            input_vars = params.input_variables
            output_var = params.output_variable
            parameters = params.parameters
            
            # Log the action
            self.log_callback(f"{'Simulating' if simulate else 'Executing'} string {operation} operation")
            
            # Get input values
            input_values = []
            for var_name in input_vars:
                if var_name in variable_store:
                    input_values.append(str(variable_store[var_name]))
                else:
                    self.log_callback(f"Variable '{var_name}' not found")
                    return False
            
            # Perform the operation
            result = None
            
            if operation == "concat":
                result = "".join(input_values)
            
            elif operation == "substring":
                if len(input_values) < 1:
                    self.log_callback("Substring operation requires at least one input")
                    return False
                
                start = parameters.get("start", 0)
                end = parameters.get("end", None)
                
                if end is not None:
                    result = input_values[0][start:end]
                else:
                    result = input_values[0][start:]
            
            elif operation == "replace":
                if len(input_values) < 1:
                    self.log_callback("Replace operation requires at least one input")
                    return False
                
                old = parameters.get("old", "")
                new = parameters.get("new", "")
                
                result = input_values[0].replace(old, new)
            
            elif operation == "length":
                if len(input_values) < 1:
                    self.log_callback("Length operation requires at least one input")
                    return False
                
                result = len(input_values[0])
            
            elif operation == "split":
                if len(input_values) < 1:
                    self.log_callback("Split operation requires at least one input")
                    return False
                
                delimiter = parameters.get("delimiter", " ")
                
                result = input_values[0].split(delimiter)
            
            elif operation == "trim":
                if len(input_values) < 1:
                    self.log_callback("Trim operation requires at least one input")
                    return False
                
                result = input_values[0].strip()
            
            else:
                self.log_callback(f"Unknown string operation: {operation}")
                return False
            
            # Store the result
            if not simulate and output_var:
                variable_store[output_var] = result
                self.log_callback(f"Stored result '{result}' in variable '{output_var}'")
            
            return True
            
        except Exception as e:
            logger.exception(f"Error in string operation action: {e}")
            self.log_callback(f"String operation action failed: {e}")
            return False
    
    def handle_list_operation(self, params: ListOperationParams, simulate: bool, 
                             variable_store: Dict[str, Any]) -> bool:
        """
        Handle list operations.
        
        Args:
            params: List operation parameters
            simulate: Whether to simulate the action
            variable_store: Store for variables
            
        Returns:
            True if the action was successful, False otherwise
        """
        try:
            operation = params.operation
            list_var = params.list_variable
            input_value = params.input_value
            output_var = params.output_variable
            index = params.index
            
            # Log the action
            self.log_callback(f"{'Simulating' if simulate else 'Executing'} list {operation} operation")
            
            # Perform the operation
            if operation == "create":
                if not simulate:
                    variable_store[list_var] = []
                    self.log_callback(f"Created empty list in variable '{list_var}'")
            
            elif operation == "append":
                # Check if the list exists
                if list_var not in variable_store:
                    self.log_callback(f"List variable '{list_var}' not found")
                    return False
                
                # Check if it's a list
                if not isinstance(variable_store[list_var], list):
                    self.log_callback(f"Variable '{list_var}' is not a list")
                    return False
                
                # Append the value
                if not simulate:
                    variable_store[list_var].append(input_value)
                    self.log_callback(f"Appended '{input_value}' to list '{list_var}'")
            
            elif operation == "get":
                # Check if the list exists
                if list_var not in variable_store:
                    self.log_callback(f"List variable '{list_var}' not found")
                    return False
                
                # Check if it's a list
                if not isinstance(variable_store[list_var], list):
                    self.log_callback(f"Variable '{list_var}' is not a list")
                    return False
                
                # Check if the index is valid
                if index < 0 or index >= len(variable_store[list_var]):
                    self.log_callback(f"Index {index} out of range for list '{list_var}'")
                    return False
                
                # Get the value
                value = variable_store[list_var][index]
                
                # Store the result
                if not simulate and output_var:
                    variable_store[output_var] = value
                    self.log_callback(f"Stored value '{value}' from list '{list_var}' at index {index} in variable '{output_var}'")
            
            elif operation == "length":
                # Check if the list exists
                if list_var not in variable_store:
                    self.log_callback(f"List variable '{list_var}' not found")
                    return False
                
                # Check if it's a list
                if not isinstance(variable_store[list_var], list):
                    self.log_callback(f"Variable '{list_var}' is not a list")
                    return False
                
                # Get the length
                length = len(variable_store[list_var])
                
                # Store the result
                if not simulate and output_var:
                    variable_store[output_var] = length
                    self.log_callback(f"Stored length {length} of list '{list_var}' in variable '{output_var}'")
            
            elif operation == "clear":
                # Check if the list exists
                if list_var not in variable_store:
                    self.log_callback(f"List variable '{list_var}' not found")
                    return False
                
                # Check if it's a list
                if not isinstance(variable_store[list_var], list):
                    self.log_callback(f"Variable '{list_var}' is not a list")
                    return False
                
                # Clear the list
                if not simulate:
                    variable_store[list_var].clear()
                    self.log_callback(f"Cleared list '{list_var}'")
            
            else:
                self.log_callback(f"Unknown list operation: {operation}")
                return False
            
            return True
            
        except Exception as e:
            logger.exception(f"Error in list operation action: {e}")
            self.log_callback(f"List operation action failed: {e}")
            return False
    
    def handle_dict_operation(self, params: DictOperationParams, simulate: bool, 
                             variable_store: Dict[str, Any]) -> bool:
        """
        Handle dictionary operations.
        
        Args:
            params: Dictionary operation parameters
            simulate: Whether to simulate the action
            variable_store: Store for variables
            
        Returns:
            True if the action was successful, False otherwise
        """
        try:
            operation = params.operation
            dict_var = params.dict_variable
            key = params.key
            value = params.value
            output_var = params.output_variable
            
            # Log the action
            self.log_callback(f"{'Simulating' if simulate else 'Executing'} dictionary {operation} operation")
            
            # Perform the operation
            if operation == "create":
                if not simulate:
                    variable_store[dict_var] = {}
                    self.log_callback(f"Created empty dictionary in variable '{dict_var}'")
            
            elif operation == "set":
                # Check if the dictionary exists
                if dict_var not in variable_store:
                    self.log_callback(f"Dictionary variable '{dict_var}' not found")
                    return False
                
                # Check if it's a dictionary
                if not isinstance(variable_store[dict_var], dict):
                    self.log_callback(f"Variable '{dict_var}' is not a dictionary")
                    return False
                
                # Process the key and value
                processed_key = self._replace_variables(key, variable_store) if isinstance(key, str) else key
                processed_value = self._replace_variables(value, variable_store) if isinstance(value, str) else value
                
                # Set the key-value pair
                if not simulate:
                    variable_store[dict_var][processed_key] = processed_value
                    self.log_callback(f"Set '{processed_key}' to '{processed_value}' in dictionary '{dict_var}'")
            
            elif operation == "get":
                # Check if the dictionary exists
                if dict_var not in variable_store:
                    self.log_callback(f"Dictionary variable '{dict_var}' not found")
                    return False
                
                # Check if it's a dictionary
                if not isinstance(variable_store[dict_var], dict):
                    self.log_callback(f"Variable '{dict_var}' is not a dictionary")
                    return False
                
                # Process the key
                processed_key = self._replace_variables(key, variable_store) if isinstance(key, str) else key
                
                # Check if the key exists
                if processed_key not in variable_store[dict_var]:
                    self.log_callback(f"Key '{processed_key}' not found in dictionary '{dict_var}'")
                    return False
                
                # Get the value and store it in the output variable
                if not simulate and output_var:
                    value = variable_store[dict_var][processed_key]
                    variable_store[output_var] = value
                    self.log_callback(f"Got value '{value}' for key '{processed_key}' from dictionary '{dict_var}' and stored in '{output_var}'")
            
            elif operation == "keys":
                # Check if the dictionary exists
                if dict_var not in variable_store:
                    self.log_callback(f"Dictionary variable '{dict_var}' not found")
                    return False
                
                # Check if it's a dictionary
                if not isinstance(variable_store[dict_var], dict):
                    self.log_callback(f"Variable '{dict_var}' is not a dictionary")
                    return False
                
                # Get the keys and store them in the output variable
                if not simulate and output_var:
                    keys = list(variable_store[dict_var].keys())
                    variable_store[output_var] = keys
                    self.log_callback(f"Got keys {keys} from dictionary '{dict_var}' and stored in '{output_var}'")
            
            elif operation == "values":
                # Check if the dictionary exists
                if dict_var not in variable_store:
                    self.log_callback(f"Dictionary variable '{dict_var}' not found")
                    return False
                
                # Check if it's a dictionary
                if not isinstance(variable_store[dict_var], dict):
                    self.log_callback(f"Variable '{dict_var}' is not a dictionary")
                    return False
                
                # Get the values and store them in the output variable
                if not simulate and output_var:
                    values = list(variable_store[dict_var].values())
                    variable_store[output_var] = values
                    self.log_callback(f"Got values {values} from dictionary '{dict_var}' and stored in '{output_var}'")
            
            elif operation == "items":
                # Check if the dictionary exists
                if dict_var not in variable_store:
                    self.log_callback(f"Dictionary variable '{dict_var}' not found")
                    return False
                
                # Check if it's a dictionary
                if not isinstance(variable_store[dict_var], dict):
                    self.log_callback(f"Variable '{dict_var}' is not a dictionary")
                    return False
                
                # Get the items and store them in the output variable
                if not simulate and output_var:
                    items = list(variable_store[dict_var].items())
                    variable_store[output_var] = items
                    self.log_callback(f"Got items {items} from dictionary '{dict_var}' and stored in '{output_var}'")
            
            elif operation == "length":
                # Check if the dictionary exists
                if dict_var not in variable_store:
                    self.log_callback(f"Dictionary variable '{dict_var}' not found")
                    return False
                
                # Check if it's a dictionary
                if not isinstance(variable_store[dict_var], dict):
                    self.log_callback(f"Variable '{dict_var}' is not a dictionary")
                    return False
                
                # Get the length and store it in the output variable
                if not simulate and output_var:
                    length = len(variable_store[dict_var])
                    variable_store[output_var] = length
                    self.log_callback(f"Got length {length} of dictionary '{dict_var}' and stored in '{output_var}'")
            
            elif operation == "clear":
                # Check if the dictionary exists
                if dict_var not in variable_store:
                    self.log_callback(f"Dictionary variable '{dict_var}' not found")
                    return False
                
                # Check if it's a dictionary
                if not isinstance(variable_store[dict_var], dict):
                    self.log_callback(f"Variable '{dict_var}' is not a dictionary")
                    return False
                
                # Clear the dictionary
                if not simulate:
                    variable_store[dict_var].clear()
                    self.log_callback(f"Cleared dictionary '{dict_var}'")
            
            elif operation == "delete":
                # Check if the dictionary exists
                if dict_var not in variable_store:
                    self.log_callback(f"Dictionary variable '{dict_var}' not found")
                    return False
                
                # Check if it's a dictionary
                if not isinstance(variable_store[dict_var], dict):
                    self.log_callback(f"Variable '{dict_var}' is not a dictionary")
                    return False
                
                # Process the key
                processed_key = self._replace_variables(key, variable_store) if isinstance(key, str) else key
                
                # Check if the key exists
                if processed_key not in variable_store[dict_var]:
                    self.log_callback(f"Key '{processed_key}' not found in dictionary '{dict_var}'")
                    return False
                
                # Delete the key
                if not simulate:
                    del variable_store[dict_var][processed_key]
                    self.log_callback(f"Deleted key '{processed_key}' from dictionary '{dict_var}'")
            
            else:
                self.log_callback(f"Unknown dictionary operation: {operation}")
                return False
            
            return True
            
        except Exception as e:
            logger.exception(f"Error in dictionary operation action: {e}")
            self.log_callback(f"Dictionary operation action failed: {e}")
            return False
                
    def handle_math_operation(self, params: MathOperationParams, simulate: bool, 
                             variable_store: Dict[str, Any]) -> bool:
        """
        Handle math operations.
        
        Args:
            params: Math operation parameters
            simulate: Whether to simulate the action
            variable_store: Store for variables
            
        Returns:
            True if the action was successful, False otherwise
        """
        try:
            operation = params.operation
            operands = params.operands
            output_var = params.output_variable
            
            # Log the action
            self.log_callback(f"{'Simulating' if simulate else 'Executing'} math {operation} operation")
            
            # Process operands (replace variables and convert to numbers)
            processed_operands = []
            for operand in operands:
                if isinstance(operand, str):
                    # Replace variables in the operand
                    operand = self._replace_variables(operand, variable_store)
                    # Try to convert to number
                    try:
                        operand = float(operand)
                        # Convert to int if it's a whole number
                        if operand.is_integer():
                            operand = int(operand)
                    except ValueError:
                        self.log_callback(f"Operand '{operand}' is not a valid number")
                        return False
                elif not isinstance(operand, (int, float)):
                    self.log_callback(f"Operand '{operand}' is not a valid number")
                    return False
                
                processed_operands.append(operand)
            
            # Check if we have enough operands
            if len(processed_operands) < 1:
                self.log_callback("Math operation requires at least one operand")
                return False
            
            # Perform the operation
            result = None
            
            if operation == "add":
                result = sum(processed_operands)
            
            elif operation == "subtract":
                if len(processed_operands) < 2:
                    self.log_callback("Subtract operation requires at least two operands")
                    return False
                result = processed_operands[0]
                for operand in processed_operands[1:]:
                    result -= operand
            
            elif operation == "multiply":
                result = 1
                for operand in processed_operands:
                    result *= operand
            
            elif operation == "divide":
                if len(processed_operands) < 2:
                    self.log_callback("Divide operation requires at least two operands")
                    return False
                result = processed_operands[0]
                for operand in processed_operands[1:]:
                    if operand == 0:
                        self.log_callback("Division by zero")
                        return False
                    result /= operand
            
            elif operation == "modulo":
                if len(processed_operands) != 2:
                    self.log_callback("Modulo operation requires exactly two operands")
                    return False
                if processed_operands[1] == 0:
                    self.log_callback("Modulo by zero")
                    return False
                result = processed_operands[0] % processed_operands[1]
            
            elif operation == "power":
                if len(processed_operands) != 2:
                    self.log_callback("Power operation requires exactly two operands")
                    return False
                result = processed_operands[0] ** processed_operands[1]
            
            elif operation == "abs":
                if len(processed_operands) != 1:
                    self.log_callback("Absolute value operation requires exactly one operand")
                    return False
                result = abs(processed_operands[0])
            
            elif operation == "round":
                if len(processed_operands) < 1 or len(processed_operands) > 2:
                    self.log_callback("Round operation requires one or two operands")
                    return False
                
                if len(processed_operands) == 1:
                    result = round(processed_operands[0])
                else:
                    result = round(processed_operands[0], int(processed_operands[1]))
            
            elif operation == "floor":
                if len(processed_operands) != 1:
                    self.log_callback("Floor operation requires exactly one operand")
                    return False
                import math
                result = math.floor(processed_operands[0])
            
            elif operation == "ceil":
                if len(processed_operands) != 1:
                    self.log_callback("Ceiling operation requires exactly one operand")
                    return False
                import math
                result = math.ceil(processed_operands[0])
            
            elif operation == "min":
                result = min(processed_operands)
            
            elif operation == "max":
                result = max(processed_operands)
            
            else:
                self.log_callback(f"Unknown math operation: {operation}")
                return False
            
            # Store the result in the output variable
            if not simulate and output_var:
                variable_store[output_var] = result
                self.log_callback(f"Stored result '{result}' in variable '{output_var}'")
            
            return True
            
        except Exception as e:
            logger.exception(f"Error in math operation action: {e}")
            self.log_callback(f"Math operation action failed: {e}")
            return False
    
    def handle_random_value(self, params: RandomValueParams, simulate: bool, 
                           variable_store: Dict[str, Any]) -> bool:
        """
        Handle generating random values.
        
        Args:
            params: Random value parameters
            simulate: Whether to simulate the action
            variable_store: Store for variables
            
        Returns:
            True if the action was successful, False otherwise
        """
        try:
            value_type = params.value_type
            min_value = params.min_value
            max_value = params.max_value
            choices = params.choices
            output_var = params.output_variable
            
            # Log the action
            self.log_callback(f"{'Simulating' if simulate else 'Generating'} random {value_type} value")
            
            # Generate the random value
            result = None
            
            if value_type == "int":
                result = random.randint(int(min_value), int(max_value))
            
            elif value_type == "float":
                result = random.uniform(float(min_value), float(max_value))
            
            elif value_type == "choice":
                if not choices:
                    self.log_callback("Choice type requires a non-empty list of choices")
                    return False
                
                result = random.choice(choices)
            
            else:
                self.log_callback(f"Unknown random value type: {value_type}")
                return False
            
            # Store the result in the output variable
            if not simulate and output_var:
                variable_store[output_var] = result
                self.log_callback(f"Stored random value '{result}' in variable '{output_var}'")
            
            return True
            
        except Exception as e:
            logger.exception(f"Error in random value action: {e}")
            self.log_callback(f"Random value action failed: {e}")
            return False
    
    def handle_file_operation(self, params: FileOperationParams, simulate: bool, 
                             variable_store: Dict[str, Any]) -> bool:
        """
        Handle file operations.
        
        Args:
            params: File operation parameters
            simulate: Whether to simulate the action
            variable_store: Store for variables
            
        Returns:
            True if the action was successful, False otherwise
        """
        try:
            operation = params.operation
            file_path = params.file_path
            content = params.content
            output_var = params.output_variable
            format_type = params.format
            
            # Replace variables in file path and content
            file_path = self._replace_variables(file_path, variable_store)
            if content:
                content = self._replace_variables(content, variable_store)
            
            # Log the action
            self.log_callback(f"{'Simulating' if simulate else 'Executing'} file {operation} operation on '{file_path}'")
            
            # Perform the operation
            if operation == "read":
                if simulate:
                    self.log_callback(f"Simulating reading from file '{file_path}'")
                else:
                    if not os.path.exists(file_path):
                        self.log_callback(f"File '{file_path}' does not exist")
                        return False
                    
                    try:
                        if format_type == "text":
                            with open(file_path, 'r', encoding='utf-8') as f:
                                data = f.read()
                        elif format_type == "json":
                            with open(file_path, 'r', encoding='utf-8') as f:
                                data = json.load(f)
                        elif format_type == "csv":
                            import csv
                            with open(file_path, 'r', encoding='utf-8', newline='') as f:
                                reader = csv.reader(f)
                                data = list(reader)
                        else:
                            self.log_callback(f"Unknown file format: {format_type}")
                            return False
                        
                        if output_var:
                            variable_store[output_var] = data
                            self.log_callback(f"Read data from '{file_path}' and stored in variable '{output_var}'")
                    except Exception as e:
                        self.log_callback(f"Error reading file: {e}")
                        return False
            
            elif operation == "write":
                if simulate:
                    self.log_callback(f"Simulating writing to file '{file_path}'")
                else:
                    try:
                        # Create directory if it doesn't exist
                        os.makedirs(os.path.dirname(os.path.abspath(file_path)), exist_ok=True)
                        
                        if format_type == "text":
                            with open(file_path, 'w', encoding='utf-8') as f:
                                f.write(str(content))
                        elif format_type == "json":
                            with open(file_path, 'w', encoding='utf-8') as f:
                                if isinstance(content, str):
                                    try:
                                        # Try to parse content as JSON
                                        data = json.loads(content)
                                        json.dump(data, f, indent=2)
                                    except json.JSONDecodeError:
                                        # If not valid JSON, write as string
                                        f.write(content)
                                else:
                                    json.dump(content, f, indent=2)
                        elif format_type == "csv":
                            import csv
                            with open(file_path, 'w', encoding='utf-8', newline='') as f:
                                writer = csv.writer(f)
                                if isinstance(content, list):
                                    for row in content:
                                        writer.writerow(row if isinstance(row, list) else [row])
                                else:
                                    writer.writerow([content])
                        else:
                            self.log_callback(f"Unknown file format: {format_type}")
                            return False
                        
                        self.log_callback(f"Wrote data to file '{file_path}'")
                    except Exception as e:
                        self.log_callback(f"Error writing to file: {e}")
                        return False
            
            elif operation == "append":
                if simulate:
                    self.log_callback(f"Simulating appending to file '{file_path}'")
                else:
                    try:
                        # Create directory if it doesn't exist
                        os.makedirs(os.path.dirname(os.path.abspath(file_path)), exist_ok=True)
                        
                        if format_type == "text":
                            with open(file_path, 'a', encoding='utf-8') as f:
                                f.write(str(content))
                        elif format_type == "json":
                            # For JSON, we need to read the file first, update the data, then write it back
                            data = {}
                            if os.path.exists(file_path):
                                try:
                                    with open(file_path, 'r', encoding='utf-8') as f:
                                        data = json.load(f)
                                except json.JSONDecodeError:
                                    # If the file exists but is not valid JSON, start with empty data
                                    pass
                            
                            # Update the data
                            if isinstance(content, str):
                                try:
                                    # Try to parse content as JSON
                                    content_data = json.loads(content)
                                    if isinstance(content_data, dict):
                                        data.update(content_data)
                                    else:
                                        self.log_callback("Content is not a valid JSON object for append operation")
                                        return False
                                except json.JSONDecodeError:
                                    self.log_callback("Content is not valid JSON for append operation")
                                    return False
                            elif isinstance(content, dict):
                                data.update(content)
                            else:
                                self.log_callback("Content must be a JSON object for append operation")
                                return False
                            
                            # Write the updated data back to the file
                            with open(file_path, 'w', encoding='utf-8') as f:
                                json.dump(data, f, indent=2)
                        elif format_type == "csv":
                            import csv
                            with open(file_path, 'a', encoding='utf-8', newline='') as f:
                                writer = csv.writer(f)
                                if isinstance(content, list):
                                    for row in content:
                                        writer.writerow(row if isinstance(row, list) else [row])
                                else:
                                    writer.writerow([content])
                        else:
                            self.log_callback(f"Unknown file format: {format_type}")
                            return False
                        
                        self.log_callback(f"Appended data to file '{file_path}'")
                    except Exception as e:
                        self.log_callback(f"Error appending to file: {e}")
                        return False
            
            else:
                self.log_callback(f"Unknown file operation: {operation}")
                return False
            
            return True
            
        except Exception as e:
            logger.exception(f"Error in file operation action: {e}")
            self.log_callback(f"File operation action failed: {e}")
            return False
    
    def _replace_variables(self, text: str, variable_store: Dict[str, Any]) -> str:
        """
        Replace variables in a string with their values from the variable store.
        
        Args:
            text: Text containing variables in the format ${variable_name}
            variable_store: Store of variables
            
        Returns:
            Text with variables replaced by their values
        """
        if not isinstance(text, str):
            return text
        
        def replace_match(match):
            var_name = match.group(1)
            if var_name in variable_store:
                return str(variable_store[var_name])
            return match.group(0)  # Return the original if variable not found
        
        return self.variable_pattern.sub(replace_match, text)
    
    def _evaluate_expression(self, expression: str, variable_store: Optional[Dict[str, Any]] = None) -> Any:
        """
        Safely evaluate an expression with variables.
        
        Args:
            expression: Expression to evaluate
            variable_store: Store of variables
            
        Returns:
            Result of the evaluation
        """
        try:
            # Create a safe environment with limited builtins
            safe_globals = {
                "__builtins__": {
                    "abs": abs,
                    "bool": bool,
                    "float": float,
                    "int": int,
                    "len": len,
                    "max": max,
                    "min": min,
                    "round": round,
                    "str": str,
                    "sum": sum
                }
            }
            
            # Add math functions
            import math
            safe_globals.update({
                "math": {
                    "ceil": math.ceil,
                    "floor": math.floor,
                    "sqrt": math.sqrt,
                    "sin": math.sin,
                    "cos": math.cos,
                    "tan": math.tan,
                    "pi": math.pi,
                    "e": math.e
                }
            })
            
            # Use variable store as locals
            safe_locals = variable_store.copy() if variable_store else {}
            
            # Evaluate the expression
            return eval(expression, safe_globals, safe_locals)
            
        except Exception as e:
            logger.exception(f"Error evaluating expression '{expression}': {e}")
            raise ValueError(f"Error evaluating expression: {e}")
        