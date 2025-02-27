"""
Automation Position Module

This module defines the Position and PositionManager classes for
managing named positions in the game window.
"""

from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
import logging

logger = logging.getLogger(__name__)

@dataclass
class Position:
    """
    Represents a named position in the game window.
    
    Attributes:
        name: Unique identifier for this position
        x: X coordinate (relative to game window)
        y: Y coordinate (relative to game window)
        description: Optional description of what this position represents
    """
    name: str
    x: int
    y: int
    description: Optional[str] = None
    
    def to_dict(self) -> dict:
        """Convert position to dictionary for storage."""
        return {
            'name': self.name,
            'x': self.x,
            'y': self.y,
            'description': self.description
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> 'Position':
        """Create position from dictionary."""
        return cls(
            name=data['name'],
            x=data['x'],
            y=data['y'],
            description=data.get('description')
        )


class PositionManager:
    """
    Manages a collection of named positions.
    
    This class provides methods for adding, removing, and retrieving
    positions by name.
    """
    
    def __init__(self):
        """Initialize the position manager."""
        self.positions: Dict[str, Position] = {}
    
    def add_position(self, position: Position) -> None:
        """
        Add a position to the manager.
        
        Args:
            position: Position to add
        """
        self.positions[position.name] = position
        logger.debug(f"Added position '{position.name}' at ({position.x}, {position.y})")
    
    def remove_position(self, name: str) -> bool:
        """
        Remove a position from the manager.
        
        Args:
            name: Name of the position to remove
            
        Returns:
            True if position was removed, False if not found
        """
        if name in self.positions:
            del self.positions[name]
            logger.debug(f"Removed position '{name}'")
            return True
        return False
    
    def get_position(self, name: str) -> Optional[Position]:
        """
        Get a position by name.
        
        Args:
            name: Name of the position to get
            
        Returns:
            Position if found, None otherwise
        """
        return self.positions.get(name)
    
    def get_all_positions(self) -> List[Position]:
        """
        Get all positions.
        
        Returns:
            List of all positions
        """
        return list(self.positions.values())
    
    def clear(self) -> None:
        """Clear all positions."""
        self.positions.clear()
        logger.debug("Cleared all positions")