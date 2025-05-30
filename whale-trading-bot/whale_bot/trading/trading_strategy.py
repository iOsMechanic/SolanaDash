"""
Trading Strategy
===============
Handles buy/sell decision logic and trading criteria evaluation
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, Tuple, Set

from ..core.models import TradingConfig, WhaleTransaction, Position
from ..core.exceptions import StrategyError, ValidationError
from ..core.constants import PositionStatus, TransactionTypes, RugcheckStatus

logger = logging.getLogger(__name__)


class TradingStrategy:
    """Handles buy/sell decision logic"""
    
    def __init__(self, config: TradingConfig):
        self.config = config
        self.processed_transactions: Set[str] = set()
        self.rejection_reasons: Dict[str, int] = {}
        
        # Strategy statistics
        self.total_evaluations = 0
        self.buy_signals_generated = 0
        self.sell_signals_generated = 0
        
        logger.info(f"✅ Trading strategy initialized with config: {config}")
    
    async def should_buy(self, transaction: WhaleTransaction, open_positions: Dict[str, Position], 
                        sol_balance: float) -> Tuple[bool, str]:
        """
        Determine if we should buy this token based on whale transaction
        
        Args:
            transaction: Whale transaction to evaluate
            open_positions: Currently open positions by token address
            sol_balance: Current SOL balance
            
        Returns:
            Tuple of (should_buy: bool, reason: str)
        """
        try:
            self.total_evaluations += 1
            
            logger.info(f"\n🔍 Evaluating: {transaction.token_symbol}")
            logger.info(f"   💰 Trade Amount: ${transaction.trade_amount:,.0f}")
            logger.info(f"   🎯 Win Rate: {transaction.win_rate:.1f}%")
            logger.info(f"   📊 Market Cap: ${transaction.token_market_cap:,.0f}")
            logger.info(f"   🛡️  Rugcheck: {transaction.rugcheck_status}")
            logger.info(f"   📈 Type: {transaction.transaction_type}")
            
            # Check if already processed
            if transaction.id in self.processed_transactions:
                reason = "Already processed this transaction"
                logger.info(f"   ❌ REJECTED: {reason}")
                self._track_rejection("already_processed")
                return False, reason
            
            # Check if we already have this position
            if transaction.token_address in open_positions:
                reason = "Already have position in this token"
                logger.info(f"   ❌ REJECTED: {reason}")
                self._track_rejection("duplicate_position")
                return False, reason
            
            # Check max positions limit
            if len(open_positions) >= self.config.max_positions:
                reason = f"Max positions reached ({self.config.max_positions})"
                logger.info(f"   ❌ REJECTED: {reason}")
                self._track_rejection("max_positions")
                return False, reason
            
            # Check SOL balance
            required_sol = self.config.sol_per_trade + self.config.priority_fee
            if sol_balance < required_sol:
                reason = f"Insufficient SOL ({sol_balance:.4f} < {required_sol:.4f})"
                logger.info(f"   ❌ REJECTED: {reason}")
                self._track_rejection("insufficient_balance")
                return False, reason
            
            # Check transaction type
            if transaction.transaction_type.lower() != TransactionTypes.BUY.value:
                reason = f"Not a buy transaction: {transaction.transaction_type}"
                logger.info(f"   ❌ REJECTED: {reason}")
                self._track_rejection("not_buy")
                return False, reason
            
            # Check win rate
            if transaction.win_rate < self.config.min_win_rate:
                reason = f"Win rate too low: {transaction.win_rate:.1f}% < {self.config.min_win_rate:.1f}%"
                logger.info(f"   ❌ REJECTED: {reason}")
                self._track_rejection("low_win_rate")
                return False, reason
            
            # Check trade amount
            if transaction.trade_amount < self.config.min_trade_amount:
                reason = f"Trade amount too low: ${transaction.trade_amount:,.0f} < ${self.config.min_trade_amount:,.0f}"
                logger.info(f"   ❌ REJECTED: {reason}")
                self._track_rejection("low_trade_amount")
                return False, reason
            
            # Check market cap
            if transaction.token_market_cap > self.config.max_market_cap:
                reason = f"Market cap too high: ${transaction.token_market_cap:,.0f} > ${self.config.max_market_cap:,.0f}"
                logger.info(f"   ❌ REJECTED: {reason}")
                self._track_rejection("high_market_cap")
                return False, reason
            
            # Check rugcheck status
            if transaction.rugcheck_status not in self.config.allowed_rugcheck_status:
                reason = f"Poor rugcheck status: {transaction.rugcheck_status}"
                logger.info(f"   ❌ REJECTED: {reason}")
                self._track_rejection("bad_rugcheck")
                return False, reason
            
            # Additional quality checks
            quality_score, quality_reason = self._calculate_quality_score(transaction)
            if quality_score < 0.5:  # Minimum quality threshold
                reason = f"Quality score too low: {quality_score:.2f} ({quality_reason})"
                logger.info(f"   ❌ REJECTED: {reason}")
                self._track_rejection("low_quality")
                return False, reason
            
            # All checks passed - mark as processed and approve
            self.processed_transactions.add(transaction.id)
            self.buy_signals_generated += 1
            
            reasons = [
                f"High win rate: {transaction.win_rate:.1f}%",
                f"Significant trade: ${transaction.trade_amount:,.0f}",
                f"Reasonable market cap: ${transaction.token_market_cap:,.0f}",
                f"Safe rugcheck: {transaction.rugcheck_status}",
                f"Quality score: {quality_score:.2f}",
                "Whale is buying"
            ]
            
            final_reason = " | ".join(reasons)
            logger.info(f"   ✅ APPROVED: All criteria met!")
            logger.info(f"   📝 Quality Score: {quality_score:.2f}")
            
            return True, final_reason
            
        except Exception as e:
            logger.error(f"Error in should_buy evaluation: {e}")
            raise StrategyError(f"Buy evaluation failed: {e}")
    
    def should_sell(self, position: Position) -> Tuple[bool, str]:
        """
        Determine if we should sell this position
        
        Args:
            position: Position to evaluate for selling
            
        Returns:
            Tuple of (should_sell: bool, reason: str)
        """
        try:
            logger.debug(f"🔍 Evaluating sell for {position.token_symbol}: {position.pnl_percentage:.1f}% P&L")
            
            # Take profit check
            if position.pnl_percentage >= self.config.take_profit_percentage:
                reason = f"Take profit target hit ({position.pnl_percentage:.1f}%)"
                logger.info(f"   💰 SELL SIGNAL: {reason}")
                self.sell_signals_generated += 1
                return True, reason
            
            # Stop loss check
            if position.pnl_percentage <= -self.config.stop_loss_percentage:
                reason = f"Stop loss triggered ({position.pnl_percentage:.1f}%)"
                logger.info(f"   🛑 SELL SIGNAL: {reason}")
                self.sell_signals_generated += 1
                return True, reason
            
            # Time-based exit check
            if position.buy_timestamp:
                try:
                    buy_time = datetime.fromisoformat(position.buy_timestamp)
                    hours_held = (datetime.now() - buy_time).total_seconds() / 3600
                    
                    # Sell after 24 hours regardless of P&L
                    if hours_held > 24:
                        reason = f"Time-based exit (held {hours_held:.1f} hours)"
                        logger.info(f"   ⏰ SELL SIGNAL: {reason}")
                        self.sell_signals_generated += 1
                        return True, reason
                    
                    # Early exit for losing positions after 4 hours
                    if hours_held > 4 and position.pnl_percentage < -10:
                        reason = f"Early exit for losing position ({position.pnl_percentage:.1f}% after {hours_held:.1f}h)"
                        logger.info(f"   ⚠️  SELL SIGNAL: {reason}")
                        self.sell_signals_generated += 1
                        return True, reason
                        
                except Exception as e:
                    logger.warning(f"Error parsing timestamp for position {position.id}: {e}")
            
            # Trailing stop logic (if position is profitable)
            if position.pnl_percentage > 10:  # Only apply if position is >10% profitable
                # This is a simplified trailing stop - in practice you'd track the high water mark
                trailing_stop_threshold = position.pnl_percentage * 0.7  # Sell if profit drops by 30%
                if position.pnl_percentage < trailing_stop_threshold:
                    reason = f"Trailing stop triggered (profit dropped to {position.pnl_percentage:.1f}%)"
                    logger.info(f"   📉 SELL SIGNAL: {reason}")
                    self.sell_signals_generated += 1
                    return True, reason
            
            return False, ""
            
        except Exception as e:
            logger.error(f"Error in should_sell evaluation: {e}")
            raise StrategyError(f"Sell evaluation failed: {e}")
    
    def _calculate_quality_score(self, transaction: WhaleTransaction) -> Tuple[float, str]:
        """
        Calculate a quality score for the whale transaction
        
        Returns:
            Tuple of (score: float, reason: str)
        """
        try:
            score = 0.0
            reasons = []
            
            # Win rate component (40% of score)
            win_rate_score = min(transaction.win_rate / 100.0, 1.0)
            score += win_rate_score * 0.4
            reasons.append(f"Win rate: {win_rate_score:.2f}")
            
            # Trade size component (30% of score)
            if transaction.trade_size.lower() == "large":
                size_score = 1.0
            elif transaction.trade_size.lower() == "medium":
                size_score = 0.7
            else:
                size_score = 0.3
            
            score += size_score * 0.3
            reasons.append(f"Size: {size_score:.2f}")
            
            # Trade amount component (20% of score)
            # Normalize trade amount (higher is better, up to a point)
            amount_score = min(transaction.trade_amount / 10000.0, 1.0)  # Max score at $10k
            score += amount_score * 0.2
            reasons.append(f"Amount: {amount_score:.2f}")
            
            # Rugcheck component (10% of score)
            if transaction.rugcheck_status == "good":
                rugcheck_score = 1.0
            elif transaction.rugcheck_status == "warning":
                rugcheck_score = 0.6
            else:
                rugcheck_score = 0.0
            
            score += rugcheck_score * 0.1
            reasons.append(f"Rugcheck: {rugcheck_score:.2f}")
            
            # Bonus for first-time tokens (can be more volatile but higher potential)
            if transaction.is_token_first_seen:
                score += 0.05
                reasons.append("First seen bonus")
            
            # Market cap penalty for very high caps (reduces potential upside)
            if transaction.token_market_cap > 50_000_000:  # >50M
                score -= 0.1
                reasons.append("High cap penalty")
            
            return score, " | ".join(reasons)
            
        except Exception as e:
            logger.error(f"Error calculating quality score: {e}")
            return 0.0, "Calculation failed"
    
    def _track_rejection(self, reason: str):
        """Track rejection reasons for statistics and analysis"""
        if reason not in self.rejection_reasons:
            self.rejection_reasons[reason] = 0
        self.rejection_reasons[reason] += 1
    
    def get_strategy_stats(self) -> Dict:
        """Get strategy performance statistics"""
        try:
            total_signals = self.buy_signals_generated + self.sell_signals_generated
            
            return {
                "total_evaluations": self.total_evaluations,
                "buy_signals_generated": self.buy_signals_generated,
                "sell_signals_generated": self.sell_signals_generated,
                "total_signals": total_signals,
                "buy_signal_rate": (self.buy_signals_generated / max(1, self.total_evaluations)) * 100,
                "rejection_reasons": dict(self.rejection_reasons),
                "processed_transactions": len(self.processed_transactions),
                "config": {
                    "min_win_rate": self.config.min_win_rate,
                    "min_trade_amount": self.config.min_trade_amount,
                    "max_market_cap": self.config.max_market_cap,
                    "sol_per_trade": self.config.sol_per_trade,
                    "take_profit_percentage": self.config.take_profit_percentage,
                    "stop_loss_percentage": self.config.stop_loss_percentage,
                    "max_positions": self.config.max_positions
                }
            }
        except Exception as e:
            logger.error(f"Error getting strategy stats: {e}")
            return {}
    
    def update_config(self, new_config: TradingConfig):
        """Update trading configuration"""
        try:
            old_config = self.config
            self.config = new_config
            
            logger.info(f"✅ Strategy config updated:")
            logger.info(f"   Min win rate: {old_config.min_win_rate}% → {new_config.min_win_rate}%")
            logger.info(f"   SOL per trade: {old_config.sol_per_trade} → {new_config.sol_per_trade}")
            logger.info(f"   Take profit: {old_config.take_profit_percentage}% → {new_config.take_profit_percentage}%")
            logger.info(f"   Stop loss: {old_config.stop_loss_percentage}% → {new_config.stop_loss_percentage}%")
            
        except Exception as e:
            logger.error(f"Error updating config: {e}")
            raise StrategyError(f"Config update failed: {e}")
    
    def reset_statistics(self):
        """Reset strategy statistics (useful for testing or new sessions)"""
        self.total_evaluations = 0
        self.buy_signals_generated = 0
        self.sell_signals_generated = 0
        self.processed_transactions.clear()
        self.rejection_reasons.clear()
        logger.info("✅ Strategy statistics reset")
    
    def is_transaction_processed(self, transaction_id: str) -> bool:
        """Check if a transaction has already been processed"""
        return transaction_id in self.processed_transactions
    
    def get_rejection_summary(self) -> Dict[str, float]:
        """Get rejection reasons as percentages"""
        try:
            total_rejections = sum(self.rejection_reasons.values())
            if total_rejections == 0:
                return {}
            
            return {
                reason: (count / total_rejections) * 100
                for reason, count in self.rejection_reasons.items()
            }
        except Exception as e:
            logger.error(f"Error getting rejection summary: {e}")
            return {}
    
    def validate_transaction(self, transaction: WhaleTransaction) -> Tuple[bool, str]:
        """
        Validate transaction data quality before evaluation
        
        Args:
            transaction: Transaction to validate
            
        Returns:
            Tuple of (is_valid: bool, error_message: str)
        """
        try:
            # Check required fields
            if not transaction.id:
                return False, "Missing transaction ID"
            
            if not transaction.token_address:
                return False, "Missing token address"
            
            if not transaction.token_symbol:
                return False, "Missing token symbol"
            
            # Check numeric fields
            if transaction.win_rate < 0 or transaction.win_rate > 100:
                return False, f"Invalid win rate: {transaction.win_rate}"
            
            if transaction.trade_amount < 0:
                return False, f"Invalid trade amount: {transaction.trade_amount}"
            
            if transaction.token_market_cap < 0:
                return False, f"Invalid market cap: {transaction.token_market_cap}"
            
            # Check enum values
            valid_transaction_types = ["buy", "sell"]
            if transaction.transaction_type.lower() not in valid_transaction_types:
                return False, f"Invalid transaction type: {transaction.transaction_type}"
            
            valid_rugcheck_statuses = ["good", "warning", "danger", "unknown"]
            if transaction.rugcheck_status.lower() not in valid_rugcheck_statuses:
                return False, f"Invalid rugcheck status: {transaction.rugcheck_status}"
            
            # Check timestamp
            try:
                datetime.fromisoformat(transaction.timestamp.replace('Z', '+00:00'))
            except (ValueError, AttributeError):
                return False, f"Invalid timestamp format: {transaction.timestamp}"
            
            return True, "Valid transaction"
            
        except Exception as e:
            logger.error(f"Error validating transaction: {e}")
            return False, f"Validation error: {e}"
