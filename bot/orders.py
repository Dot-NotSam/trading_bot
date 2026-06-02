import logging
from typing import Dict, Any
from binance.client import Client
from binance.exceptions import BinanceAPIException, BinanceRequestException

from .client import retry_network_failures
from .validators import (
    validate_symbol,
    validate_side,
    validate_quantity,
    validate_price,
    ValidationError
)

class OrderPlacementError(RuntimeError):
    """Exception raised when an order fails to be placed on the exchange."""
    pass


class OrderManager:
    """
    Manages order placement logic on the Binance Futures Testnet.
    Ensures comprehensive audit trails of API requests and responses, 
    automatic connection retry loops, and descriptive exception logging.
    """

    def __init__(self, binance_client: Client) -> None:
        """
        Initializes the OrderManager with an active Binance Client instance.

        Args:
            binance_client (Client): An initialized python-binance Client instance.
        """
        self.client = binance_client
        self.logger = logging.getLogger(self.__class__.__name__)

    @retry_network_failures(max_retries=3, initial_delay=1.0, backoff=2.0)
    def place_market_order(self, symbol: str, side: str, quantity: float) -> Dict[str, Any]:
        """
        Places a Market order on Binance Futures Testnet with automatic network retry logic.
        Executes immediately at the best available market price.

        Args:
            symbol (str): The trading pair (e.g., 'BTCUSDT').
            side (str): The order side ('BUY' or 'SELL').
            quantity (float): The trade quantity.

        Returns:
            Dict[str, Any]: The structured success response from the exchange.

        Raises:
            ValidationError: If any of the inputs fail validation (logged in validators).
            OrderPlacementError: If the order execution fails on the exchange.
        """
        # Validate inputs (Validation failures are logged inside the validator module)
        validated_symbol = validate_symbol(symbol)
        validated_side = validate_side(side)
        validated_quantity = validate_quantity(quantity)
        
        # 1. Log API Request
        self.logger.info(
            "Sending Market order request to exchange REST API.",
            extra={
                "action": "API Market Order Request",
                "symbol": validated_symbol,
                "side": validated_side,
                "order_type": "MARKET"
            }
        )

        try:
            order_response = self.client.futures_create_order(
                symbol=validated_symbol,
                side=validated_side,
                type="MARKET",
                quantity=validated_quantity,
                recvWindow=6000
            )
            
            # 2. Log API Response
            self.logger.info(
                f"Market order execution accepted. ID: {order_response.get('orderId')}",
                extra={
                    "action": f"API Market Order Response - Executed (Status: {order_response.get('status')})",
                    "symbol": validated_symbol,
                    "side": validated_side,
                    "order_type": "MARKET"
                }
            )
            return order_response

        except BinanceAPIException as e:
            err_msg = (
                f"Exchange rejected Market order: [Status Code {e.status_code}] "
                f"[API Code {e.code}] - {e.message}"
            )
            # Log Binance API exception structured block
            self.logger.error(
                err_msg,
                exc_info=True,
                extra={"exception_type": "BinanceAPIException"}
            )
            raise OrderPlacementError(err_msg) from e
            
        except BinanceRequestException as e:
            # Network failure (propagates through retry decorator, logged on final exhaustion)
            raise
            
        except Exception as e:
            # Unexpected exception
            err_msg = f"Unexpected system error during Market order: {str(e)}"
            self.logger.error(
                err_msg,
                exc_info=True,
                extra={"exception_type": type(e).__name__}
            )
            raise OrderPlacementError(err_msg) from e

    @retry_network_failures(max_retries=3, initial_delay=1.0, backoff=2.0)
    def place_limit_order(self, symbol: str, side: str, quantity: float, price: float) -> Dict[str, Any]:
        """
        Places a Limit order on Binance Futures Testnet with automatic network retry logic.
        Executes only at the specified limit price or better.

        Args:
            symbol (str): The trading pair (e.g., 'BTCUSDT').
            side (str): The order side ('BUY' or 'SELL').
            quantity (float): The trade quantity.
            price (float): The limit price.

        Returns:
            Dict[str, Any]: The structured success response from the exchange.

        Raises:
            ValidationError: If any of the inputs fail validation (logged in validators).
            OrderPlacementError: If the order execution fails on the exchange.
        """
        # Validate inputs (Validation failures are logged inside the validator module)
        validated_symbol = validate_symbol(symbol)
        validated_side = validate_side(side)
        validated_quantity = validate_quantity(quantity)
        validated_price = validate_price(price)
        
        if validated_price is None:
            raise ValidationError("Price is required for Limit orders.")
            
        # 1. Log API Request
        self.logger.info(
            "Sending Limit order request to exchange REST API.",
            extra={
                "action": f"API Limit Order Request (Price: {validated_price})",
                "symbol": validated_symbol,
                "side": validated_side,
                "order_type": "LIMIT"
            }
        )

        try:
            order_response = self.client.futures_create_order(
                symbol=validated_symbol,
                side=validated_side,
                type="LIMIT",
                quantity=validated_quantity,
                price=validated_price,
                timeInForce="GTC",
                recvWindow=6000
            )
            
            # 2. Log API Response
            self.logger.info(
                f"Limit order execution accepted. ID: {order_response.get('orderId')}",
                extra={
                    "action": f"API Limit Order Response - Placed (Status: {order_response.get('status')})",
                    "symbol": validated_symbol,
                    "side": validated_side,
                    "order_type": "LIMIT"
                }
            )
            return order_response

        except BinanceAPIException as e:
            err_msg = (
                f"Exchange rejected Limit order: [Status Code {e.status_code}] "
                f"[API Code {e.code}] - {e.message}"
            )
            # Log Binance API exception structured block
            self.logger.error(
                err_msg,
                exc_info=True,
                extra={"exception_type": "BinanceAPIException"}
            )
            raise OrderPlacementError(err_msg) from e
            
        except BinanceRequestException as e:
            # Network failure (propagates through retry decorator, logged on final exhaustion)
            raise
            
        except Exception as e:
            # Unexpected exception
            err_msg = f"Unexpected system error during Limit order: {str(e)}"
            self.logger.error(
                err_msg,
                exc_info=True,
                extra={"exception_type": type(e).__name__}
            )
            raise OrderPlacementError(err_msg) from e
