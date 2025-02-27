"""
Screen Capture Module

This module provides functionality for capturing screens and windows in the TB Scout application.
It includes components for listing available screens and windows, capturing their content,
and providing a user interface for interacting with these capabilities.
"""

from scout.screen_capture.capture_manager import CaptureManager
from scout.screen_capture.screen_list_model import ScreenListModel
from scout.screen_capture.window_list_model import WindowListModel
from scout.screen_capture.capture_tab import CaptureTab
from scout.screen_capture.utils import (
    qimage_to_numpy,
    numpy_to_qimage,
    scale_rect_to_fit,
    crop_numpy_array,
    apply_overlay
)

__all__ = [
    'CaptureManager',
    'ScreenListModel',
    'WindowListModel',
    'CaptureTab',
    'qimage_to_numpy',
    'numpy_to_qimage',
    'scale_rect_to_fit',
    'crop_numpy_array',
    'apply_overlay'
]
