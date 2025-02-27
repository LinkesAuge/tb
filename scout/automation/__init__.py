"""
Automation System for Total Battle Scout

This package provides a modular system for automating game interactions through:
- Position marking and tracking
- Action sequences
- Conditional execution
- Visual debugging
"""

# Update imports to match the new module structure
from scout.automation.core import AutomationCore
from scout.automation.position import Position, PositionManager
from scout.automation.sequence import AutomationSequence, SequenceManager
from scout.automation.context import ExecutionContext
from scout.automation.progress_tracker import ProgressTracker
from scout.automation.actions import ActionType, AutomationAction

__version__ = '1.0.0'
