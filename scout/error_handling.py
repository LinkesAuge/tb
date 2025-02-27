"""
Error handling module for the Scout application.

This module provides standardized error handling mechanisms including custom exceptions,
error logging, and user-friendly error messages.
"""

import logging
import traceback
import sys
from typing import Optional, Callable, Any, Type, Dict, List, Union

# Configure logger
logger = logging.getLogger(__name__)


class ScoutError(Exception):
    """Base exception class for all Scout application errors."""
    
    def __init__(self, message: str, details: Optional[str] = None):
        """
        Initialize a new ScoutError.
        
        Args:
            message: A user-friendly error message
            details: Technical details about the error (optional)
        """
        self.message = message
        self.details = details
        super().__init__(message)


class ConfigError(ScoutError):
    """Exception raised for configuration-related errors."""
    pass


class CaptureError(ScoutError):
    """Exception raised for screen/window capture errors."""
    pass


class TemplateError(ScoutError):
    """Exception raised for template matching errors."""
    pass


class OCRError(ScoutError):
    """Exception raised for OCR-related errors."""
    pass


class AutomationError(ScoutError):
    """Exception raised for automation-related errors."""
    pass


class WindowError(ScoutError):
    """Exception raised for window management errors."""
    pass


class ErrorHandler:
    """
    Central error handling class for the Scout application.
    
    This class provides methods for handling exceptions, logging errors,
    and presenting user-friendly error messages.
    """
    
    def __init__(self, signal_bus=None):
        """
        Initialize the error handler.
        
        Args:
            signal_bus: Optional signal bus for emitting error signals
        """
        # Store signal bus for emitting error signals
        self.signal_bus = signal_bus
        
        # Map of exception types to handler functions
        self._handlers: Dict[Type[Exception], List[Callable[[Exception], Any]]] = {}
        
        # Register default handlers
        self.register_handler(Exception, self._default_handler)
    
    def register_handler(self, 
                         exception_type: Type[Exception], 
                         handler: Callable[[Exception], Any]) -> None:
        """
        Register a handler function for a specific exception type.
        
        Args:
            exception_type: The type of exception to handle
            handler: Function to call when this exception occurs
        """
        if exception_type not in self._handlers:
            self._handlers[exception_type] = []
        
        self._handlers[exception_type].append(handler)
    
    def handle_exception(self, 
                         exc: Exception, 
                         reraise: bool = False,
                         log_level: int = logging.ERROR) -> None:
        """
        Handle an exception using registered handlers.
        
        Args:
            exc: The exception to handle
            reraise: Whether to re-raise the exception after handling
            log_level: Logging level to use
        """
        # Find the most specific handler for this exception type
        handled = False
        for exc_type, handlers in self._handlers.items():
            if isinstance(exc, exc_type):
                for handler in handlers:
                    handler(exc)
                handled = True
                break
        
        # If no specific handler was found, use the default handler
        if not handled:
            self._default_handler(exc)
        
        # Log the exception
        self._log_exception(exc, log_level)
        
        # Emit signal if signal bus is available
        if self.signal_bus:
            error_type = type(exc).__name__
            message = str(exc)
            self.signal_bus.error_occurred.emit(error_type, message)
        
        # Re-raise if requested
        if reraise:
            raise exc
    
    def handle_error(self, error_type: str, message: str) -> None:
        """
        Handle an error with type and message.
        
        Args:
            error_type: Type of error
            message: Error message
        """
        # Log the error
        logger.error(f"{error_type}: {message}")
        
        # Create a generic exception for internal handling
        exc = ScoutError(message)
        
        # Find and call appropriate handlers
        self._default_handler(exc)
    
    def _default_handler(self, exc: Exception) -> None:
        """
        Default exception handler.
        
        Args:
            exc: The exception to handle
        """
        # Default implementation just logs the error
        pass
    
    def _log_exception(self, exc: Exception, log_level: int = logging.ERROR) -> None:
        """
        Log an exception with appropriate level and details.
        
        Args:
            exc: The exception to log
            log_level: Logging level to use
        """
        exc_info = (type(exc), exc, exc.__traceback__)
        
        # Format the error message
        if isinstance(exc, ScoutError) and exc.details:
            message = f"{exc.message} - Details: {exc.details}"
        else:
            message = str(exc)
        
        # Log with appropriate level
        logger.log(log_level, message, exc_info=exc_info)


# Global error handler instance
error_handler = ErrorHandler()


def handle_errors(log_level: int = logging.ERROR, 
                  reraise: bool = False) -> Callable:
    """
    Decorator for handling exceptions in functions.
    
    Args:
        log_level: Logging level to use
        reraise: Whether to re-raise the exception after handling
        
    Returns:
        Decorated function
    """
    def decorator(func: Callable) -> Callable:
        def wrapper(*args, **kwargs) -> Any:
            try:
                return func(*args, **kwargs)
            except Exception as e:
                error_handler.handle_exception(e, reraise=reraise, log_level=log_level)
                if not reraise:
                    # Return a default value appropriate for the function
                    return None
        return wrapper
    return decorator


def format_exception(exc: Exception) -> str:
    """
    Format an exception into a readable string with traceback.
    
    Args:
        exc: The exception to format
        
    Returns:
        Formatted exception string
    """
    if isinstance(exc, ScoutError):
        base_msg = f"{type(exc).__name__}: {exc.message}"
        if exc.details:
            base_msg += f"\nDetails: {exc.details}"
    else:
        base_msg = f"{type(exc).__name__}: {str(exc)}"
    
    # Add traceback
    tb_lines = traceback.format_exception(type(exc), exc, exc.__traceback__)
    tb_text = ''.join(tb_lines)
    
    return f"{base_msg}\n\nTraceback:\n{tb_text}"


def get_last_exception_info() -> Dict[str, str]:
    """
    Get information about the last exception that occurred.
    
    Returns:
        Dictionary with exception type, message, and traceback
    """
    exc_type, exc_value, exc_traceback = sys.exc_info()
    
    if exc_type is None:
        return {
            "type": "None",
            "message": "No exception occurred",
            "traceback": ""
        }
    
    return {
        "type": exc_type.__name__,
        "message": str(exc_value),
        "traceback": ''.join(traceback.format_exception(exc_type, exc_value, exc_traceback))
    }


def setup_exception_handling() -> None:
    """
    Set up global exception handling for the application.
    
    This function installs a global exception hook to catch and handle
    unhandled exceptions at the application level.
    """
    def global_exception_handler(exc_type, exc_value, exc_traceback):
        """Global exception handler for unhandled exceptions."""
        # Skip KeyboardInterrupt (Ctrl+C) so it can be handled normally
        if issubclass(exc_type, KeyboardInterrupt):
            sys.__excepthook__(exc_type, exc_value, exc_traceback)
            return
        
        # Log the exception
        logger.critical(
            "Unhandled exception",
            exc_info=(exc_type, exc_value, exc_traceback)
        )
        
        # Format the exception for display
        exception_text = ''.join(traceback.format_exception(exc_type, exc_value, exc_traceback))
        
        # Print to stderr (useful for console applications)
        print(f"Unhandled exception:\n{exception_text}", file=sys.stderr)
        
        # Let the global error handler handle it if available
        try:
            error_handler.handle_exception(exc_value)
        except Exception as e:
            # If error handler fails, log that too
            logger.critical(f"Error handler failed: {e}")
    
    # Install the global exception hook
    sys.excepthook = global_exception_handler
    
    logger.info("Global exception handling set up")
