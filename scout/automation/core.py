"""
Core Automation System

This module provides the core classes for the automation system:
- AutomationManager: Central manager for all automation functionality
- AutomationPosition: Represents a marked position in the game
- AutomationSequence: Defines a sequence of actions to perform
"""

from typing import Dict, List, Optional, Tuple
import json
import logging
from pathlib import Path
from dataclasses import dataclass, asdict
from scout.window_manager import WindowManager
from scout.config_manager import ConfigManager

logger = logging.getLogger(__name__)

@dataclass
class AutomationPosition:
    """
    Represents a marked position in the game window.
    
    Attributes:
        name: Unique identifier for this position
        x: X coordinate relative to game window
        y: Y coordinate relative to game window
        description: Optional description of what this position represents
    """
    name: str
    x: int
    y: int
    description: Optional[str] = None
    
    def to_dict(self) -> Dict:
        """Convert position to dictionary for storage."""
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'AutomationPosition':
        """Create position from dictionary."""
        return cls(**data)

@dataclass
class AutomationSequence:
    """
    Defines a sequence of automation actions.
    
    Attributes:
        name: Unique identifier for this sequence
        actions: List of actions to perform
        description: Optional description of what this sequence does
    """
    name: str
    actions: List[Dict]  # Will be replaced with AutomationAction objects when actions.py is implemented
    description: Optional[str] = None
    
    def to_dict(self) -> Dict:
        """Convert sequence to dictionary for storage."""
        return {
            'name': self.name,
            'actions': self.actions,
            'description': self.description
        }
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'AutomationSequence':
        """Create sequence from dictionary."""
        return cls(**data)

class AutomationManager:
    """
    Central manager for the automation system.
    
    This class manages:
    - Position tracking and storage
    - Sequence execution
    - Configuration loading/saving
    - Integration with other system components
    
    The manager maintains positions relative to the game window and handles
    conversion between screen and window coordinates.
    """
    
    def __init__(self, window_manager: WindowManager):
        """
        Initialize the automation manager.
        
        Args:
            window_manager: WindowManager instance for coordinate conversion
        """
        self.window_manager = window_manager
        self.config_manager = ConfigManager()
        
        # Create actions directory if it doesn't exist
        self.actions_dir = Path('config/actions')
        self.actions_dir.mkdir(parents=True, exist_ok=True)
        
        # Initialize storage
        self.positions: Dict[str, AutomationPosition] = {}
        self.sequences: Dict[str, AutomationSequence] = {}
        
        # Load any existing configurations
        self._load_configurations()
        
    def _load_configurations(self) -> None:
        """Load all saved positions and sequences."""
        try:
            # Load positions
            positions_file = self.actions_dir / 'positions.json'
            if positions_file.exists():
                with open(positions_file, 'r') as f:
                    positions_data = json.load(f)
                    self.positions = {
                        name: AutomationPosition.from_dict(data)
                        for name, data in positions_data.items()
                    }
            
            # Load sequences
            sequences_dir = self.actions_dir / 'sequences'
            sequences_dir.mkdir(exist_ok=True)
            for sequence_file in sequences_dir.glob('*.json'):
                try:
                    with open(sequence_file, 'r') as f:
                        sequence_data = json.load(f)
                        sequence = AutomationSequence.from_dict(sequence_data)
                        self.sequences[sequence.name] = sequence
                except Exception as e:
                    logger.error(f"Failed to load sequence {sequence_file}: {e}")
                    
        except Exception as e:
            logger.error(f"Failed to load configurations: {e}")
            
    def save_configurations(self) -> None:
        """Save all positions and sequences to disk."""
        try:
            # Save positions
            positions_file = self.actions_dir / 'positions.json'
            positions_data = {
                name: pos.to_dict() for name, pos in self.positions.items()
            }
            with open(positions_file, 'w') as f:
                json.dump(positions_data, f, indent=4)
            
            # Save sequences
            sequences_dir = self.actions_dir / 'sequences'
            sequences_dir.mkdir(exist_ok=True)
            for sequence in self.sequences.values():
                sequence_file = sequences_dir / f"{sequence.name}.json"
                with open(sequence_file, 'w') as f:
                    json.dump(sequence.to_dict(), f, indent=4)
                    
        except Exception as e:
            logger.error(f"Failed to save configurations: {e}")
            
    def add_position(self, position: AutomationPosition) -> None:
        """
        Add a new marked position.
        
        Args:
            position: Position to add
        """
        self.positions[position.name] = position
        self.save_configurations()
        
    def remove_position(self, name: str) -> None:
        """
        Remove a marked position.
        
        Args:
            name: Name of position to remove
        """
        if name in self.positions:
            del self.positions[name]
            self.save_configurations()
            
    def add_sequence(self, sequence: AutomationSequence) -> None:
        """
        Add a new action sequence.
        
        Args:
            sequence: Sequence to add
        """
        self.sequences[sequence.name] = sequence
        self.save_configurations()
        
    def remove_sequence(self, name: str) -> None:
        """
        Remove an action sequence.
        
        Args:
            name: Name of sequence to remove
        """
        if name in self.sequences:
            del self.sequences[name]
            self.save_configurations()
            
    def get_position(self, name: str) -> Optional[AutomationPosition]:
        """
        Get a position by name.
        
        Args:
            name: Name of position to get
            
        Returns:
            Position if found, None otherwise
        """
        return self.positions.get(name)
        
    def get_sequence(self, name: str) -> Optional[AutomationSequence]:
        """
        Get a sequence by name.
        
        Args:
            name: Name of sequence to get
            
        Returns:
            Sequence if found, None otherwise
        """
        return self.sequences.get(name)
        
    def convert_to_screen_coords(self, x: int, y: int) -> Tuple[int, int]:
        """
        Convert window-relative coordinates to screen coordinates.
        
        Args:
            x: Window-relative X coordinate
            y: Window-relative Y coordinate
            
        Returns:
            Tuple of (screen_x, screen_y)
        """
        return self.window_manager.client_to_screen(x, y)
        
    def convert_to_window_coords(self, screen_x: int, screen_y: int) -> Tuple[int, int]:
        """
        Convert screen coordinates to window-relative coordinates.
        
        Args:
            screen_x: Screen X coordinate
            screen_y: Screen Y coordinate
            
        Returns:
            Tuple of (window_x, window_y)
        """
        return self.window_manager.screen_to_client(screen_x, screen_y) 