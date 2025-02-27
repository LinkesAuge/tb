"""
Overlay System

This module provides a transparent overlay for visualizing detected game elements.
It handles:
- Template matching visualization
- Real-time updates
- Visual feedback
"""

from typing import Optional, List, Tuple, Dict, Any
import cv2
import numpy as np
import win32gui
import win32con
import win32api
from scout.window_manager import WindowManager
from scout.template_matcher import TemplateMatch, GroupedMatch, TemplateMatcher
import logging
from PyQt6.QtWidgets import QWidget
from PyQt6.QtCore import QTimer, pyqtSignal, QRectF
import time
from PyQt6.QtGui import QColor, QPen
from datetime import datetime

logger = logging.getLogger(__name__)

class Overlay(QWidget):
    """
    Creates a transparent overlay window to visualize detected game elements.
    
    This class provides real-time visual feedback by drawing on top of the game window:
    - Rectangles around detected elements
    - Text labels showing what was detected and confidence levels
    - Cross markers at the center of detected elements
    - Color-coded indicators based on detection type
    
    The overlay is:
    - Transparent to mouse clicks (passes through to game)
    - Always on top of the game window
    - Automatically repositioned when the game window moves
    - Configurable in terms of colors, sizes, and display options
    
    Key Features:
    - Real-time template match visualization
    - Click-through transparency
    - Automatic window tracking
    - Configurable visual elements
    """
    
    # Signals
    visibility_changed = pyqtSignal(bool)  # Emitted when overlay visibility changes
    
    def __init__(self, window_manager: WindowManager, 
                 template_settings: Dict[str, Any], overlay_settings: Dict[str, Any]) -> None:
        """
        Initialize the overlay window with specified settings.
        
        Creates a transparent window that tracks and draws over the game window.
        The overlay uses OpenCV for drawing and Win32 API for window management.
        
        Args:
            window_manager: Manager for tracking the game window
            template_settings: Template matching configuration
            overlay_settings: Visual settings (colors, sizes, etc.)
        """
        super().__init__()
        self.window_manager = window_manager
        self.window_name = "TB Scout Overlay"
        self.active = overlay_settings.get("active", False)
        self.template_matching_active = False
        self.window_hwnd = None  # Store window handle
        self.window_created = False  # Flag to track if window has been created
        
        # Add opacity attribute (default 0.7 = 70%)
        self.opacity = overlay_settings.get("opacity", 0.7)
        
        # Initialize debug visualization flags - RESTORE DEBUG OPTIONS
        self.debug_mode = overlay_settings.get("debug_mode", False)
        self.debug_visuals = overlay_settings.get("debug_visuals", True)
        self.show_text = True
        self.show_cross = True
        self.show_debug_info = True  # New option for showing debug info
        self.update_rate = template_settings.get("target_frequency", 1.0)
        
        # Separate timers for template matching and drawing
        self.template_matching_timer = QTimer()
        self.template_matching_timer.timeout.connect(self._update_template_matching)
        
        self.draw_timer = QTimer()
        self.draw_timer.timeout.connect(self._draw_overlay)
        self.draw_timer.setInterval(33)  # ~30 FPS for drawing
        
        # Add match caching with group persistence
        self.cached_matches: List[Tuple[str, int, int, int, int, float]] = []  # Current cached matches
        self.match_counters: Dict[str, int] = {}  # Cache counters for groups
        # Load persistence and distance settings from config
        self.match_persistence = template_settings.get("match_persistence", 3)  # Default to 3 frames if not in config
        self.distance_threshold = template_settings.get("distance_threshold", 100)  # Default to 100 pixels if not in config
        
        # Reduce persistence for more responsive updates
        self.match_persistence = 1  # Force to 1 frame to make matches disappear more quickly when moving
        logger.info(f"Using match persistence of {self.match_persistence} frames for more responsive updates")
        
        # Convert QColor to BGR format for OpenCV
        rect_color = overlay_settings["rect_color"]
        font_color = overlay_settings["font_color"]
        cross_color = overlay_settings["cross_color"]
        
        # Drawing settings (in BGR format for OpenCV)
        self.rect_color = (rect_color.blue(), rect_color.green(), rect_color.red())
        self.rect_thickness = overlay_settings["rect_thickness"]
        self.rect_scale = overlay_settings["rect_scale"]
        self.font_color = (font_color.blue(), font_color.green(), font_color.red())
        self.font_size = overlay_settings["font_size"]
        self.text_thickness = overlay_settings["text_thickness"]
        self.cross_color = (cross_color.blue(), cross_color.green(), cross_color.red())
        self.cross_size = overlay_settings["cross_size"]
        self.cross_thickness = overlay_settings["cross_thickness"]
        self.cross_scale = overlay_settings.get("cross_scale", 1.0)  # Default to 1.0 if not set
        
        # Track last movement time for more frequent updates when moving
        self.last_movement_time = 0.0
        
        # Create template matcher and make it accessible
        self.template_matcher = TemplateMatcher(
            window_manager=self.window_manager,
            confidence=min(template_settings.get("confidence", 0.8), 0.5),  # Even lower confidence threshold for testing
            target_frequency=template_settings["target_frequency"],
            sound_enabled=template_settings["sound_enabled"]
        )
        
        logger.info(f"Using very lenient confidence threshold of {self.template_matcher.confidence_threshold} to find any possible templates")
        
        # Ensure templates are loaded
        self.template_matcher.reload_templates()
        template_count = len(self.template_matcher.templates)
        logger.info(f"Loaded {template_count} templates for template matching")
        
        # Log detailed template information for debugging
        if template_count > 0:
            logger.info("Templates loaded:")
            for name, template in self.template_matcher.templates.items():
                logger.info(f"  - {name}: Size={template.shape[1]}x{template.shape[0]}")
        else:
            logger.warning("No templates found! Template matching will not work without templates")
            # Log template directory information
            try:
                templates_dir = self.template_matcher.templates_dir
                logger.warning(f"Template directory path: {templates_dir.absolute()}")
                
                # Check if directory exists
                if not templates_dir.exists():
                    logger.error(f"Template directory does not exist: {templates_dir.absolute()}")
                else:
                    # List all files in directory
                    files = list(templates_dir.glob("*"))
                    logger.warning(f"Files in template directory: {[f.name for f in files]}")
                    
                    # List PNG files specifically
                    png_files = list(templates_dir.glob("*.png"))
                    logger.warning(f"PNG files in template directory: {[f.name for f in png_files]}")
            except Exception as e:
                logger.error(f"Error checking template directory: {e}")

        logger.debug(f"Initialized overlay with rect_color={self.rect_color}, "
                    f"font_color={self.font_color}, "
                    f"thickness={self.rect_thickness}, "
                    f"font_size={self.font_size}, "
                    f"rect_scale={self.rect_scale}")

        # Create the overlay window now, but keep it hidden
        logger.info("Creating overlay window at initialization")
        self.create_overlay_window()
        if not self.active:
            self._hide_window()

        # For settings UI
        self.highlight_color_name = "Green"  # Default color name

    def create_overlay_window(self) -> None:
        """Create the overlay window with transparency."""
        # Check if we already have a valid window
        if self.window_hwnd and win32gui.IsWindow(self.window_hwnd):
            logger.info(f"Window already exists with handle {self.window_hwnd} - updating position")
            self._update_window_position()
            return
            
        logger.info("Creating overlay window")
        
        # Get window position
        pos = self.window_manager.get_window_rect()
        if not pos:
            logger.warning("Target window not found, cannot create overlay")
            return
        
        # Unpack the tuple (left, top, right, bottom)
        left, top, right, bottom = pos
        width = right - left
        height = bottom - top
        x = left
        y = top
        
        # Validate dimensions
        if width <= 0 or height <= 0:
            logger.error(f"Invalid window dimensions: {width}x{height}")
            return
        
        logger.debug(f"Creating overlay window at ({x}, {y}) with size {width}x{height}")
        
        try:
            # Create initial transparent overlay
            overlay = np.zeros((height, width, 3), dtype=np.uint8)
            overlay[:] = (255, 0, 255)  # Magenta background for transparency
            
            # Create window with proper style - initially invisible
            window_style = cv2.WINDOW_NORMAL | cv2.WINDOW_FREERATIO
            cv2.namedWindow(self.window_name, window_style)
            
            # Get window handle before showing anything
            hwnd = win32gui.FindWindow(None, self.window_name)
            if not hwnd:
                logger.error("Failed to create overlay window")
                return
                
            # Store the new window handle
            self.window_hwnd = hwnd
            self.window_created = True
            logger.debug(f"Created window with handle: {hwnd}")
            
            # Set window styles for transparency BEFORE showing content
            style = win32gui.GetWindowLong(hwnd, win32con.GWL_STYLE)
            style &= ~(win32con.WS_CAPTION | win32con.WS_THICKFRAME | win32con.WS_BORDER)
            style |= win32con.WS_POPUP
            win32gui.SetWindowLong(hwnd, win32con.GWL_STYLE, style)
            
            # Set extended window styles for transparency and click-through
            ex_style = win32gui.GetWindowLong(hwnd, win32con.GWL_EXSTYLE)
            ex_style |= (win32con.WS_EX_LAYERED | win32con.WS_EX_TRANSPARENT | win32con.WS_EX_TOOLWINDOW)
            win32gui.SetWindowLong(hwnd, win32con.GWL_EXSTYLE, ex_style)
            
            # Position window off-screen initially to prevent flash
            win32gui.SetWindowPos(
                hwnd, win32con.HWND_TOPMOST,
                -10000, -10000, width, height,  # Position off-screen initially
                win32con.SWP_NOACTIVATE
            )
            
            # Apply transparency color key
            win32gui.SetLayeredWindowAttributes(
                hwnd,
                win32api.RGB(255, 0, 255),  # Magenta color key
                0,  # Alpha (0 = fully transparent for non-magenta pixels)
                win32con.LWA_COLORKEY
            )
            
            # Now show the content with transparency 
            cv2.imshow(self.window_name, overlay)
            try:
                cv2.waitKey(1)
            except (cv2.error, Exception) as e:
                # This can happen in certain environments, but we can safely ignore it
                # as long as the window is displayed correctly
                logger.debug(f"Ignored OpenCV waitKey error: {str(e)}")
                # Continue with the drawing process despite the error
            
            # Wait a tiny bit for window to initialize transparency
            time.sleep(0.05)
            
            # Move window to proper position
            win32gui.SetWindowPos(
                hwnd, win32con.HWND_TOPMOST,
                x, y, width, height,
                win32con.SWP_NOACTIVATE
            )
            
            # Initially hide the window if overlay is not active
            if not self.active:
                self._hide_window()
                logger.debug("Window initially hidden as overlay is not active")
            else:
                # Make sure transparency settings are applied
                self._draw_empty_overlay()
                logger.debug("Window initially shown with transparency")
            
            logger.debug("Overlay window created with transparency settings")
            
        except Exception as e:
            logger.error(f"Error creating overlay window: {e}")
            return

    def _draw_empty_overlay(self) -> None:
        """Draw an empty transparent overlay to ensure window is properly initialized."""
        if not self.window_hwnd or not win32gui.IsWindow(self.window_hwnd):
            return
            
        try:
            # Get current window size
            pos = self.window_manager.get_window_rect()
            if not pos:
                return
                
            # Unpack the tuple (left, top, right, bottom)
            left, top, right, bottom = pos
            width = right - left
            height = bottom - top
            
            # Create empty magenta background (for transparency)
            overlay = np.zeros((height, width, 3), dtype=np.uint8)
            overlay[:] = (255, 0, 255)  # Set background to magenta
            
            # Show the empty overlay
            cv2.imshow(self.window_name, overlay)
            try:
                cv2.waitKey(1)
            except (cv2.error, Exception) as e:
                # This can happen in certain environments, but we can safely ignore it
                # as long as the window is displayed correctly
                logger.debug(f"Ignored OpenCV waitKey error: {str(e)}")
            
            # Refresh transparency settings
            win32gui.SetLayeredWindowAttributes(
                self.window_hwnd,
                win32api.RGB(255, 0, 255),  # Magenta color key
                0,  # Alpha
                win32con.LWA_COLORKEY
            )
        except Exception as e:
            logger.error(f"Error drawing empty overlay: {e}")

    def _update_window_position(self) -> None:
        """Update the overlay window position and size to match the game window."""
        if not self.window_hwnd or not win32gui.IsWindow(self.window_hwnd):
            logger.warning("Cannot update position - window handle is invalid")
            return
            
        pos = self.window_manager.get_window_rect()
        if not pos:
            logger.warning("Target window not found, cannot update overlay position")
            return
            
        # Unpack the tuple (left, top, right, bottom)
        left, top, right, bottom = pos
        width = right - left
        height = bottom - top
        x = left
        y = top
        
        # Track if window has moved to reduce logging noise
        if hasattr(self, 'last_window_pos'):
            window_moved = self.last_window_pos != (x, y, width, height)
        else:
            window_moved = True
            
        # Store current position for future comparisons
        self.last_window_pos = (x, y, width, height)
        
        try:
            if window_moved:
                logger.debug(f"Window moved to ({x}, {y}) with size {width}x{height}, updating overlay")
                # Track movement time for faster updates
                self.last_movement_time = time.time()
                
                # Adjust position check timer to run more frequently during movement
                if hasattr(self, 'position_check_timer') and self.position_check_timer.isActive():
                    # Speed up checks when window is moving (every 50ms)
                    self.position_check_timer.setInterval(50)
                
            # Calculate time since last movement
            since_last_movement = time.time() - self.last_movement_time
            
            # Update window position, size and ensure it's topmost
            win32gui.SetWindowPos(
                self.window_hwnd, win32con.HWND_TOPMOST,
                x, y, width, height,
                win32con.SWP_SHOWWINDOW | win32con.SWP_NOACTIVATE
            )
            
            # After 2 seconds without movement, slow down the position checks again
            if since_last_movement > 2.0 and hasattr(self, 'position_check_timer') and self.position_check_timer.interval() < 200:
                self.position_check_timer.setInterval(200)
            
            if window_moved:
                logger.debug(f"Updated window position to ({x}, {y}) with size {width}x{height}")
                
                # Force a template matching update when window moves
                if since_last_movement < 2.0:  # If moved within last 2 seconds
                    # Trigger an immediate update to keep matches current when moving
                    QTimer.singleShot(10, self._update_template_matching)
                
                # Force a redraw when window moves
                QTimer.singleShot(50, self._draw_overlay)
        except Exception as e:
            logger.error(f"Error updating window position: {e}")

    def _hide_window(self) -> None:
        """Hide the overlay window."""
        if not self.window_created or not self.window_hwnd:
            return
            
        if not win32gui.IsWindow(self.window_hwnd):
            logger.warning("Invalid window handle in hide_window - marking as not created")
            self.window_hwnd = None
            self.window_created = False
            return
            
        try:
            win32gui.ShowWindow(self.window_hwnd, win32con.SW_HIDE)
            logger.debug("Window hidden")
        except Exception as e:
            logger.error(f"Error hiding window: {e}")
            # Even if hiding fails, we keep the handle since we might be able to use it later

    def _show_window(self) -> None:
        """Show the overlay window."""
        if not self.window_created or not self.window_hwnd:
            # Create window if it doesn't exist
            self.create_overlay_window()
            return
            
        if not win32gui.IsWindow(self.window_hwnd):
            logger.warning("Invalid window handle - recreating window")
            self.window_hwnd = None
            self.window_created = False
            self.create_overlay_window()
            return
            
        try:
            # Update position before showing
            self._update_window_position()
            
            # Draw something immediately to ensure proper transparency
            self._draw_empty_overlay()
            
            # Show window and make it topmost
            win32gui.ShowWindow(self.window_hwnd, win32con.SW_SHOW)
            win32gui.SetWindowPos(
                self.window_hwnd, win32con.HWND_TOPMOST,
                0, 0, 0, 0,  # Ignore position/size parameters
                win32con.SWP_NOMOVE | win32con.SWP_NOSIZE | win32con.SWP_SHOWWINDOW | win32con.SWP_NOACTIVATE
            )
            
            # Refresh transparency
            win32gui.SetLayeredWindowAttributes(
                self.window_hwnd,
                win32api.RGB(255, 0, 255),  # Magenta color key
                0,  # Alpha
                win32con.LWA_COLORKEY
            )
            
            logger.debug("Window shown and set as topmost with transparency")
        except Exception as e:
            logger.error(f"Error showing window: {e}")
            # If we encounter an error, try recreating the window
            self.window_hwnd = None
            self.window_created = False
            self.create_overlay_window()

    def start_template_matching(self) -> None:
        """Start continuous template matching."""
        if not self.active:
            logger.debug("Set active to True and showing overlay window")
            self.active = True
            self._show_window()
        
        if not self.template_matching_active:
            logger.info("Starting template matching")
            self.template_matching_active = True
            
            # Make sure window is created and visible
            if not self.window_created or not self.window_hwnd:
                logger.debug("Creating overlay window for template matching")
                self.create_overlay_window()
                
            # Ensure the overlay is visible
            self._show_window()
            
            # Configure template matching timer
            if not hasattr(self, 'template_matching_timer') or self.template_matching_timer is None:
                logger.debug("Creating template matching timer")
                self.template_matching_timer = QTimer()
                self.template_matching_timer.timeout.connect(self._update_template_matching)
            
            # Create a separate position check timer that runs more frequently
            if not hasattr(self, 'position_check_timer') or self.position_check_timer is None:
                logger.debug("Creating position check timer")
                self.position_check_timer = QTimer()
                self.position_check_timer.timeout.connect(self._update_window_position)
                # Check position 5 times per second
                self.position_check_timer.start(200)
                logger.info("Position check timer started with interval 200ms")
            
            # Calculate timer interval for template matching
            interval_ms = int(1000 / self.update_rate)
            logger.info(f"Setting template matching timer interval to {interval_ms}ms")
            
            # Start timer
            self.template_matching_timer.start(interval_ms)
            logger.info(f"Template matching timer started with interval {interval_ms}ms")
            
            # Force an immediate window position update
            self._update_window_position()
            
            # Force an immediate update to populate matches
            QTimer.singleShot(100, self._update_template_matching)
            
            # Also force a redraw
            QTimer.singleShot(200, self._draw_overlay)
        else:
            logger.debug("Template matching already active")
            
        # Visual confirmation
        logger.info("Template matching started")

    def update_timer_interval(self) -> None:
        """Update the template matching timer interval based on target frequency."""
        if not hasattr(self.template_matcher, 'target_frequency'):
            logger.warning("Template matcher has no target_frequency attribute")
            return
            
        # Force a higher update frequency for more responsive updates
        # Set minimum interval to 16ms (60 FPS) for maximum responsiveness
        target_frequency = max(10.0, self.template_matcher.target_frequency) 
        interval = max(int(1000 / target_frequency), 16)
        
        logger.debug(
            f"Updating template matching timer interval: "
            f"target_frequency={target_frequency:.2f} updates/sec -> "
            f"interval={interval}ms (faster for responsive updates)"
        )
        
        if self.template_matching_active:
            # Stop the timer if it's running
            if self.template_matching_timer.isActive():
                self.template_matching_timer.stop()
            
            # Set new interval and start timer
            self.template_matching_timer.setInterval(interval)
            self.template_matching_timer.start()
            logger.info(f"Template matching timer restarted with new interval: {interval}ms")

    def _destroy_window_safely(self) -> None:
        """Safely destroy the overlay window if it exists."""
        try:
            # First check if we have a stored handle
            if self.window_hwnd and win32gui.IsWindow(self.window_hwnd):
                logger.debug(f"Hiding window with stored handle: {self.window_hwnd}")
                self._hide_window()
                # Don't destroy window, just hide it
                # cv2.destroyWindow(self.window_name)
                # self.window_hwnd = None
                # self.window_created = False
                # logger.info("Overlay window destroyed (using stored handle)")
                return
                
            # If not, try to find by name
            hwnd = win32gui.FindWindow(None, self.window_name)
            if hwnd:
                logger.debug(f"Hiding window with found handle: {hwnd}")
                self.window_hwnd = hwnd
                self._hide_window()
                # Don't destroy window, just hide it
                # cv2.destroyWindow(self.window_name)
                # logger.info("Overlay window destroyed (using found handle)")
        except Exception as e:
            logger.debug(f"Window hide skipped: {e}")

    def _get_group_key(self, match: Tuple[str, int, int, int, int, float]) -> str:
        """Get the cache key for a match based on approximate position only (not template name)."""
        _, x, y, _, _, _ = match
        # Use grid-based position to allow for small movements
        grid_size = self.distance_threshold
        grid_x = x // grid_size
        grid_y = y // grid_size
        # No longer include template name in key since we want to group across templates
        return f"pos_{grid_x}_{grid_y}"

    def _is_same_group(self, match1: Tuple[str, int, int, int, int, float],
                      match2: Tuple[str, int, int, int, int, float]) -> bool:
        """
        Check if two matches belong to the same group based on position.
        Matches from different templates can be grouped if they are close enough.
        
        Args:
            match1: First match tuple (name, x, y, w, h, conf)
            match2: Second match tuple (name, x, y, w, h, conf)
            
        Returns:
            bool: True if matches are in the same group
        """
        # Extract positions and dimensions
        name1, x1, y1, w1, h1, _ = match1
        name2, x2, y2, w2, h2, _ = match2
        
        # Calculate centers
        center1_x = x1 + w1 // 2
        center1_y = y1 + h1 // 2
        center2_x = x2 + w2 // 2
        center2_y = y2 + h2 // 2
        
        # Check if centers are within threshold
        return (abs(center1_x - center2_x) <= self.distance_threshold and
                abs(center1_y - center2_y) <= self.distance_threshold)

    def _update_template_matching(self) -> None:
        """Update template matching matches."""
        if not self.template_matching_active or not self.active:
            logger.debug("Template matching not active, skipping update")
            return
            
        if not self.template_matcher:
            logger.warning("No template matcher available")
            return
            
        try:
            # Get current time and check if we're in a movement state
            current_time = time.time()
            is_moving = (current_time - self.last_movement_time) < 1.0
            
            # Get screenshot
            screenshot = self.window_manager.capture_screenshot()
            
            if screenshot is None:
                logger.warning("Failed to capture screenshot for template matching")
                return
                
            # Log screenshot capture success
            logger.debug(f"Captured screenshot for template matching: {screenshot.shape}")
            
            # Find matches using template matcher
            if hasattr(self.template_matcher, 'find_all_templates'):
                # Clear previous matches
                self.cached_matches = []
                
                # When moving, we use a higher confidence threshold to only 
                # show high-confidence matches for better performance
                original_threshold = None
                if is_moving and not self.debug_mode:
                    original_threshold = self.template_matcher.confidence_threshold
                    # Use higher threshold during movement to only show strong matches
                    self.template_matcher.set_confidence_threshold(0.85)
                    logger.debug("Using higher confidence threshold during movement")
                
                # Find new matches
                matches = self.template_matcher.find_all_templates(screenshot)
                
                # Restore original threshold if it was changed
                if original_threshold is not None:
                    self.template_matcher.set_confidence_threshold(original_threshold)
                
                # Update cached matches
                self.cached_matches.extend(matches)
                
                # Log number of matches found
                logger.debug(f"Template matcher found {len(matches)} matches")
                if len(matches) > 0:
                    logger.debug(f"First match: {matches[0]}")
                    
                # Update the overlay display
                self._draw_overlay()
                
                # If we're moving, schedule another update soon to keep matches fresh
                if is_moving:
                    QTimer.singleShot(100, self._update_template_matching)
            else:
                logger.warning("Template matcher missing find_all_templates method")
                
        except Exception as e:
            logger.error(f"Error in template matching update: {e}", exc_info=True)

    def _draw_overlay(self) -> None:
        """Draw the overlay with all registered elements."""
        if not self.window_hwnd or not win32gui.IsWindow(self.window_hwnd):
            logger.warning("Cannot draw overlay - window handle is invalid")
            return
            
        try:
            # Get window position and size - ensure position is synced
            pos = self.window_manager.get_window_rect()
            if not pos:
                logger.warning("Failed to get window position for drawing overlay")
                return
                
            # Unpack the tuple (left, top, right, bottom)
            left, top, right, bottom = pos
            width = right - left
            height = bottom - top
            
            # Create a transparent overlay
            overlay_image = np.zeros((height, width, 3), dtype=np.uint8)
            overlay_image[:] = (255, 0, 255)  # Magenta for transparency
            
            # Draw template matches if available
            draw_count = 0
            if hasattr(self, 'cached_matches') and self.cached_matches:
                match_count = len(self.cached_matches)
                logger.debug(f"Drawing {match_count} template matches")
                
                # Sort matches by confidence (highest first)
                sorted_matches = sorted(self.cached_matches, key=lambda m: m[5], reverse=True)
                
                # Limit to top 50 matches to avoid clutter and ensure performance
                if not self.debug_visuals:
                    sorted_matches = sorted_matches[:50]
                
                # Count matches by confidence range
                high_conf_count = 0
                med_conf_count = 0
                low_conf_count = 0
                
                for i, match in enumerate(sorted_matches):
                    try:
                        # Extract match information
                        template_name, x, y, width, height, confidence = match
                        
                        # Validate coordinates and size
                        if width <= 0 or height <= 0:
                            logger.warning(f"Invalid match dimensions: {width}x{height} for {template_name}")
                            continue
                            
                        if x < 0 or y < 0:
                            logger.warning(f"Negative coordinates: ({x}, {y}) for {template_name}")
                            # Adjust to visible area
                            width = width + x if x < 0 else width
                            height = height + y if y < 0 else height
                            x = max(0, x)
                            y = max(0, y)
                            if width <= 0 or height <= 0:
                                continue
                                
                        # Skip if position is outside the window
                        if x >= right - left or y >= bottom - top:
                            logger.warning(f"Coordinates outside window: ({x}, {y}) for {template_name}")
                            continue
                        
                        # Choose color based on confidence
                        # Always show high confidence matches, but only show lower confidence in debug mode
                        if confidence >= 0.8:
                            rect_color = (0, 255, 0)  # Green for high confidence
                            high_conf_count += 1
                        elif confidence >= 0.7 and self.debug_visuals:
                            rect_color = (0, 255, 255)  # Yellow for medium confidence
                            med_conf_count += 1
                        elif confidence >= 0.5 and self.debug_visuals:
                            rect_color = (0, 0, 255)  # Red for low confidence
                            low_conf_count += 1
                        else:
                            # Skip drawing if confidence is too low and not in debug mode
                            continue
                        
                        # Always draw high confidence matches
                        # Draw rectangle with thicker lines for better visibility
                        thickness = 2 if confidence >= 0.8 else 1
                        cv2.rectangle(overlay_image, (x, y), (x + width, y + height), rect_color, thickness)
                        
                        # Draw text label if debug visuals enabled or high confidence
                        if self.debug_visuals or confidence >= 0.8:
                            # Prepare text
                            text = f"{template_name} ({confidence:.2f})"
                            
                            # Calculate text size and position
                            font = cv2.FONT_HERSHEY_SIMPLEX
                            font_scale = 0.5
                            text_thickness = 1
                            (text_width, text_height), _ = cv2.getTextSize(text, font, font_scale, text_thickness)
                            
                            # Draw background for text
                            text_bg_color = (0, 0, 0)  # Black background for text
                            cv2.rectangle(overlay_image, (x, y - text_height - 5), (x + text_width, y), text_bg_color, -1)
                            
                            # Draw text
                            cv2.putText(overlay_image, text, (x, y - 5), font, font_scale, (255, 255, 255), text_thickness)
                        
                        draw_count += 1
                    except Exception as e:
                        logger.warning(f"Error drawing match {i}: {e}")
                
                # Log counts by confidence level
                logger.debug(f"Match confidence breakdown - High: {high_conf_count}, Medium: {med_conf_count}, Low: {low_conf_count}")
            
            # Draw debug visuals if enabled
            if self.debug_visuals:
                # Draw circle at top-left corner for debugging
                cv2.circle(overlay_image, (10, 10), 5, (0, 0, 255), -1)
                
                # Draw debug text
                debug_text = f"Overlay Active - Matches: {draw_count}"
                cv2.putText(overlay_image, debug_text, (20, 20), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 255), 1)
                
                # Show current time
                time_text = f"Time: {time.strftime('%H:%M:%S')}"
                cv2.putText(overlay_image, time_text, (20, 40), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 255), 1)
            
            # Draw debug info if enabled
            if self.show_debug_info:
                # Draw debug information at bottom of screen
                window_text = f"Window: {self.window_manager.window_title} ({self.window_hwnd})"
                cv2.putText(overlay_image, window_text, (20, height - 60), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 255), 1)
                
                # Show window position and size
                pos_text = f"Position: ({left}, {top}) Size: {width}x{height}"
                cv2.putText(overlay_image, pos_text, (20, height - 40), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 255), 1)
                
                # Show match count
                if hasattr(self, 'cached_matches'):
                    match_text = f"Matches: {len(self.cached_matches)} (Drawn: {draw_count})"
                    cv2.putText(overlay_image, match_text, (20, height - 20), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 255), 1)
            
            # Display the overlay
            cv2.imshow(self.window_name, overlay_image)
            cv2.waitKey(1)  # Update the window, required for OpenCV
            
            # Ensure the window stays on top
            if self.window_hwnd:
                win32gui.SetWindowPos(
                    self.window_hwnd,
                    win32con.HWND_TOPMOST,
                    0, 0, 0, 0,
                    win32con.SWP_NOMOVE | win32con.SWP_NOSIZE
                )
                
            # Set transparency (magenta color key)
            win32gui.SetLayeredWindowAttributes(
                self.window_hwnd,
                win32api.RGB(255, 0, 255),  # Magenta
                0,  # Alpha
                win32con.LWA_COLORKEY
            )
            
            logger.debug(f"Overlay drawing completed successfully")
        except Exception as e:
            logger.error(f"Error drawing overlay: {e}", exc_info=True)

    def stop_template_matching(self) -> None:
        """Stop template matching."""
        logger.info("Stopping template matching")
        self.template_matching_active = False
        
        # Save the template matching active state to ensure it persists across sessions
        try:
            # Check if we have access to config manager through parent or signal bus
            if hasattr(self, 'window_manager') and hasattr(self.window_manager, 'config_manager'):
                self.window_manager.config_manager.set("template_matching.active", str(self.template_matching_active).lower())
                self.window_manager.config_manager.save_config()
                logger.info(f"Saved template matching active state: {self.template_matching_active}")
        except Exception as e:
            logger.warning(f"Could not save template matching active state: {e}")
        
        # Stop timers
        if hasattr(self, 'template_matching_timer') and self.template_matching_timer.isActive():
            self.template_matching_timer.stop()
            logger.debug("Stopped template matching timer")
        
        if hasattr(self, 'position_check_timer') and self.position_check_timer.isActive():
            self.position_check_timer.stop()
            logger.debug("Stopped position check timer")
        
        if hasattr(self, 'draw_timer') and self.draw_timer.isActive():
            self.draw_timer.stop()
            logger.debug("Stopped draw timer")
        
        # Reset template matcher frequency
        self.template_matcher.update_frequency = 0.0
        self.template_matcher.last_update_time = 0.0
        
        # Clear match cache
        self.cached_matches = []
        self.match_counters.clear()
        
        # Hide window but never destroy it
        if self.window_hwnd and win32gui.IsWindow(self.window_hwnd):
            self._hide_window()
            
        logger.debug("Template matching stopped, window hidden")

    def toggle(self) -> None:
        """Toggle the overlay visibility."""
        previous_state = self.active
        self.active = not self.active
        logger.info(f"Overlay {'activated' if self.active else 'deactivated'}")
        
        if self.active:
            # Show window if template matching is also active
            if self.template_matching_active:
                self._show_window()
                
                # Force an immediate draw to show visuals
                logger.debug("Forcing immediate overlay draw after activation")
                self._draw_overlay()
        else:
            # Hide window 
            self._hide_window()
        
        # Save the active state to ensure it persists across sessions
        try:
            # Check if we have access to config manager through parent or signal bus
            if hasattr(self, 'window_manager') and hasattr(self.window_manager, 'config_manager'):
                self.window_manager.config_manager.set("Overlay.active", str(self.active).lower())
                self.window_manager.config_manager.save_config()
                logger.info(f"Saved overlay active state: {self.active}")
        except Exception as e:
            logger.warning(f"Could not save overlay active state: {e}")
        
        # Emit signal if state changed
        if previous_state != self.active:
            self.visibility_changed.emit(self.active)

    def clear(self) -> None:
        """
        Clear all matches and reset the overlay.
        """
        logger.debug("Clearing overlay matches")
        # Clear match cache
        self.cached_matches = []
        self.match_counters.clear()
        
        # Force redraw
        if self.active and self.template_matching_active:
            self._draw_overlay()
            
        # Emit signal that visibility might have changed
        self.visibility_changed.emit(False)

    def set_visible(self, visible: bool) -> None:
        """
        Set the overlay visibility state.
        
        Args:
            visible: Whether overlay should be visible
        """
        if self.active != visible:
            self.active = visible
            logger.info(f"Overlay {'activated' if self.active else 'deactivated'}")
            
            if self.active:
                # Show window if template matching is also active
                if self.template_matching_active:
                    self._show_window()
                    
                    # Force an immediate draw to show visuals
                    logger.debug("Forcing immediate overlay draw after activation")
                    self._draw_overlay()
            else:
                # Hide window
                self._hide_window()
                
            # Save the active state to ensure it persists across sessions
            try:
                # Check if we have access to config manager through parent or signal bus
                if hasattr(self, 'window_manager') and hasattr(self.window_manager, 'config_manager'):
                    self.window_manager.config_manager.set("Overlay.active", str(self.active).lower())
                    self.window_manager.config_manager.save_config()
                    logger.info(f"Saved overlay active state: {self.active}")
            except Exception as e:
                logger.warning(f"Could not save overlay active state: {e}")
                
            # Emit signal for visibility change
            self.visibility_changed.emit(self.active)

    def set_opacity(self, opacity: float) -> None:
        """
        Set the overlay opacity.
        
        Args:
            opacity: Opacity value between 0.0 and 1.0
        """
        self.opacity = max(0.0, min(1.0, opacity))
        logger.debug(f"Overlay opacity set to {self.opacity}")
        
    def set_highlight_color(self, color_name: str) -> None:
        """
        Set the highlight color for the overlay.
        
        Args:
            color_name: Color name (e.g., "Red", "Green", "Blue", etc.)
        """
        self.highlight_color_name = color_name
        
        # Map color name to BGR values for OpenCV
        color_map = {
            "Red": (0, 0, 255),    # BGR format
            "Green": (0, 255, 0),
            "Blue": (255, 0, 0),
            "Yellow": (0, 255, 255),
            "Cyan": (255, 255, 0),
            "Magenta": (255, 0, 255),
            "White": (255, 255, 255),
            "Orange": (0, 165, 255),
            "Purple": (128, 0, 128)
        }
        
        # Set the rect_color to the mapped color or default to green
        if color_name in color_map:
            self.rect_color = color_map[color_name]
            logger.debug(f"Highlight color set to {color_name}: {self.rect_color}")
        else:
            self.rect_color = (0, 255, 0)  # Default to green
            logger.warning(f"Unknown color name '{color_name}', using green as default")
        
    def update_position(self) -> None:
        """Update the position of the overlay window to match the target window."""
        if self.window_created and self.window_hwnd and win32gui.IsWindow(self.window_hwnd):
            self._update_window_position()
        else:
            # If window doesn't exist, try to create it
            self.create_overlay_window()

    def toggle_debug_visuals(self) -> None:
        """Toggle debug visualizations on/off."""
        self.debug_visuals = not self.debug_visuals
        logger.info(f"Debug visuals {'enabled' if self.debug_visuals else 'disabled'}")
        
        # Save setting to configuration if available
        if hasattr(self, 'window_manager') and hasattr(self.window_manager, 'config_manager') and self.window_manager.config_manager:
            self.window_manager.config_manager.set("Overlay.debug_visuals", str(self.debug_visuals).lower())
            self.window_manager.config_manager.save_config()
            logger.debug(f"Saved debug visuals setting: {self.debug_visuals}")
        
        # Clear cached matches to force a fresh draw
        if hasattr(self, 'cached_matches'):
            self.cached_matches = []
        
        # Force an immediate redraw to show/hide debug elements
        self._draw_overlay()
        
    def toggle_debug_info(self) -> None:
        """Toggle debug information display on/off."""
        self.show_debug_info = not self.show_debug_info
        logger.info(f"Debug info {'enabled' if self.show_debug_info else 'disabled'}")
        
        # Save setting to configuration if available
        if hasattr(self, 'window_manager') and hasattr(self.window_manager, 'config_manager') and self.window_manager.config_manager:
            self.window_manager.config_manager.set("Overlay.show_debug_info", str(self.show_debug_info).lower())
            self.window_manager.config_manager.save_config()
            logger.debug(f"Saved debug info setting: {self.show_debug_info}")
        
        # Clear cached matches to force a fresh draw
        if hasattr(self, 'cached_matches'):
            self.cached_matches = []
        
        # Force an immediate redraw to show/hide debug info
        self._draw_overlay()
        
    def set_debug_mode(self, enabled: bool) -> None:
        """
        Set debug mode on or off.
        
        Args:
            enabled: Whether debug mode should be enabled
        """
        self.debug_mode = enabled
        # When enabling debug mode, also enable visuals and info
        if enabled:
            self.debug_visuals = True
            self.show_debug_info = True
        logger.info(f"Debug mode {'enabled' if enabled else 'disabled'}")
        
        # Save settings to configuration if available
        if hasattr(self, 'window_manager') and hasattr(self.window_manager, 'config_manager') and self.window_manager.config_manager:
            self.window_manager.config_manager.set("Overlay.debug_mode", str(self.debug_mode).lower())
            self.window_manager.config_manager.set("Overlay.debug_visuals", str(self.debug_visuals).lower())
            self.window_manager.config_manager.set("Overlay.show_debug_info", str(self.show_debug_info).lower())
            self.window_manager.config_manager.save_config()
            logger.debug(f"Saved debug mode settings")
        
        # Clear cached matches to force a fresh draw
        if hasattr(self, 'cached_matches'):
            self.cached_matches = []
        
        # Force an immediate redraw
        self._draw_overlay()
