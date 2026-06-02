import argparse
import sys
import json
import logging
from typing import List, Optional

# Import premium terminal rendering components from Rich
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.prompt import Confirm
from rich.json import JSON

from .logging_config import setup_logging
from .client import BinanceFuturesClient, ClientConfigError, ClientConnectionError
from .orders import OrderManager, OrderPlacementError
from .validators import (
    validate_symbol,
    validate_side,
    validate_quantity,
    validate_price,
    ValidationError
)

# Initialize application-wide Rich console
console = Console()


def create_parser() -> argparse.ArgumentParser:
    """
    Creates and configures the command-line argument parser.
    """
    parser = argparse.ArgumentParser(
        description="Production Binance Futures Testnet Trading CLI Bot. Places market or limit orders safely.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )
    
    parser.add_argument(
        "--symbol",
        type=str,
        required=True,
        help="The trading symbol pair (e.g., BTCUSDT, ETHUSDT)."
    )
    
    parser.add_argument(
        "--side",
        type=str,
        required=True,
        choices=["BUY", "SELL", "buy", "sell"],
        help="The order side: BUY or SELL."
    )
    
    parser.add_argument(
        "--type",
        type=str,
        required=True,
        choices=["MARKET", "LIMIT", "market", "limit"],
        help="The order type: MARKET or LIMIT."
    )
    
    parser.add_argument(
        "--quantity",
        type=str,
        required=True,
        help="The quantity of the asset to trade (must be a positive number)."
    )
    
    parser.add_argument(
        "--price",
        type=str,
        default=None,
        help="The price at which to place the order (required and positive only for LIMIT orders)."
    )
    
    return parser


def display_order_summary_table(symbol: str, side: str, order_type: str, quantity: float, price: Optional[float]) -> None:
    """
    Constructs and prints a premium, colorful Rich table displaying order parameters.
    """
    table = Table(
        title="[bold cyan]Order Summary[/bold cyan]",
        show_header=True,
        header_style="bold magenta",
        border_style="bright_blue"
    )
    table.add_column("Parameter", style="dim cyan", width=15)
    table.add_column("Value", style="bold white")
    
    # Side color: Green for BUY, Red for SELL
    side_style = "bold green" if side == "BUY" else "bold red"
    
    table.add_row("Symbol", symbol)
    table.add_row("Side", f"[{side_style}]{side}[/{side_style}]")
    table.add_row("Type", order_type)
    table.add_row("Quantity", f"{quantity:f}".rstrip('0').rstrip('.'))
    table.add_row("Price", f"{price:.4f}" if price is not None else "[dim yellow]N/A (Market)[/dim yellow]")
    
    console.print("\n")
    console.print(table)
    console.print("\n")


def main(args_list: Optional[List[str]] = None) -> int:
    """
    Main entry point for the trading bot CLI.
    Initializes logging, parses arguments, validates them, setups client, and places orders.

    Args:
        args_list (List[str], optional): Command line arguments to parse. Defaults to sys.argv[1:].

    Returns:
        int: Exit status code (0 for success, 1 for failure).
    """
    # 1. Initialize logging system
    logger = setup_logging()
    
    parser = create_parser()
    parsed_args = parser.parse_args(args_list)
    
    symbol = parsed_args.symbol
    side = parsed_args.side.upper()
    order_type = parsed_args.type.upper()
    quantity_raw = parsed_args.quantity
    price_raw = parsed_args.price

    # Audit API CLI Execution start as INFO
    logger.info(
        "Parsing command line execution arguments.",
        extra={
            "action": "Parse CLI Arguments Success",
            "symbol": symbol.strip().upper() if isinstance(symbol, str) else "-",
            "side": side,
            "order_type": order_type
        }
    )

    try:
        # Perform validators check (Validation errors are logged inside validate functions)
        validated_symbol = validate_symbol(symbol)
        validated_side = validate_side(side)
        validated_quantity = validate_quantity(quantity_raw)
        validated_price = validate_price(price_raw)
        
        # Enforce conditional rule: Limit orders require a valid price
        if order_type == "LIMIT" and validated_price is None:
            from .validators import _raise_validation_error
            _raise_validation_error("Price (--price) is required and must be positive when --type is LIMIT.")
        
        # Warn if price is supplied for a MARKET order
        if order_type == "MARKET" and validated_price is not None:
            logger.warning(
                "Price was supplied for a MARKET order and will be ignored by the exchange.",
                extra={"exception_type": "UserWarning"}
            )
            console.print(
                "[bold yellow]Warning: Price was supplied for a MARKET order and will be ignored.[/bold yellow]"
            )
            
    except ValidationError as e:
        # Render gorgeous validation error panel with red border
        console.print(
            Panel(
                f"[bold white]{str(e)}[/bold white]",
                title="[bold red]Validation Failure[/bold red]",
                border_style="red",
                expand=False
            )
        )
        return 1

    # 2. Render Order Summary and Confirm Details before submission
    display_order_summary_table(
        symbol=validated_symbol,
        side=validated_side,
        order_type=order_type,
        quantity=validated_quantity,
        price=validated_price
    )
    
    # Block and ask user for explicit confirmation using Confirm prompt
    if not Confirm.ask("[bold yellow]Proceed with order placement?[/bold yellow]"):
        logger.info(
            "User aborted order placement before submission.",
            extra={
                "action": "Order Aborted By User",
                "symbol": validated_symbol,
                "side": validated_side,
                "order_type": order_type
            }
        )
        console.print("\n[bold yellow]! Order execution cancelled by user.[/bold yellow]\n")
        return 0

    # 3. Establish client connection to Binance Futures Testnet
    try:
        futures_client = BinanceFuturesClient()
        futures_client.ping_connection()
        
    except ClientConfigError as e:
        console.print(
            Panel(
                f"[bold white]{str(e)}[/bold white]\n\nPlease check your .env file or environment settings.",
                title="[bold red]Configuration Error[/bold red]",
                border_style="red",
                expand=False
            )
        )
        return 1
        
    except ClientConnectionError as e:
        console.print(
            Panel(
                f"[bold white]{str(e)}[/bold white]\n\nPlease verify your internet connection and API keys.",
                title="[bold red]Connection Error[/bold red]",
                border_style="red",
                expand=False
            )
        )
        return 1

    # 4. Create the order using OrderManager
    try:
        binance_sdk_client = futures_client.get_binance_client()
        order_manager = OrderManager(binance_sdk_client)
        
        if order_type == "MARKET":
            result = order_manager.place_market_order(
                symbol=validated_symbol,
                side=validated_side,
                quantity=validated_quantity
            )
        else:  # LIMIT order
            result = order_manager.place_limit_order(
                symbol=validated_symbol,
                side=validated_side,
                quantity=validated_quantity,
                price=validated_price
            )
            
        # Render gorgeous syntax-highlighted JSON inside green Success Panel
        response_json = JSON(json.dumps(result, indent=2))
        console.print("\n")
        console.print(
            Panel(
                response_json,
                title="[bold green]Order Execution Successful[/bold green]",
                border_style="green",
                expand=False
            )
        )
        console.print("\n")
        return 0
        
    except OrderPlacementError as e:
        console.print(
            Panel(
                f"[bold white]{str(e)}[/bold white]",
                title="[bold red]Order Placement Failed[/bold red]",
                border_style="red",
                expand=False
            )
        )
        return 1
        
    except Exception as e:
        # Unexpected critical system failures caught here
        logger.critical(
            f"Unhandled system error occurred: {str(e)}",
            exc_info=True,
            extra={"exception_type": type(e).__name__}
        )
        console.print(
            Panel(
                f"[bold white]{str(e)}[/bold white]",
                title="[bold red]Critical System Error[/bold red]",
                border_style="red",
                expand=False
            )
        )
        return 1


if __name__ == "__main__":
    sys.exit(main())
