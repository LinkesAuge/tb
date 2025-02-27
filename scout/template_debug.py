"""
Template Matching Debug Script

This standalone script tests template matching at extremely low confidence 
thresholds to diagnose problems with match detection.
"""

import cv2
import numpy as np
import logging
import time
import os
from pathlib import Path
import sys
import pyautogui
import win32gui
import win32con

# Add parent directory to path to import scout modules
sys.path.append(str(Path(__file__).parent.parent))

from scout.config_manager import ConfigManager

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('template_debug.log', mode='w')
    ]
)

logger = logging.getLogger("template_debug")

def save_debug_image(image, name, matches=None):
    """Save debug image with optional matches marked."""
    debug_dir = Path("debug_images")
    debug_dir.mkdir(exist_ok=True)
    
    # Copy image to avoid modifying original
    debug_image = image.copy()
    
    # Draw matches if provided
    if matches:
        for i, match in enumerate(matches):
            name_match, x, y, w, h, conf = match
            # Draw rectangle
            cv2.rectangle(debug_image, (x, y), (x + w, y + h), (0, 255, 0), 2)
            # Draw text with match info
            cv2.putText(
                debug_image,
                f"{name_match} ({conf:.2f})",
                (x, max(y - 5, 10)),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.5,
                (0, 255, 0),
                1
            )
    
    # Save image
    timestamp = time.strftime("%H%M%S")
    output_path = debug_dir / f"{name}_{timestamp}.png"
    cv2.imwrite(str(output_path), debug_image)
    logger.info(f"Saved debug image to {output_path}")
    return str(output_path)

def find_window(window_title):
    """Find window by title."""
    result = None
    
    def callback(hwnd, extra):
        if win32gui.IsWindowVisible(hwnd):
            title = win32gui.GetWindowText(hwnd)
            if window_title.lower() in title.lower():
                extra.append(hwnd)
    
    windows = []
    win32gui.EnumWindows(callback, windows)
    
    if windows:
        return windows[0]
    return None

def list_all_windows():
    """List all visible windows."""
    windows = []
    
    def callback(hwnd, windows_list):
        if win32gui.IsWindowVisible(hwnd):
            title = win32gui.GetWindowText(hwnd)
            if title:  # Only include windows with a title
                windows_list.append((hwnd, title))
    
    win32gui.EnumWindows(callback, windows)
    return sorted(windows, key=lambda x: x[1].lower())

def capture_window(hwnd):
    """Capture a screenshot of a window by handle."""
    if not hwnd:
        logger.error("No window handle provided")
        return None
    
    try:
        # Get window rectangle
        left, top, right, bottom = win32gui.GetWindowRect(hwnd)
        width = right - left
        height = bottom - top
        
        # Ensure positive dimensions
        if width <= 0 or height <= 0:
            logger.error(f"Invalid window dimensions: {width}x{height}")
            return None
        
        # Capture screenshot of window
        screenshot = pyautogui.screenshot(region=(left, top, width, height))
        
        # Convert to numpy array (BGR format for OpenCV)
        image = np.array(screenshot)
        image = cv2.cvtColor(image, cv2.COLOR_RGB2BGR)
        
        return image
    except Exception as e:
        logger.error(f"Error capturing window: {e}")
        return None

def diagnose_template_loading():
    """Run extra diagnostics to understand where templates are being loaded from."""
    
    logger.info("=" * 50)
    logger.info("TEMPLATE LOADING DIAGNOSTICS")
    logger.info("=" * 50)
    
    # Check working directory
    cwd = os.getcwd()
    logger.info(f"Current working directory: {cwd}")
    
    # Check for templates directory in different locations
    possible_templates_dirs = [
        Path(cwd) / "templates",
        Path(cwd) / "scout" / "templates",
        Path(__file__).parent / "templates",
        Path(__file__).parent.parent / "scout" / "templates",
        Path(__file__).parent.parent / "templates",
        Path("D:/OneDrive/AI/Projekte/Scout/tb/scout/templates"),
        Path("D:/OneDrive/AI/Projekte/Scout/tb/templates"),
    ]
    
    logger.info("Checking for templates in possible locations:")
    for dir_path in possible_templates_dirs:
        try:
            dir_exists = dir_path.exists()
            dir_is_dir = dir_path.is_dir() if dir_exists else False
            
            status = "EXISTS" if dir_exists else "NOT FOUND"
            if dir_exists and not dir_is_dir:
                status = "EXISTS BUT NOT A DIRECTORY"
            
            logger.info(f"  {dir_path.absolute()}: {status}")
            
            if dir_exists and dir_is_dir:
                # List all files
                files = list(dir_path.glob("*"))
                logger.info(f"    Contains {len(files)} files: {[f.name for f in files]}")
                
                # Check for PNG files specifically
                png_files = list(dir_path.glob("*.png"))
                logger.info(f"    PNG files: {[f.name for f in png_files]}")
                
                # Try to actually read one image if available
                if png_files:
                    test_file = png_files[0]
                    try:
                        img = cv2.imread(str(test_file))
                        if img is not None:
                            logger.info(f"    Successfully read test image: {test_file.name} ({img.shape})")
                        else:
                            logger.error(f"    Failed to read test image: {test_file.name}")
                            
                            # Try with different flags
                            img = cv2.imread(str(test_file), cv2.IMREAD_UNCHANGED)
                            if img is not None:
                                logger.info(f"    Successfully read test image with IMREAD_UNCHANGED: {test_file.name} ({img.shape})")
                            else:
                                logger.error(f"    Still failed to read test image with IMREAD_UNCHANGED")
                    except Exception as e:
                        logger.error(f"    Error reading test image: {e}")
        
        except Exception as e:
            logger.error(f"Error checking templates dir {dir_path}: {e}")
    
    logger.info("=" * 50)
    logger.info("END TEMPLATE LOADING DIAGNOSTICS")
    logger.info("=" * 50)

def run_thorough_template_test():
    """Run extensive template matching tests at very low thresholds."""
    logger.info("=" * 50)
    logger.info("STARTING EXTREMELY THOROUGH TEMPLATE MATCHING DEBUG")
    logger.info("=" * 50)
    
    # Run diagnostics first
    diagnose_template_loading()
    
    # List all visible windows
    all_windows = list_all_windows()
    
    print("Available windows:")
    for i, (hwnd, title) in enumerate(all_windows):
        print(f"{i+1}. {title}")
    
    # Let user select which window to use
    try:
        choice = int(input("\nEnter the number of the window to test with (or 0 to use config): "))
        if choice == 0:
            # Load config
            config = ConfigManager()
            window_title = config.get("Window.title", "Tribal Wars 2")
            logger.info(f"Using window title from config: '{window_title}'")
            hwnd = find_window(window_title)
        elif 1 <= choice <= len(all_windows):
            hwnd = all_windows[choice-1][0]
            window_title = all_windows[choice-1][1]
            logger.info(f"Selected window: {window_title}")
        else:
            logger.error("Invalid selection")
            return
    except ValueError:
        logger.error("Invalid input, please enter a number")
        return
    
    if not hwnd:
        logger.error(f"Window not found or invalid selection")
        return
    
    # Get window info
    window_title_actual = win32gui.GetWindowText(hwnd)
    logger.info(f"Using window: {window_title_actual} (handle: {hwnd})")
    
    # Get window rect
    left, top, right, bottom = win32gui.GetWindowRect(hwnd)
    width = right - left
    height = bottom - top
    logger.info(f"Window dimensions: {width}x{height} at ({left}, {top})")
    
    # Get absolute path to templates directory
    current_dir = Path(os.path.dirname(os.path.abspath(__file__)))
    templates_dir = current_dir / "templates"
    logger.info(f"Templates directory: {templates_dir.absolute()}")
    
    # List templates
    if templates_dir.exists():
        template_files = list(templates_dir.glob("*.png"))
        logger.info(f"Found {len(template_files)} template files: {[f.name for f in template_files]}")
        
        # Load templates directly
        templates = {}
        
        # Log template sizes
        for template_file in template_files:
            try:
                template = cv2.imread(str(template_file))
                if template is not None:
                    template_name = template_file.stem
                    templates[template_name] = template
                    h, w = template.shape[:2]
                    logger.info(f"Template {template_file.name}: {w}x{h} pixels")
                else:
                    logger.error(f"Failed to load template: {template_file}")
            except Exception as e:
                logger.error(f"Error checking template {template_file}: {e}")
    else:
        logger.error(f"Templates directory not found: {templates_dir.absolute()}")
        return
    
    if not templates:
        logger.error("No templates loaded")
        return
    
    # Capture window
    logger.info("Capturing window screenshot...")
    image = capture_window(hwnd)
    
    if image is None:
        logger.error("Failed to capture window!")
        return
    
    logger.info(f"Captured image with dimensions: {image.shape[1]}x{image.shape[0]}")
    
    # Save captured image
    capture_path = save_debug_image(image, "captured_window")
    logger.info(f"Saved window capture to {capture_path}")
    print(f"\nSaved window screenshot to: {capture_path}")
    print("Please check this image to confirm the correct window was captured.")
    
    # Let user decide whether to continue
    continue_test = input("\nDoes the captured image show the correct window? (y/n): ").lower()
    if continue_test != 'y':
        logger.info("User aborted test after window capture")
        print("\nTest aborted. Please try again and select the correct window.")
        return
    
    # Try different thresholds
    test_thresholds = [0.8, 0.7, 0.6, 0.5, 0.4, 0.3, 0.2, 0.1, 0.05, 0.01]
    
    print("\nTesting with thresholds:")
    
    for threshold in test_thresholds:
        logger.info(f"\nTesting with threshold: {threshold}")
        print(f"  - Testing threshold: {threshold}")
        
        # Try each template individually
        for template_name, template in templates.items():
            logger.info(f"Testing template: {template_name}")
            
            # Try to find matches directly
            try:
                result = cv2.matchTemplate(image, template, cv2.TM_CCOEFF_NORMED)
                locations = np.where(result >= threshold)
                
                if locations and len(locations[0]) > 0:
                    match_count = len(locations[0])
                    logger.info(f"Found {match_count} matches for {template_name} at threshold {threshold}")
                    print(f"    * Found {match_count} matches for {template_name}")
                    
                    # Convert matches to tuples
                    match_tuples = []
                    template_width = template.shape[1]
                    template_height = template.shape[0]
                    
                    # Get the top 5 matches (or fewer if less than 5 found)
                    indices = np.arange(len(locations[0]))
                    sorted_indices = indices[np.argsort(
                        [result[locations[0][i], locations[1][i]] for i in indices]
                    )][::-1]  # Sort by confidence, descending
                    
                    for idx in sorted_indices[:5]:  # Limit to top 5
                        y, x = locations[0][idx], locations[1][idx]
                        confidence = float(result[y, x])
                        
                        match_tuple = (
                            template_name,
                            int(x),
                            int(y),
                            template_width,
                            template_height,
                            confidence
                        )
                        match_tuples.append(match_tuple)
                        logger.info(f"Match: {match_tuple}")
                        print(f"      - Match at ({int(x)}, {int(y)}) with confidence {confidence:.3f}")
                    
                    # Save debug image with matches
                    match_path = save_debug_image(image, f"{template_name}_thresh{threshold}", match_tuples)
                    logger.info(f"Saved match visualization to {match_path}")
                    print(f"      - Visualization saved to: {match_path}")
                else:
                    logger.info(f"No matches found for {template_name} at threshold {threshold}")
            except Exception as e:
                logger.error(f"Error in template matching: {e}")
    
    # Special test: try various scaling factors
    logger.info("\nTesting with different scaling factors")
    print("\nTesting with different scaling factors:")
    scale_factors = [0.5, 0.75, 1.0, 1.25, 1.5, 2.0]
    
    # Use a moderate threshold for scaling tests
    threshold = 0.3
    
    for scale in scale_factors:
        logger.info(f"Testing with scale factor: {scale}")
        print(f"  - Testing scale factor: {scale}")
        
        # Resize image
        if scale != 1.0:
            new_width = int(image.shape[1] * scale)
            new_height = int(image.shape[0] * scale)
            resized = cv2.resize(image, (new_width, new_height))
            logger.info(f"Resized image to {new_width}x{new_height}")
        else:
            resized = image
        
        # Try each template
        for template_name, template in templates.items():
            logger.info(f"Testing template {template_name} with scale {scale}")
            
            template_h, template_w = template.shape[:2]
            
            # Check if template is too large for image
            if template_w > resized.shape[1] or template_h > resized.shape[0]:
                logger.warning(f"Template too large for scaled image, skipping")
                continue
            
            # Try to match template directly with OpenCV for more debug info
            try:
                result = cv2.matchTemplate(resized, template, cv2.TM_CCOEFF_NORMED)
                min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(result)
                
                logger.info(f"Direct OpenCV match: min={min_val:.4f}, max={max_val:.4f}")
                logger.info(f"Best match at: {max_loc} with confidence {max_val:.4f}")
                
                # If max_val is above threshold, save a debug image
                if max_val > threshold:
                    # Draw rectangle on debug image
                    debug_image = resized.copy()
                    top_left = max_loc
                    bottom_right = (top_left[0] + template_w, top_left[1] + template_h)
                    cv2.rectangle(debug_image, top_left, bottom_right, (0, 0, 255), 2)
                    
                    # Save debug image
                    direct_match_path = save_debug_image(
                        debug_image, 
                        f"{template_name}_direct_scale{scale}"
                    )
                    logger.info(f"Saved direct match visualization to {direct_match_path}")
                    print(f"    * Found match for {template_name} at {max_loc} with confidence {max_val:.3f}")
                    print(f"      - Visualization saved to: {direct_match_path}")
                else:
                    print(f"    * Best match for {template_name}: confidence {max_val:.3f} (below threshold)")
            except Exception as e:
                logger.error(f"Error in direct template matching: {e}")
    
    logger.info("=" * 50)
    logger.info("TEMPLATE MATCHING DEBUG COMPLETE")
    logger.info("=" * 50)
    
    print("\n")
    print("=" * 50)
    print("TEMPLATE MATCHING DEBUG COMPLETE")
    print("=" * 50)
    print("\nCheck the debug_images folder for visualizations.")
    print("Look at template_debug.log for detailed information.")

if __name__ == "__main__":
    try:
        run_thorough_template_test()
    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True) 