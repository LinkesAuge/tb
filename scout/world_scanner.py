from dataclasses import dataclass
from typing import Tuple, Optional, List, Dict, Any
import pyautogui
import cv2
import numpy as np
import logging
from time import sleep
from pathlib import Path
import pytesseract
from mss import mss
import time
from PyQt6.QtCore import QObject, pyqtSignal, QTimer
from scout.template_matcher import TemplateMatcher
from scout.config_manager import ConfigManager
from scout.debug_window import DebugWindow
from scout.window_manager import WindowManager
from datetime import datetime

# Set Tesseract executable path
pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'  # Adjust path if needed

logger = logging.getLogger(__name__)

@dataclass
class WorldPosition:
    """
    Represents a location in the game world's coordinate system.
    
    The game world uses a grid-based coordinate system where each position
    is defined by:
    - x: Horizontal position (0-999)
    - y: Vertical position (0-999)
    - k: World/kingdom number
    
    This class is used to track and navigate between different locations
    in the game world during scanning operations.
    """
    x: int  # 0-999
    y: int  # 0-999
    k: int  # World number
    description: Optional[str] = None
    
class WorldScanner(QObject):
    """
    Screen capturing and template matching system.
    
    This class provides continuous scanning of the game window by:
    1. Taking screenshots at regular intervals
    2. Performing template matching on the entire screenshot
    3. Updating the overlay with match results
    4. Tracking performance metrics
    
    This design focuses on real-time template matching without any navigation
    or coordinate-based movement, simply analyzing what's visible on screen.
    
    Key Features:
    - Continuous screenshot capture
    - Full-screen template matching
    - Overlay integration for visual feedback
    - Performance tracking
    """
    
    # Add signals for scanning status
    scanning_started = pyqtSignal()
    scanning_stopped = pyqtSignal()
    scan_results_updated = pyqtSignal(dict)
    
    def __init__(self, window_manager: WindowManager, template_matcher=None, overlay=None):
        """Initialize the world scanner."""
        super().__init__()  # Initialize QObject base class
        self.window_manager = window_manager
        self.template_matcher = template_matcher
        self.overlay = overlay
        self.config_manager = ConfigManager()
        
        # Add scanning state
        self.is_scanning = False
        self.scan_results = {}
        
        # Configure scanning options
        self.scan_interval = 1.0  # Default scan interval (seconds)
        
        # Create debug window
        self.debug_window = DebugWindow()
        
        # Signal for debug images (will be connected by worker)
        self.debug_image = None
        
        logger.debug("WorldScanner initialized")
        
    def start_scanning(self) -> None:
        """
        Start the scanning process.
        
        This method:
        1. Sets up the scanning state
        2. Initializes the scan results dictionary
        3. Makes the overlay visible
        4. Starts template matching
        5. Sets up timers for periodic updates
        """
        if self.is_scanning:
            logger.info("Scanning is already active - ignoring start request")
            return
            
        logger.info("Starting screen scanning")
        self.is_scanning = True
        
        # Initialize scan results dictionary
        self.scan_results = {
            "status": "Active",
            "start_time": time.time(),  # Store time as float for timestamp
            "start_time_str": time.strftime("%H:%M:%S"),  # Store formatted time for display
            "matches_found": 0,
            "templates_checked": 0,
            "screenshots_taken": 0
        }
        
        # Emit initial scan results
        self.scan_results_updated.emit(self.scan_results)
        logger.info(f"Emitted initial scan results: {self.scan_results}")
        
        # Start template matching if available
        if self.template_matcher and self.overlay:
            # Log the current overlay state
            logger.debug(f"Current overlay state: active={self.overlay.active}, template_matching_active={self.overlay.template_matching_active}")
            
            # Make sure overlay is visible
            self.overlay.set_visible(True)
            logger.info("Force-enabled overlay visibility for scanning")
            
            # Ensure template_matching_active is True even if it was not set already
            if hasattr(self.overlay, 'template_matching_active'):
                if not self.overlay.template_matching_active:
                    logger.info("Forcing template_matching_active to True")
                    self.overlay.template_matching_active = True
                    
            # Start template matching
            self.overlay.start_template_matching()
            
            # Force an immediate draw of the overlay
            if hasattr(self.overlay, '_draw_overlay'):
                logger.info("Forcing immediate overlay draw to show debug visuals")
                self.overlay._draw_overlay()
                
            logger.info("Started template matching for scanning")
            
            # Set up timer to periodically update scan results
            if not hasattr(self, 'scan_update_timer'):
                # Use QTimer for periodic updates
                self.scan_update_timer = QTimer()
                self.scan_update_timer.timeout.connect(self._update_scan_results)
                logger.info("Created scan update timer")
            
            # Start the timer to update results every second
            self.scan_update_timer.start(1000)  # 1 second interval
            logger.info("Started scan results update timer")
            
        else:
            if not self.template_matcher:
                logger.warning("No template matcher available for scanning")
            if not self.overlay:
                logger.warning("No overlay available for scanning")
        
        # Emit signal that scanning has started
        self.scanning_started.emit()
        
    def stop_scanning(self) -> None:
        """
        Stop the scanning process.
        
        This method:
        1. Updates the scanning state
        2. Stops timers
        3. Updates final scan results
        4. Stops template matching
        """
        if not self.is_scanning:
            logger.info("Scanning is not active - ignoring stop request") 
            return
            
        logger.info("Stopping scanning")
        self.is_scanning = False
        
        # Stop scan update timer if it exists and is active
        if hasattr(self, 'scan_update_timer') and self.scan_update_timer.isActive():
            self.scan_update_timer.stop()
            logger.info("Stopped scan results update timer")
        
        # Update and emit final scan results
        if hasattr(self, 'scan_results'):
            self.scan_results["status"] = "Stopped"
            self.scan_results["end_time"] = time.strftime("%H:%M:%S")
            self.scan_results_updated.emit(self.scan_results)
            logger.info(f"Emitted final scan results: {self.scan_results}")
        
        # Stop template matching if available
        if self.template_matcher and self.overlay:
            # Stop template matching
            self.overlay.stop_template_matching()
            logger.info("Stopped template matching")
        
        # Emit signal that scanning has stopped
        self.scanning_stopped.emit()
            
    def _update_scan_results(self) -> None:
        """
        Update and emit the scan results.
        
        This method:
        1. Takes a new screenshot
        2. Performs template matching
        3. Updates the overlay with match results
        4. Updates scan metrics
        5. Emits updated scan results
        """
        try:
            if not self.template_matcher or not self.overlay:
                logger.warning("Template matcher or overlay not available")
                return
                
            if not self.is_scanning:
                logger.debug("Not scanning, skipping update_scan_results")
                return
                
            # Get the current time
            current_time = time.time()
            
            # Get a fresh screenshot
            force_update = True  # Always get a fresh screenshot
            if hasattr(self.window_manager, 'clear_screenshot_cache'):
                self.window_manager.clear_screenshot_cache()
            current_screenshot = self.window_manager.capture_screenshot(force_update=force_update)
            
            # Track the screenshot count
            self.scan_results["screenshots_taken"] = self.scan_results.get("screenshots_taken", 0) + 1
            
            # Process screenshot if available
            if current_screenshot is not None:
                # Get matches from template matcher 
                if hasattr(self.template_matcher, 'find_all_templates'):
                    # This will update the template matcher's internal cache
                    matches = self.template_matcher.find_all_templates(current_screenshot)
                    logger.debug(f"Found {len(matches)} template matches in this scan update")
                    
                    # Track the number of templates checked
                    template_count = len(self.template_matcher.templates) if hasattr(self.template_matcher, 'templates') else 0
                    self.scan_results["templates_checked"] = template_count
                    
                    # Make sure overlay has the matches
                    if hasattr(self.overlay, 'cached_matches'):
                        # Clear previous matches first (to avoid accumulation)
                        self.overlay.cached_matches = []
                        # Add new matches
                        self.overlay.cached_matches.extend(matches)
                        logger.debug(f"Updated overlay's cached_matches with {len(matches)} matches")
                        
                        # Force redraw of overlay
                        if hasattr(self.overlay, '_draw_overlay'):
                            self.overlay._draw_overlay()
                            logger.debug("Forced overlay to redraw with new matches")
                    else:
                        logger.warning("Overlay has no cached_matches attribute")
                else:
                    logger.warning("Template matcher has no find_all_templates method")
            else:
                logger.warning("Could not capture screenshot for template matching")
            
            # Calculate elapsed time as float
            start_timestamp = self.scan_results.get("start_time", current_time)
            elapsed_seconds = current_time - start_timestamp
            
            # Format elapsed time as string
            elapsed_minutes = int(elapsed_seconds // 60)
            elapsed_seconds_remainder = int(elapsed_seconds % 60)
            elapsed_time_str = f"{elapsed_minutes:02d}:{elapsed_seconds_remainder:02d}"
            
            # Update scan results
            self.scan_results.update({
                "status": "Active" if self.is_scanning else "Stopped",
                "elapsed_time": elapsed_seconds,
                "elapsed_time_str": elapsed_time_str,
                "last_update": datetime.now().strftime("%H:%M:%S"),
                "matches_found": len(self.overlay.cached_matches) if hasattr(self.overlay, 'cached_matches') else 0
            })
            
            # Log scan results
            logger.debug(f"Scan results updated: {self.scan_results}")
            logger.debug(f"Matches found: {self.scan_results.get('matches_found', 0)}")
            
            # Emit the updated scan results
            self.scan_results_updated.emit(self.scan_results)
            
        except Exception as e:
            logger.error(f"Error in _update_scan_results: {e}", exc_info=True)

    def set_scan_interval(self, interval_seconds: float) -> None:
        """
        Set the scanning interval.
        
        Args:
            interval_seconds: Time between scans in seconds
        """
        self.scan_interval = max(0.1, min(10.0, interval_seconds))  # Clamp between 0.1 and 10 seconds
        
        # Update timer if active
        if hasattr(self, 'scan_update_timer') and self.scan_update_timer.isActive():
            interval_ms = int(self.scan_interval * 1000)
            self.scan_update_timer.setInterval(interval_ms)
            logger.info(f"Updated scan interval to {self.scan_interval:.1f} seconds")

def test_coordinate_reading():
    """Test function to check coordinate reading."""
    scanner = WorldScanner(WindowManager())
    
    logger.info("Starting coordinate reading test...")
    position = scanner.get_current_position()
    
    if position:
        logger.info(f"Test successful! Found position: X={position.x}, Y={position.y}, K={position.k}")
    else:
        logger.error("Test failed! Could not read coordinates")

class ScanLogHandler:
    """Handles logging for the world scanner."""
    
    def __init__(self) -> None:
        self.log_dir = Path("scan_logs")
        self.log_dir.mkdir(exist_ok=True)
        
        # Create new log file with timestamp
        timestamp = time.strftime("%Y%m%d-%H%M%S")
        self.log_file = self.log_dir / f"scan_log_{timestamp}.txt"
        
        # Create and configure file handler
        self.file_handler = logging.FileHandler(self.log_file)
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        self.file_handler.setFormatter(formatter)
        self.file_handler.setLevel(logging.DEBUG)
        
        # Create console handler with the same formatter
        self.console_handler = logging.StreamHandler()
        self.console_handler.setFormatter(formatter)
        self.console_handler.setLevel(logging.DEBUG)
        
        # Add handlers to logger
        logger.addHandler(self.file_handler)
        logger.addHandler(self.console_handler)
        
        # Log initial message
        logger.info("=== Starting new scan session ===")
        logger.info(f"Log file created at: {self.log_file}")
        
    def cleanup(self) -> None:
        """Clean up logging handlers."""
        logger.info("=== Ending scan session ===")
        logger.removeHandler(self.file_handler)
        logger.removeHandler(self.console_handler)
        self.file_handler.close()
        self.console_handler.close()

class ScanWorker(QObject):
    """Worker for running the world scan in a separate thread."""
    position_found = pyqtSignal(object)  # Emits WorldPosition
    error = pyqtSignal(str)
    finished = pyqtSignal()
    debug_image = pyqtSignal(object, str, int)  # image, coord_type, value
    
    def __init__(self, scanner: WorldScanner, template_matcher: 'TemplateMatcher') -> None:
        """
        Initialize scan worker.
        
        Args:
            scanner: WorldScanner instance
            template_matcher: TemplateMatcher instance
        """
        super().__init__()
        self.scanner = scanner
        self.template_matcher = template_matcher
        self.should_stop = False
        # Pass the debug signal to the scanner
        self.scanner.debug_image = self.debug_image
        self.last_debug_update = 0
        self.debug_update_interval = 0.5  # Update debug images every 0.5 seconds
        
    def run(self) -> None:
        """Run the scanning process."""
        try:
            logger.info("Starting continuous scan...")
            while not self.should_stop:
                try:
                    # Update debug images periodically
                    current_time = time.time()
                    if current_time - self.last_debug_update >= self.debug_update_interval:
                        self.update_debug_images()
                        self.last_debug_update = current_time
                    
                    # Try to read current position
                    current_pos = self.scanner.get_current_position()
                    if not current_pos:
                        logger.warning("Failed to read coordinates, retrying in 2 seconds...")
                        sleep(2)  # Wait before retry
                        continue
                    
                    # Update scanner start position
                    self.scanner.start_pos = current_pos
                    logger.info(f"Current position: X={current_pos.x}, Y={current_pos.y}, K={current_pos.k}")
                    
                    # Start scanning from current position
                    found_pos = self.scanner.scan_world_until_match(
                        self.template_matcher,
                        max_attempts=10
                    )
                    
                    if found_pos:
                        logger.info(f"Match found at position: {found_pos}")
                        self.position_found.emit(found_pos)
                        break
                    
                    # If no match found, continue scanning from a new position
                    logger.info("No match found in current area, moving to next area...")
                    # Move to a new starting position
                    new_x = (current_pos.x + 100) % 1000  # Move 100 units right, wrap around at 1000
                    new_y = current_pos.y
                    new_pos = WorldPosition(x=new_x, y=new_y, k=current_pos.k)
                    
                    move_success = False
                    retry_count = 0
                    while not move_success and retry_count < 3 and not self.should_stop:
                        move_success = self.scanner.move_to_position(new_pos)
                        if not move_success:
                            retry_count += 1
                            logger.warning(f"Failed to move to new position, retry {retry_count}/3")
                            sleep(1)
                    
                    if move_success:
                        logger.info(f"Successfully moved to new position: X={new_x}, Y={new_y}")
                        sleep(2)  # Wait before next scan attempt
                    else:
                        logger.warning("Failed to move after retries, will try new coordinates")
                        sleep(1)
                    
                except Exception as e:
                    logger.error(f"Error during scan: {e}")
                    sleep(2)  # Wait before retry
                    continue
                
            logger.info("Scan stopped by user" if self.should_stop else "Scan completed")
            
        except Exception as e:
            logger.error(f"Fatal error in scan worker: {e}", exc_info=True)
            self.error.emit(str(e))
        finally:
            if self.should_stop:
                logger.info("Scan worker stopped by user")
            self.finished.emit()

    def update_debug_images(self) -> None:
        """Capture and update debug images."""
        try:
            # Get scanner settings
            config = ConfigManager()
            scanner_settings = config.get_scanner_settings()
            
            # Get minimap dimensions
            minimap_left = scanner_settings.get('minimap_left', 0)
            minimap_top = scanner_settings.get('minimap_top', 0)
            minimap_width = scanner_settings.get('minimap_width', 0)
            minimap_height = scanner_settings.get('minimap_height', 0)
            
            # Define regions relative to minimap
            coordinate_regions = {
                'x': {
                    'left': minimap_left,
                    'top': minimap_top + minimap_height,
                    'width': minimap_width // 3,
                    'height': 20
                },
                'y': {
                    'left': minimap_left + minimap_width // 3,
                    'top': minimap_top + minimap_height,
                    'width': minimap_width // 3,
                    'height': 20
                },
                'k': {
                    'left': minimap_left + (2 * minimap_width) // 3,
                    'top': minimap_top + minimap_height,
                    'width': minimap_width // 3,
                    'height': 20
                }
            }
            
            with mss() as sct:
                for coord_type, region in coordinate_regions.items():
                    # Capture and process image
                    screenshot = np.array(sct.grab(region))
                    gray = cv2.cvtColor(screenshot, cv2.COLOR_BGR2GRAY)
                    gray = cv2.convertScaleAbs(gray, alpha=2.0, beta=0)
                    blurred = cv2.GaussianBlur(gray, (3, 3), 0)
                    thresh = cv2.adaptiveThreshold(
                        blurred, 255,
                        cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
                        cv2.THRESH_BINARY,
                        11, 2
                    )
                    
                    # Try OCR
                    text = pytesseract.image_to_string(
                        thresh,
                        config='--psm 7 --oem 3 -c tessedit_char_whitelist=0123456789'
                    )
                    
                    # Clean text and get value
                    try:
                        value = int(''.join(filter(str.isdigit, text.strip())))
                    except ValueError:
                        value = 0
                    
                    # Emit image and value
                    self.debug_image.emit(thresh, coord_type, value)
                    
        except Exception as e:
            logger.error(f"Error updating debug images: {e}")
    
    def stop(self) -> None:
        """Signal the worker to stop."""
        self.should_stop = True

if __name__ == "__main__":
    # Set up logging
    logging.basicConfig(
        level=logging.DEBUG,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%H:%M:%S'
    )
    
    # Run test
    test_coordinate_reading() 