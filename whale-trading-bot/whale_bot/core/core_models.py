"""
Core Data Models
===============
All dataclasses and data structures used throughout the application
"""

from dataclasses import dataclass
from typing import List, Optional, Any, Dict
from datetime import datetime


@dataclass
class WhaleTransaction:
    """Whale transaction data structure"""
    id: str
    timestamp: str
    transaction_type: str
    token_id: str
    token_name: str
    token_symbol: str
    token_address: str
    trade_size: str
    trade_amount: float
    win_rate: float
    token_market_cap: float
    rugcheck_status: str
    is_token_first_seen: bool
    logo_url: str = ""


@dataclass
class BuyDecision:
    """Buy decision data structure"""
    id: str
    whale_transaction_id: str
    token_symbol: str
    token_name: str
    token_address: str
    decision_timestamp: str
    win_rate: float
    trade_amount: float
    market_cap: float
    rugcheck_status: str
    buy_amount_usd: float
    decision_reason: str
    executed: bool = False


@dataclass
class Position:
    """Trading position structure"""
    id: str
    token_address: str
    token_symbol: str
    token_name: str
    buy_amount_sol: float
    buy_amount_usd: float
    token_amount: float
    buy_price_usd: float
    buy_transaction_id: str
    buy_timestamp: str
    current_price_usd: float = 0.0
    current_value_usd: float = 0.0
    pnl_usd: float = 0.0
    pnl_percentage: float = 0.0
    sell_transaction_id: str = ""
    sell_timestamp: str = ""
    status: str = "open"  # open, closed, failed


@dataclass
class TradeExecution:
    """Trade execution result"""
    success: bool
    transaction_id: str
    token_address: str
    input_amount: float
    output_amount: float
    price_per_token: float
    slippage: float
    fees: float
    error_message: str = ""


@dataclass
class TradingConfig:
    """Trading configuration"""
    min_win_rate: float = 60.0
    min_trade_amount: float = 1000.0
    max_market_cap: float = 100_000_000.0
    allowed_rugcheck_status: List[str] = None
    sol_per_trade: float = 0.1
    take_profit_percentage: float = 50.0
    stop_loss_percentage: float = 20.0
    max_positions: int = 5
    slippage_bps: int = 300
    priority_fee: float = 0.001
    
    def __post_init__(self):
        if self.allowed_rugcheck_status is None:
            self.allowed_rugcheck_status = ["good", "warning"]


@dataclass
class TradingStats:
    """Trading statistics data structure"""
    total_trades: int = 0
    winning_trades: int = 0
    losing_trades: int = 0
    win_rate: float = 0.0
    total_profit: float = 0.0
    total_loss: float = 0.0
    net_pnl: float = 0.0
    max_drawdown: float = 0.0
    sharpe_ratio: float = 0.0
    avg_trade_duration: float = 0.0


@dataclass
class WalletInfo:
    """Wallet information structure"""
    address: str
    sol_balance: float
    token_balances: Dict[str, float]
    total_value_usd: float = 0.0


@dataclass
class AlertMessage:
    """Alert message structure"""
    id: str
    type: str  # INFO, WARNING, ERROR
    title: str
    message: str
    timestamp: str
    data: Optional[Dict[str, Any]] = None
