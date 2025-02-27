"""
Automation Actions

This module defines the action types and parameter classes for automation actions.
Actions represent operations that can be performed during automation sequences,
such as clicking, typing, waiting, and more complex operations.
"""

import enum
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional, Union, Type, TypeVar, Generic, Callable
import json
import logging
from abc import ABC, abstractmethod

logger = logging.getLogger(__name__)

class ActionType(enum.Enum):
    """
    Types of automation actions.
    """
    # Basic actions
    CLICK = "click"
    RIGHT_CLICK = "right_click"
    DOUBLE_CLICK = "double_click"
    DRAG = "drag"
    TYPE_TEXT = "type_text"
    WAIT = "wait"
    
    # Visual actions
    TEMPLATE_SEARCH = "template_search"
    WAIT_FOR_OCR = "wait_for_ocr"
    
    # Flow control
    CONDITIONAL = "conditional"
    LOOP = "loop"
    
    # Data manipulation
    VARIABLE_SET = "variable_set"
    VARIABLE_INCREMENT = "variable_increment"
    STRING_OPERATION = "string_operation"
    LIST_OPERATION = "list_operation"
    DICT_OPERATION = "dict_operation"
    MATH_OPERATION = "math_operation"
    FILE_OPERATION = "file_operation"
    
    # Advanced flow control
    SWITCH_CASE = "switch_case"
    TRY_CATCH = "try_catch"
    PARALLEL_EXECUTION = "parallel_execution"
    BREAKPOINT = "breakpoint"
    
    # Utility
    LOG = "log"
    SCREENSHOT = "screenshot"


@dataclass
class ActionParamsCommon:
    """
    Common parameters for all actions.
    
    Attributes:
        name: Name of the action
        description: Description of the action
        enabled: Whether the action is enabled
        timeout: Timeout for the action in seconds
        retry_count: Number of times to retry the action
        retry_interval: Interval between retries in seconds
        on_failure: What to do if the action fails
        failure_message: Message to display if the action fails
    """
    name: str = ""
    description: str = ""
    enabled: bool = True
    timeout: float = 30.0
    retry_count: int = 0
    retry_interval: float = 1.0
    on_failure: str = "stop"  # stop, continue, retry
    failure_message: str = ""


@dataclass
class ClickParams(ActionParamsCommon):
    """
    Parameters for click actions.
    
    Attributes:
        x: X coordinate to click
        y: Y coordinate to click
        button: Mouse button to use
        relative_to: What the coordinates are relative to
        move_duration: Duration of mouse movement in seconds
    """
    x: int = 0
    y: int = 0
    button: str = "left"  # left, right, middle
    relative_to: str = "window"  # window, screen, last_match
    move_duration: float = 0.2


@dataclass
class DragParams(ActionParamsCommon):
    """
    Parameters for drag actions.
    
    Attributes:
        start_x: Starting X coordinate
        start_y: Starting Y coordinate
        end_x: Ending X coordinate
        end_y: Ending Y coordinate
        button: Mouse button to use
        relative_to: What the coordinates are relative to
        duration: Duration of the drag in seconds
    """
    start_x: int = 0
    start_y: int = 0
    end_x: int = 0
    end_y: int = 0
    button: str = "left"  # left, right, middle
    relative_to: str = "window"  # window, screen, last_match
    duration: float = 0.5


@dataclass
class TypeParams(ActionParamsCommon):
    """
    Parameters for typing actions.
    
    Attributes:
        text: Text to type
        delay: Delay between keystrokes in seconds
        use_clipboard: Whether to use clipboard for pasting
    """
    text: str = ""
    delay: float = 0.05
    use_clipboard: bool = False


@dataclass
class WaitParams(ActionParamsCommon):
    """
    Parameters for wait actions.
    
    Attributes:
        duration: Duration to wait in seconds
        random_variation: Random variation to add/subtract from duration
    """
    duration: float = 1.0
    random_variation: float = 0.0


@dataclass
class TemplateSearchParams(ActionParamsCommon):
    """
    Parameters for template search actions.
    
    Attributes:
        template_path: Path to the template image
        confidence: Confidence threshold for matching
        search_region: Region to search in (x, y, width, height)
        max_matches: Maximum number of matches to find
        save_to_variable: Variable to save the match results to
    """
    template_path: str = ""
    confidence: float = 0.8
    search_region: Optional[List[int]] = None  # [x, y, width, height]
    max_matches: int = 1
    save_to_variable: str = ""


@dataclass
class OCRWaitParams(ActionParamsCommon):
    """
    Parameters for OCR wait actions.
    
    Attributes:
        text: Text to wait for
        region: Region to search in (x, y, width, height)
        case_sensitive: Whether the search is case sensitive
        save_to_variable: Variable to save the OCR results to
    """
    text: str = ""
    region: Optional[List[int]] = None  # [x, y, width, height]
    case_sensitive: bool = False
    save_to_variable: str = ""


@dataclass
class ConditionalParams(ActionParamsCommon):
    """
    Parameters for conditional actions.
    
    Attributes:
        condition: Condition to evaluate
        then_actions: Actions to execute if condition is true
        else_actions: Actions to execute if condition is false
    """
    condition: str = ""
    then_actions: List[Dict[str, Any]] = field(default_factory=list)
    else_actions: List[Dict[str, Any]] = field(default_factory=list)


@dataclass
class LoopParams(ActionParamsCommon):
    """
    Parameters for loop actions.
    
    Attributes:
        loop_type: Type of loop
        count: Number of iterations for count loops
        condition: Condition for while loops
        variable: Variable for for-each loops
        collection: Collection for for-each loops
        actions: Actions to execute in the loop
    """
    loop_type: str = "count"  # count, while, for-each
    count: int = 1
    condition: str = ""
    variable: str = ""
    collection: str = ""
    actions: List[Dict[str, Any]] = field(default_factory=list)


@dataclass
class VariableSetParams(ActionParamsCommon):
    """
    Parameters for variable set actions.
    
    Attributes:
        variable_name: Name of the variable to set
        value: Value to set
        value_type: Type of the value
    """
    variable_name: str = ""
    value: Any = None
    value_type: str = "string"  # string, number, boolean, list, dict


@dataclass
class VariableIncrementParams(ActionParamsCommon):
    """
    Parameters for variable increment actions.
    
    Attributes:
        variable_name: Name of the variable to increment
        increment_by: Amount to increment by
    """
    variable_name: str = ""
    increment_by: float = 1.0


@dataclass
class StringOperationParams(ActionParamsCommon):
    """
    Parameters for string operation actions.
    
    Attributes:
        operation: Type of string operation
        input_string: Input string
        additional_input: Additional input for the operation
        result_variable: Variable to store the result
    """
    operation: str = "concat"  # concat, substring, replace, format, etc.
    input_string: str = ""
    additional_input: str = ""
    result_variable: str = ""


@dataclass
class ListOperationParams(ActionParamsCommon):
    """
    Parameters for list operation actions.
    
    Attributes:
        operation: Type of list operation
        list_variable: List variable to operate on
        item: Item for the operation
        index: Index for the operation
        result_variable: Variable to store the result
    """
    operation: str = "create"  # create, append, get, set, remove, etc.
    list_variable: str = ""
    item: Any = None
    index: int = 0
    result_variable: str = ""


@dataclass
class DictOperationParams(ActionParamsCommon):
    """
    Parameters for dictionary operation actions.
    
    Attributes:
        operation: Type of dictionary operation
        dict_variable: Dictionary variable to operate on
        key: Key for the operation
        value: Value for the operation
        result_variable: Variable to store the result
    """
    operation: str = "create"  # create, get, set, remove, etc.
    dict_variable: str = ""
    key: str = ""
    value: Any = None
    result_variable: str = ""


@dataclass
class MathOperationParams(ActionParamsCommon):
    """
    Parameters for math operation actions.
    
    Attributes:
        operation: Type of math operation
        operand1: First operand
        operand2: Second operand
        result_variable: Variable to store the result
    """
    operation: str = "add"  # add, subtract, multiply, divide, etc.
    operand1: Union[float, str] = 0.0
    operand2: Union[float, str] = 0.0
    result_variable: str = ""


@dataclass
class FileOperationParams(ActionParamsCommon):
    """
    Parameters for file operation actions.
    
    Attributes:
        operation: Type of file operation
        file_path: Path to the file
        content: Content for write operations
        result_variable: Variable to store the result
    """
    operation: str = "read"  # read, write, append, etc.
    file_path: str = ""
    content: str = ""
    result_variable: str = ""


@dataclass
class LogParams(ActionParamsCommon):
    """
    Parameters for log actions.
    
    Attributes:
        message: Message to log
        level: Log level
    """
    message: str = ""
    level: str = "info"  # debug, info, warning, error


@dataclass
class ScreenshotParams(ActionParamsCommon):
    """
    Parameters for screenshot actions.
    
    Attributes:
        region: Region to capture (x, y, width, height)
        file_path: Path to save the screenshot
        include_timestamp: Whether to include a timestamp in the filename
    """
    region: Optional[List[int]] = None  # [x, y, width, height]
    file_path: str = ""
    include_timestamp: bool = True


@dataclass
class SwitchCaseParams(ActionParamsCommon):
    """
    Parameters for switch/case actions.
    
    Attributes:
        expression: Expression to evaluate
        cases: Dictionary of case values to actions
        default_actions: Actions to execute if no case matches
    """
    expression: str = ""
    cases: Dict[str, List[Dict[str, Any]]] = field(default_factory=dict)
    default_actions: List[Dict[str, Any]] = field(default_factory=list)


@dataclass
class TryCatchParams(ActionParamsCommon):
    """
    Parameters for try/catch actions.
    
    Attributes:
        try_actions: Actions to execute in the try block
        catch_actions: Actions to execute in the catch block
        finally_actions: Actions to execute in the finally block
        error_variable: Variable to store the error
    """
    try_actions: List[Dict[str, Any]] = field(default_factory=list)
    catch_actions: List[Dict[str, Any]] = field(default_factory=list)
    finally_actions: List[Dict[str, Any]] = field(default_factory=list)
    error_variable: str = ""


@dataclass
class ParallelExecutionParams(ActionParamsCommon):
    """
    Parameters for parallel execution actions.
    
    Attributes:
        actions: List of action groups to execute in parallel
        max_workers: Maximum number of worker threads
        wait_for_all: Whether to wait for all actions to complete
    """
    actions: List[List[Dict[str, Any]]] = field(default_factory=list)
    max_workers: int = 4
    wait_for_all: bool = True


@dataclass
class BreakpointParams(ActionParamsCommon):
    """
    Parameters for breakpoint actions.
    
    Attributes:
        condition: Condition to evaluate for the breakpoint
        message: Message to display when the breakpoint is hit
    """
    condition: str = "True"
    message: str = "Breakpoint hit"


class AutomationAction:
    """
    Represents an action to be performed during automation.
    
    This class encapsulates an action type and its parameters.
    """
    
    def __init__(self, action_type: ActionType, params: Union[
        ClickParams, DragParams, TypeParams, WaitParams,
        TemplateSearchParams, OCRWaitParams, ConditionalParams, LoopParams,
        VariableSetParams, VariableIncrementParams, StringOperationParams,
        ListOperationParams, DictOperationParams, MathOperationParams,
        FileOperationParams, LogParams, ScreenshotParams,
        SwitchCaseParams, TryCatchParams, ParallelExecutionParams, BreakpointParams
    ]):
        """
        Initialize an automation action.
        
        Args:
            action_type: Type of action
            params: Parameters for the action
        """
        self.action_type = action_type
        self.params = params
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Convert the action to a dictionary.
        
        Returns:
            Dictionary representation of the action
        """
        result = {
            "type": self.action_type.value,
            "params": {}
        }
        
        # Convert params to dictionary
        for key, value in self.params.__dict__.items():
            # Handle nested actions for complex action types
            if key in ("then_actions", "else_actions", "actions", "try_actions", 
                      "catch_actions", "finally_actions") and isinstance(value, list):
                result["params"][key] = [
                    action.to_dict() if isinstance(action, AutomationAction) else action
                    for action in value
                ]
            elif key == "cases" and isinstance(value, dict):
                result["params"][key] = {
                    case_key: [
                        action.to_dict() if isinstance(action, AutomationAction) else action
                        for action in case_actions
                    ]
                    for case_key, case_actions in value.items()
                }
            elif key == "actions" and isinstance(value, list) and all(isinstance(item, list) for item in value):
                # Handle parallel execution actions
                result["params"][key] = [
                    [
                        action.to_dict() if isinstance(action, AutomationAction) else action
                        for action in action_group
                    ]
                    for action_group in value
                ]
            else:
                result["params"][key] = value
        
        return result
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'AutomationAction':
        """
        Create an action from a dictionary.
        
        Args:
            data: Dictionary representation of the action
            
        Returns:
            AutomationAction instance
        """
        action_type = ActionType(data["type"])
        params_data = data.get("params", {})
        
        # Handle nested actions for complex action types
        if action_type == ActionType.CONDITIONAL:
            if "then_actions" in params_data:
                params_data["then_actions"] = [
                    cls.from_dict(action) if isinstance(action, dict) and "type" in action else action
                    for action in params_data["then_actions"]
                ]
            if "else_actions" in params_data:
                params_data["else_actions"] = [
                    cls.from_dict(action) if isinstance(action, dict) and "type" in action else action
                    for action in params_data["else_actions"]
                ]
        elif action_type in (ActionType.LOOP, ActionType.TRY_CATCH):
            for key in ("actions", "try_actions", "catch_actions", "finally_actions"):
                if key in params_data:
                    params_data[key] = [
                        cls.from_dict(action) if isinstance(action, dict) and "type" in action else action
                        for action in params_data[key]
                    ]
        elif action_type == ActionType.SWITCH_CASE and "cases" in params_data:
            params_data["cases"] = {
                case_key: [
                    cls.from_dict(action) if isinstance(action, dict) and "type" in action else action
                    for action in case_actions
                ]
                for case_key, case_actions in params_data["cases"].items()
            }
            if "default_actions" in params_data:
                params_data["default_actions"] = [
                    cls.from_dict(action) if isinstance(action, dict) and "type" in action else action
                    for action in params_data["default_actions"]
                ]
        elif action_type == ActionType.PARALLEL_EXECUTION and "actions" in params_data:
            params_data["actions"] = [
                [
                    cls.from_dict(action) if isinstance(action, dict) and "type" in action else action
                    for action in action_group
                ]
                for action_group in params_data["actions"]
            ]
        
        # Create appropriate params object based on action type
        return create_action_from_type(action_type, **params_data)


class ActionHandler(ABC):
    """
    Abstract base class for action handlers.
    
    Action handlers are responsible for executing specific types of actions.
    """
    
    @abstractmethod
    def can_handle(self, action_type: ActionType) -> bool:
        """
        Check if this handler can handle the given action type.
        
        Args:
            action_type: Type of action to check
            
        Returns:
            True if this handler can handle the action type, False otherwise
        """
        pass
    
    @abstractmethod
    def handle(self, action: AutomationAction, context: Any, simulate: bool = False) -> bool:
        """
        Handle the given action.
        
        Args:
            action: Action to handle
            context: Execution context
            simulate: Whether to simulate the action
            
        Returns:
            True if the action was handled successfully, False otherwise
        """
        pass
    
    def validate_params(self, action: AutomationAction) -> bool:
        """
        Validate the parameters of the given action.
        
        Args:
            action: Action to validate
            
        Returns:
            True if the parameters are valid, False otherwise
        """
        # Default implementation always returns True
        # Subclasses should override this method to provide specific validation
        return True
    
    def log_action(self, action: AutomationAction, message: str, level: str = "info") -> None:
        """
        Log information about the action.
        
        Args:
            action: Action being executed
            message: Message to log
            level: Log level
        """
        log_func = getattr(logger, level.lower(), logger.info)
        action_name = action.params.name or action.action_type.value
        log_func(f"[{action_name}] {message}")


def create_action_from_type(action_type: ActionType, **params) -> AutomationAction:
    """
    Create an action of the specified type with the given parameters.
    
    Args:
        action_type: Type of action to create
        **params: Parameters for the action
        
    Returns:
        AutomationAction instance
    """
    # Create appropriate params object based on action type
    if action_type in (ActionType.CLICK, ActionType.RIGHT_CLICK, ActionType.DOUBLE_CLICK):
        params_obj = ClickParams(**params)
    elif action_type == ActionType.DRAG:
        params_obj = DragParams(**params)
    elif action_type == ActionType.TYPE_TEXT:
        params_obj = TypeParams(**params)
    elif action_type == ActionType.WAIT:
        params_obj = WaitParams(**params)
    elif action_type == ActionType.TEMPLATE_SEARCH:
        params_obj = TemplateSearchParams(**params)
    elif action_type == ActionType.WAIT_FOR_OCR:
        params_obj = OCRWaitParams(**params)
    elif action_type == ActionType.CONDITIONAL:
        params_obj = ConditionalParams(**params)
    elif action_type == ActionType.LOOP:
        params_obj = LoopParams(**params)
    elif action_type == ActionType.VARIABLE_SET:
        params_obj = VariableSetParams(**params)
    elif action_type == ActionType.VARIABLE_INCREMENT:
        params_obj = VariableIncrementParams(**params)
    elif action_type == ActionType.STRING_OPERATION:
        params_obj = StringOperationParams(**params)
    elif action_type == ActionType.LIST_OPERATION:
        params_obj = ListOperationParams(**params)
    elif action_type == ActionType.DICT_OPERATION:
        params_obj = DictOperationParams(**params)
    elif action_type == ActionType.MATH_OPERATION:
        params_obj = MathOperationParams(**params)
    elif action_type == ActionType.FILE_OPERATION:
        params_obj = FileOperationParams(**params)
    elif action_type == ActionType.LOG:
        params_obj = LogParams(**params)
    elif action_type == ActionType.SCREENSHOT:
        params_obj = ScreenshotParams(**params)
    elif action_type == ActionType.SWITCH_CASE:
        params_obj = SwitchCaseParams(**params)
    elif action_type == ActionType.TRY_CATCH:
        params_obj = TryCatchParams(**params)
    elif action_type == ActionType.PARALLEL_EXECUTION:
        params_obj = ParallelExecutionParams(**params)
    elif action_type == ActionType.BREAKPOINT:
        params_obj = BreakpointParams(**params)
    else:
        raise ValueError(f"Unknown action type: {action_type}")
    
    # Validate required parameters
    validate_action_params(action_type, params_obj)
    
    return AutomationAction(action_type, params_obj)


def validate_action_params(action_type: ActionType, params: Any) -> None:
    """
    Validate that the parameters for an action are valid.
    
    Args:
        action_type: Type of action
        params: Parameters for the action
        
    Raises:
        ValueError: If the parameters are invalid
    """
    # Validate common parameters
    if not params.name:
        params.name = f"{action_type.value}_action"
    
    # Validate specific parameters based on action type
    if action_type in (ActionType.CLICK, ActionType.RIGHT_CLICK, ActionType.DOUBLE_CLICK):
        if not isinstance(params.x, (int, float)) or not isinstance(params.y, (int, float)):
            raise ValueError(f"Click action requires valid x and y coordinates")
    elif action_type == ActionType.DRAG:
        if not all(isinstance(v, (int, float)) for v in [params.start_x, params.start_y, params.end_x, params.end_y]):
            raise ValueError(f"Drag action requires valid start and end coordinates")
    elif action_type == ActionType.TYPE_TEXT:
        if not params.text:
            raise ValueError(f"Type action requires text to type")
    elif action_type == ActionType.TEMPLATE_SEARCH:
        if not params.template_path:
            raise ValueError(f"Template search action requires a template path")
    elif action_type == ActionType.WAIT_FOR_OCR:
        if not params.text:
            raise ValueError(f"OCR wait action requires text to wait for")
    elif action_type == ActionType.CONDITIONAL:
        if not params.condition:
            raise ValueError(f"Conditional action requires a condition")
    elif action_type == ActionType.LOOP:
        if params.loop_type == "count" and params.count <= 0:
            raise ValueError(f"Count loop requires a positive count")
        elif params.loop_type == "while" and not params.condition:
            raise ValueError(f"While loop requires a condition")
        elif params.loop_type == "for-each" and (not params.variable or not params.collection):
            raise ValueError(f"For-each loop requires a variable and collection")
    elif action_type == ActionType.VARIABLE_SET:
        if not params.variable_name:
            raise ValueError(f"Variable set action requires a variable name")
    elif action_type == ActionType.VARIABLE_INCREMENT:
        if not params.variable_name:
            raise ValueError(f"Variable increment action requires a variable name")
    elif action_type == ActionType.STRING_OPERATION:
        if not params.operation or not params.result_variable:
            raise ValueError(f"String operation requires an operation and result variable")
    elif action_type == ActionType.LIST_OPERATION:
        if not params.operation or not params.list_variable:
            raise ValueError(f"List operation requires an operation and list variable")
    elif action_type == ActionType.DICT_OPERATION:
        if not params.operation or not params.dict_variable:
            raise ValueError(f"Dict operation requires an operation and dict variable")
    elif action_type == ActionType.MATH_OPERATION:
        if not params.operation or not params.result_variable:
            raise ValueError(f"Math operation requires an operation and result variable")
    elif action_type == ActionType.FILE_OPERATION:
        if not params.operation or not params.file_path:
            raise ValueError(f"File operation requires an operation and file path")
    elif action_type == ActionType.LOG:
        if not params.message:
            raise ValueError(f"Log action requires a message")
    elif action_type == ActionType.SCREENSHOT:
        if not params.file_path:
            raise ValueError(f"Screenshot action requires a file path")
    elif action_type == ActionType.SWITCH_CASE:
        if not params.expression or not params.cases:
            raise ValueError(f"Switch/case action requires an expression and cases")
    elif action_type == ActionType.PARALLEL_EXECUTION:
        if not params.actions:
            raise ValueError(f"Parallel execution action requires actions")
