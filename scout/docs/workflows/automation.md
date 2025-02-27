# Automation Workflow

## Overview

The automation workflow in TB Scout enables users to create, manage, and execute sequences of actions to automate interactions with the game. This document describes the complete workflow from sequence creation to execution and monitoring.

## Workflow Diagram

```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│                 │     │                 │     │                 │
│  Create/Edit    │────►│ Validate        │────►│ Save Sequence   │
│  Sequence       │     │ Sequence        │     │                 │
│                 │     │                 │     │                 │
└─────────────────┘     └─────────────────┘     └─────────────────┘
         │                                               │
         │                                               ▼
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│                 │     │                 │     │                 │
│ Monitor Progress│◄────│ Execute         │◄────│ Load Sequence   │
│                 │     │ Sequence        │     │                 │
└─────────────────┘     └─────────────────┘     └─────────────────┘
```

## Sequence Creation

### Using the Sequence Builder UI

The Sequence Builder provides a graphical interface for creating automation sequences:

1. Open the Automation tab in the main application
2. Click "New Sequence" to create a new sequence
3. Add actions using the "Add Action" button
4. Configure each action's parameters
5. Arrange actions using drag-and-drop
6. Save the sequence with a descriptive name

### Manual JSON Creation

Sequences can also be created manually as JSON files:

```json
{
  "name": "Farm Resources",
  "description": "Automatically farms resources from the map",
  "version": "1.0",
  "actions": [
    {
      "type": "find_template",
      "template": "resource_icon",
      "variable": "resource",
      "threshold": 0.8,
      "description": "Find resource on map"
    },
    {
      "type": "if",
      "condition": "resource != None",
      "then": [
        {
          "type": "click_template",
          "template_result": "resource",
          "description": "Click on resource"
        }
      ],
      "else": [
        {
          "type": "log",
          "message": "No resource found",
          "level": "warning"
        }
      ]
    }
  ]
}
```

### Action Types

TB Scout supports various action types for different automation needs:

#### Basic Actions

- **click**: Click at specific coordinates
- **right_click**: Right-click at specific coordinates
- **double_click**: Double-click at specific coordinates
- **key_press**: Press a keyboard key
- **key_combination**: Press a combination of keys
- **text_input**: Type text
- **mouse_move**: Move the mouse to coordinates
- **scroll**: Scroll the mouse wheel

#### Template Actions

- **find_template**: Find a template on screen
- **click_template**: Click on a found template
- **wait_for_template**: Wait until a template appears
- **wait_for_template_to_vanish**: Wait until a template disappears

#### OCR Actions

- **read_text**: Extract text from a region
- **find_text**: Find specific text on screen
- **click_text**: Click on found text

#### Flow Control Actions

- **wait**: Wait for a specified time
- **repeat**: Repeat a sequence of actions
- **while**: Repeat while a condition is true
- **if**: Conditional execution
- **for_each**: Iterate over a collection
- **break**: Exit from a loop
- **continue**: Skip to the next iteration

#### Advanced Flow Actions

- **parallel**: Execute actions in parallel
- **try_catch**: Handle errors in a sequence
- **switch**: Multi-way conditional
- **call_sequence**: Call another sequence

#### Data Actions

- **set_variable**: Set a variable value
- **increment**: Increment a numeric variable
- **decrement**: Decrement a numeric variable
- **random**: Generate a random value
- **calculate**: Perform a calculation

#### System Actions

- **log**: Write a message to the log
- **play_sound**: Play a notification sound
- **show_message**: Display a message to the user
- **exit**: Exit the sequence

## Sequence Validation

Before execution, sequences are validated to ensure they are well-formed:

```python
# Validate a sequence
validation_result = automation_core.validate_sequence(sequence)
if not validation_result.is_valid:
    print(f"Validation errors: {validation_result.errors}")
```

Validation checks include:
- Required parameters for each action
- Valid action types
- Valid variable references
- Valid conditions
- Proper nesting of control structures

## Sequence Storage

Sequences are stored as JSON files in the `sequences/` directory:

```
sequences/
├── farming/
│   ├── farm_resources.json
│   └── collect_gold.json
├── combat/
│   ├── attack_monster.json
│   └── defend_city.json
└── utility/
    ├── login.json
    └── collect_daily.json
```

## Sequence Execution

### Starting Execution

Sequences can be executed through the UI or programmatically:

```python
# Execute a sequence through the UI
automation_tab.load_sequence("farming/farm_resources")
automation_tab.start_execution()

# Execute programmatically
executor = SequenceExecutor(automation_core)
executor.load_sequence("farming/farm_resources")
executor.start()
```

### Execution Context

Each sequence execution maintains a context that includes:

- **Variables**: Values that can be set and referenced by actions
- **Execution state**: Current step, execution status
- **Results**: Results from previous actions
- **Statistics**: Execution time, success/failure counts

```python
# Access the execution context
context = executor.context
print(f"Current step: {context.current_step}")
print(f"Variables: {context.variables}")
```

### Execution Control

During execution, sequences can be controlled:

```python
# Pause execution
executor.pause()

# Resume execution
executor.resume()

# Stop execution
executor.stop()

# Step through execution
executor.step()
```

## Progress Tracking

The `ProgressTracker` monitors and reports on sequence execution:

```python
# Get execution progress
progress = progress_tracker.get_progress()
print(f"Progress: {progress.percent_complete}%")
print(f"Current action: {progress.current_action}")
print(f"Elapsed time: {progress.elapsed_time}")
```

Progress information includes:
- Current step
- Total steps
- Percent complete
- Elapsed time
- Estimated time remaining
- Current action description
- Success/failure counts

## Error Handling

Automation sequences can handle errors in several ways:

### Try-Catch Actions

```json
{
  "type": "try_catch",
  "try": [
    {
      "type": "click_template",
      "template": "confirm_button"
    }
  ],
  "catch": [
    {
      "type": "log",
      "message": "Failed to click confirm button",
      "level": "error"
    }
  ],
  "finally": [
    {
      "type": "wait",
      "duration": 1
    }
  ]
}
```

### Retry Logic

```json
{
  "type": "retry",
  "max_attempts": 3,
  "actions": [
    {
      "type": "find_template",
      "template": "login_button",
      "variable": "button"
    },
    {
      "type": "click_template",
      "template_result": "button"
    }
  ],
  "on_failure": [
    {
      "type": "log",
      "message": "Failed after 3 attempts",
      "level": "error"
    }
  ]
}
```

### Global Error Handlers

```python
# Set a global error handler
automation_core.set_error_handler(lambda error, context: {
    print(f"Error in step {context.current_step}: {error}")
    return ErrorHandlingAction.CONTINUE
})
```

## Debugging Automation

TB Scout provides several tools for debugging automation sequences:

### Execution Logging

Detailed logs of sequence execution:

```
[INFO] Starting sequence 'Farm Resources'
[DEBUG] Executing step 1: find_template(resource_icon)
[DEBUG] Template 'resource_icon' found at (320, 240) with confidence 0.92
[DEBUG] Variable 'resource' set to TemplateMatch(...)
[DEBUG] Executing step 2: if(resource != None)
[DEBUG] Condition 'resource != None' evaluated to True
[DEBUG] Executing then branch
[DEBUG] Executing step 2.1: click_template(resource)
[INFO] Clicked at (320, 240)
```

### Visual Debugging

The overlay can visualize automation actions:

- Highlight templates being searched for
- Show click locations
- Display text being read
- Visualize regions of interest

### Step-by-Step Execution

For detailed debugging:

1. Enable "Debug Mode" in the Automation tab
2. Use the "Step" button to execute one action at a time
3. Inspect variables and state after each step
4. Use breakpoints to pause at specific actions

## Integration with Other Components

### Template Matching

Automation sequences can use template matching to find and interact with game elements:

```json
{
  "type": "find_template",
  "template": "button_attack",
  "variable": "attack_button",
  "threshold": 0.8
},
{
  "type": "click_template",
  "template_result": "attack_button",
  "anchor": "center"
}
```

### OCR Integration

Text recognition can be used in automation sequences:

```json
{
  "type": "read_text",
  "region": [100, 200, 200, 50],
  "variable": "resource_count",
  "preprocess": "digits_only"
},
{
  "type": "log",
  "message": "Resource count: {resource_count}"
}
```

### Window Management

Automation can interact with window management:

```json
{
  "type": "activate_window",
  "window_title": "Total Battle"
},
{
  "type": "resize_window",
  "width": 1280,
  "height": 720
}
```

## Advanced Automation Techniques

### Parameterized Sequences

Sequences can be parameterized for reuse:

```json
{
  "name": "Click Button",
  "parameters": ["button_name", "wait_time"],
  "actions": [
    {
      "type": "find_template",
      "template": "{button_name}",
      "variable": "button"
    },
    {
      "type": "click_template",
      "template_result": "button"
    },
    {
      "type": "wait",
      "duration": "{wait_time}"
    }
  ]
}
```

Usage:
```json
{
  "type": "call_sequence",
  "sequence": "Click Button",
  "parameters": {
    "button_name": "ok_button",
    "wait_time": 2
  }
}
```

### Data-Driven Automation

Automation can be driven by external data:

```json
{
  "type": "load_csv",
  "file": "targets.csv",
  "variable": "targets"
},
{
  "type": "for_each",
  "collection": "targets",
  "variable": "target",
  "actions": [
    {
      "type": "log",
      "message": "Processing target: {target.name}"
    },
    {
      "type": "navigate_to",
      "x": "{target.x}",
      "y": "{target.y}"
    }
  ]
}
```

### State Machines

Complex workflows can be implemented as state machines:

```json
{
  "type": "state_machine",
  "initial_state": "search",
  "states": {
    "search": {
      "actions": [
        {
          "type": "find_template",
          "template": "resource",
          "variable": "resource"
        }
      ],
      "transitions": [
        {
          "condition": "resource != None",
          "target": "collect"
        },
        {
          "condition": "resource == None",
          "target": "move"
        }
      ]
    },
    "collect": {
      "actions": [
        {
          "type": "click_template",
          "template_result": "resource"
        }
      ],
      "transitions": [
        {
          "target": "search"
        }
      ]
    },
    "move": {
      "actions": [
        {
          "type": "scroll",
          "direction": "down",
          "amount": 10
        }
      ],
      "transitions": [
        {
          "target": "search"
        }
      ]
    }
  }
}
```

## Best Practices

### Sequence Design

1. **Keep sequences focused**
   - Each sequence should have a single responsibility
   - Break complex tasks into smaller sequences

2. **Use descriptive names**
   - Name sequences based on their purpose
   - Use clear action descriptions

3. **Add error handling**
   - Use try-catch for error-prone operations
   - Add retry logic for unreliable operations
   - Include fallback actions

4. **Use variables effectively**
   - Initialize variables at the beginning
   - Use meaningful variable names
   - Document variable purposes

### Performance Optimization

1. **Limit search regions**
   - Specify regions of interest for template matching
   - Use game knowledge to focus searches

2. **Optimize wait times**
   - Use the minimum necessary wait duration
   - Use wait_for_template instead of fixed waits when possible

3. **Batch operations**
   - Combine similar operations
   - Reuse search results

### Maintenance

1. **Version control**
   - Store sequences in version control
   - Document changes

2. **Testing**
   - Test sequences in different game states
   - Create test sequences for critical functionality

3. **Documentation**
   - Document sequence purpose and usage
   - Document dependencies and assumptions

## Example Workflows

### Resource Farming Workflow

```json
{
  "name": "Farm Resources",
  "description": "Automatically farms resources from the map",
  "version": "1.0",
  "actions": [
    {
      "type": "set_variable",
      "name": "resources_collected",
      "value": 0
    },
    {
      "type": "while",
      "condition": "resources_collected < 10",
      "actions": [
        {
          "type": "find_template",
          "template": "resource_icon",
          "variable": "resource",
          "threshold": 0.8
        },
        {
          "type": "if",
          "condition": "resource != None",
          "then": [
            {
              "type": "click_template",
              "template_result": "resource"
            },
            {
              "type": "wait",
              "duration": 1
            },
            {
              "type": "find_template",
              "template": "collect_button",
              "variable": "collect_button"
            },
            {
              "type": "if",
              "condition": "collect_button != None",
              "then": [
                {
                  "type": "click_template",
                  "template_result": "collect_button"
                },
                {
                  "type": "increment",
                  "variable": "resources_collected"
                },
                {
                  "type": "log",
                  "message": "Collected resource {resources_collected}/10"
                }
              ]
            }
          ],
          "else": [
            {
              "type": "scroll",
              "direction": "down",
              "amount": 5
            },
            {
              "type": "wait",
              "duration": 0.5
            }
          ]
        }
      ]
    },
    {
      "type": "play_sound",
      "sound": "complete"
    },
    {
      "type": "show_message",
      "message": "Resource collection complete!"
    }
  ]
}
```

### Login Workflow

```json
{
  "name": "Game Login",
  "description": "Automatically logs into the game",
  "version": "1.0",
  "actions": [
    {
      "type": "activate_window",
      "window_title": "Total Battle"
    },
    {
      "type": "try_catch",
      "try": [
        {
          "type": "find_template",
          "template": "login_button",
          "variable": "login_button",
          "timeout": 10
        },
        {
          "type": "click_template",
          "template_result": "login_button"
        },
        {
          "type": "wait",
          "duration": 2
        },
        {
          "type": "find_template",
          "template": "username_field",
          "variable": "username_field"
        },
        {
          "type": "click_template",
          "template_result": "username_field"
        },
        {
          "type": "text_input",
          "text": "{username}"
        },
        {
          "type": "find_template",
          "template": "password_field",
          "variable": "password_field"
        },
        {
          "type": "click_template",
          "template_result": "password_field"
        },
        {
          "type": "text_input",
          "text": "{password}"
        },
        {
          "type": "find_template",
          "template": "submit_button",
          "variable": "submit_button"
        },
        {
          "type": "click_template",
          "template_result": "submit_button"
        },
        {
          "type": "wait_for_template",
          "template": "game_loaded",
          "timeout": 30
        },
        {
          "type": "log",
          "message": "Successfully logged in",
          "level": "info"
        }
      ],
      "catch": [
        {
          "type": "log",
          "message": "Login failed",
          "level": "error"
        },
        {
          "type": "show_message",
          "message": "Failed to log in. Please check credentials or try manually."
        }
      ]
    }
  ]
}
```

## Troubleshooting

### Common Issues

1. **Sequence fails at specific step**
   - Check action parameters
   - Verify templates exist and are recognizable
   - Add debug logging
   - Use try-catch to handle potential failures

2. **Sequence works inconsistently**
   - Add wait times between actions
   - Implement retry logic
   - Check for game state variations
   - Use more robust template matching

3. **Variables not working as expected**
   - Check variable initialization
   - Verify variable references
   - Add debug logging to show variable values
   - Check for scope issues

### Debugging Techniques

1. **Enable verbose logging**
   ```python
   automation_core.set_log_level(logging.DEBUG)
   ```

2. **Add debug actions**
   ```json
   {
     "type": "log",
     "message": "Debug: resource = {resource}",
     "level": "debug"
   }
   ```

3. **Use the step-by-step execution**
   - Enable debug mode
   - Use the step button
   - Inspect variables after each step

4. **Check the execution trace**
   - Review the execution log
   - Look for error messages
   - Check variable values at each step