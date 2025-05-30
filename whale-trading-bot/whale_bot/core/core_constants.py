"""
Application Constants
====================
Global constants used throughout the application
"""

from enum import Enum


# Solana Network Constants
class SolanaNetworks:
    MAINNET = "https://api.mainnet-beta.solana.com"
    DEVNET = "https://api.devnet.solana.com"
    TESTNET = "https://api.testnet.solana.com"


# Token Addresses
class TokenAddresses:
    SOL = "So11111111111111111111111111111111111111112"
    USDC = "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v"
    USDT = "Es9vMFrzaCERmJfrF4H2FYD4KCoNkY11McCe8BenwNYB"


# API Endpoints
class APIEndpoints:
    ASSETDASH_BASE = "https://swap-api.assetdash.com/api/api_v5"
    JUPITER_V6 = "https://quote-api.jup.ag/v6"
    
    # AssetDash endpoints
    WHALE_TRANSACTIONS = "/whalewatch/transactions/list"
    TRENDING_TOKENS = "/swap/trending_leaderboard"
    TOKEN_PRICE = "/swap/token_price"
    
    # Jupiter endpoints
    JUPITER_QUOTE = "/quote"
    JUPITER_SWAP = "/swap"


# Trading Constants
class TradingDefaults:
    MIN_WIN_RATE = 60.0
    MIN_TRADE_AMOUNT = 1000.0
    MAX_MARKET_CAP = 100_000_000.0
    SOL_PER_TRADE = 0.1
    TAKE_PROFIT_PCT = 50.0
    STOP_LOSS_PCT = 20.0
    MAX_POSITIONS = 5
    SLIPPAGE_BPS = 300
    PRIORITY_FEE = 0.001


# Position Status
class PositionStatus(Enum):
    OPEN = "open"
    CLOSED = "closed"
    FAILED = "failed"
    PENDING = "pending"


# Transaction Types
class TransactionTypes(Enum):
    BUY = "buy"
    SELL = "sell"


# Trade Sizes
class TradeSizes(Enum):
    SMALL = "small"
    MEDIUM = "medium"
    LARGE = "large"


# Rugcheck Status
class RugcheckStatus(Enum):
    GOOD = "good"
    WARNING = "warning"
    DANGER = "danger"
    UNKNOWN = "unknown"


# Alert Types
class AlertTypes(Enum):
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    SUCCESS = "success"


# Database Collections
class Collections:
    WHALE_TRANSACTIONS = "whale_transactions"
    BUY_DECISIONS = "buy_decisions"
    POSITIONS = "positions"
    TRADES = "trades"
    DAILY_STATS = "daily_stats"
    ALERTS = "alerts"


# Time Constants (in seconds)
class TimeConstants:
    MINUTE = 60
    HOUR = 3600
    DAY = 86400
    WEEK = 604800
    
    # Trading intervals
    MONITOR_INTERVAL = 30
    POSITION_CHECK_INTERVAL = 60
    WHALE_FETCH_INTERVAL = 120
    
    # Timeouts
    RPC_TIMEOUT = 30
    API_TIMEOUT = 30
    TRANSACTION_TIMEOUT = 60


# Rate Limits
class RateLimits:
    ASSETDASH_RPM = 100  # Requests per minute
    JUPITER_RPS = 10     # Requests per second
    SOLANA_RPS = 50      # Requests per second


# Logging
class LogLevels:
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


# File Paths
class Paths:
    LOGS_DIR = "logs"
    CONFIG_DIR = "config"
    DATA_DIR = "data"
    WALLETS_DIR = "wallets"


# Environment Variables
class EnvVars:
    # Required
    SOLANA_PRIVATE_KEY = "SOLANA_PRIVATE_KEY"
    
    # Optional - Trading
    SOL_PER_TRADE = "SOL_PER_TRADE"
    TAKE_PROFIT = "TAKE_PROFIT_PERCENTAGE"
    STOP_LOSS = "STOP_LOSS_PERCENTAGE"
    MAX_POSITIONS = "MAX_POSITIONS"
    
    # Optional - Strategy
    MIN_WIN_RATE = "MIN_WIN_RATE"
    MIN_TRADE_AMOUNT = "MIN_TRADE_AMOUNT"
    MAX_MARKET_CAP = "MAX_MARKET_CAP"
    
    # Optional - Database
    MONGODB_URI = "MONGODB_URI"
    MONGODB_DATABASE = "MONGODB_DATABASE"
    
    # Optional - API
    ASSETDASH_TOKEN = "ASSETDASH_TOKEN"
    API_PORT = "API_PORT"
    API_HOST = "API_HOST"
    
    # Optional - Network
    SOLANA_RPC_URL = "SOLANA_RPC_URL"
    
    # Optional - Logging
    LOG_LEVEL = "LOG_LEVEL"
    LOG_FILE = "LOG_FILE"


# Default Configuration Values
DEFAULT_CONFIG = {
    "trading": {
        "sol_per_trade": TradingDefaults.SOL_PER_TRADE,
        "take_profit_percentage": TradingDefaults.TAKE_PROFIT_PCT,
        "stop_loss_percentage": TradingDefaults.STOP_LOSS_PCT,
        "max_positions": TradingDefaults.MAX_POSITIONS,
        "min_win_rate": TradingDefaults.MIN_WIN_RATE,
        "min_trade_amount": TradingDefaults.MIN_TRADE_AMOUNT,
        "max_market_cap": TradingDefaults.MAX_MARKET_CAP,
        "slippage_bps": TradingDefaults.SLIPPAGE_BPS,
        "priority_fee": TradingDefaults.PRIORITY_FEE,
        "allowed_rugcheck_status": ["good", "warning"]
    },
    "database": {
        "uri": "mongodb://localhost:27017/",
        "database": "whale_trading"
    },
    "api": {
        "host": "localhost",
        "port": 8080
    },
    "solana": {
        "rpc_url": SolanaNetworks.MAINNET
    },
    "logging": {
        "level": "INFO",
        "file": "logs/whale_bot.log"
    },
    "monitoring": {
        "enable_prometheus": False,
        "prometheus_port": 9090
    }
}


# Error Codes
class ErrorCodes:
    # Database errors (1000-1099)
    DB_CONNECTION_FAILED = "DB_1000"
    DB_OPERATION_FAILED = "DB_1001"
    DB_VALIDATION_FAILED = "DB_1002"
    
    # Trading errors (2000-2099)
    TRADE_EXECUTION_FAILED = "TRADE_2000"
    INSUFFICIENT_BALANCE = "TRADE_2001"
    INVALID_TOKEN = "TRADE_2002"
    POSITION_NOT_FOUND = "TRADE_2003"
    RISK_LIMIT_EXCEEDED = "TRADE_2004"
    
    # API errors (3000-3099)
    API_CONNECTION_FAILED = "API_3000"
    API_RATE_LIMITED = "API_3001"
    API_AUTHENTICATION_FAILED = "API_3002"
    API_DATA_INVALID = "API_3003"
    
    # Configuration errors (4000-4099)
    CONFIG_INVALID = "CONFIG_4000"
    ENV_VAR_MISSING = "CONFIG_4001"
    WALLET_INVALID = "CONFIG_4002"


# Success Messages
class SuccessMessages:
    TRADE_EXECUTED = "Trade executed successfully"
    POSITION_OPENED = "Position opened successfully"
    POSITION_CLOSED = "Position closed successfully"
    DATABASE_CONNECTED = "Database connected successfully"
    BOT_INITIALIZED = "Bot initialized successfully"
    API_SERVER_STARTED = "API server started successfully"
