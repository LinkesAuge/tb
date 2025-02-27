from typing import Optional
from pathlib import Path
import pygame
import time
import logging
import os

logger = logging.getLogger(__name__)

class SoundManager:
    """
    Manages audio alerts for important game events.
    
    This class provides audio feedback when significant events occur,
    such as pattern matches being found. It includes features for:
    - Loading and playing sound files
    - Controlling sound frequency with cooldowns
    - Enabling/disabling sound alerts
    - Managing sound resources
    - Volume control
    
    The sound system helps users stay aware of detections without
    having to constantly watch the screen. It includes cooldown
    functionality to prevent sound spam.
    """
    
    def __init__(self, sounds_dir: str = None, cooldown: float = 5.0) -> None:
        """
        Initialize the sound system with specified settings.
        
        Sets up the pygame audio system and loads sound files from the
        specified directory. Includes cooldown management to prevent
        sounds from playing too frequently.
        
        Args:
            sounds_dir: Directory containing .wav sound files (default: "scout/sounds")
            cooldown: Minimum seconds between sound plays
        """
        pygame.mixer.init()
        
        if sounds_dir is None:
            # Get the directory where this file is located
            current_dir = Path(os.path.dirname(os.path.abspath(__file__)))
            sounds_dir = current_dir / "sounds"
            
        self.sounds_dir = Path(sounds_dir)
        self.cooldown = cooldown
        self.last_play_time = 0.0
        self.enabled = True
        self._volume = 0.5  # Default 50% volume
        self.sound: Optional[pygame.mixer.Sound] = None
        
        self.load_sound()
    
    @property
    def volume(self) -> float:
        """Get the current volume (0.0 to 1.0)."""
        return self._volume
        
    @volume.setter
    def volume(self, value: float) -> None:
        """
        Set the volume level.
        
        Args:
            value: Volume level from 0.0 (silent) to 1.0 (maximum)
        """
        self._volume = max(0.0, min(1.0, value))
        if self.sound:
            self.sound.set_volume(self._volume)
        logger.debug(f"Sound volume set to {self._volume:.2f}")
    
    def set_volume(self, value: float) -> None:
        """
        Set the volume level.
        
        Args:
            value: Volume level from 0.0 (silent) to 1.0 (maximum)
        """
        self.volume = value
    
    def set_enabled(self, enabled: bool) -> None:
        """
        Enable or disable sound alerts.
        
        Args:
            enabled: True to enable sounds, False to disable
        """
        self.enabled = enabled
        logger.debug(f"Sound alerts {'enabled' if enabled else 'disabled'}")
        
    def load_sound(self) -> None:
        """
        Load the alert sound file from disk.
        
        Searches the sounds directory for .wav files and loads the first
        one found. Logs warnings if no sound files are available or if
        loading fails.
        """
        try:
            if not self.sounds_dir.exists():
                logger.warning(f"Sounds directory not found: {self.sounds_dir}")
                return
            
            sound_files = list(self.sounds_dir.glob("*.wav"))
            if not sound_files:
                logger.warning("No .wav files found in sounds directory")
                return
            
            self.sound = pygame.mixer.Sound(str(sound_files[0]))
            # Set initial volume
            self.sound.set_volume(self._volume)
            logger.debug(f"Loaded sound: {sound_files[0]} with volume {self._volume:.2f}")
            
        except Exception as e:
            logger.error(f"Error loading sound: {str(e)}", exc_info=True)
    
    def play_if_ready(self) -> None:
        """Play sound if enabled and cooldown has elapsed."""
        if not self.enabled or not self.sound:
            return
            
        current_time = time.time()
        if current_time - self.last_play_time >= self.cooldown:
            try:
                self.sound.play()
                self.last_play_time = current_time
                logger.debug("Played alert sound")
            except Exception as e:
                logger.error(f"Error playing sound: {str(e)}", exc_info=True)
    
    def play_sound(self, sound_name: str) -> None:
        """
        Play a specific sound file by name.
        
        Args:
            sound_name: Name of the sound file without extension (e.g., "alert")
        """
        if not self.enabled:
            return
            
        try:
            sound_path = self.sounds_dir / f"{sound_name}.wav"
            if not sound_path.exists():
                logger.warning(f"Sound file not found: {sound_path}")
                return
                
            sound = pygame.mixer.Sound(str(sound_path))
            sound.set_volume(self._volume)
            sound.play()
            logger.debug(f"Played sound: {sound_name}")
        except Exception as e:
            logger.error(f"Error playing sound '{sound_name}': {str(e)}", exc_info=True)
    
    def toggle(self) -> None:
        """Toggle sound on/off."""
        self.enabled = not self.enabled
        logger.info(f"Sound {'enabled' if self.enabled else 'disabled'}")
        
    def reset_cooldown(self) -> None:
        """
        Reset the cooldown timer to allow immediate sound play.
        
        This method is useful when starting a new detection session
        and you want to ensure the first match will trigger a sound
        regardless of when the last sound was played.
        """
        self.last_play_time = 0.0
        logger.debug("Sound cooldown reset") 