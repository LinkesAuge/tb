"""
Logging utilities for the Scout application.

This module provides a centralized logging system with configurable handlers,
formatters, and log levels. It supports both file and console logging with
different verbosity levels.
"""

import logging
import os
import sys
import traceback
from datetime import datetime
from pathlib import Path
from typing import Dict, Optional, Union, List, Callable, Any

# Default log format
DEFAULT_LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
# More detailed format for debugging
DEBUG_LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s"

# Default log levels
DEFAULT_CONSOLE_LEVEL = logging.INFO
DEFAULT_FILE_LEVEL = logging.DEBUG

# Global logger registry to avoid duplicate loggers
_loggers: Dict[str, logging.Logger] = {}


def setup_logging(console_level: int = DEFAULT_CONSOLE_LEVEL,
                 file_level: int = DEFAULT_FILE_LEVEL,
                 log_dir: str = "logs",
                 log_format: str = DEFAULT_LOG_FORMAT,
                 debug_mode: bool = False) -> None:
    """
    Set up the application-wide logging configuration.
    
    This function configures the root logger and sets up both console and file logging.
    It should be called once at the start of the application.
    
    Args:
        console_level: Logging level for console output
        file_level: Logging level for file output
        log_dir: Directory to store log files
        log_format: Format string for log messages
        debug_mode: If True, use more verbose logging and DEBUG level
    """
    # If in debug mode, use more verbose format and DEBUG level
    if debug_mode:
        console_level = min(console_level, logging.DEBUG)
        log_format = DEBUG_LOG_FORMAT
    
    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(min(console_level, file_level))
    
    # Remove any existing handlers
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)
    
    # Create formatters
    formatter = logging.Formatter(log_format)
    
    # Add console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(console_level)
    console_handler.setFormatter(formatter)
    root_logger.addHandler(console_handler)
    
    # Add file handler if log_dir is specified
    if log_dir:
        log_dir_path = Path(log_dir)
        log_dir_path.mkdir(parents=True, exist_ok=True)
        
        # Create log filename with timestamp
        timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        log_file = log_dir_path / f"scout-{timestamp}.log"
        
        file_handler = logging.FileHandler(log_file, encoding='utf-8')
        file_handler.setLevel(file_level)
        file_handler.setFormatter(formatter)
        root_logger.addHandler(file_handler)
    
    # Log startup message
    root_logger.info(f"Logging initialized: console={logging.getLevelName(console_level)}, "
                    f"file={logging.getLevelName(file_level)}, log_dir={log_dir}")
    
    if debug_mode:
        root_logger.info("Debug mode enabled")


def get_logger(name: str, 
               console_level: Optional[int] = None,
               file_level: Optional[int] = None,
               log_dir: Optional[str] = None,
               log_format: Optional[str] = None,
               propagate: bool = False) -> logging.Logger:
    """
    Get or create a logger with the specified name and configuration.
    
    Args:
        name: The name of the logger, typically __name__ of the calling module
        console_level: Logging level for console output (default: INFO)
        file_level: Logging level for file output (default: DEBUG)
        log_dir: Directory to store log files (default: logs/ in current directory)
        log_format: Format string for log messages (default: DEFAULT_LOG_FORMAT)
        propagate: Whether to propagate logs to parent loggers (default: False)
        
    Returns:
        A configured logger instance
    """
    # Return existing logger if already configured
    if name in _loggers:
        return _loggers[name]
    
    # Create new logger
    logger = logging.getLogger(name)
    
    # Prevent duplicate handlers if logger already exists
    if logger.handlers:
        return logger
    
    # Set default levels if not specified
    console_level = console_level if console_level is not None else DEFAULT_CONSOLE_LEVEL
    file_level = file_level if file_level is not None else DEFAULT_FILE_LEVEL
    log_format = log_format if log_format is not None else DEFAULT_LOG_FORMAT
    
    # Set propagation
    logger.propagate = propagate
    
    # Set the logger's level to the minimum of console and file levels
    logger.setLevel(min(console_level, file_level))
    
    # Create formatters
    formatter = logging.Formatter(log_format)
    
    # Add console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(console_level)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)
    
    # Add file handler if log_dir is specified
    if log_dir:
        log_dir_path = Path(log_dir)
        log_dir_path.mkdir(parents=True, exist_ok=True)
        
        # Create log filename with timestamp
        timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        log_file = log_dir_path / f"{name.replace('.', '_')}-{timestamp}.log"
        
        file_handler = logging.FileHandler(log_file, encoding='utf-8')
        file_handler.setLevel(file_level)
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
    
    # Store logger in registry
    _loggers[name] = logger
    
    return logger


def configure_root_logger(console_level: int = DEFAULT_CONSOLE_LEVEL,
                          file_level: int = DEFAULT_FILE_LEVEL,
                          log_dir: str = "logs",
                          log_format: str = DEFAULT_LOG_FORMAT) -> logging.Logger:
    """
    Configure the root logger for the application.
    
    Args:
        console_level: Logging level for console output
        file_level: Logging level for file output
        log_dir: Directory to store log files
        log_format: Format string for log messages
        
    Returns:
        The configured root logger
    """
    return get_logger("scout", console_level, file_level, log_dir, log_format)


def log_exception(logger: logging.Logger, 
                  exc_info: Optional[tuple] = None, 
                  level: int = logging.ERROR,
                  msg: str = "An exception occurred:") -> None:
    """
    Log an exception with traceback information.
    
    Args:
        logger: The logger to use
        exc_info: Exception info tuple (type, value, traceback)
        level: Logging level to use
        msg: Message prefix for the log entry
    """
    if exc_info is None:
        exc_info = sys.exc_info()
    
    if exc_info[0] is not None:  # If there's an actual exception
        tb_lines = traceback.format_exception(*exc_info)
        logger.log(level, f"{msg}\n{''.join(tb_lines)}")
    else:
        logger.log(level, msg)


class LoggerAdapter(logging.LoggerAdapter):
    """
    Logger adapter that adds context information to log messages.
    
    This adapter allows adding additional context to log messages,
    such as user ID, session ID, or component name.
    """
    
    def __init__(self, logger: logging.Logger, extra: Optional[Dict[str, Any]] = None):
        """
        Initialize the adapter with a logger and optional extra context.
        
        Args:
            logger: The logger to adapt
            extra: Dictionary of extra context to add to all messages
        """
        super().__init__(logger, extra or {})
    
    def process(self, msg: str, kwargs: Dict[str, Any]) -> tuple:
        """
        Process the log message by adding context information.
        
        Args:
            msg: The log message
            kwargs: Additional keyword arguments for the logging call
            
        Returns:
            Tuple of (modified_message, modified_kwargs)
        """
        # Add context prefix if extra data exists
        if self.extra:
            context_str = ' '.join(f"[{k}={v}]" for k, v in self.extra.items())
            msg = f"{context_str} {msg}"
        
        return msg, kwargs


def get_context_logger(name: str, context: Dict[str, Any], **logger_kwargs) -> LoggerAdapter:
    """
    Get a logger with additional context information.
    
    Args:
        name: The name of the logger
        context: Dictionary of context information to add to log messages
        **logger_kwargs: Additional arguments to pass to get_logger
        
    Returns:
        A LoggerAdapter that adds context to log messages
    """
    logger = get_logger(name, **logger_kwargs)
    return LoggerAdapter(logger, context)


def set_log_level(logger_name: Optional[str] = None, 
                  level: int = logging.INFO,
                  handler_type: Optional[str] = None) -> None:
    """
    Set the log level for a specific logger or all loggers.
    
    Args:
        logger_name: Name of the logger to modify (None for all loggers)
        level: New logging level
        handler_type: Type of handler to modify ('console', 'file', or None for all)
    """
    if logger_name:
        loggers = [_loggers.get(logger_name)] if logger_name in _loggers else []
    else:
        loggers = list(_loggers.values())
    
    for logger in loggers:
        if logger:
            if handler_type is None:
                logger.setLevel(level)
                for handler in logger.handlers:
                    handler.setLevel(level)
            else:
                for handler in logger.handlers:
                    if (handler_type == 'console' and isinstance(handler, logging.StreamHandler) and 
                        not isinstance(handler, logging.FileHandler)):
                        handler.setLevel(level)
                    elif handler_type == 'file' and isinstance(handler, logging.FileHandler):
                        handler.setLevel(level)


def create_rotating_file_handler(log_file: Union[str, Path], 
                                max_bytes: int = 10 * 1024 * 1024,  # 10 MB
                                backup_count: int = 5,
                                level: int = logging.DEBUG,
                                log_format: Optional[str] = None) -> logging.Handler:
    """
    Create a rotating file handler for log rotation based on file size.
    
    Args:
        log_file: Path to the log file
        max_bytes: Maximum size of the log file before rotation
        backup_count: Number of backup files to keep
        level: Logging level for the handler
        log_format: Format string for log messages
        
    Returns:
        A configured RotatingFileHandler
    """
    from logging.handlers import RotatingFileHandler
    
    # Ensure directory exists
    log_path = Path(log_file)
    log_path.parent.mkdir(parents=True, exist_ok=True)
    
    handler = RotatingFileHandler(
        log_path, 
        maxBytes=max_bytes,
        backupCount=backup_count,
        encoding='utf-8'
    )
    handler.setLevel(level)
    
    if log_format:
        formatter = logging.Formatter(log_format)
        handler.setFormatter(formatter)
    
    return handler


def create_timed_rotating_file_handler(log_file: Union[str, Path],
                                      when: str = 'midnight',
                                      interval: int = 1,
                                      backup_count: int = 30,
                                      level: int = logging.DEBUG,
                                      log_format: Optional[str] = None) -> logging.Handler:
    """
    Create a time-based rotating file handler for log rotation.
    
    Args:
        log_file: Path to the log file
        when: When to rotate ('S', 'M', 'H', 'D', 'W0'-'W6', 'midnight')
        interval: Interval for rotation
        backup_count: Number of backup files to keep
        level: Logging level for the handler
        log_format: Format string for log messages
        
    Returns:
        A configured TimedRotatingFileHandler
    """
    from logging.handlers import TimedRotatingFileHandler
    
    # Ensure directory exists
    log_path = Path(log_file)
    log_path.parent.mkdir(parents=True, exist_ok=True)
    
    handler = TimedRotatingFileHandler(
        log_path,
        when=when,
        interval=interval,
        backupCount=backup_count,
        encoding='utf-8'
    )
    handler.setLevel(level)
    
    if log_format:
        formatter = logging.Formatter(log_format)
        handler.setFormatter(formatter)
    
    return handler


def add_handler_to_logger(logger_name: str, handler: logging.Handler) -> None:
    """
    Add a handler to a specific logger.
    
    Args:
        logger_name: Name of the logger
        handler: Handler to add
    """
    if logger_name in _loggers:
        _loggers[logger_name].addHandler(handler)


def remove_all_handlers(logger_name: Optional[str] = None) -> None:
    """
    Remove all handlers from a specific logger or all loggers.
    
    Args:
        logger_name: Name of the logger (None for all loggers)
    """
    if logger_name:
        loggers = [_loggers.get(logger_name)] if logger_name in _loggers else []
    else:
        loggers = list(_loggers.values())
    
    for logger in loggers:
        if logger:
            for handler in list(logger.handlers):
                logger.removeHandler(handler)


class LoggingContext:
    """
    Context manager for temporarily changing log levels.
    
    Example:
        with LoggingContext('scout', logging.DEBUG):
            # Code that generates debug logs
    """
    
    def __init__(self, logger_name: str, level: int):
        """
        Initialize the context manager.
        
        Args:
            logger_name: Name of the logger to modify
            level: Temporary logging level
        """
        self.logger_name = logger_name
        self.level = level
        self.logger = _loggers.get(logger_name)
        self.old_level = None
    
    def __enter__(self):
        """Set the temporary log level."""
        if self.logger:
            self.old_level = self.logger.level
            self.logger.setLevel(self.level)
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Restore the original log level."""
        if self.logger and self.old_level is not None:
            self.logger.setLevel(self.old_level)


def log_function_call(logger: logging.Logger, level: int = logging.DEBUG):
    """
    Decorator to log function calls with arguments and return values.
    
    Args:
        logger: Logger to use
        level: Logging level
        
    Returns:
        Decorator function
    """
    def decorator(func: Callable) -> Callable:
        def wrapper(*args, **kwargs):
            func_name = func.__name__
            logger.log(level, f"Calling {func_name} with args={args}, kwargs={kwargs}")
            try:
                result = func(*args, **kwargs)
                logger.log(level, f"{func_name} returned: {result}")
                return result
            except Exception as e:
                logger.log(logging.ERROR, f"{func_name} raised exception: {e}")
                raise
        return wrapper
    return decorator
