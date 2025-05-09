import logging
import logging.handlers
import os
import sys
from pathlib import Path
from typing import Optional, Dict, Any
from functools import wraps
import traceback

class AppLogger:
    """Central logging utility for the Building Generator application.
    
    This class provides:
    - Configurable logging levels and formats
    - File and console output
    - Error tracking and reporting
    - Decorator for function error handling
    """
    
    # Singleton instance
    _instance: Optional['AppLogger'] = None
    
    # Default configuration
    DEFAULT_CONFIG = {
        'log_level': logging.INFO,
        'log_format': '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        'log_dir': 'logs',
        'max_bytes': 5_000_000,  # 5MB
        'backup_count': 5
    }
    
    def __new__(cls, config: Optional[Dict[str, Any]] = None):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialize(config or cls.DEFAULT_CONFIG)
        return cls._instance
    
    def _initialize(self, config: Dict[str, Any]):
        """Initialize the logger with configuration."""
        self.config = config
        self.logger = logging.getLogger('BuildingGenerator')
        self.logger.setLevel(config['log_level'])
        
        # Create log directory if it doesn't exist
        log_dir = Path(config['log_dir'])
        log_dir.mkdir(parents=True, exist_ok=True)
        
        # Setup handlers
        self._setup_file_handler(log_dir)
        self._setup_console_handler()
        
        # Log startup information
        self.logger.info('Logging system initialized')
        
    def _setup_file_handler(self, log_dir: Path):
        """Setup rotating file handler."""
        file_handler = logging.handlers.RotatingFileHandler(
            log_dir / 'app.log',
            maxBytes=self.config['max_bytes'],
            backupCount=self.config['backup_count']
        )
        file_handler.setFormatter(logging.Formatter(self.config['log_format']))
        self.logger.addHandler(file_handler)
        
    def _setup_console_handler(self):
        """Setup console output handler."""
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setFormatter(logging.Formatter(self.config['log_format']))
        self.logger.addHandler(console_handler)
        
    def log_error(self, error: Exception, context: str = ''):
        """Log an error with full traceback and context."""
        error_details = {
            'type': type(error).__name__,
            'message': str(error),
            'traceback': traceback.format_exc(),
            'context': context
        }
        
        self.logger.error(
            f"Error in {context if context else 'application'}: "
            f"{error_details['type']}: {error_details['message']}\n"
            f"Traceback:\n{error_details['traceback']}"
        )
        
        return error_details
    
    @staticmethod
    def handle_errors(error_message: str = "An error occurred"):
        """Decorator for handling function errors.
        
        Args:
            error_message: Custom error message to display
            
        Example:
            @AppLogger.handle_errors("Error processing file")
            def process_file(filename):
                # Function code here
        """
        def decorator(func):
            @wraps(func)
            def wrapper(*args, **kwargs):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    logger = AppLogger()
                    error_details = logger.log_error(
                        e,
                        f"{error_message} in {func.__name__}"
                    )
                    
                    # If running in GUI context, show error dialog
                    if 'tkinter' in sys.modules:
                        import tkinter.messagebox as messagebox
                        messagebox.showerror(
                            "Error",
                            f"{error_message}\n{str(e)}"
                        )
                    return None
            return wrapper
        return decorator
    
    def debug(self, message: str):
        """Log a debug message."""
        self.logger.debug(message)
        
    def info(self, message: str):
        """Log an info message."""
        self.logger.info(message)
        
    def warning(self, message: str):
        """Log a warning message."""
        self.logger.warning(message)
        
    def error(self, message: str):
        """Log an error message."""
        self.logger.error(message)
        
    def critical(self, message: str):
        """Log a critical message."""
        self.logger.critical(message)

# Create global logger instance
logger = AppLogger()

# Example usage of error handler decorator
@logger.handle_errors("Error loading file")
def load_file(filepath: str) -> Any:
    """Example function showing error handler usage."""
    if not os.path.exists(filepath):
        raise FileNotFoundError(f"File not found: {filepath}")
    # File loading code here
    return None 