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
                 target_frequency: float = 1.0, sound_enabled: bool = False):
        """
        Initialize the template matcher.
        
        Args:
            window_manager: WindowManager instance for capturing screenshots
            confidence: Minimum confidence threshold for matches (0.0-1.0)
            target_frequency: Target updates per second
            sound_enabled: Whether to play sounds on matches
        """
        self.window_manager = window_manager
        self.confidence = confidence
        self.target_frequency = target_frequency
        self.sound_enabled = sound_enabled
        
        # Create sound manager
        self.sound_manager = SoundManager()
        
        # Initialize template storage
        self.templates: Dict[str, np.ndarray] = {}
        self.template_sizes: Dict[str, Tuple[int, int]] = {}
        
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
            templates_dir = Path("scout/templates")
            logger.debug(f"Looking for templates in: {templates_dir.absolute()}")
            
            if not templates_dir.exists():
                logger.warning(f"Templates directory not found at {templates_dir.absolute()}")
                return
                
            template_files = list(templates_dir.glob("*.png"))
            logger.debug(f"Found {len(template_files)} template files: {[f.name for f in template_files]}")
            
            for template_file in template_files:
                try:
                    # Read template image
                    template = cv2.imread(str(template_file))
                    if template is None:
                        logger.error(f"Failed to load template: {template_file}")
                        continue
                        
                    # Store template and its size
                    name = template_file.stem
                    self.templates[name] = template
                    self.template_sizes[name] = (template.shape[1], template.shape[0])
                    logger.debug(f"Successfully loaded template: {name} ({template.shape[1]}x{template.shape[0]})")
                    
                except Exception as e:
                    logger.error(f"Error loading template {template_file}: {e}")
                    
            logger.info(f"Loaded {len(self.templates)} templates: {list(self.templates.keys())}")
            
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
                
            all_matches: List[TemplateMatch] = []
            
            # Search for each template
            for name in template_names:
                if name not in self.templates:
                    logger.warning(f"Template not found: {name}")
                    continue
                    
                template = self.templates[name]
                matches = self._find_template(image, template, name)
                all_matches.extend(matches)
                
            # Group matches if requested
            if group_matches:
                return self._group_matches(all_matches)
            else:
                # Convert single matches to GroupedMatch format
                return [
                    GroupedMatch(
                        template_name=match.template_name,
                        bounds=match.bounds,
                        confidence=match.confidence,
                        matches=[match]
                    )
                    for match in all_matches
                ]
                
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
            
            # Perform template matching
            result = cv2.matchTemplate(image, template, cv2.TM_CCOEFF_NORMED)
            
            # Find matches above confidence threshold
            locations = np.where(result >= self.confidence)
            matches: List[TemplateMatch] = []
            
            for y, x in zip(*locations):
                matches.append(TemplateMatch(
                    template_name=template_name,
                    bounds=(int(x), int(y), template_width, template_height),
                    confidence=float(result[y, x])
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
        Find all templates in an image.
        
        Args:
            image: Image to search in (BGR format)
            
        Returns:
            List of tuples (template_name, x, y, w, h, confidence)
        """
        matches = self.find_matches(image)
        
        # Convert to legacy format
        return [
            (match.template_name, *match.bounds, match.confidence)
            for match in matches
        ]
        
    def start_template_matching(self) -> None:
        """Start continuous template matching."""
        logger.info("Starting template matching")
        # This is handled by the overlay system
        
    def stop_template_matching(self) -> None:
        """Stop continuous template matching."""
        logger.info("Stopping template matching")
        # This is handled by the overlay system 