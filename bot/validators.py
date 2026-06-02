import re
import logging
from typing import Any, Union

class ValidationError(ValueError):
    """Exception raised for errors in order parameter validation."""
    pass


# Instantiate module-level logger for auditing validation failures
logger = logging.getLogger(__name__)


def _raise_validation_error(message: str) -> None:
    """
    Helper function to log the validation error to the audit trail
    under [ERROR] and raise the ValidationError.
    """
    logger.error(message, extra={"exception_type": "ValidationError"})
    raise ValidationError(message)


def validate_symbol(symbol: Any) -> str:
    """
    Validates the trading symbol (e.g., BTCUSDT).
    Must be a non-empty string consisting only of alphanumeric uppercase characters.

    Args:
        symbol (Any): The trading symbol to validate.

    Returns:
        str: The cleaned, uppercase symbol string.

    Raises:
        ValidationError: If symbol is empty, not a string, or contains invalid characters.
    """
    if not isinstance(symbol, str):
        _raise_validation_error(f"Symbol must be a string, got {type(symbol).__name__}")
        
    cleaned_symbol = symbol.strip().upper()
    
    if not cleaned_symbol:
        _raise_validation_error("Symbol cannot be empty or whitespace only")
        
    pattern = re.compile(r"^[A-Z0-9]{3,20}$")
    if not pattern.match(cleaned_symbol):
        _raise_validation_error(
            f"Invalid symbol format: '{symbol}'. "
            f"Symbol must be alphanumeric, 3-20 characters long, and uppercase."
        )
        
    return cleaned_symbol


def validate_side(side: Any) -> str:
    """
    Validates the order side. Must be either 'BUY' or 'SELL'.

    Args:
        side (Any): The order side to validate.

    Returns:
        str: The normalized 'BUY' or 'SELL' string.

    Raises:
        ValidationError: If side is not a string or is not equal to 'BUY' or 'SELL'.
    """
    if not isinstance(side, str):
        _raise_validation_error(f"Order side must be a string, got {type(side).__name__}")
        
    cleaned_side = side.strip().upper()
    
    valid_sides = {"BUY", "SELL"}
    if cleaned_side not in valid_sides:
        _raise_validation_error(
            f"Invalid order side: '{side}'. "
            f"Allowed values are: {', '.join(sorted(valid_sides))}."
        )
        
    return cleaned_side


def validate_quantity(quantity: Any) -> float:
    """
    Validates the order quantity. Must be a positive floating-point number.

    Args:
        quantity (Any): The order quantity to validate.

    Returns:
        float: The validated quantity as a float.

    Raises:
        ValidationError: If quantity cannot be converted to a positive float.
    """
    if quantity is None:
        _raise_validation_error("Quantity is required and cannot be None")
        
    try:
        float_quantity = float(quantity)
    except (ValueError, TypeError):
        _raise_validation_error(
            f"Invalid quantity: '{quantity}'. "
            f"Quantity must be a valid number."
        )
        
    if float_quantity <= 0.0:
        _raise_validation_error(
            f"Invalid quantity: {float_quantity}. "
            f"Quantity must be strictly greater than 0."
        )
        
    return float_quantity


def validate_price(price: Any) -> Union[float, None]:
    """
    Validates the order price. 
    If price is provided, it must be a positive floating-point number.
    If price is None, it is returned as None (valid for MARKET orders).

    Args:
        price (Any): The order price to validate.

    Returns:
        float | None: The validated price as a float, or None.

    Raises:
        ValidationError: If price is provided but cannot be converted to a positive float.
    """
    if price is None:
        return None
        
    if isinstance(price, str) and price.strip().upper() in {"", "NONE", "NULL"}:
        return None

    try:
        float_price = float(price)
    except (ValueError, TypeError):
        _raise_validation_error(
            f"Invalid price: '{price}'. "
            f"Price must be a valid number."
        )
        
    if float_price <= 0.0:
        _raise_validation_error(
            f"Invalid price: {float_price}. "
            f"Price must be strictly greater than 0."
        )
        
    return float_price
