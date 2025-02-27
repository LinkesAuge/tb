"""
Template Search Module

This module provides enhanced template matching functionality for the TB Scout application.
It extends the basic pattern matching with more robust search capabilities, including:
- Multi-scale template matching
- Rotation-invariant matching
- Confidence scoring and filtering
- Region-of-interest based searching
- Caching of results for performance
"""

import cv2
import numpy as np
import os
import time
from pathlib import Path
from typing import Dict, List, Tuple, Optional, Union, Any
from PyQt6.QtCore import QObject, pyqtSignal, QRect, QPoint, QSize

class TemplateMatch:
    """Represents a single template match result."""
    
    def __init__(self, template_name: str, location: QPoint, size: QSize, 
                 confidence: float, angle: float = 0.0, scale: float = 1.0):
        """
        Initialize a template match result.
        
        Args:
            template_name: Name of the matched template
            location: Top-left position of the match (QPoint)
            size: Size of the matched template (QSize)
            confidence: Match confidence score (0.0-1.0)
            angle: Rotation angle of the match in degrees (if rotation matching was used)
            scale: Scale factor of the match (if multi-scale matching was used)
        """
        self.template_name = template_name
        self.location = location
        self.size = size
        self.confidence = confidence
        self.angle = angle
        self.scale = scale
        self.timestamp = time.time()
    
    @property
    def rect(self) -> QRect:
        """Get the match rectangle."""
        return QRect(self.location, self.size)
    
    @property
    def center(self) -> QPoint:
        """Get the center point of the match."""
        return QPoint(
            self.location.x() + self.size.width() // 2,
            self.location.y() + self.size.height() // 2
        )
    
    def __repr__(self) -> str:
        """String representation of the match."""
        return (f"TemplateMatch('{self.template_name}', pos={self.location.x(), self.location.y()}, "
                f"size={self.size.width(), self.size.height()}, conf={self.confidence:.2f}, "
                f"angle={self.angle:.1f}, scale={self.scale:.2f})")


class TemplateSearcher(QObject):
    """
    Enhanced template matching engine for finding patterns in images.
    
    This class provides advanced template matching capabilities beyond basic OpenCV
    template matching, including multi-scale search, rotation invariance, and result caching.
    """
    
    # Signals
    template_matched = pyqtSignal(TemplateMatch)
    search_completed = pyqtSignal(list)  # List of TemplateMatch objects
    search_started = pyqtSignal(str)  # Template name
    error_occurred = pyqtSignal(str)  # Error message
    
    def __init__(self, template_matcher, window_manager, templates_dir="templates"):
        """
        Initialize the template searcher.
        
        Args:
            template_matcher: The template matcher to use for detection
            window_manager: The window manager to use for window operations
            templates_dir: Directory containing template images (default: "templates")
        """
        self.template_matcher = template_matcher
        self.window_manager = window_manager
        self.templates_dir = Path(templates_dir)  # This line is causing the error
        
        # Initialize other properties
        self.search_area = None
        self.search_results = []
        self.is_searching = False
        self.search_thread = None
        self.stop_requested = False
    
    def load_templates(self, subdirectory: Optional[str] = None) -> int:
        """
        Load template images from the templates directory.
        
        Args:
            subdirectory: Optional subdirectory within templates_dir to load from
            
        Returns:
            Number of templates loaded
        """
        path = self.templates_dir
        if subdirectory:
            path = path / subdirectory
            
        if not path.exists():
            self.error_occurred.emit(f"Template directory not found: {path}")
            return 0
            
        count = 0
        for file_path in path.glob("*.png"):
            try:
                # Load template image
                template = cv2.imread(str(file_path), cv2.IMREAD_UNCHANGED)
                if template is None:
                    self.error_occurred.emit(f"Failed to load template: {file_path}")
                    continue
                    
                template_name = file_path.stem
                
                # Handle templates with alpha channel (transparency)
                if template.shape[2] == 4:
                    # Extract the mask from the alpha channel
                    mask = template[:, :, 3]
                    # Convert template to BGR
                    template = template[:, :, :3]
                    self.template_masks[template_name] = mask
                else:
                    self.template_masks[template_name] = None
                
                self.templates[template_name] = template
                self.template_sizes[template_name] = QSize(template.shape[1], template.shape[0])
                count += 1
                
            except Exception as e:
                self.error_occurred.emit(f"Error loading template {file_path}: {str(e)}")
        
        return count
    
    def search(self, image: np.ndarray, template_name: str, 
               min_confidence: Optional[float] = None,
               region: Optional[QRect] = None,
               use_cache: bool = True) -> List[TemplateMatch]:
        """
        Search for a specific template in the image.
        
        Args:
            image: Image to search in (numpy array in BGR format)
            template_name: Name of the template to search for
            min_confidence: Minimum confidence threshold (0.0-1.0)
            region: Region of interest to search within
            use_cache: Whether to use cached results if available
            
        Returns:
            List of TemplateMatch objects
        """
        if min_confidence is None:
            min_confidence = self.min_confidence
            
        # Check if template exists
        if template_name not in self.templates:
            self.error_occurred.emit(f"Template not found: {template_name}")
            return []
            
        # Check cache if enabled
        if use_cache and template_name in self.result_cache:
            cached_results = self.result_cache[template_name]
            if cached_results and (time.time() - cached_results[0].timestamp) < self.cache_timeout:
                # Filter cached results by region if specified
                if region:
                    return [match for match in cached_results 
                            if region.contains(match.location)]
                return cached_results
        
        self.search_started.emit(template_name)
        
        # Prepare the search region
        if region:
            x, y, w, h = region.x(), region.y(), region.width(), region.height()
            if x < 0 or y < 0 or x + w > image.shape[1] or y + h > image.shape[0]:
                # Adjust region to fit within image bounds
                x = max(0, x)
                y = max(0, y)
                w = min(image.shape[1] - x, w)
                h = min(image.shape[0] - y, h)
                region = QRect(x, y, w, h)
                
            # Extract region of interest
            roi = image[y:y+h, x:x+w]
        else:
            roi = image
            
        # Get template and mask
        template = self.templates[template_name]
        mask = self.template_masks.get(template_name)
        
        # Perform template matching
        try:
            result = cv2.matchTemplate(
                roi, 
                template, 
                cv2.TM_CCOEFF_NORMED, 
                mask=mask
            )
            
            # Find matches above threshold
            locations = np.where(result >= min_confidence)
            matches = []
            
            for pt in zip(*locations[::-1]):  # Reverse for (x, y)
                # Calculate absolute position if using region
                if region:
                    abs_pt = (pt[0] + region.x(), pt[1] + region.y())
                else:
                    abs_pt = pt
                    
                confidence = result[pt[1], pt[0]]
                match = TemplateMatch(
                    template_name=template_name,
                    location=QPoint(abs_pt[0], abs_pt[1]),
                    size=self.template_sizes[template_name],
                    confidence=float(confidence)
                )
                matches.append(match)
                self.template_matched.emit(match)
            
            # Sort matches by confidence (highest first)
            matches.sort(key=lambda m: m.confidence, reverse=True)
            
            # Update cache
            self.result_cache[template_name] = matches
            
            self.search_completed.emit(matches)
            return matches
            
        except Exception as e:
            self.error_occurred.emit(f"Error searching for template {template_name}: {str(e)}")
            return []
    
    def search_multi_scale(self, image: np.ndarray, template_name: str,
                          min_confidence: Optional[float] = None,
                          region: Optional[QRect] = None,
                          scale_range: Tuple[float, float] = (0.8, 1.2),
                          scale_steps: int = 5) -> List[TemplateMatch]:
        """
        Search for a template at multiple scales.
        
        Args:
            image: Image to search in
            template_name: Name of the template to search for
            min_confidence: Minimum confidence threshold
            region: Region of interest to search within
            scale_range: Range of scales to try (min, max)
            scale_steps: Number of scale steps to try
            
        Returns:
            List of TemplateMatch objects
        """
        if min_confidence is None:
            min_confidence = self.min_confidence
            
        # Check if template exists
        if template_name not in self.templates:
            self.error_occurred.emit(f"Template not found: {template_name}")
            return []
            
        self.search_started.emit(template_name)
        
        # Prepare the search region
        if region:
            x, y, w, h = region.x(), region.y(), region.width(), region.height()
            roi = image[y:y+h, x:x+w]
        else:
            roi = image
            x, y = 0, 0
            
        # Get template and mask
        template = self.templates[template_name]
        mask = self.template_masks.get(template_name)
        template_h, template_w = template.shape[:2]
        
        # Generate scale factors
        min_scale, max_scale = scale_range
        scale_factors = np.linspace(min_scale, max_scale, scale_steps)
        
        all_matches = []
        
        for scale in scale_factors:
            # Resize template
            scaled_w = int(template_w * scale)
            scaled_h = int(template_h * scale)
            
            if scaled_w <= 0 or scaled_h <= 0:
                continue
                
            scaled_template = cv2.resize(template, (scaled_w, scaled_h), interpolation=cv2.INTER_AREA)
            
            # Resize mask if it exists
            scaled_mask = None
            if mask is not None:
                scaled_mask = cv2.resize(mask, (scaled_w, scaled_h), interpolation=cv2.INTER_AREA)
            
            try:
                # Perform template matching
                result = cv2.matchTemplate(
                    roi, 
                    scaled_template, 
                    cv2.TM_CCOEFF_NORMED, 
                    mask=scaled_mask
                )
                
                # Find matches above threshold
                locations = np.where(result >= min_confidence)
                
                for pt in zip(*locations[::-1]):  # Reverse for (x, y)
                    # Calculate absolute position
                    abs_pt = (pt[0] + x, pt[1] + y)
                    confidence = result[pt[1], pt[0]]
                    
                    match = TemplateMatch(
                        template_name=template_name,
                        location=QPoint(abs_pt[0], abs_pt[1]),
                        size=QSize(scaled_w, scaled_h),
                        confidence=float(confidence),
                        scale=scale
                    )
                    all_matches.append(match)
                    self.template_matched.emit(match)
                    
            except Exception as e:
                self.error_occurred.emit(f"Error in multi-scale search for {template_name} at scale {scale}: {str(e)}")
        
        # Sort matches by confidence (highest first)
        all_matches.sort(key=lambda m: m.confidence, reverse=True)
        
        self.search_completed.emit(all_matches)
        return all_matches
    
    def search_all(self, image: np.ndarray, 
                  template_names: Optional[List[str]] = None,
                  min_confidence: Optional[float] = None,
                  region: Optional[QRect] = None) -> Dict[str, List[TemplateMatch]]:
        """
        Search for multiple templates in the image.
        
        Args:
            image: Image to search in
            template_names: List of template names to search for (None for all)
            min_confidence: Minimum confidence threshold
            region: Region of interest to search within
            
        Returns:
            Dictionary mapping template names to lists of TemplateMatch objects
        """
        if template_names is None:
            template_names = list(self.templates.keys())
            
        results = {}
        for name in template_names:
            matches = self.search(image, name, min_confidence, region)
            if matches:
                results[name] = matches
                
        return results
    
    def clear_cache(self, template_name: Optional[str] = None):
        """
        Clear the result cache.
        
        Args:
            template_name: Specific template to clear from cache (None for all)
        """
        if template_name:
            if template_name in self.result_cache:
                del self.result_cache[template_name]
        else:
            self.result_cache.clear()
    
    def get_template_image(self, template_name: str) -> Optional[np.ndarray]:
        """
        Get a copy of a template image.
        
        Args:
            template_name: Name of the template
            
        Returns:
            Template image as numpy array or None if not found
        """
        return self.templates.get(template_name, None)
    
    def get_template_names(self) -> List[str]:
        """
        Get a list of all loaded template names.
        
        Returns:
            List of template names
        """
        return list(self.templates.keys())
