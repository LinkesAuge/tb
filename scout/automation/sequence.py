"""
Automation Sequence Module

This module defines the Sequence and SequenceManager classes for
managing automation sequences.
"""

from typing import Dict, List, Optional, Any
from dataclasses import dataclass
import logging

from scout.automation.actions import AutomationAction

logger = logging.getLogger(__name__)

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
    actions: List[Dict[str, Any]]
    description: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert the sequence to a dictionary representation."""
        return {
            "name": self.name,
            "actions": self.actions,
            "description": self.description
        }

class SequenceManager:
    """
    Manages automation sequences, including loading, saving, and validation.
    """
    
    def __init__(self):
        """Initialize the sequence manager."""
        self.sequences: Dict[str, AutomationSequence] = {}
    
    def add_sequence(self, sequence: AutomationSequence) -> None:
        """Add a sequence to the manager."""
        self.sequences[sequence.name] = sequence
    
    def get_sequence(self, name: str) -> Optional[AutomationSequence]:
        """Get a sequence by name."""
        return self.sequences.get(name)
    
    def get_all_sequences(self) -> List[AutomationSequence]:
        """Get all sequences."""
        return list(self.sequences.values())
    
    def remove_sequence(self, name: str) -> bool:
        """Remove a sequence by name."""
        if name in self.sequences:
            del self.sequences[name]
            return True
        return False
