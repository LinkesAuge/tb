# Screen Capture Component

## Overview

The Screen Capture component is responsible for capturing screenshots from the game window or screen. It provides a flexible and robust system for obtaining high-quality images that can be used by other components for template matching, OCR, and automation.

## Architecture

The Screen Capture component follows a modular design with clear separation between models, managers, and UI elements:

```
screen_capture/
├── __init__.py
├── capture_manager.py     # Core capture functionality
├── screen_list_model.py   # Lists available screens
├── window_list_model.py   # Lists available windows
├── capture_tab.py         # UI for capture selection/preview
└── utils.py               # Helper functions
```

## Key Components

### CaptureManager

The `CaptureManager` is the central component that coordinates all capture operations. It:

- Manages the available capture sources (screens and windows)
- Provides methods to capture screenshots from the selected source
- Handles capture timing and refresh rates
- Maintains capture settings and preferences
- Emits signals when new captures are available

```python
class CaptureManager(QObject):
    """
    Manages screen and window capture operations.
    
    This class provides a unified interface for capturing screenshots from
    various sources (screens, windows) and makes them available to other
    components of the application.
    """
    
    capture_updated = pyqtSignal(np.ndarray)
    capture_error = pyqtSignal(str)
    
    def __init__(self, window_interface=None):
        """Initialize the capture manager."""
        super().__init__()
        self._window_interface = window_interface
        self._screen_model = ScreenListModel()
        self._window_model = WindowListModel()
        self._current_source = None
        self._capture_timer = QTimer()
        self._setup_timer()
```

### ScreenListModel

The `ScreenListModel` provides a Qt model for listing all available screens/monitors in the system:

- Detects all connected screens
- Provides screen information (resolution, position, name)
- Updates when screen configuration changes
- Integrates with Qt's Model/View architecture

### WindowListModel

The `WindowListModel` provides a Qt model for listing all available windows in the system:

- Detects all open windows
- Provides window information (title, handle, position, size)
- Updates when windows are opened or closed
- Filters windows based on visibility and other criteria
- Integrates with Qt's Model/View architecture

### CaptureTab

The `CaptureTab` provides a user interface for selecting and previewing capture sources:

- Displays lists of available screens and windows
- Shows a preview of the current capture
- Provides controls for capture settings (refresh rate, region selection)
- Allows saving screenshots for debugging purposes

### Utils

The `utils.py` module provides helper functions for the capture system:

- Converting between different image formats (QImage, numpy arrays, etc.)
- Scaling and transforming images
- Calculating capture regions
- Handling platform-specific capture operations

## Capture Methods

The Screen Capture component supports multiple capture methods:

1. **Qt Screen Capture**: Uses Qt's native screen capture capabilities
2. **Window Capture**: Captures specific windows using platform APIs
3. **Fallback to MSS**: Uses the MSS library as a fallback for compatibility

## Integration with Other Components

The Screen Capture component integrates with other parts of the application:

- **Template Matcher**: Provides images for pattern matching
- **Text OCR**: Supplies screenshots for text recognition
- **Overlay**: Coordinates with the overlay to ensure proper positioning
- **Automation**: Provides visual feedback for automation actions

## Configuration Options

The component can be configured through the application settings:

- **Capture Refresh Rate**: How frequently screenshots are taken
- **Capture Quality**: Balance between quality and performance
- **Auto-detection**: Whether to automatically detect the game window
- **Region Selection**: Ability to capture only a portion of a screen or window

## Error Handling

The component includes robust error handling:

- Graceful degradation when preferred capture methods fail
- Clear error messages for troubleshooting
- Automatic retry mechanisms
- Signal emission for error notification

## Performance Considerations

Screen capture can be resource-intensive, so the component implements several optimizations:

- Capture only when needed
- Configurable capture rate
- Efficient image format conversions
- Region-based capture to minimize processing
- Background processing to avoid UI freezing

## Future Enhancements

Planned improvements for the Screen Capture component:

- Support for video recording
- Enhanced region selection with visual editor
- Multi-monitor configuration profiles
- Performance profiling and optimization