from .logging_config import setup_logging
from .client import (
    BinanceFuturesClient,
    ClientConfigError,
    ClientConnectionError
)
from .validators import (
    ValidationError,
    validate_symbol,
    validate_side,
    validate_quantity,
    validate_price
)
from .orders import (
    OrderManager,
    OrderPlacementError
)

__all__ = [
    "setup_logging",
    "BinanceFuturesClient",
    "ClientConfigError",
    "ClientConnectionError",
    "ValidationError",
    "validate_symbol",
    "validate_side",
    "validate_quantity",
    "validate_price",
    "OrderManager",
    "OrderPlacementError",
]

__version__ = "1.0.0"
