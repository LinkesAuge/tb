"""
File utility functions for TB Scout.

This module provides utility functions for file operations,
including resource path resolution for bundled applications.
"""

import os
import sys
from pathlib import Path

def get_resource_path(relative_path):
    """
    Get absolute path to resource, works for development and PyInstaller.
    
    Args:
        relative_path: Path relative to the application root
        
    Returns:
        Absolute path to the resource
    """
    try:
        # PyInstaller creates a temp folder and stores path in _MEIPASS
        base_path = sys._MEIPASS
    except Exception:
        # We are not running in a PyInstaller bundle
        base_path = os.path.abspath(".")
    
    return os.path.join(base_path, relative_path)

def ensure_directory_exists(directory_path):
    """
    Ensure that a directory exists, creating it if necessary.
    
    Args:
        directory_path: Path to the directory to ensure exists
    """
    Path(directory_path).mkdir(parents=True, exist_ok=True)
    
def get_file_extension(file_path):
    """
    Get the extension of a file.
    
    Args:
        file_path: Path to the file
        
    Returns:
        File extension (without the dot)
    """
    return os.path.splitext(file_path)[1][1:]