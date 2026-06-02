import os
import time
import logging
import functools
import requests
from typing import Optional, Any, Callable
from dotenv import load_dotenv
from binance.client import Client
from binance.exceptions import BinanceAPIException, BinanceRequestException

# Custom exceptions for trading client domain
class ClientConfigError(ValueError):
    """Exception raised when API configuration is missing or invalid."""
    pass


class ClientConnectionError(ConnectionError):
    """Exception raised when connection to the Binance Futures Testnet fails."""
    pass


def retry_network_failures(max_retries: int = 3, initial_delay: float = 1.0, backoff: float = 2.0) -> Callable:
    """
    Exponential backoff retry decorator for handling transient network failures.
    Catches BinanceRequestException and general requests.exceptions.RequestException.
    
    Args:
        max_retries (int): Total number of attempts.
        initial_delay (float): Wait time before the first retry (seconds).
        backoff (float): Multiplier for subsequent retry delays.
    """
    def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            delay = initial_delay
            logger = logging.getLogger(func.__module__)
            
            for attempt in range(1, max_retries + 1):
                try:
                    return func(*args, **kwargs)
                except (BinanceRequestException, requests.exceptions.RequestException) as e:
                    # Log as error if this is the final attempt
                    if attempt == max_retries:
                        logger.error(
                            f"Network connection failed permanently after {max_retries} attempts: {str(e)}",
                            exc_info=True,
                            extra={"exception_type": type(e).__name__}
                        )
                        raise ClientConnectionError(f"Permanent network failure: {str(e)}") from e
                    
                    # Log transient failure and sleep
                    logger.warning(
                        f"Transient network error on {func.__name__} (attempt {attempt}/{max_retries}): {str(e)}. "
                        f"Retrying in {delay:.2f}s...",
                        exc_info=True,
                        extra={"exception_type": type(e).__name__}
                    )
                    time.sleep(delay)
                    delay *= backoff
            return func(*args, **kwargs)
        return wrapper
    return decorator


class BinanceFuturesClient:
    """
    Wrapper class for the Binance Futures Testnet Client.
    Handles environment configuration, pings, and transient network retry setups.
    """

    def __init__(self, api_key: Optional[str] = None, api_secret: Optional[str] = None) -> None:
        """
        Initializes the BinanceFuturesClient, loading credentials.
        """
        load_dotenv()
        self.api_key = api_key or os.getenv("BINANCE_API_KEY")
        self.api_secret = api_secret or os.getenv("BINANCE_API_SECRET")
        self.logger = logging.getLogger(self.__class__.__name__)
        
        if not self.api_key or not self.api_secret:
            error_msg = (
                "Binance API Key or Secret is missing. Ensure BINANCE_API_KEY and "
                "BINANCE_API_SECRET are set in your environment or configured in a .env file."
            )
            # Log validation/configuration error as ERROR
            self.logger.error(
                error_msg,
                extra={"exception_type": "ClientConfigError"}
            )
            raise ClientConfigError(error_msg)
            
        self.client: Optional[Client] = None
        self._initialize_connection()

    def _initialize_connection(self) -> None:
        """
        Initializes the python-binance Client for Binance Futures Testnet.
        """
        self.logger.info(
            "Initializing connection parameters to Binance Futures Testnet.",
            extra={
                "action": "Initialize Client Connection Parameters",
                "symbol": "-",
                "side": "-",
                "order_type": "-"
            }
        )
        try:
            self.client = Client(
                api_key=self.api_key,
                api_secret=self.api_secret,
                testnet=True
            )
            self.client.FUTURES_URL = "https://testnet.binancefuture.com/fapi"
            
            self.logger.info(
                "API client wrapper initialization success.",
                extra={
                    "action": "Initialize Client Connection Success",
                    "symbol": "-",
                    "side": "-",
                    "order_type": "-"
                }
            )
        except Exception as e:
            self.logger.error(
                f"Unexpected error during client initialization: {str(e)}",
                exc_info=True,
                extra={"exception_type": type(e).__name__}
            )
            raise ClientConnectionError(f"Connection initialization failed: {str(e)}") from e

    @retry_network_failures(max_retries=3, initial_delay=1.0, backoff=2.0)
    def ping_connection(self) -> bool:
        """
        Verifies active connection and api keys by pinging and checking account balances.
        Retries transient network anomalies automatically up to 3 times.
        """
        if not self.client:
            raise ClientConnectionError("Client is not initialized.")
            
        # 1. Log API Request
        self.logger.info(
            "Sending Ping and Account Balance request to verify API keys.",
            extra={
                "action": "API Ping and Balance Verification Request",
                "symbol": "-",
                "side": "-",
                "order_type": "-"
            }
        )
        
        try:
            # REST Ping
            self.client.futures_ping()
            
            # REST Read Action to verify credentials
            self.client.futures_account_balance(recvWindow=6000)
            
            # 2. Log API Response
            self.logger.info(
                "Ping and authentication check completed successfully.",
                extra={
                    "action": "API Ping and Balance Verification Response",
                    "symbol": "-",
                    "side": "-",
                    "order_type": "-"
                }
            )
            return True
            
        except BinanceAPIException as e:
            # Specific exchange errors (invalid keys, permission errors, etc.)
            self.logger.error(
                f"Binance Futures Testnet API Key check failed: [Code {e.code}] {e.message}",
                exc_info=True,
                extra={"exception_type": "BinanceAPIException"}
            )
            raise ClientConnectionError(f"API Authentication failed: {e.message}") from e
            
        except (BinanceRequestException, requests.exceptions.RequestException) as e:
            # Handled by retry decorator, but re-raised on exhaustion
            raise
            
        except Exception as e:
            self.logger.error(
                f"Unexpected connectivity error during verification ping: {str(e)}",
                exc_info=True,
                extra={"exception_type": type(e).__name__}
            )
            raise ClientConnectionError(f"Unexpected connection error: {str(e)}") from e

    def get_binance_client(self) -> Client:
        """
        Exposes the underlying python-binance Client.
        """
        if not self.client:
            raise ClientConnectionError("Binance Client is not initialized.")
        return self.client
