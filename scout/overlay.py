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
from PyQt6.QtCore import QTimer

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
        
        # Create template matcher and make it accessible
        self.template_matcher = TemplateMatcher(
            window_manager=self.window_manager,
            confidence=template_settings["confidence"],
            target_frequency=template_settings["target_frequency"],
            sound_enabled=template_settings["sound_enabled"]
        )
        
        # Ensure templates are loaded
        self.template_matcher.reload_templates()
        template_count = len(self.template_matcher.templates)
        logger.info(f"Loaded {template_count} templates for template matching")
        if template_count == 0:
            logger.warning("No templates found! Template matching will not work without templates")

        logger.debug(f"Initialized overlay with rect_color={self.rect_color}, "
                    f"font_color={self.font_color}, "
                    f"thickness={self.rect_thickness}, "
                    f"font_size={self.font_size}, "
                    f"rect_scale={self.rect_scale}")

    def create_overlay_window(self) -> None:
        """Create the overlay window with transparency."""
        logger.info("Creating overlay window")
        
        pos = self.window_manager.get_window_position()
        if not pos:
            logger.warning("Target window not found, cannot create overlay")
            return
        
        x, y, width, height = pos
        
        # Validate dimensions
        if width <= 0 or height <= 0:
            logger.error(f"Invalid window dimensions: {width}x{height}")
            return
        
        logger.debug(f"Creating overlay window at ({x}, {y}) with size {width}x{height}")
        
        try:
            # Create initial transparent overlay
            overlay = np.zeros((height, width, 3), dtype=np.uint8)
            overlay[:] = (255, 0, 255)  # Magenta background for transparency
            
            # Create window with proper style
            cv2.namedWindow(self.window_name, cv2.WINDOW_NORMAL | cv2.WINDOW_FREERATIO)
            cv2.imshow(self.window_name, overlay)
            cv2.waitKey(1)  # Process events
            
            hwnd = win32gui.FindWindow(None, self.window_name)
            if not hwnd:
                logger.error("Failed to create overlay window")
                return
            
            # Set window styles for transparency
            style = win32gui.GetWindowLong(hwnd, win32con.GWL_STYLE)
            style &= ~(win32con.WS_CAPTION | win32con.WS_THICKFRAME | win32con.WS_BORDER)
            style |= win32con.WS_POPUP
            win32gui.SetWindowLong(hwnd, win32con.GWL_STYLE, style)
            
            # Set extended window styles for transparency and click-through
            ex_style = win32gui.GetWindowLong(hwnd, win32con.GWL_EXSTYLE)
            ex_style |= (win32con.WS_EX_LAYERED | win32con.WS_EX_TRANSPARENT | win32con.WS_EX_TOOLWINDOW)
            win32gui.SetWindowLong(hwnd, win32con.GWL_EXSTYLE, ex_style)
            
            # Position window and ensure it's topmost
            win32gui.SetWindowPos(
                hwnd, win32con.HWND_TOPMOST,
                x, y, width, height,
                win32con.SWP_SHOWWINDOW | win32con.SWP_NOACTIVATE
            )
            
            # Set transparency color key
            win32gui.SetLayeredWindowAttributes(
                hwnd,
                win32api.RGB(255, 0, 255),  # Magenta color key
                0,  # Alpha (0 = fully transparent for non-magenta pixels)
                win32con.LWA_COLORKEY
            )
            
            logger.debug("Overlay window created with transparency settings")
            
        except Exception as e:
            logger.error(f"Error creating overlay window: {e}")
            return

    def start_template_matching(self) -> None:
        """Start template matching."""
        logger.info("Starting template matching")
        self.template_matching_active = True
        
        # Create overlay window if both overlay and template matching are now active
        if self.active and self.template_matching_active:
            self.create_overlay_window()
        
        # Start both timers
        self.update_timer_interval()  # This will start the template matching timer
        self.draw_timer.start()  # Start the drawing timer
        logger.debug("Template matching and draw timers started")

    def update_timer_interval(self) -> None:
        """Update the template matching timer interval based on target frequency."""
        if not hasattr(self.template_matcher, 'target_frequency'):
            logger.warning("Template matcher has no target_frequency attribute")
            return
            
        interval = max(int(1000 / self.template_matcher.target_frequency), 16)  # Minimum 16ms (60 FPS max)
        logger.debug(
            f"Updating template matching timer interval: "
            f"target_frequency={self.template_matcher.target_frequency:.2f} updates/sec -> "
            f"interval={interval}ms"
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
            # Check if window exists before destroying
            hwnd = win32gui.FindWindow(None, self.window_name)
            if hwnd:
                cv2.destroyWindow(self.window_name)
                logger.info("Overlay window destroyed")
        except Exception as e:
            logger.debug(f"Window destruction skipped: {e}")

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
        """Run template matching update cycle."""
        try:
            logger.debug("Running template matching update")
            
            # Capture window image
            image = self.template_matcher.capture_window()
            if image is None:
                logger.warning("Failed to capture window for template matching")
                return
                
            logger.debug(f"Captured image with shape: {image.shape}")
            
            # First get all matches in GroupedMatch format
            matches = self.template_matcher.find_matches(image)
            logger.debug(f"Found {len(matches)} match groups")
            
            # Convert grouped matches to tuple format with averaged positions
            current_matches = []
            
            for group in matches:
                # Calculate average position for the group
                avg_x = sum(m.bounds[0] for m in group.matches) // len(group.matches)
                avg_y = sum(m.bounds[1] for m in group.matches) // len(group.matches)
                # Use width and height from first match since they should be the same
                width = group.matches[0].bounds[2]
                height = group.matches[0].bounds[3]
                # Use highest confidence from the group
                confidence = max(m.confidence for m in group.matches)
                
                match_tuple = (
                    group.template_name,
                    avg_x,
                    avg_y,
                    width,
                    height,
                    confidence
                )
                current_matches.append(match_tuple)
                
                logger.debug(
                    f"Group for {group.template_name}: {len(group.matches)} matches, "
                    f"average position: ({avg_x}, {avg_y}), confidence: {confidence:.2f}"
                )
            
            # Handle match persistence based on groups
            all_matches = []
            new_counters = {}
            
            # First, add all current matches
            for current_match in current_matches:
                group_key = self._get_group_key(current_match)
                # Check if we already have a match in this group
                existing_match = None
                for match in all_matches:
                    if self._is_same_group(current_match, match):
                        existing_match = match
                        break
                
                if existing_match:
                    # If existing match has lower confidence, replace it
                    if current_match[5] > existing_match[5]:
                        all_matches.remove(existing_match)
                        all_matches.append(current_match)
                        new_counters[group_key] = 0
                else:
                    # No existing match in this group, add new match
                    all_matches.append(current_match)
                    new_counters[group_key] = 0
                
                logger.debug(f"Added current match for group {group_key}")
            
            # Then check cached matches
            for cached_match in self.cached_matches:
                group_key = self._get_group_key(cached_match)
                
                # Skip if this group already has a match
                if group_key in new_counters:
                    continue
                
                # Check if this cached match is close to any current match
                # Skip if it's too close to avoid duplicates
                if any(self._is_same_group(cached_match, current) for current in current_matches):
                    continue
                
                # Increment counter for this group
                counter = self.match_counters.get(group_key, 0) + 1
                
                if counter < self.match_persistence:
                    # Keep the match if within persistence window
                    all_matches.append(cached_match)
                    new_counters[group_key] = counter
                    logger.debug(f"Using cached match for group {group_key} (frame {counter}/{self.match_persistence})")
                else:
                    logger.debug(f"Cache cleared for group {group_key}")
            
            # Update cache and counters
            self.cached_matches = all_matches
            self.match_counters = new_counters
            
        except Exception as e:
            logger.error(f"Error in template matching update: {e}", exc_info=True)

    def _draw_overlay(self) -> None:
        """Draw the overlay with current matches."""
        if not self.active or not self.template_matching_active:
            return
        
        if not self.window_manager.find_window():
            logger.warning("Target window not found during draw")
            return
        
        pos = self.window_manager.get_window_position()
        if not pos:
            logger.warning("Could not get window position")
            return
        
        x, y, width, height = pos
        # Ensure positive coordinates
        if x < 0:
            width += x
            x = 0
        if y < 0:
            height += y
            y = 0
            
        window_title = win32gui.GetWindowText(self.window_manager.hwnd)
        
        # Handle browser-specific window adjustments
        client_offset_x = 0
        client_offset_y = 0
        try:
            # Check if running in a browser
            if any(browser in window_title for browser in ["Chrome", "Firefox", "Edge", "Opera"]):
                import ctypes
                from ctypes.wintypes import RECT, POINT
                
                # Get client rect (actual content area)
                rect = RECT()
                if ctypes.windll.user32.GetClientRect(self.window_manager.hwnd, ctypes.byref(rect)):
                    client_width = rect.right - rect.left
                    client_height = rect.bottom - rect.top
                    
                    # Get client area position
                    point = POINT(0, 0)
                    if ctypes.windll.user32.ClientToScreen(self.window_manager.hwnd, ctypes.byref(point)):
                        client_x, client_y = point.x, point.y
                        
                        # Calculate offset from window to client
                        client_offset_x = client_x - x
                        client_offset_y = client_y - y
                        
                        # Update coordinates to use client area
                        x, y = client_x, client_y
                        width, height = client_width, client_height
                        
                        logger.debug(f"Browser client area adjusted: pos=({x}, {y}), size={width}x{height}, offset=({client_offset_x}, {client_offset_y})")
                
        except Exception as e:
            logger.warning(f"Failed to adjust for browser client area: {e}")
        
        try:
            # Ensure window exists before drawing
            hwnd = win32gui.FindWindow(None, self.window_name)
            if not hwnd:
                logger.debug("Creating overlay window as it doesn't exist")
                self.create_overlay_window()
                hwnd = win32gui.FindWindow(None, self.window_name)
                if not hwnd:
                    logger.error("Failed to create overlay window")
                    return
            
            # Create magenta background (will be transparent)
            overlay = np.zeros((height, width, 3), dtype=np.uint8)
            overlay[:] = (255, 0, 255)  # Set background to magenta
            
            # Only draw matches if we have any
            if self.cached_matches:
                logger.debug(f"Drawing {len(self.cached_matches)} matches on overlay")
                # Draw matches
                for name, match_x, match_y, match_width, match_height, confidence in self.cached_matches:
                    # Adjust match position by client offset
                    match_x = match_x - client_offset_x
                    match_y = match_y - client_offset_y
                    
                    # Adjust for negative window position
                    if x < 0:
                        match_x += abs(x)
                    if y < 0:
                        match_y += abs(y)
                    
                    logger.debug(f"Drawing match - Original bounds: ({match_x}, {match_y}, {match_width}, {match_height})")
                    logger.debug(f"Client offset being applied: ({client_offset_x}, {client_offset_y})")
                    
                    # Skip if dimensions are invalid
                    if match_width <= 0 or match_height <= 0:
                        continue
                    
                    # Calculate center point
                    center_x = match_x + match_width // 2
                    center_y = match_y + match_height // 2
                    
                    # Calculate scaled dimensions
                    scaled_width = int(match_width * self.rect_scale)
                    scaled_height = int(match_height * self.rect_scale)
                    
                    # Calculate new bounds ensuring they're integers
                    new_x1 = max(0, min(int(center_x - scaled_width // 2), width))
                    new_y1 = max(0, min(int(center_y - scaled_height // 2), height))
                    new_x2 = max(0, min(int(new_x1 + scaled_width), width))
                    new_y2 = max(0, min(int(new_y1 + scaled_height), height))
                    
                    logger.debug(f"Drawing scaled rectangle at: ({new_x1}, {new_y1}) -> ({new_x2}, {new_y2})")
                    
                    # Ensure color values are tuples of integers
                    rect_color = tuple(map(int, self.rect_color))
                    font_color = tuple(map(int, self.font_color))
                    cross_color = tuple(map(int, self.cross_color))
                    
                    # Draw rectangle
                    cv2.rectangle(
                        overlay,
                        (new_x1, new_y1),
                        (new_x2, new_y2),
                        rect_color,
                        self.rect_thickness
                    )
                    
                    # Draw text above the rectangle
                    text = f"{name} ({confidence:.2f})"
                    cv2.putText(
                        overlay,
                        text,
                        (new_x1, new_y1 - 5),
                        cv2.FONT_HERSHEY_SIMPLEX,
                        self.font_size / 30,
                        font_color,
                        self.text_thickness
                    )
                    
                    # Draw cross at center
                    # Scale the cross size based on cross_scale setting
                    scaled_cross_size = int(self.cross_size * self.cross_scale)
                    half_size = scaled_cross_size // 2
                    
                    # Draw cross with scaled size
                    cv2.line(
                        overlay,
                        (center_x - half_size, center_y),
                        (center_x + half_size, center_y),
                        cross_color,
                        self.cross_thickness
                    )
                    cv2.line(
                        overlay,
                        (center_x, center_y - half_size),
                        (center_x, center_y + half_size),
                        cross_color,
                        self.cross_thickness
                    )
            
            # Show overlay
            cv2.imshow(self.window_name, overlay)
            cv2.waitKey(1)
            
            # Update window position and ensure topmost
            win32gui.SetWindowPos(
                hwnd,
                win32con.HWND_TOPMOST,
                x, y, width, height,
                win32con.SWP_SHOWWINDOW | win32con.SWP_NOACTIVATE
            )
            
            # Refresh transparency settings
            win32gui.SetLayeredWindowAttributes(
                hwnd,
                win32api.RGB(255, 0, 255),  # Magenta color key
                0,  # Alpha (0 = fully transparent for non-magenta pixels)
                win32con.LWA_COLORKEY
            )
            
        except Exception as e:
            logger.error(f"Error updating overlay: {str(e)}", exc_info=True)

    def stop_template_matching(self) -> None:
        """Stop template matching."""
        logger.info("Stopping template matching")
        self.template_matching_active = False
        self.template_matching_timer.stop()
        self.draw_timer.stop()
        
        # Reset template matcher frequency
        self.template_matcher.update_frequency = 0.0
        self.template_matcher.last_update_time = 0.0
        
        # Clear match cache
        self.cached_matches = []
        self.match_counters.clear()
        
        # Safely destroy window when template matching stops
        self._destroy_window_safely()
        
        # Clear any existing matches from display
        self._draw_overlay()

    def toggle(self) -> None:
        """Toggle the overlay visibility."""
        previous_state = self.active
        self.active = not self.active
        logger.info(f"Overlay {'activated' if self.active else 'deactivated'}")
        
        # Only destroy window if we're turning off
        if not self.active:
            self._destroy_window_safely()
        # Only create window if we're turning on AND template matching is active
        elif self.template_matching_active:
            self.create_overlay_window() 