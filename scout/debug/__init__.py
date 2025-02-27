"""
Debug visualization package for Scout.

This package provides components for debugging and visualizing various aspects
of the Scout application, including:
- Image visualization
- Template matching results
- OCR text extraction
- Automation execution
- Screen capture
"""

from scout.debug.base import DebugWindowBase
from scout.debug.manager import DebugWindowManager
from scout.debug.image_tab import ImageTab
from scout.debug.automation_tab import AutomationTab
from scout.debug.capture_tab import CaptureTab
from scout.debug.ocr_tab import OCRTab
from scout.debug.preview import ImagePreview

__all__ = [
    'DebugWindowBase',
    'DebugWindowManager',
    'ImageTab',
    'AutomationTab',
    'CaptureTab',
    'OCRTab',
    'ImagePreview'
]