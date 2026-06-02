import os
import logging
from pathlib import Path

class StructuredFormatter(logging.Formatter):
    """
    Custom Formatter to format log entries exactly as requested:
    
    [INFO]
    timestamp
    action
    symbol
    side
    order_type
    
    [ERROR]
    timestamp
    exception_type
    message
    """
    
    def format(self, record: logging.LogRecord) -> str:
        # Generate clean timestamp without fractional seconds
        timestamp = self.formatTime(record, "%Y-%m-%d %H:%M:%S")
        
        # Enforce exact structured formatting for INFO log messages
        if record.levelno == logging.INFO:
            action = getattr(record, "action", record.getMessage())
            symbol = getattr(record, "symbol", "-")
            side = getattr(record, "side", "-")
            order_type = getattr(record, "order_type", "-")
            
            return (
                f"[INFO]\n"
                f"{timestamp}\n"
                f"{action}\n"
                f"{symbol}\n"
                f"{side}\n"
                f"{order_type}\n"
            )
            
        # Enforce exact structured formatting for WARNING/ERROR/CRITICAL logs
        elif record.levelno >= logging.WARNING:
            exc_class_name = "-"
            
            # Attempt to extract exception class name dynamically from exc_info
            if record.exc_info:
                exc_type = record.exc_info[0]
                if exc_type:
                    exc_class_name = exc_type.__name__
            
            # Allow manual injection of custom exception types via `extra` context
            exception_type = getattr(record, "exception_type", exc_class_name)
            if exception_type == "-":
                exception_type = "ValidationError" if "Validation" in record.getMessage() else record.levelname
                
            return (
                f"[ERROR]\n"
                f"{timestamp}\n"
                f"{exception_type}\n"
                f"{record.getMessage()}\n"
            )
            
        # Fallback for DEBUG or lower level records
        else:
            return f"[DEBUG]\n{timestamp}\n{record.getMessage()}\n"


def setup_logging(log_file_name: str = "trading_bot.log") -> logging.Logger:
    """
    Configures application-wide logging with structured output formatting.
    Creates a 'logs/' directory at the project root and sets up structured logging to file.
    
    Args:
        log_file_name (str): Name of the log file to generate. Defaults to "trading_bot.log".

    Returns:
        logging.Logger: The configured root logger instance.
    """
    bot_dir = Path(__file__).resolve().parent
    project_root = bot_dir.parent
    logs_dir = project_root / "logs"
    
    logs_dir.mkdir(parents=True, exist_ok=True)
    log_path = logs_dir / log_file_name
    
    # Initialize the custom structured formatter
    formatter = StructuredFormatter()
    
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.INFO)
    
    if root_logger.hasHandlers():
        root_logger.handlers.clear()
        
    # File Handler
    file_handler = logging.FileHandler(log_path, encoding="utf-8")
    file_handler.setLevel(logging.INFO)
    file_handler.setFormatter(formatter)
    root_logger.addHandler(file_handler)
    
    # Console Handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(formatter)
    root_logger.addHandler(console_handler)
    
    # Log successful configuration of structured logging
    logging.info(
        f"Logging system initialized.",
        extra={
            "action": "Logging system initialized",
            "symbol": "-",
            "side": "-",
            "order_type": "-"
        }
    )
    
    return root_logger
