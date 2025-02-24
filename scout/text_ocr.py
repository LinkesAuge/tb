from typing import Optional, Dict, Any, NamedTuple
import numpy as np
import cv2
import logging
import pytesseract
from PyQt6.QtCore import QObject, QTimer, pyqtSignal, QDateTime
import re
from dataclasses import dataclass
from scout.debug_window import DebugWindow
from scout.window_manager import WindowManager
import mss

logger = logging.getLogger(__name__)

@dataclass
class GameCoordinates:
    """Represents coordinates in the game world."""
    k: Optional[int] = None
    x: Optional[int] = None
    y: Optional[int] = None
    timestamp: Optional[str] = None

    def is_valid(self) -> bool:
        """Check if all coordinates are present."""
        return all(isinstance(v, int) for v in [self.k, self.x, self.y])

    def __str__(self) -> str:
        """String representation of coordinates with timestamp."""
        coords = f"K: {self.k if self.k is not None else 'None'}, "
        coords += f"X: {self.x if self.x is not None else 'None'}, "
        coords += f"Y: {self.y if self.y is not None else 'None'}"
        if self.timestamp:
            coords += f" ({self.timestamp})"
        return coords

class TextOCR(QObject):
    """
    Handles continuous OCR processing of a selected screen region.
    
    This class provides:
    - Continuous capture of a specified screen region
    - OCR processing of the captured region
    - Coordinate extraction and validation
    - Debug visualization of the captured region and OCR results
    - Configurable update frequency
    """
    
    # Signals
    debug_image = pyqtSignal(str, object, dict)  # name, image, metadata
    coordinates_updated = pyqtSignal(GameCoordinates)  # Emits when coordinates are read
    
    def __init__(self, debug_window: DebugWindow, window_manager: WindowManager) -> None:
        """
        Initialize Text OCR processor.
        
        Args:
            debug_window: Debug window for visualization
            window_manager: Window manager instance for window tracking and coordinate handling
        """
        super().__init__()
        self.debug_window = debug_window
        self.window_manager = window_manager
        self.active = False
        self.region: Optional[Dict[str, int]] = None
        self.update_frequency = 0.5  # Default 0.5 updates/sec
        
        # Initialize coordinates
        self.current_coords = GameCoordinates()
        
        # Create timer for updates
        self.update_timer = QTimer()
        self.update_timer.timeout.connect(self._process_region)
        
        logger.debug("TextOCR initialized")
    
    def set_region(self, region: Dict[str, int]) -> None:
        """
        Set the region to process.
        
        Args:
            region: Dictionary with left, top, width, height in physical coordinates
        """
        self.region = region
        logger.info(f"OCR region set to: {region}")
        
        # If active, force an immediate capture
        if self.active:
            self._process_region()
    
    def set_frequency(self, frequency: float) -> None:
        """
        Set update frequency.
        
        Args:
            frequency: Updates per second
        """
        self.update_frequency = frequency
        interval = int(1000 / frequency)  # Convert to milliseconds
        
        if self.active:
            self.update_timer.setInterval(interval)
            logger.debug(f"Update interval set to {interval}ms ({frequency} updates/sec)")
    
    def start(self) -> None:
        """Start OCR processing."""
        if not self.region:
            logger.warning("Cannot start OCR - no region set")
            return
            
        self.active = True
        interval = int(1000 / self.update_frequency)
        self.update_timer.start(interval)
        logger.info(f"OCR processing started with {self.update_frequency} updates/sec")
        
        # Force initial capture
        self._process_region()
    
    def stop(self) -> None:
        """Stop OCR processing."""
        self.active = False
        self.update_timer.stop()
        logger.info("OCR processing stopped")
    
    def _validate_coordinate(self, value: Optional[int], coord_type: str) -> Optional[int]:
        """
        Validate a coordinate value.
        
        Args:
            value: The coordinate value to validate
            coord_type: The type of coordinate (K, X, or Y)
            
        Returns:
            The value if valid, None otherwise
        """
        if value is None:
            return None
            
        if not (0 <= value <= 999):
            logger.error(f"Invalid {coord_type} coordinate: {value} (must be between 0 and 999)")
            return None
            
        return value

    def _extract_coordinates(self, text: str) -> GameCoordinates:
        """
        Extract coordinates from OCR text, handling noise and invalid characters.
        
        Uses strict regex patterns to find coordinates in the format:
        K: number, X: number, Y: number
        Ignores any additional characters or noise in the text.
        
        Args:
            text: The OCR text to parse
            
        Returns:
            GameCoordinates object with extracted values
        """
        # Create new coordinates with current timestamp
        coords = GameCoordinates(
            timestamp=QDateTime.currentDateTime().toString("yyyy-MM-dd hh:mm:ss")
        )
        
        try:
            # Clean text by removing common OCR artifacts and normalizing separators
            cleaned_text = text.replace(';', ':').replace('|', ':')
            
            # Use more precise regex patterns that ignore surrounding noise
            # Look for numbers that appear after K:, X:, or Y: (allowing for optional space)
            k_match = re.search(r'K:?\s*(\d+)(?:\D|$)', cleaned_text)
            x_match = re.search(r'X:?\s*(\d+)(?:\D|$)', cleaned_text)
            y_match = re.search(r'Y:?\s*(\d+)(?:\D|$)', cleaned_text)
            
            # Log the regex matches for debugging
            logger.debug(f"Regex matches - K: {k_match.group(1) if k_match else 'None'}, "
                        f"X: {x_match.group(1) if x_match else 'None'}, "
                        f"Y: {y_match.group(1) if y_match else 'None'}")
            
            # Extract and validate each coordinate
            if k_match:
                try:
                    k_val = self._validate_coordinate(int(k_match.group(1)), "K")
                    coords.k = k_val if k_val is not None else self.current_coords.k
                except ValueError:
                    logger.warning(f"Invalid K value found: {k_match.group(1)}")
                    coords.k = self.current_coords.k
            
            if x_match:
                try:
                    x_val = self._validate_coordinate(int(x_match.group(1)), "X")
                    coords.x = x_val if x_val is not None else self.current_coords.x
                except ValueError:
                    logger.warning(f"Invalid X value found: {x_match.group(1)}")
                    coords.x = self.current_coords.x
            
            if y_match:
                try:
                    y_val = self._validate_coordinate(int(y_match.group(1)), "Y")
                    coords.y = y_val if y_val is not None else self.current_coords.y
                except ValueError:
                    logger.warning(f"Invalid Y value found: {y_match.group(1)}")
                    coords.y = self.current_coords.y
            
            # Log the final extracted coordinates
            logger.debug(f"Extracted coordinates: {coords}")
            
        except Exception as e:
            logger.error(f"Error parsing coordinates: {e}")
            # Keep previous values on error
            coords.k = self.current_coords.k
            coords.x = self.current_coords.x
            coords.y = self.current_coords.y
            
        return coords

    def _process_region(self) -> None:
        """Capture and process the OCR region."""
        if not self.region:
            return
            
        try:
            # Get window position from window manager
            if not self.window_manager.find_window():
                logger.warning("Target window not found")
                return
            
            # Set up capture region using the coordinates directly
            capture_region = {
                'left': self.region['left'],
                'top': self.region['top'],
                'width': self.region['width'],
                'height': self.region['height']
            }
            
            logger.debug(f"Capturing region at: {capture_region}")
            
            # Capture region using mss
            with mss.mss() as sct:
                screenshot = np.array(sct.grab(capture_region))
            
            if screenshot is None:
                logger.warning("Failed to capture OCR region")
                return
            
            # Process image to get white text on black background
            # Convert to grayscale
            gray = cv2.cvtColor(screenshot, cv2.COLOR_BGR2GRAY)
            
            # Apply binary threshold to get black and white image
            _, binary = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
            
            # Invert if text is black (majority of pixels are white)
            white_pixel_count = np.sum(binary == 255)
            total_pixels = binary.size
            if white_pixel_count > total_pixels / 2:
                logger.debug("Inverting image (black text detected)")
                binary = cv2.bitwise_not(binary)
            
            # Perform OCR on the processed image
            text = pytesseract.image_to_string(
                binary,
                config='--psm 6'  # Assume uniform block of text
            )
            
            # Clean text
            raw_text = text.strip()
            
            # Extract and validate coordinates
            new_coords = self._extract_coordinates(raw_text)
            
            # Update current coordinates and emit signal
            self.current_coords = new_coords
            self.coordinates_updated.emit(new_coords)
            
            # Log OCR results
            logger.info("OCR Results:")
            logger.info(f"  Raw text: '{raw_text}'")
            logger.info(f"  Coordinates: {new_coords}")
            logger.info(f"  Region: ({self.region['left']}, {self.region['top']}) {self.region['width']}x{self.region['height']}")
            
            # Update debug window with both original and processed images
            self.debug_window.update_image(
                "OCR Region (Original)",
                screenshot,
                metadata={
                    "size": f"{screenshot.shape[1]}x{screenshot.shape[0]}",
                    "coords": f"({self.region['left']}, {self.region['top']})",
                    "text": raw_text,
                    "coordinates": str(new_coords)
                },
                save=True
            )
            
            self.debug_window.update_image(
                "OCR Region (Processed)",
                binary,
                metadata={
                    "text": raw_text,
                    "coordinates": str(new_coords)
                },
                save=True
            )
            
        except Exception as e:
            logger.error(f"Error processing OCR region: {e}", exc_info=True) 