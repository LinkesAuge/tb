"""Utility functions for screen capture module."""

import numpy as np
from PyQt6.QtGui import QImage, QPixmap
from PyQt6.QtCore import QRect, QPoint, QSize, Qt
import cv2
import logging

# Set up logging
logger = logging.getLogger(__name__)

def qimage_to_numpy(qimage: QImage) -> np.ndarray:
    """
    Convert a QImage to a numpy array (OpenCV format).
    
    Args:
        qimage: The QImage to convert
        
    Returns:
        A numpy array in BGR format (OpenCV standard)
    """
    try:
        # Convert QImage to the right format for conversion
        if qimage.format() != QImage.Format.Format_RGB32:
            qimage = qimage.convertToFormat(QImage.Format.Format_RGB32)
            
        # Get image dimensions
        width = qimage.width()
        height = qimage.height()
        
        # Convert to numpy array (format is RGBA)
        ptr = qimage.bits()
        ptr.setsize(height * width * 4)
        arr = np.frombuffer(ptr, np.uint8).reshape((height, width, 4))
        
        # Convert RGBA to BGR (OpenCV format)
        return cv2.cvtColor(arr, cv2.COLOR_RGBA2BGR)
    except Exception as e:
        logger.error(f"Error converting QImage to numpy array: {e}")
        return np.array([])

def numpy_to_qimage(arr: np.ndarray) -> QImage:
    """
    Convert a numpy array (OpenCV format) to a QImage.
    
    Args:
        arr: The numpy array in BGR format (OpenCV standard)
        
    Returns:
        A QImage in RGB format
    """
    try:
        # Convert BGR to RGB
        if arr.shape[2] == 3:  # BGR format
            rgb = cv2.cvtColor(arr, cv2.COLOR_BGR2RGB)
        elif arr.shape[2] == 4:  # BGRA format
            rgb = cv2.cvtColor(arr, cv2.COLOR_BGRA2RGBA)
        else:
            logger.error(f"Unsupported array shape: {arr.shape}")
            return QImage()
            
        # Create QImage from numpy array
        height, width, channels = rgb.shape
        bytes_per_line = channels * width
        return QImage(rgb.data, width, height, bytes_per_line, QImage.Format.Format_RGB888)
    except Exception as e:
        logger.error(f"Error converting numpy array to QImage: {e}")
        return QImage()

def numpy_to_qpixmap(arr: np.ndarray) -> QPixmap:
    """
    Convert a numpy array (OpenCV format) to a QPixmap.
    
    Args:
        arr: The numpy array in BGR format (OpenCV standard)
        
    Returns:
        A QPixmap for display in Qt widgets
    """
    try:
        qimage = numpy_to_qimage(arr)
        return QPixmap.fromImage(qimage)
    except Exception as e:
        logger.error(f"Error converting numpy array to QPixmap: {e}")
        return QPixmap()

def qpixmap_to_numpy(pixmap: QPixmap) -> np.ndarray:
    """
    Convert a QPixmap to a numpy array (OpenCV format).
    
    Args:
        pixmap: The QPixmap to convert
        
    Returns:
        A numpy array in BGR format (OpenCV standard)
    """
    try:
        qimage = pixmap.toImage()
        return qimage_to_numpy(qimage)
    except Exception as e:
        logger.error(f"Error converting QPixmap to numpy array: {e}")
        return np.array([])

def scale_rect_to_fit(rect: QRect, target_size: QSize, keep_aspect_ratio: bool = True) -> QRect:
    """
    Scale a rectangle to fit within a target size while optionally maintaining aspect ratio.
    
    Args:
        rect: The source rectangle
        target_size: The target size to fit within
        keep_aspect_ratio: Whether to maintain the aspect ratio
        
    Returns:
        A scaled QRect that fits within the target size
    """
    if rect.isEmpty() or target_size.isEmpty():
        return QRect()
        
    if keep_aspect_ratio:
        # Scale while maintaining aspect ratio
        scaled = rect.size().scaled(target_size, Qt.AspectRatioMode.KeepAspectRatio)
    else:
        # Scale to fill the target size
        scaled = target_size
        
    # Center the scaled rectangle
    x = (target_size.width() - scaled.width()) // 2
    y = (target_size.height() - scaled.height()) // 2
    
    return QRect(QPoint(x, y), scaled)

def crop_numpy_array(arr: np.ndarray, rect: QRect) -> np.ndarray:
    """
    Crop a numpy array using a QRect.
    
    Args:
        arr: The numpy array to crop
        rect: The rectangle defining the crop region
        
    Returns:
        A cropped numpy array
    """
    try:
        if arr.size == 0 or rect.isEmpty():
            return np.array([])
            
        # Ensure the rect is within the array bounds
        height, width = arr.shape[:2]
        x = max(0, rect.x())
        y = max(0, rect.y())
        right = min(width, rect.right() + 1)
        bottom = min(height, rect.bottom() + 1)
        
        # Crop the array
        return arr[y:bottom, x:right]
    except Exception as e:
        logger.error(f"Error cropping numpy array: {e}")
        return np.array([])

def apply_overlay(base_image: np.ndarray, overlay_image: np.ndarray, 
                 position: QPoint, alpha: float = 0.5) -> np.ndarray:
    """
    Apply an overlay image onto a base image at the specified position with transparency.
    
    Args:
        base_image: The base numpy array (BGR format)
        overlay_image: The overlay numpy array (BGR format)
        position: The position to place the overlay
        alpha: The transparency factor (0.0 to 1.0)
        
    Returns:
        A numpy array with the overlay applied
    """
    try:
        if base_image.size == 0 or overlay_image.size == 0:
            return base_image
            
        # Get dimensions
        h_overlay, w_overlay = overlay_image.shape[:2]
        h_base, w_base = base_image.shape[:2]
        
        # Calculate the overlay region
        x, y = position.x(), position.y()
        
        # Ensure the overlay region is within the base image
        if x >= w_base or y >= h_base or x + w_overlay <= 0 or y + h_overlay <= 0:
            return base_image
            
        # Calculate the valid region for overlay
        x1 = max(0, x)
        y1 = max(0, y)
        x2 = min(w_base, x + w_overlay)
        y2 = min(h_base, y + h_overlay)
        
        # Calculate the corresponding region in the overlay image
        ox1 = x1 - x
        oy1 = y1 - y
        ox2 = ox1 + (x2 - x1)
        oy2 = oy1 + (y2 - y1)
        
        # Create a copy of the base image
        result = base_image.copy()
        
        # Apply the overlay with alpha blending
        overlay_region = overlay_image[oy1:oy2, ox1:ox2]
        base_region = result[y1:y2, x1:x2]
        
        # Perform alpha blending
        result[y1:y2, x1:x2] = cv2.addWeighted(
            base_region, 1 - alpha, overlay_region, alpha, 0
        )
        
        return result
    except Exception as e:
        logger.error(f"Error applying overlay: {e}")
        return base_image
