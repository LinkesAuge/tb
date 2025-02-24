
## Summary of Codebase Functionality

The TB Scout codebase is modularly designed, with each component in the `scout` directory handling a specific aspect of the application. `main.py` orchestrates the application, while `window_manager.py`, `overlay.py`, `gui/overlay_controller.py`, `pattern_matcher.py`, `config_manager.py`, and `sound_manager.py` provide functionalities for window management, overlay visualization, user interface, pattern detection, configuration handling, and sound effects, respectively.  The `utils/` and `patterns/` directories offer supporting utilities and pattern images. This structure promotes maintainability, organization, and extensibility of the application.



## Project Overview

TB Scout is a Python application designed for automating interactions with the "Total Battle" browser game. It works with both browser-based and standalone versions of the game. The application leverages computer vision and automation techniques to extract information from the game world and control in-game actions.

**Key Features:**

- Window detection and tracking for both standalone and browser versions of "Total Battle".
- Screenshot capture and analysis of the game window.
- Pattern matching to identify game elements (cities, monsters, resources, etc.).
- OCR (Optical Character Recognition) for extracting text from the game screen.
- Mouse and keyboard automation to interact with the game.
- A transparent overlay to visualize detected elements on top of the game.
- Configuration management for settings related to overlay, pattern matching, and application behavior.
- Sound notifications for game events or detections.

**Tech Stack:**

- Python
- PyQt6 (GUI)
- pynput, pydirectinput, pyautogui (Mouse/Keyboard Control)
- Windows API (Window Management)
- OpenCV (cv2) (Computer Vision)
- pytesseract (OCR)
- mss (Screenshot Capture)
- numpy (Math and Data Handling)
- uv (Dependency Management)

## Detailed Codebase Explanation (`scout/` Directory)

The `scout` directory is the core of the TB Scout application, containing the main logic and modules. Here's a breakdown of the files and their likely functionalities:

**1. `main.py` - Application Entry Point and Initialization**

- **Function:**  Starts the application, initializes all components, and sets up the main event loop.
- **Workflow:**
    1. Sets up logging.
    2. Initializes the PyQt6 `QApplication`.
    3. Loads configurations using `ConfigManager` (`overlay_settings`, `pattern_settings`).
    4. Initializes `WindowManager` to manage the "Total Battle" game window.
    5. Creates `Overlay` instance, passing `WindowManager` and settings.
    6. Creates `OverlayController` instance (GUI), passing `Overlay` and settings.
    7. Sets up callbacks to connect GUI actions to `Overlay` and `QApplication`.
    8. Shows the `OverlayController` window.
    9. Starts the PyQt6 event loop (`app.exec()`).
    10. Includes error handling to catch and log exceptions.

**2. `window_manager.py` - Game Window Handling**

- **Purpose:** Manages finding, tracking, and interacting with the "Total Battle" game window.
- **Key Class: `WindowManager`**
    - Detects the game window by title ("Total Battle") using Windows API.
    - Stores the game window handle.
    - Provides methods to get window position and size.
    - Offers functionality to capture screenshots of the game window (likely using `mss`).
    - May include functions for window focus control.
    - Handles errors if the game window is not found or becomes invalid.

**3. `overlay.py` - Game Overlay Implementation**

- **Purpose:** Creates and manages the transparent overlay window for visualizing game information.
- **Key Class: `Overlay`**
    - Creates a transparent, borderless PyQt6 window that sits on top of the game.
    - Positions and sizes the overlay to match the game window using `WindowManager`.
    - Provides drawing methods (using PyQt6's `QPainter`) to visualize detected elements.
    - Visualizes pattern detection results (bounding boxes, highlights) based on data from `PatternMatcher`.
    - Implements `toggle()` method to control overlay visibility.
    - Applies overlay settings from `overlay_settings`.
    - Receives `pattern_settings` for visualization adjustments.

**4. `gui/overlay_controller.py` - User Interface Controller**

- **Purpose:** Manages the user interface (GUI) for controlling the overlay and application features.
- **Key Class: `OverlayController`**
    - Creates the main control window using PyQt6 with UI elements (buttons, checkboxes, etc.).
    - Includes UI elements to toggle the overlay, trigger scanning, clear overlay, and potentially modify settings.
    - Manages callbacks for GUI actions (toggle overlay, quit application).
    - Handles user interactions with GUI elements.
    - May include UI for viewing and modifying application settings, interacting with `ConfigManager`.

**5. `pattern_matcher.py` - Pattern Detection Logic**

- **Purpose:** Implements pattern matching logic to detect game elements in screenshots.
- **Key Class: `PatternMatcher`**
    - Integrates OpenCV (`cv2`) for image processing and computer vision.
    - Loads pattern images from files (likely from `patterns/` directory).
    - Implements pattern matching algorithms (e.g., template matching, feature matching) using OpenCV.
    - Supports Region of Interest (ROI) for focused pattern matching.
    - Uses thresholds and parameters (from `pattern_settings`) to control detection sensitivity.
    - Returns structured data for detected patterns (location, confidence, type).
    - Takes screenshots (from `WindowManager`) as input.

**6. `config_manager.py` - Configuration Management**

- **Purpose:** Handles loading, saving, and accessing application configuration settings.
- **Key Class: `ConfigManager`**
    - Manages configuration data, likely stored in files (e.g., JSON, TOML).
    - Loads settings from configuration files at startup.
    - Saves settings to files when modified.
    - Provides methods to access settings (`get_overlay_settings()`, `get_pattern_matching_settings()`).
    - Defines default settings if configuration files are missing.
    - May include settings validation.

**7. `sound_manager.py` - Sound Effects Management**

- **Purpose:** Manages and plays sound effects for application events.
- **Key Class: `SoundManager`**
    - Loads sound files (e.g., WAV, MP3).
    - Provides functions to play sound files.
    - Maps application events to specific sound effects.
    - May include sound control features (volume, mute).

**8. `utils/` and `patterns/` Directories**

- **`utils/`**: Contains utility modules with helper functions for image processing, OCR, logging, etc., promoting code reusability.
- **`patterns/`**: Stores image files used as patterns for `PatternMatcher`, organized by game element type.

## File Structure Overview

tb-scout/
├── scout/
│ ├── init.py
│ ├── main.py
│ ├── overlay.py
│ ├── gui/
│ │ ├── init.py
│ │ ├── overlay_controller.py
│ ├── pattern_matcher.py
│ ├── config_manager.py
│ ├── sound_manager.py
│ ├── window_manager.py
│ ├── utils/
│ │ ├── init.py
│ │ ├── ...
│ ├── patterns/
│ │ ├── init.py
│ │ ├── ...
│ ├── ocr/ # (Likely - if OCR is complex)
│ │ ├── init.py
│ │ ├── ...
├── tests/
│ ├── init.py
│ ├── ...
├── pyproject.toml
├── README.md
├── LICENSE
├── .gitignore
├── .pre-commit-config.yaml
└── .github/
└── workflows/

