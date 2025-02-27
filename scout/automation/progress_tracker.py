"""
Automation Progress Tracker Module

This module defines the ProgressTracker class which is responsible for
tracking and reporting the progress of automation sequences.
"""

from typing import Dict, List, Optional, Callable
from dataclasses import dataclass
import time
import logging

logger = logging.getLogger(__name__)

@dataclass
class ExecutionStats:
    """
    Statistics about sequence execution.
    
    Attributes:
        start_time: When execution started
        end_time: When execution ended (None if still running)
        total_actions: Total number of actions in the sequence
        completed_actions: Number of actions completed
        successful_actions: Number of actions that succeeded
        failed_actions: Number of actions that failed
    """
    start_time: float
    end_time: Optional[float] = None
    total_actions: int = 0
    completed_actions: int = 0
    successful_actions: int = 0
    failed_actions: int = 0
    
    @property
    def is_complete(self) -> bool:
        """Check if execution is complete."""
        return self.completed_actions >= self.total_actions
    
    @property
    def success_rate(self) -> float:
        """Calculate success rate as percentage."""
        if self.completed_actions == 0:
            return 0.0
        return (self.successful_actions / self.completed_actions) * 100
    
    @property
    def elapsed_time(self) -> float:
        """Calculate elapsed time in seconds."""
        end = self.end_time or time.time()
        return end - self.start_time
    
    @property
    def progress_percentage(self) -> float:
        """Calculate progress as percentage."""
        if self.total_actions == 0:
            return 0.0
        return (self.completed_actions / self.total_actions) * 100


class ProgressTracker:
    """
    Tracks and reports progress of automation sequences.
    
    This class maintains statistics about sequence execution and
    provides methods for updating and reporting progress.
    """
    
    def __init__(self):
        """Initialize the progress tracker."""
        self.current_stats: Optional[ExecutionStats] = None
        self.historical_stats: List[ExecutionStats] = []
        self.progress_callbacks: List[Callable[[ExecutionStats], None]] = []
    
    def start_tracking(self, total_actions: int) -> None:
        """
        Start tracking a new sequence execution.
        
        Args:
            total_actions: Total number of actions in the sequence
        """
        self.current_stats = ExecutionStats(
            start_time=time.time(),
            total_actions=total_actions
        )
        logger.debug(f"Started tracking sequence with {total_actions} actions")
        self._notify_progress()
    
    def action_completed(self, success: bool) -> None:
        """
        Record completion of an action.
        
        Args:
            success: Whether the action was successful
        """
        if not self.current_stats:
            logger.warning("Attempted to record action completion without active tracking")
            return
            
        self.current_stats.completed_actions += 1
        if success:
            self.current_stats.successful_actions += 1
        else:
            self.current_stats.failed_actions += 1
            
        logger.debug(f"Action completed (success={success}), "
                    f"progress: {self.current_stats.progress_percentage:.1f}%")
        
        self._notify_progress()
    
    def stop_tracking(self) -> ExecutionStats:
        """
        Stop tracking the current sequence execution.
        
        Returns:
            The final execution statistics
        """
        if not self.current_stats:
            logger.warning("Attempted to stop tracking without active tracking")
            return ExecutionStats(start_time=time.time(), end_time=time.time())
            
        self.current_stats.end_time = time.time()
        
        # Add to historical stats
        self.historical_stats.append(self.current_stats)
        
        # Log summary
        logger.info(f"Sequence execution completed: "
                   f"{self.current_stats.completed_actions}/{self.current_stats.total_actions} actions, "
                   f"{self.current_stats.success_rate:.1f}% success rate, "
                   f"{self.current_stats.elapsed_time:.1f}s elapsed")
        
        stats = self.current_stats
        self.current_stats = None
        self._notify_progress()
        return stats
    
    def register_progress_callback(self, callback: Callable[[ExecutionStats], None]) -> None:
        """
        Register a callback to be notified of progress updates.
        
        Args:
            callback: Function to call with updated stats
        """
        self.progress_callbacks.append(callback)
    
    def _notify_progress(self) -> None:
        """Notify all registered callbacks of current progress."""
        stats = self.current_stats or (self.historical_stats[-1] if self.historical_stats else None)
        if stats:
            for callback in self.progress_callbacks:
                try:
                    callback(stats)
                except Exception as e:
                    logger.error(f"Error in progress callback: {e}")