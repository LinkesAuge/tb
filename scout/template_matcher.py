"""
Template Matcher

This module provides template matching functionality for detecting game elements.
It uses OpenCV's template matching to find and track specific visual elements
in the game window.
"""

from typing import List, Dict, Optional, Tuple, Any
import cv2
import numpy as np
import logging
from pathlib import Path
from dataclasses import dataclass
from scout.window_manager import WindowManager
from scout.sound_manager import SoundManager
import os

logger = logging.getLogger(__name__)

@dataclass
class TemplateMatch:
    """Represents a single template match result."""
    template_name: str
    bounds: Tuple[int, int, int, int]  # x, y, width, height
    confidence: float

@dataclass
class GroupedMatch:
    """Represents a group of similar template matches."""
    template_name: str
    bounds: Tuple[int, int, int, int]  # x, y, width, height
    confidence: float
    matches: List[TemplateMatch]

class TemplateMatcher:
    """
    Handles template matching for game elements.
    
    This class provides functionality to:
    - Load and manage templates
    - Find matches in screenshots
    - Group similar matches
    - Track match frequency and performance
    - Provide visual feedback through overlay
    """
    
    def __init__(self, window_manager: WindowManager, confidence: float = 0.8,
                 target_frequency: float = 1.0, sound_enabled: bool = False,
                 templates_dir: str = None):
        """
        Initialize the template matcher.
        
        Args:
            window_manager: WindowManager instance for capturing screenshots
            confidence: Minimum match confidence value (0.0-1.0)
            target_frequency: Target frequency for template matching (Hz)
            sound_enabled: Whether to play sounds on matches
            templates_dir: Directory containing template images (default: "scout/templates")
        """
        self.window_manager = window_manager
        self.confidence_threshold = confidence  # Store as confidence_threshold for consistency
        self.target_frequency = target_frequency
        self.sound_enabled = sound_enabled
        
        # Set default method name (for UI)
        self.method_name = "TM_CCOEFF_NORMED"
        self.method = cv2.TM_CCOEFF_NORMED
        
        # Create sound manager
        self.sound_manager = SoundManager()
        
        # Initialize template storage
        self.templates: Dict[str, np.ndarray] = {}
        self.template_sizes: Dict[str, Tuple[int, int]] = {}
        
        # Set templates directory
        if templates_dir is None:
            # Get the directory where this file is located
            current_dir = Path(os.path.dirname(os.path.abspath(__file__)))
            self.templates_dir = current_dir / "templates"
        else:
            self.templates_dir = Path(templates_dir)
        
        # Performance tracking
        self.update_frequency = 0.0
        self.last_update_time = 0.0
        
        # Debug settings
        self.debug_mode = False
        self.debug_screenshots_dir = Path("scout/debug_screenshots")
        
        # Load templates
        self.reload_templates()
        
    def reload_templates(self) -> None:
        """Reload all template images from the templates directory."""
        try:
            # Clear existing templates
            self.templates.clear()
            self.template_sizes.clear()
            logger.debug("Cleared existing templates")
            
            # Load templates from directory
            logger.debug(f"Looking for templates in: {self.templates_dir.absolute()}")
            
            if not self.templates_dir.exists():
                logger.error(f"Templates directory not found at {self.templates_dir.absolute()}")
                # Try to create the directory
                try:
                    self.templates_dir.mkdir(parents=True, exist_ok=True)
                    logger.info(f"Created templates directory at {self.templates_dir.absolute()}")
                except Exception as e:
                    logger.error(f"Failed to create templates directory: {e}")
                return
                
            # Enhanced debug output
            template_files = list(self.templates_dir.glob("*.png"))
            # Convert from Path objects to strings for more readable output
            template_files_str = [str(f) for f in template_files]
            logger.debug(f"Found {len(template_files)} template files: {template_files_str}")
            
            # If no templates found, provide more diagnostics
            if not template_files:
                logger.error("No .png template files found!")
                
                # List all files in the directory for debugging
                all_files = list(self.templates_dir.glob("*"))
                logger.debug(f"All files in templates directory: {[str(f) for f in all_files]}")
                
                # Try to list the templates directory contents
                try:
                    import os
                    logger.debug(f"Directory contents using os.listdir: {os.listdir(str(self.templates_dir))}")
                except Exception as e:
                    logger.error(f"Error listing directory contents: {e}")
                
                return  # Can't load templates if there are none
            
            for template_file in template_files:
                try:
                    # Read template image
                    template = cv2.imread(str(template_file))
                    if template is None:
                        logger.error(f"Failed to load template: {template_file}")
                        # Try with imread flags to see if that helps
                        template = cv2.imread(str(template_file), cv2.IMREAD_UNCHANGED)
                        if template is None:
                            logger.error(f"Still failed to load template with IMREAD_UNCHANGED: {template_file}")
                            continue
                    
                    # Convert template to grayscale if it's not already
                    if len(template.shape) == 3:
                        template = cv2.cvtColor(template, cv2.COLOR_BGR2GRAY)
                        logger.debug(f"Converted template to grayscale: {template_file.stem}")
                        
                    # Store template and its size
                    name = template_file.stem
                    self.templates[name] = template
                    self.template_sizes[name] = (template.shape[1], template.shape[0])
                    logger.debug(f"Successfully loaded template: {name} ({template.shape[1]}x{template.shape[0]})")
                    
                except Exception as e:
                    logger.error(f"Error loading template {template_file}: {e}", exc_info=True)
                    
            logger.info(f"Loaded {len(self.templates)} templates: {list(self.templates.keys())}")
            
            # If no templates were loaded, log a more prominent error
            if not self.templates:
                logger.error("NO TEMPLATES LOADED! Template matching will not work without templates.")
            
        except Exception as e:
            logger.error(f"Error reloading templates: {e}", exc_info=True)
            
    def find_matches(self, image: np.ndarray, template_names: Optional[List[str]] = None,
                    group_matches: bool = True) -> List[GroupedMatch]:
        """
        Find template matches in an image.
        
        Args:
            image: Image to search in (BGR format)
            template_names: List of template names to search for (None for all)
            group_matches: Whether to group similar matches
            
        Returns:
            List of GroupedMatch objects
        """
        try:
            # Use all templates if none specified
            if template_names is None:
                template_names = list(self.templates.keys())
                
            logger.debug(f"Searching for templates: {template_names} with confidence threshold: {self.confidence_threshold}")
            
            all_matches: List[TemplateMatch] = []
            
            # Search for each template
            for name in template_names:
                if name not in self.templates:
                    logger.warning(f"Template not found: {name}")
                    continue
                    
                template = self.templates[name]
                logger.debug(f"Searching for template: {name} ({template.shape[1]}x{template.shape[0]})")
                
                matches = self._find_template(image, template, name)
                logger.debug(f"Found {len(matches)} raw matches for template: {name}")
                all_matches.extend(matches)
                
            # Group matches if requested
            if group_matches:
                result = self._group_matches(all_matches)
                logger.debug(f"Found {len(result)} grouped matches from {len(all_matches)} raw matches")
                return result
            else:
                # Convert single matches to GroupedMatch format
                result = [
                    GroupedMatch(
                        template_name=match.template_name,
                        bounds=match.bounds,
                        confidence=match.confidence,
                        matches=[match]
                    )
                    for match in all_matches
                ]
                logger.debug(f"Returning {len(result)} individual matches")
                return result
                
        except Exception as e:
            logger.error(f"Error finding matches: {e}")
            return []
            
    def _find_template(self, image: np.ndarray, template: np.ndarray,
                      template_name: str) -> List[TemplateMatch]:
        """
        Find all instances of a template in an image.
        
        Args:
            image: Image to search in
            template: Template to search for
            template_name: Name of the template
            
        Returns:
            List of TemplateMatch objects
        """
        try:
            # Get template size
            template_width = template.shape[1]
            template_height = template.shape[0]
            
            # Check if template is larger than the image
            if template_width > image.shape[1] or template_height > image.shape[0]:
                logger.warning(f"Template {template_name} ({template_width}x{template_height}) is larger than the image ({image.shape[1]}x{image.shape[0]})")
                return []
            
            # Check if the image is extremely large compared to the template
            # Large images can cause memory issues with OpenCV's matchTemplate
            max_dimension = 2000  # Maximum dimension before scaling
            scale_factor = 1.0
            scaled_image = image
            
            if image.shape[0] > max_dimension or image.shape[1] > max_dimension:
                # Calculate scale factor to reduce image size
                height_scale = max_dimension / image.shape[0] if image.shape[0] > max_dimension else 1.0
                width_scale = max_dimension / image.shape[1] if image.shape[1] > max_dimension else 1.0
                scale_factor = min(height_scale, width_scale)
                
                # Scale down the image
                new_width = int(image.shape[1] * scale_factor)
                new_height = int(image.shape[0] * scale_factor)
                scaled_image = cv2.resize(image, (new_width, new_height))
                
                # Scale down the template proportionally
                scaled_template = cv2.resize(template, 
                                           (int(template_width * scale_factor), 
                                            int(template_height * scale_factor)))
                
                logger.debug(f"Scaled image from {image.shape[1]}x{image.shape[0]} to {new_width}x{new_height} for template matching")
                
                # Update template variables
                template = scaled_template
                template_width = template.shape[1]
                template_height = template.shape[0]
                
                # If template becomes too small after scaling, template matching might not work well
                if template_width < 8 or template_height < 8:
                    logger.warning(f"Scaled template {template_name} is too small ({template_width}x{template_height}), skipping")
                    return []
            
            # Perform template matching
            logger.debug(f"Running matchTemplate with method: {self.method_name}, template size: {template_width}x{template_height}, image size: {scaled_image.shape[1]}x{scaled_image.shape[0]}")
            
            try:
                result = cv2.matchTemplate(scaled_image, template, self.method)
            except cv2.error as e:
                logger.error(f"OpenCV error during template matching: {str(e)}")
                return []
            except Exception as e:
                logger.error(f"Unexpected error during template matching: {str(e)}")
                return []
            
            # Find matches above confidence threshold
            try:
                locations = np.where(result >= self.confidence_threshold)
                match_count = len(locations[0]) if locations and len(locations) > 0 else 0
                logger.debug(f"Found {match_count} locations above confidence threshold {self.confidence_threshold}")
                
                # Add more information about match locations
                if match_count > 0:
                    logger.info(f"TEMPLATE MATCH: Found {match_count} matches for template '{template_name}' with confidence >= {self.confidence_threshold}")
                else:
                    logger.info(f"TEMPLATE MATCH: No matches found for template '{template_name}' with confidence >= {self.confidence_threshold}")
                    
                    # Try with lower threshold for diagnostic purposes
                    diagnostic_threshold = self.confidence_threshold * 0.8  # Try with 80% of the actual threshold
                    diagnostic_locations = np.where(result >= diagnostic_threshold)
                    diagnostic_count = len(diagnostic_locations[0]) if diagnostic_locations and len(diagnostic_locations) > 0 else 0
                    
                    if diagnostic_count > 0:
                        # There are matches at a lower threshold
                        max_value = np.max(result)
                        logger.info(f"DIAGNOSTIC: Would find {diagnostic_count} matches at lower threshold {diagnostic_threshold:.2f}. Max confidence value: {max_value:.2f}")
                
            except Exception as e:
                logger.error(f"Error processing match results: {str(e)}")
                return []
            
            matches: List[TemplateMatch] = []
            
            for y, x in zip(*locations):
                confidence = float(result[y, x])
                
                # Scale coordinates back if we resized the image
                if scale_factor != 1.0:
                    x = int(x / scale_factor)
                    y = int(y / scale_factor)
                    scaled_template_width = int(template_width / scale_factor)
                    scaled_template_height = int(template_height / scale_factor)
                else:
                    scaled_template_width = template_width
                    scaled_template_height = template_height
                
                logger.debug(f"Match at ({x}, {y}) with confidence {confidence:.4f}")
                matches.append(TemplateMatch(
                    template_name=template_name,
                    bounds=(int(x), int(y), int(scaled_template_width), int(scaled_template_height)),
                    confidence=confidence
                ))
                
            return matches
            
        except Exception as e:
            logger.error(f"Error finding template {template_name}: {e}")
            return []
            
    def _group_matches(self, matches: List[TemplateMatch],
                      distance_threshold: int = 10) -> List[GroupedMatch]:
        """
        Group similar matches together.
        
        Args:
            matches: List of matches to group
            distance_threshold: Maximum pixel distance between matches to group
            
        Returns:
            List of GroupedMatch objects
        """
        if not matches:
            return []
            
        # Sort matches by confidence
        matches = sorted(matches, key=lambda m: m.confidence, reverse=True)
        
        groups: List[List[TemplateMatch]] = []
        used_indices = set()
        
        # Group matches
        for i, match in enumerate(matches):
            if i in used_indices:
                continue
                
            # Start new group
            current_group = [match]
            used_indices.add(i)
            
            # Find similar matches
            for j, other in enumerate(matches):
                if j in used_indices:
                    continue
                    
                # Check if matches are close enough
                if (abs(match.bounds[0] - other.bounds[0]) <= distance_threshold and
                    abs(match.bounds[1] - other.bounds[1]) <= distance_threshold and
                    match.template_name == other.template_name):
                    current_group.append(other)
                    used_indices.add(j)
                    
            groups.append(current_group)
            
        # Convert groups to GroupedMatch objects
        return [
            GroupedMatch(
                template_name=group[0].template_name,
                bounds=group[0].bounds,
                confidence=group[0].confidence,
                matches=group
            )
            for group in groups
        ]
        
    def set_debug_mode(self, enabled: bool) -> None:
        """
        Enable or disable debug mode.
        
        Args:
            enabled: Whether to enable debug mode
        """
        self.debug_mode = enabled
        logger.debug(f"Debug mode {'enabled' if enabled else 'disabled'}")
        
    def capture_window(self) -> Optional[np.ndarray]:
        """
        Capture a screenshot of the game window.
        
        Returns:
            Screenshot as numpy array in BGR format, or None if failed
        """
        return self.window_manager.capture_screenshot()
        
    def find_all_templates(self, image: np.ndarray) -> List[Tuple[str, int, int, int, int, float]]:
        """
        Find all templates in an image and return their positions.
        
        Args:
            image: Image to search in
            
        Returns:
            List of tuples (template_name, x, y, width, height, confidence)
        """
        if image is None:
            logger.warning("Cannot search for templates in a None image")
            return []
            
        logger.debug(f"Finding all templates in image of size {image.shape}")
        
        result_matches = []
        
        # Convert image to grayscale before template matching loop
        gray_image = image
        if len(image.shape) == 3:
            gray_image = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
            logger.debug(f"Converted image to grayscale for template matching")
        
        # Perform template matching for each template
        for template_name, template in self.templates.items():
            try:
                # Skip template if image is too small
                if template.shape[0] > gray_image.shape[0] or template.shape[1] > gray_image.shape[1]:
                    logger.warning(f"Template {template_name} ({template.shape}) is larger than image ({gray_image.shape}), skipping")
                    continue
                
                # Ensure template and image have the same number of channels
                template_for_matching = template
                if len(template.shape) != len(gray_image.shape):
                    logger.warning(f"Template {template_name} has {len(template.shape)} dimensions but image has {len(gray_image.shape)}. Converting template.")
                    if len(template.shape) == 3 and len(gray_image.shape) == 2:
                        template_for_matching = cv2.cvtColor(template, cv2.COLOR_BGR2GRAY)
                    elif len(template.shape) == 2 and len(gray_image.shape) == 3:
                        template_for_matching = cv2.cvtColor(template, cv2.COLOR_GRAY2BGR)
                
                # Perform template matching using properly formatted images
                logger.debug(f"Running template matching for {template_name} with shape {template_for_matching.shape}")
                result = cv2.matchTemplate(gray_image, template_for_matching, self.method)
                
                # Get locations where the match exceeds the threshold
                locations = np.where(result >= self.confidence_threshold)
                
                # Count how many matches found
                match_count = len(locations[0]) if locations and len(locations) > 0 else 0
                logger.debug(f"Found {match_count} raw matches for template: {template_name}")
                
                # Skip further processing if no matches
                if match_count == 0:
                    continue
                
                # Prune matches to avoid clutter (keep only top 100)
                if match_count > 100:
                    # Get all matches and their confidences
                    matches_with_confidence = []
                    for y, x in zip(*locations):
                        confidence = result[y, x]
                        matches_with_confidence.append((y, x, confidence))
                    
                    # Sort by confidence (highest first) and take top 100
                    matches_with_confidence.sort(key=lambda m: m[2], reverse=True)
                    matches_with_confidence = matches_with_confidence[:100]
                    
                    # Extract back into separate arrays
                    ys = [m[0] for m in matches_with_confidence]
                    xs = [m[1] for m in matches_with_confidence]
                    locations = (np.array(ys), np.array(xs))
                    match_count = len(locations[0])
                    logger.debug(f"Pruned to top {match_count} matches by confidence")
                
                # Get template dimensions
                template_height, template_width = template.shape[:2]
                
                # Convert matches to result format and filter out duplicates
                for y, x in zip(*locations):
                    confidence = float(result[y, x])
                    
                    # Extra verification for confidence
                    if confidence < self.confidence_threshold:
                        continue
                        
                    # Validate match position and ensure it doesn't overlap with existing matches
                    valid_match = True
                    
                    # Check for overlapping matches
                    match_rect = (int(x), int(y), template_width, template_height)
                    
                    # Check if this match overlaps with any existing match in result_matches
                    for existing_match in result_matches:
                        if self._rectangles_overlap(
                            match_rect,
                            (existing_match[1], existing_match[2], existing_match[3], existing_match[4])
                        ):
                            # If existing match has higher confidence, skip this one
                            if existing_match[5] >= confidence:
                                valid_match = False
                                break
                            # Otherwise, we'll keep this match and remove the existing one
                            else:
                                result_matches.remove(existing_match)
                    
                    if valid_match:
                        result_matches.append((template_name, int(x), int(y), template_width, template_height, confidence))
                
            except Exception as e:
                logger.error(f"Error searching for template {template_name}: {e}")
        
        # Sort matches by confidence (highest first)
        logger.info(f"Found {len(result_matches)} template matches")
        
        # Log the top matches for debugging
        result_matches.sort(key=lambda m: m[5], reverse=True)
        for i, match in enumerate(result_matches[:3]):
            logger.debug(f"Match {i+1}: {match}")
            
        return result_matches
        
    def start_template_matching(self) -> None:
        """Start continuous template matching."""
        logger.info("Starting template matching")
        # This is handled by the overlay system
        
    def stop_template_matching(self) -> None:
        """Stop continuous template matching."""
        logger.info("Stopping template matching")
        # This is handled by the overlay system 

    def get_matches(self) -> List[Tuple[str, int, int, int, int, float]]:
        """
        Get the current matches in a standardized format.
        
        Returns:
            List of tuples (template_name, x, y, width, height, confidence)
        """
        # If there's a current overlay instance and it has cached matches
        if hasattr(self, 'overlay') and hasattr(self.overlay, 'cached_matches'):
            return self.overlay.cached_matches
            
        # Otherwise return empty list
        return [] 

    def set_confidence_threshold(self, confidence: float) -> None:
        """
        Set the confidence threshold for template matching.
        
        Args:
            confidence: Minimum match confidence value (0.0-1.0)
        """
        self.confidence_threshold = max(0.0, min(1.0, confidence))  # Clamp between 0 and 1
        logger.debug(f"Set confidence threshold to {self.confidence_threshold}") 
        
    def set_method(self, method_name: str) -> None:
        """
        Set the template matching method to use.
        
        Args:
            method_name: Method name (e.g., "TM_CCOEFF_NORMED", "TM_CCORR_NORMED", etc.)
        """
        # Store method name for reference
        self.method_name = method_name
        
        # Map method name to OpenCV constants
        method_map = {
            "TM_CCOEFF_NORMED": cv2.TM_CCOEFF_NORMED,
            "TM_CCORR_NORMED": cv2.TM_CCORR_NORMED,
            "TM_SQDIFF_NORMED": cv2.TM_SQDIFF_NORMED,
            "TM_CCOEFF": cv2.TM_CCOEFF,
            "TM_CCORR": cv2.TM_CCORR,
            "TM_SQDIFF": cv2.TM_SQDIFF
        }
        
        # Set method to use for template matching
        if method_name in method_map:
            self.method = method_map[method_name]
            logger.debug(f"Set template matching method to {method_name}")
        else:
            logger.warning(f"Unknown method name '{method_name}', using TM_CCOEFF_NORMED as default")
            self.method = cv2.TM_CCOEFF_NORMED 

    def test_all_templates(self) -> List[Tuple[str, int, int, int, int, float]]:
        """
        Test all templates against current window with progressively lower thresholds.
        This is useful for debugging template matching issues.
        
        Returns:
            List of matches found during testing
        """
        logger.info("Starting test of all templates with different thresholds")
        
        # Capture current window
        image = self.capture_window()
        if image is None:
            logger.error("Failed to capture window for template testing")
            return []
            
        logger.info(f"Captured image with dimensions: {image.shape[1]}x{image.shape[0]}")
        
        # Store original threshold
        original_threshold = self.confidence_threshold
        test_results = []
        
        try:
            # Try with progressively lower thresholds
            test_thresholds = [0.8, 0.7, 0.6, 0.5, 0.4]
            
            for threshold in test_thresholds:
                # Set threshold for this test
                logger.info(f"Testing with threshold: {threshold}")
                self.confidence_threshold = threshold
                
                # Try to find matches with this threshold
                matches = self.find_matches(image)
                
                if matches:
                    # Convert grouped matches to tuple format
                    match_tuples = []
                    for group in matches:
                        match_tuple = (
                            group.template_name,
                            group.bounds[0],
                            group.bounds[1],
                            group.bounds[2],
                            group.bounds[3],
                            group.confidence
                        )
                        match_tuples.append(match_tuple)
                        
                    logger.info(f"Found {len(match_tuples)} matches with threshold {threshold}")
                    
                    # Add to results with this threshold
                    test_results.extend(match_tuples)
                    
                    # If we found matches, we can stop testing lower thresholds
                    if len(match_tuples) > 0:
                        logger.info(f"Successfully found matches at threshold {threshold}, stopping tests")
                        break
                else:
                    logger.info(f"No matches found with threshold {threshold}")
            
            if not test_results:
                logger.warning("No matches found with any threshold")
                
            return test_results
            
        finally:
            # Restore original threshold
            self.confidence_threshold = original_threshold
            logger.info(f"Restored original confidence threshold: {self.confidence_threshold}") 

    def find_template_with_progressively_lower_threshold(self, template_name: str) -> List[Tuple[str, int, int, int, int, float]]:
        """
        Find a specific template with progressively lower thresholds.
        
        This debug method tries to find a specific template with increasingly lower
        confidence thresholds to diagnose why a template might not be matching.
        
        Args:
            template_name: Name of the template to find
            
        Returns:
            List of match tuples found at each confidence level
        """
        if template_name not in self.templates:
            logger.error(f"Template '{template_name}' not found")
            return []
            
        logger.info(f"Testing template '{template_name}' with progressively lower thresholds")
        
        # Capture window
        image = self.capture_window()
        if image is None:
            logger.error("Failed to capture window")
            return []
            
        # Store original threshold
        original_threshold = self.confidence_threshold
        all_matches = []
        
        try:
            # Try with progressively lower thresholds
            test_thresholds = [0.9, 0.8, 0.7, 0.6, 0.5, 0.4, 0.3]
            
            template = self.templates[template_name]
            
            # Log template dimensions
            h, w = template.shape[:2]
            logger.info(f"Template '{template_name}' dimensions: {w}x{h}")
            
            for threshold in test_thresholds:
                self.confidence_threshold = threshold
                logger.info(f"Testing with threshold: {threshold}")
                
                # Find matches for this template
                matches = self._find_template(image, template, template_name)
                
                if matches:
                    # Convert to match tuples
                    for match in matches:
                        x, y, width, height = match.bounds
                        match_tuple = (template_name, x, y, width, height, match.confidence)
                        all_matches.append(match_tuple)
                        
                    count = len(matches)
                    logger.info(f"Found {count} matches with threshold {threshold}")
                    
                    # Log first few matches
                    for i, match in enumerate(matches[:5]):
                        x, y, w, h = match.bounds
                        logger.info(f"Match {i+1}: ({x}, {y}) size {w}x{h} conf={match.confidence:.2f}")
                else:
                    logger.info(f"No matches found with threshold {threshold}")
                    
                    # If no matches at very low threshold, try match_template directly
                    if threshold <= 0.4:
                        logger.info("Running matchTemplate directly for diagnostic purposes")
                        try:
                            result = cv2.matchTemplate(image, template, self.method)
                            min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(result)
                            logger.info(f"Direct matchTemplate - min: {min_val:.4f}, max: {max_val:.4f}")
                            logger.info(f"Best match would be at {max_loc} with confidence {max_val:.4f}")
                            
                            # Add this as a match for visualization
                            if max_val > 0.2:  # Even with a very low threshold
                                match_tuple = (template_name, max_loc[0], max_loc[1], w, h, max_val)
                                all_matches.append(match_tuple)
                                
                        except Exception as e:
                            logger.error(f"Error running direct matchTemplate: {e}")
            
            return all_matches
            
        finally:
            # Restore original threshold
            self.confidence_threshold = original_threshold 

    def _rectangles_overlap(self, rect1: Tuple[int, int, int, int], rect2: Tuple[int, int, int, int]) -> bool:
        """
        Check if two rectangles overlap.
        
        Args:
            rect1: First rectangle as (x, y, width, height)
            rect2: Second rectangle as (x, y, width, height)
            
        Returns:
            True if rectangles overlap, False otherwise
        """
        # Extract coordinates
        x1, y1, w1, h1 = rect1
        x2, y2, w2, h2 = rect2
        
        # Convert to (left, top, right, bottom) format
        left1, top1, right1, bottom1 = x1, y1, x1 + w1, y1 + h1
        left2, top2, right2, bottom2 = x2, y2, x2 + w2, y2 + h2
        
        # Check if rectangles overlap
        if right1 < left2 or right2 < left1 or bottom1 < top2 or bottom2 < top1:
            return False
        return True 