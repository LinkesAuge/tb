#!/usr/bin/env python3
"""
Template path fixer script for Scout

This script helps diagnose and fix template path issues in the Scout application.
It copies template files to multiple potential locations where they might be loaded from.
"""

import os
import sys
import logging
import shutil
from pathlib import Path

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('template_fix.log', mode='w')
    ]
)

logger = logging.getLogger("template_fix")

def fix_template_paths():
    """Copy template files to multiple locations to ensure they can be found."""
    
    logger.info("=" * 50)
    logger.info("SCOUT TEMPLATE PATH FIXER")
    logger.info("=" * 50)
    
    # Check working directory
    cwd = os.getcwd()
    logger.info(f"Current working directory: {cwd}")
    
    # Define source template location - the location where we know templates exist
    # The output of dir D:\OneDrive\AI\Projekte\Scout\tb\scout\templates showed crypt_small.png
    source_dir = Path("D:/OneDrive/AI/Projekte/Scout/tb/scout/templates")
    
    if not source_dir.exists() or not source_dir.is_dir():
        logger.error(f"Source templates directory not found at {source_dir}")
        return False
    
    # Get all PNG files from source directory
    template_files = list(source_dir.glob("*.png"))
    logger.info(f"Found {len(template_files)} template files in source directory:")
    for file in template_files:
        logger.info(f"  - {file.name}")
    
    if not template_files:
        logger.error("No template files found in source directory!")
        return False
    
    # Define destination directories
    dest_dirs = [
        Path(cwd) / "templates",
        Path(cwd) / "scout" / "templates",
        Path.home() / ".scout" / "templates",  # User home directory
        Path(os.path.dirname(os.path.abspath(__file__))) / "templates",  # Script directory
        Path(os.path.dirname(os.path.abspath(__file__))).parent / "templates",  # Parent of script directory
    ]
    
    # Create destination directories and copy templates
    success_count = 0
    for dest_dir in dest_dirs:
        try:
            # Create directory if it doesn't exist
            if not dest_dir.exists():
                dest_dir.mkdir(parents=True, exist_ok=True)
                logger.info(f"Created directory: {dest_dir}")
            
            # Copy template files
            for file in template_files:
                dest_file = dest_dir / file.name
                shutil.copy2(file, dest_file)
                logger.info(f"Copied {file.name} to {dest_file}")
                success_count += 1
                
            logger.info(f"Successfully copied templates to {dest_dir}")
            
        except Exception as e:
            logger.error(f"Error copying templates to {dest_dir}: {e}")
    
    logger.info("=" * 50)
    logger.info(f"Template fix completed. Copied {success_count} files to {len(dest_dirs)} locations.")
    logger.info("=" * 50)
    
    return success_count > 0

if __name__ == "__main__":
    if fix_template_paths():
        logger.info("Template path fix was successful! Try running the application again.")
        sys.exit(0)
    else:
        logger.error("Template path fix failed!")
        sys.exit(1) 