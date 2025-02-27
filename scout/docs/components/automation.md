# Automation Component

## Overview

The Automation component is responsible for executing sequences of actions to automate interactions with the game. It provides a flexible and powerful system for defining, managing, and executing automation sequences with robust error handling and progress tracking.

## Architecture

The Automation component follows a modular design with clear separation between core functionality, execution, and specialized action handlers:

```
automation/
├── __init__.py
├── core.py                        # Core automation functionality
├── executor.py                    # Sequence execution engine
├── progress_tracker.py            # Tracks execution progress
├── action_handlers_basic.py       # Basic action implementations
├── action_handlers_flow.py        # Flow control actions
├── action_handlers_advancedflow.py # Advanced flow control
├── action_handlers_data.py        # Data manipulation actions
├── action_handlers_visual.py      # Visual detection actions
└── gui/                           # Automation UI components
    ├── __init__.py
    ├── automation_tab.py          # Main automation UI tab
    └── sequence_builder.py        # UI for building sequences
```

## Key Components

### AutomationCore

The `AutomationCore` is the central component that coordinates all automation activities:

```python
class AutomationCore:
    """
    Core automation system that coordinates sequence execution,
    action handling, and integration with other components.
    
    This class serves as the main entry point for automation
    functionality and provides a high-level API for automation tasks.
    """
    
    def __init__(self, window_interface, template_matcher, text_ocr, 
                 game_actions, config_manager, signal_bus=None):
        """Initialize the automation core with required dependencies."""
        self._window_interface = window_interface
        self._template_matcher = template_matcher
        self._text_ocr = text_ocr
        self._game_actions = game_actions
        self._config_manager = config_manager
        self._signal_bus = signal_bus
        
        # Create executor and progress tracker
        self._progress_tracker = ProgressTracker()
        self._executor = SequenceExecutor(
            window_interface=window_interface,
            template_matcher=template_matcher,
            text_ocr=text_ocr,
            game_actions=game_actions,
            progress_tracker=self._progress_tracker,
            signal_bus=signal_bus
        )
        
        # Initialize action handlers
        self._initialize_action_handlers()
        
        # Load saved sequences
        self._sequences = {}
        self._load_sequences()
```

### SequenceExecutor

The `SequenceExecutor` is responsible for executing automation sequences:

- Manages the execution flow of action sequences
- Handles pausing, resuming, and stopping execution
- Provides step-by-step execution for debugging
- Implements error handling and recovery strategies
- Emits signals for execution events (step completed, sequence completed, errors)

### ProgressTracker

The `ProgressTracker` monitors and reports on the progress of automation sequences:

- Tracks the current step in the sequence
- Calculates completion percentage
- Records execution time
- Maintains execution history
- Provides statistics on sequence performance

### Action Handlers

The Automation component includes several specialized action handlers:

#### Basic Actions (`action_handlers_basic.py`)
- Mouse clicks (left, right, middle)
- Key presses and combinations
- Mouse movement
- Delays and waits

#### Flow Control Actions (`action_handlers_flow.py`)
- Conditional execution (if/else)
- Loops (for, while)
- Sequence calls (sub-sequences)
- Error handling (try/catch)

#### Advanced Flow Control (`action_handlers_advancedflow.py`)
- Parallel execution
- State machines
- Event-driven actions
- Complex branching logic

#### Data Actions (`action_handlers_data.py`)
- Variable manipulation
- Data extraction
- Calculations
- String operations

#### Visual Actions (`action_handlers_visual.py`)
- Template matching
- Color detection
- Text recognition (OCR)
- Image comparison

## Sequence Definition

Automation sequences are defined as a series of actions with parameters:

```python
sequence = {
    "name": "Collect Resources",
    "description": "Automatically collects resources from the map",
    "version": "1.0",
    "actions": [
        {
            "type": "click",
            "x": 100,
            "y": 200,
            "button": "left",
            "description": "Click on map button"
        },
        {
            "type": "wait",
            "duration": 1.5,
            "description": "Wait for map to open"
        },
        {
            "type": "find_template",
            "template": "resource_icon",
            "variable": "resource_pos",
            "description": "Find resource icon"
        },
        {
            "type": "if",
            "condition": "resource_pos != None",
            "then": [
                {
                    "type": "click",
                    "x": "resource_pos[0]",
                    "y": "resource_pos[1]",
                    "description": "Click on resource"
                }
            ],
            "else": [
                {
                    "type": "log",
                    "message": "No resources found",
                    "level": "warning"
                }
            ]
        }
    ]
}
```

## Execution Context

The `ExecutionContext` maintains the state during sequence execution:

- Variables and their values
- Execution settings (delay between steps, error handling mode)
- References to required components (template matcher, game actions, etc.)
- Logging and debugging information

## Integration with Other Components

The Automation component integrates with several other parts of the application:

- **Window Interface**: For capturing screenshots and window information
- **Template Matcher**: For finding game elements
- **Text OCR**: For reading text from the game
- **Game Actions**: For interacting with the game
- **Configuration Manager**: For loading and saving sequences and settings
- **Signal Bus**: For communicating with other components

## Error Handling

The Automation component includes robust error handling:

- Configurable error handling modes (stop, continue, retry)
- Detailed error reporting
- Recovery strategies
- Timeout handling
- Validation of sequence definitions

## Performance Optimization

The Automation system is optimized for performance:

- Efficient action execution
- Minimal overhead between steps
- Optimized template matching and OCR calls
- Resource cleanup after execution
- Parallel execution where appropriate

## Extensibility

The Automation component is designed to be easily extended:

- New action types can be added by implementing new action handlers
- Custom execution strategies can be implemented
- Additional error handling strategies can be added
- The sequence format supports versioning for backward compatibility

## User Interface

The Automation component includes UI elements for:

- Creating and editing sequences
- Managing saved sequences
- Executing sequences
- Monitoring execution progress
- Debugging sequences

## Future Enhancements

Planned improvements for the Automation component:

- Visual sequence builder with drag-and-drop interface
- Advanced debugging tools (breakpoints, variable inspection)
- Performance profiling for sequences
- AI-assisted sequence creation
- Cloud synchronization of sequences

## Usage Examples

### Creating and Running a Simple Sequence

```python
# Create a simple sequence
sequence = {
    "name": "Click Center",
    "description": "Clicks in the center of the game window",
    "actions": [
        {
            "type": "click",
            "x": "window_width / 2",
            "y": "window_height / 2",
            "button": "left",
            "description": "Click center"
        }
    ]
}

# Add the sequence to the automation core
automation_core.add_sequence(sequence)

# Run the sequence
automation_core.run_sequence("Click Center")
```

### Using Variables and Conditions

```python
# Create a sequence with variables and conditions
sequence = {
    "name": "Find and Click",
    "description": "Finds a template and clicks on it if found",
    "actions": [
        {
            "type": "find_template",
            "template": "button_template",
            "variable": "button_pos",
            "description": "Find button"
        },
        {
            "type": "if",
            "condition": "button_pos != None",
            "then": [
                {
                    "type": "click",
                    "x": "button_pos[0]",
                    "y": "button_pos[1]",
                    "description": "Click on button"
                }
            ],
            "else": [
                {
                    "type": "log",
                    "message": "Button not found",
                    "level": "warning"
                }
            ]
        }
    ]
}

# Run the sequence
automation_core.run_sequence("Find and Click")
```

### Creating a Loop

```python
# Create a sequence with a loop
sequence = {
    "name": "Click Multiple Times",
    "description": "Clicks multiple times at a position",
    "actions": [
        {
            "type": "set_variable",
            "name": "counter",
            "value": 0,
            "description": "Initialize counter"
        },
        {
            "type": "while",
            "condition": "counter < 5",
            "actions": [
                {
                    "type": "click",
                    "x": 100,
                    "y": 200,
                    "description": "Click position"
                },
                {
                    "type": "wait",
                    "duration": 0.5,
                    "description": "Wait between clicks"
                },
                {
                    "type": "set_variable",
                    "name": "counter",
                    "value": "counter + 1",
                    "description": "Increment counter"
                }
            ]
        }
    ]
}

# Run the sequence
automation_core.run_sequence("Click Multiple Times")
```