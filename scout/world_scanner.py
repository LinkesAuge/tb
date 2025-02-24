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
from PyQt6.QtCore import QObject, pyqtSignal
from scout.template_matcher import TemplateMatcher
from scout.config_manager import ConfigManager
from scout.debug_window import DebugWindow
from scout.window_manager import WindowManager

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
    
class WorldScanner:
    """
    Automated system for exploring and scanning the game world.
    
    This class provides systematic exploration of the game world by:
    1. Reading current coordinates using OCR (Optical Character Recognition)
    2. Moving to new positions by simulating coordinate input
    3. Generating efficient search patterns for exploration
    4. Working with pattern matching to find specific game elements
    
    The scanner uses a spiral search pattern to methodically cover an area
    around the starting position, ensuring thorough exploration while
    minimizing travel distance.
    
    Key Features:
    - Coordinate detection using Tesseract OCR
    - Automated navigation between positions
    - Spiral search pattern generation
    - Integration with pattern matching for target detection
    """
    
    def __init__(self, window_manager: WindowManager):
        """Initialize the world scanner."""
        self.window_manager = window_manager
        self.config_manager = ConfigManager()
        self.current_pos = None
        self.start_pos = None
        self.scan_step = 50
        self.move_delay = 1.0
        self.visited_positions: List[WorldPosition] = []
        self.minimap_left = 0
        self.minimap_top = 0
        self.minimap_width = 0
        self.minimap_height = 0
        self.dpi_scale = 1.0
        
        # Create debug window
        self.debug_window = DebugWindow()
        
        # Signal for debug images (will be connected by worker)
        self.debug_image = None
        
        logger.debug("WorldScanner initialized")
        
    def get_current_position(self) -> Optional[WorldPosition]:
        """
        Get the current position from the minimap coordinates.
        
        Returns:
            WorldPosition object if coordinates are found, None otherwise
        """
        try:
            # Calculate coordinate regions (scaled for DPI)
            coord_height = int(20 * self.dpi_scale)  # Height for coordinate regions
            coord_spacing = int(5 * self.dpi_scale)  # Space between regions
            
            # Define regions for each coordinate type
            coordinate_regions = {
                'x': {
                    'left': self.minimap_left,
                    'top': self.minimap_top + self.minimap_height + coord_spacing,
                    'width': int(50 * self.dpi_scale),
                    'height': coord_height
                },
                'y': {
                    'left': self.minimap_left + int(60 * self.dpi_scale),
                    'top': self.minimap_top + self.minimap_height + coord_spacing,
                    'width': int(50 * self.dpi_scale),
                    'height': coord_height
                },
                'k': {
                    'left': self.minimap_left + int(120 * self.dpi_scale),
                    'top': self.minimap_top + self.minimap_height + coord_spacing,
                    'width': int(30 * self.dpi_scale),
                    'height': coord_height
                }
            }
            
            # Add visual debug for coordinate regions
            with mss() as sct:
                # Take screenshot of entire minimap area plus coordinates
                context_region = {
                    'left': self.minimap_left,
                    'top': self.minimap_top,
                    'width': self.minimap_width,
                    'height': self.minimap_height + int(30 * self.dpi_scale)  # Add scaled space for coordinates below
                }
                context_shot = np.array(sct.grab(context_region))
                
                # Draw rectangles around coordinate regions
                for coord_type, region in coordinate_regions.items():
                    # Calculate relative positions to context region
                    x1 = region['left'] - context_region['left']
                    y1 = region['top'] - context_region['top']
                    x2 = x1 + region['width']
                    y2 = y1 + region['height']
                    
                    # Only draw if within bounds
                    if (0 <= x1 < context_shot.shape[1] and 
                        0 <= y1 < context_shot.shape[0] and 
                        0 <= x2 < context_shot.shape[1] and 
                        0 <= y2 < context_shot.shape[0]):
                        cv2.rectangle(context_shot, (x1, y1), (x2, y2), (0, 255, 0), 1)
                        cv2.putText(context_shot, coord_type, (x1, y1-5), 
                                  cv2.FONT_HERSHEY_SIMPLEX, 0.5 * self.dpi_scale, (0, 255, 0), 1)
                
                # Update debug window with context image
                self.debug_window.update_image(
                    "Coordinate Regions",
                    context_shot,
                    metadata={
                        "dpi_scale": self.dpi_scale,
                        "minimap_size": f"{self.minimap_width}x{self.minimap_height}"
                    },
                    save=True
                )
                
                # Process each coordinate region
                coordinates = {}
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
                        coordinates[coord_type] = value
                    except ValueError:
                        coordinates[coord_type] = 0
                        logger.warning(f"Failed to parse {coord_type} coordinate")
                    
                    # Update debug window with processed image
                    self.debug_window.update_image(
                        f"Coordinate {coord_type}",
                        thresh,
                        metadata={
                            "raw_text": text.strip(),
                            "value": coordinates[coord_type]
                        },
                        save=True
                    )
                
                if all(coord in coordinates for coord in ['x', 'y', 'k']):
                    position = WorldPosition(
                        x=coordinates['x'],
                        y=coordinates['y'],
                        k=coordinates['k']
                    )
                    logger.info(f"Successfully detected position: X={position.x}, Y={position.y}, K={position.k}")
                    return position
                
                return None
                
        except Exception as e:
            logger.error(f"Error getting current position: {e}", exc_info=True)
            return None
            
    def move_to_position(self, target: WorldPosition) -> bool:
        """
        Move camera to specific coordinates.
        
        Args:
            target: Target position to move to
            
        Returns:
            bool: True if move successful
        """
        try:
            logger.info(f"Moving to position: X={target.x}, Y={target.y}, K={target.k}")
            
            # Get input field coordinates from config
            config = ConfigManager()
            input_settings = config.get_scanner_settings()
            input_x = input_settings.get('input_field_x', 0)
            input_y = input_settings.get('input_field_y', 0)
            
            # Click on coordinate input field
            logger.debug(f"Clicking input field at ({input_x}, {input_y})")
            pyautogui.click(x=input_x, y=input_y)
            sleep(0.2)  # Small delay to ensure click registered
            
            # Clear existing text
            pyautogui.hotkey('ctrl', 'a')
            pyautogui.press('backspace')
            
            # Type coordinates
            coord_text = f"{target.x},{target.y}"
            logger.debug(f"Entering coordinates: {coord_text}")
            pyautogui.write(coord_text)
            pyautogui.press('enter')
            
            # Wait for movement and verify position
            sleep(self.move_delay)
            current_pos = self.get_current_position()
            
            if current_pos:
                success = (current_pos.x == target.x and 
                          current_pos.y == target.y and 
                          current_pos.k == target.k)
                if success:
                    logger.info("Successfully moved to target position")
                else:
                    logger.warning(
                        f"Position mismatch - Target: ({target.x}, {target.y}, {target.k}), "
                        f"Current: ({current_pos.x}, {current_pos.y}, {current_pos.k})"
                    )
                return success
            else:
                logger.error("Failed to verify position after movement")
                return False
            
        except Exception as e:
            logger.error(f"Error moving to position: {e}", exc_info=True)
            return False
            
    def generate_spiral_pattern(self, max_distance: int) -> List[WorldPosition]:
        """
        Generate spiral search pattern starting from current position.
        This ensures methodical coverage of the map.
        """
        positions = []
        x, y = 0, 0
        dx, dy = self.scan_step, 0
        steps = 1
        
        while abs(x) <= max_distance and abs(y) <= max_distance:
            if -1 <= x <= 999 and -1 <= y <= 999:  # Check world boundaries
                new_pos = WorldPosition(
                    x=self.start_pos.x + x,
                    y=self.start_pos.y + y,
                    k=self.start_pos.k
                )
                positions.append(new_pos)
            
            x, y = x + dx, y + dy
            
            if steps % 2 == 0:
                dx, dy = -dy, dx  # Turn 90 degrees
                steps = 0
            steps += 1
            
        return positions
        
    def scan_world_until_match(self, template_matcher: 'TemplateMatcher',
                             max_attempts: int = 10) -> Optional[Tuple[int, int]]:
        """
        Scan the world until a template match is found.
        
        Args:
            template_matcher: TemplateMatcher instance to detect matches
            max_attempts: Maximum number of scan attempts
            
        Returns:
            Tuple of (x, y) coordinates if match found, None otherwise
        """
        attempts = 0
        while attempts < max_attempts:
            # Take screenshot
            screenshot = self.window_manager.capture_screenshot()
            if screenshot is None:
                continue
                
            # Look for matches
            matches = template_matcher.find_matches()
            if matches:
                match = matches[0]  # Take first match
                return (match.bounds[0], match.bounds[1])
                
            attempts += 1
            
        return None

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