# Overlay Component

## Overview

The Overlay component creates a transparent window that sits on top of the game window, allowing the application to visually highlight detected elements, display information, and provide visual feedback during automation. It serves as the primary visual interface between the application and the game.

## Architecture

The Overlay component is designed with a focus on performance, flexibility, and minimal interference with the game:

```
scout/
├── overlay.py             # Main overlay implementation
└── window_interface.py    # Interface for window management
```

## Key Components

### Overlay Class

The `Overlay` class is the central component that manages the transparent window:

```python
class Overlay(QWidget):
    """
    Creates a transparent overlay window on top of the game window.
    
    The overlay is used to highlight detected game elements, display
    information, and provide visual feedback during automation.
    """
    
    def __init__(self, window_interface, config_manager, signal_bus=None):
        """Initialize the overlay window."""
        super().__init__(None, Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        
        self._window_interface = window_interface
        self._config_manager = config_manager
        self._signal_bus = signal_bus
        
        # Drawing properties
        self._elements = []
        self._text_elements = []
        self._highlight_color = QColor(255, 0, 0, 128)
        self._text_color = QColor(255, 255, 255, 255)
        self._font = QFont("Arial", 10)
        
        # Setup
        self._setup_signals()
        self._load_config()
        self._update_timer = QTimer()
        self._update_timer.timeout.connect(self._update_position)
        self._update_timer.start(100)  # Update position every 100ms
```

### Drawing System

The Overlay includes a sophisticated drawing system that:

- Renders different types of visual elements (rectangles, circles, text, etc.)
- Supports customizable colors, line styles, and transparency
- Optimizes rendering performance
- Handles coordinate transformations between game and screen space

### Element Management

The Overlay provides methods to manage the visual elements:

- Adding elements to highlight game features
- Removing elements when they're no longer needed
- Updating element properties (position, color, etc.)
- Grouping elements for organized display

### Window Tracking

The Overlay automatically tracks the game window:

- Positions itself to exactly match the game window
- Resizes when the game window changes size
- Hides when the game window is minimized
- Reappears when the game window is restored

## Integration with Other Components

The Overlay component integrates with several other parts of the application:

- **Window Interface**: Uses the window interface to track the game window
- **Template Matcher**: Displays the results of template matching
- **Text OCR**: Shows recognized text areas
- **Automation**: Provides visual feedback during automation sequences
- **Configuration Manager**: Loads and saves overlay settings

## Rendering Pipeline

The Overlay uses an efficient rendering pipeline:

1. **Element Collection**: Gathers all elements to be displayed
2. **Coordinate Transformation**: Converts game coordinates to screen coordinates
3. **Clipping**: Ensures elements are only drawn within the game window
4. **Rendering**: Draws all elements with appropriate styles
5. **Optimization**: Uses techniques like dirty region tracking to minimize redraw operations

## Customization Options

The Overlay appearance can be customized through configuration:

- **Colors**: Different colors for different types of elements
- **Transparency**: Adjustable transparency levels
- **Line Styles**: Solid, dashed, or dotted lines
- **Text Formatting**: Font, size, and style options
- **Animation**: Optional animations for highlighting

## Performance Considerations

The Overlay is designed to minimize performance impact:

- Efficient drawing algorithms
- Minimal redraw operations
- Low CPU and GPU usage
- Optimized update frequency
- Automatic disabling when not needed

## Error Handling

The Overlay includes robust error handling:

- Graceful recovery from window tracking failures
- Fallback rendering modes
- Clear error logging
- Automatic retry mechanisms

## Future Enhancements

Planned improvements for the Overlay component:

- Advanced animation effects
- Custom themes and styles
- Interactive overlay elements
- Improved performance through hardware acceleration
- Support for multiple overlays (e.g., debug overlay, info overlay)

## Usage Examples

### Highlighting a Detected Element

```python
# Add a rectangle to highlight a detected city
overlay.add_rectangle(
    x=100, y=200,           # Position
    width=50, height=50,    # Size
    color=(255, 0, 0, 128), # Red with 50% transparency
    line_width=2,           # Border thickness
    tag="city"              # Tag for grouping/identification
)

# Add text label
overlay.add_text(
    text="City (Level 5)",
    x=100, y=190,           # Position (above rectangle)
    color=(255, 255, 255),  # White text
    font_size=12,
    tag="city"
)
```

### Clearing Elements

```python
# Clear all elements
overlay.clear_all()

# Clear only elements with a specific tag
overlay.clear_by_tag("city")
```

### Temporarily Hiding the Overlay

```python
# Hide the overlay
overlay.hide()

# Show the overlay again
overlay.show()
```