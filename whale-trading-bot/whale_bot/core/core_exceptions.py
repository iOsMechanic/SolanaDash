"""
Custom Exceptions
================
Application-specific exception classes
"""


class WhaleBotException(Exception):
    """Base exception for whale trading bot"""
    def __init__(self, message: str, error_code: str = None):
        self.message = message
        self.error_code = error_code
        super().__init__(self.message)


class DatabaseError(WhaleBotException):
    """Database operation errors"""
    pass


class TradingError(WhaleBotException):
    """Trading operation errors"""
    pass


class SolanaRPCError(TradingError):
    """Solana RPC connection errors"""
    pass


class InsufficientFundsError(TradingError):
    """Insufficient funds for trading"""
    pass


class InvalidTokenError(TradingError):
    """Invalid token address or data"""
    pass


class PositionError(TradingError):
    """Position management errors"""
    pass


class StrategyError(WhaleBotException):
    """Trading strategy errors"""
    pass


class ConfigurationError(WhaleBotException):
    """Configuration or setup errors"""
    pass


class APIError(WhaleBotException):
    """External API errors"""
    pass


class WhaleDataError(APIError):
    """Whale data fetching errors"""
    pass


class JupiterAPIError(TradingError):
    """Jupiter swap API errors"""
    pass


class TransactionError(TradingError):
    """Transaction execution errors"""
    pass


class ValidationError(WhaleBotException):
    """Data validation errors"""
    pass


class RiskManagementError(TradingError):
    """Risk management violations"""
    pass


class MonitoringError(WhaleBotException):
    """Monitoring and alerting errors"""
    pass


class WebServerError(WhaleBotException):
    """Web API server errors"""
    pass
