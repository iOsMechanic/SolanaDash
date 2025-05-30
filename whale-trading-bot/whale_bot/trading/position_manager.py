"""
Position Manager
===============
Manages trading positions, P&L calculations, and portfolio tracking
"""

import logging
from datetime import datetime
from typing import Dict, List, Optional, Tuple
import random

from ..core.models import TradingConfig, Position, TradeExecution, WhaleTransaction, TradingStats
from ..core.exceptions import PositionError, DatabaseError
from ..core.constants import PositionStatus
from ..database.manager import DatabaseManager

logger = logging.getLogger(__name__)


class PositionManager:
    """Manages trading positions and P&L calculations"""
    
    def __init__(self, config: TradingConfig, db: DatabaseManager, trader):
        self.config = config
        self.db = db
        self.trader = trader
        self.open_positions: Dict[str, Position] = {}
        
        # Statistics tracking
        self.total_trades_executed = 0
        self.total_profits = 0.0
        self.total_losses = 0.0
        self.max_concurrent_positions = 0
        self.avg_holding_time = 0.0
        
        # Performance tracking
        self.winning_trades = 0
        self.losing_trades = 0
        self.break_even_trades = 0
        
        logger.info("✅ Position Manager initialized")
    
    async def initialize(self):
        """Load existing open positions from database"""
        try:
            positions = await self.db.get_open_positions()
            for position in positions:
                self.open_positions[position.token_address] = position
            
            # Update statistics
            await self._recalculate_statistics()
            
            logger.info(f"✅ Loaded {len(self.open_positions)} open positions")
            
        except Exception as e:
            logger.error(f"Failed to initialize position manager: {e}")
            raise PositionError(f"Failed to initialize: {e}")
    
    async def create_position(self, transaction: WhaleTransaction, trade_result: TradeExecution) -> Position:
        """
        Create new position from successful trade
        
        Args:
            transaction: Whale transaction that triggered the trade
            trade_result: Result of the executed trade
            
        Returns:
            Created Position object
        """
        try:
            # Estimate USD value (using rough SOL price)
            sol_price_usd = await self._get_sol_price_estimate()
            buy_amount_usd = self.config.sol_per_trade * sol_price_usd
            buy_price_usd = buy_amount_usd / trade_result.output_amount if trade_result.output_amount > 0 else 0
            
            position = Position(
                id=f"pos_{int(datetime.now().timestamp())}_{transaction.token_symbol}",
                token_address=transaction.token_address,
                token_symbol=transaction.token_symbol,
                token_name=transaction.token_name,
                buy_amount_sol=self.config.sol_per_trade,
                buy_amount_usd=buy_amount_usd,
                token_amount=trade_result.output_amount,
                buy_price_usd=buy_price_usd,
                buy_transaction_id=trade_result.transaction_id,
                buy_timestamp=datetime.now().isoformat(),
                current_price_usd=buy_price_usd,
                current_value_usd=buy_amount_usd,
                status=PositionStatus.OPEN.value
            )
            
            # Store position in memory and database
            self.open_positions[transaction.token_address] = position
            await self.db.store_position(position)
            
            # Update statistics
            self.total_trades_executed += 1
            self.max_concurrent_positions = max(self.max_concurrent_positions, len(self.open_positions))
            
            logger.info(f"✅ Position created: {position.id}")
            logger.info(f"   Token: {position.token_symbol}")
            logger.info(f"   Amount: {position.token_amount:.6f} tokens")
            logger.info(f"   Value: ${position.buy_amount_usd:.2f}")
            
            return position
            
        except Exception as e:
            logger.error(f"Failed to create position: {e}")
            raise PositionError(f"Failed to create position: {e}")
    
    async def close_position(self, position: Position, trade_result: TradeExecution, reason: str) -> bool:
        """
        Close position with sell trade result
        
        Args:
            position: Position to close
            trade_result: Result of the sell trade
            reason: Reason for closing
            
        Returns:
            True if successfully closed
        """
        try:
            # Calculate P&L
            sol_price_usd = await self._get_sol_price_estimate()
            sell_amount_usd = trade_result.output_amount * sol_price_usd
            pnl_usd = sell_amount_usd - position.buy_amount_usd
            pnl_percentage = (pnl_usd / position.buy_amount_usd) * 100 if position.buy_amount_usd > 0 else 0
            
            # Calculate holding time
            holding_time_hours = self._calculate_holding_time(position)
            
            # Update position
            position.sell_transaction_id = trade_result.transaction_id
            position.sell_timestamp = datetime.now().isoformat()
            position.current_price_usd = sell_amount_usd / position.token_amount if position.token_amount > 0 else 0
            position.current_value_usd = sell_amount_usd
            position.pnl_usd = pnl_usd
            position.pnl_percentage = pnl_percentage
            position.status = PositionStatus.CLOSED.value
            
            # Remove from open positions
            if position.token_address in self.open_positions:
                del self.open_positions[position.token_address]
            
            # Update statistics
            await self._update_statistics_on_close(pnl_usd, holding_time_hours)
            
            # Store updated position
            await self.db.store_position(position)
            
            logger.info(f"✅ Position closed: {position.id}")
            logger.info(f"   Reason: {reason}")
            logger.info(f"   P&L: ${pnl_usd:.2f} ({pnl_percentage:.1f}%)")
            logger.info(f"   Holding time: {holding_time_hours:.1f} hours")
            logger.info(f"   SOL received: {trade_result.output_amount:.6f}")
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to close position: {e}")
            raise PositionError(f"Failed to close position: {e}")
    
    async def update_position_values(self, position: Position, current_token_price_usd: Optional[float] = None):
        """
        Update position with current market values
        
        Args:
            position: Position to update
            current_token_price_usd: Current token price in USD (if available)
        """
        try:
            # If no price provided, simulate price movement for demo
            if current_token_price_usd is None:
                current_token_price_usd = await self._simulate_price_movement(position)
            
            # Update position values
            position.current_price_usd = current_token_price_usd
            position.current_value_usd = current_token_price_usd * position.token_amount
            position.pnl_usd = position.current_value_usd - position.buy_amount_usd
            position.pnl_percentage = (position.pnl_usd / position.buy_amount_usd) * 100 if position.buy_amount_usd > 0 else 0
            
            # Store updated position
            await self.db.store_position(position)
            
        except Exception as e:
            logger.error(f"Failed to update position values: {e}")
    
    async def monitor_positions(self, strategy) -> List[Tuple[Position, str]]:
        """
        Monitor positions and return those that should be sold
        
        Args:
            strategy: Trading strategy instance for sell decisions
            
        Returns:
            List of (position, reason) tuples for positions to sell
        """
        positions_to_sell = []
        
        if not self.open_positions:
            return positions_to_sell
        
        logger.info(f"📊 Monitoring {len(self.open_positions)} open positions...")
        
        for token_address, position in list(self.open_positions.items()):
            try:
                # Check if we still have the tokens on-chain
                if hasattr(self.trader, 'get_token_balance'):
                    current_balance = await self.trader.get_token_balance(token_address)
                    
                    if current_balance == 0:
                        logger.warning(f"⚠️  No tokens found for {position.token_symbol}, marking as closed")
                        position.status = PositionStatus.CLOSED.value
                        if position.token_address in self.open_positions:
                            del self.open_positions[position.token_address]
                        await self.db.store_position(position)
                        continue
                    
                    # Update token amount if different (in case of partial sales, etc.)
                    if abs(current_balance - position.token_amount) > 0.000001:  # Small tolerance for precision
                        logger.info(f"📊 Updated token amount for {position.token_symbol}: {position.token_amount:.6f} → {current_balance:.6f}")
                        position.token_amount = current_balance
                
                # Update position values with current market data
                await self.update_position_values(position)
                
                logger.info(f"📈 {position.token_symbol}: {position.pnl_percentage:.1f}% P&L (${position.pnl_usd:.2f})")
                
                # Check if should sell using strategy
                should_sell, reason = strategy.should_sell(position)
                if should_sell:
                    positions_to_sell.append((position, reason))
                
            except Exception as e:
                logger.error(f"Error monitoring position {position.token_symbol}: {e}")
                continue
        
        return positions_to_sell
    
    async def get_portfolio_summary(self) -> Dict:
        """Get comprehensive portfolio summary"""
        try:
            # Current positions
            total_open_value_usd = sum(pos.current_value_usd for pos in self.open_positions.values())
            total_unrealized_pnl = sum(pos.pnl_usd for pos in self.open_positions.values())
            
            # Get SOL balance
            sol_balance = 0.0
            if hasattr(self.trader, 'get_sol_balance'):
                try:
                    sol_balance = await self.trader.get_sol_balance()
                except:
                    pass
            
            sol_price_usd = await self._get_sol_price_estimate()
            sol_value_usd = sol_balance * sol_price_usd
            
            # Calculate total portfolio value
            total_portfolio_value = sol_value_usd + total_open_value_usd
            
            return {
                "timestamp": datetime.now().isoformat(),
                "sol_balance": sol_balance,
                "sol_value_usd": sol_value_usd,
                "open_positions_count": len(self.open_positions),
                "total_open_value_usd": total_open_value_usd,
                "total_unrealized_pnl": total_unrealized_pnl,
                "total_portfolio_value": total_portfolio_value,
                "positions": [
                    {
                        "token_symbol": pos.token_symbol,
                        "token_amount": pos.token_amount,
                        "current_value_usd": pos.current_value_usd,
                        "pnl_usd": pos.pnl_usd,
                        "pnl_percentage": pos.pnl_percentage,
                        "holding_time_hours": self._calculate_holding_time(pos)
                    }
                    for pos in self.open_positions.values()
                ]
            }
            
        except Exception as e:
            logger.error(f"Failed to get portfolio summary: {e}")
            return {}
    
    async def get_performance_metrics(self) -> TradingStats:
        """Calculate comprehensive performance metrics"""
        try:
            # Get all closed positions for analysis
            closed_positions = await self.db.get_all_positions("closed")
            
            if not closed_positions:
                return TradingStats()
            
            # Calculate basic metrics
            total_trades = len(closed_positions)
            winning_trades = len([pos for pos in closed_positions if pos.get("pnl_usd", 0) > 0])
            losing_trades = len([pos for pos in closed_positions if pos.get("pnl_usd", 0) < 0])
            break_even_trades = total_trades - winning_trades - losing_trades
            
            win_rate = (winning_trades / total_trades * 100) if total_trades > 0 else 0
            
            # Calculate P&L
            total_profit = sum(pos.get("pnl_usd", 0) for pos in closed_positions if pos.get("pnl_usd", 0) > 0)
            total_loss = sum(pos.get("pnl_usd", 0) for pos in closed_positions if pos.get("pnl_usd", 0) < 0)
            net_pnl = total_profit + total_loss
            
            # Calculate average trade duration
            holding_times = []
            for pos in closed_positions:
                try:
                    buy_time = datetime.fromisoformat(pos.get("buy_timestamp", ""))
                    sell_time = datetime.fromisoformat(pos.get("sell_timestamp", ""))
                    duration = (sell_time - buy_time).total_seconds() / 3600  # hours
                    holding_times.append(duration)
                except:
                    continue
            
            avg_trade_duration = sum(holding_times) / len(holding_times) if holding_times else 0
            
            # Calculate max drawdown (simplified)
            max_drawdown = 0.0
            running_pnl = 0.0
            peak_pnl = 0.0
            
            for pos in sorted(closed_positions, key=lambda x: x.get("sell_timestamp", "")):
                running_pnl += pos.get("pnl_usd", 0)
                if running_pnl > peak_pnl:
                    peak_pnl = running_pnl
                drawdown = (peak_pnl - running_pnl) / max(abs(peak_pnl), 1) if peak_pnl != 0 else 0
                max_drawdown = max(max_drawdown, drawdown)
            
            # Calculate Sharpe ratio (simplified)
            if len(holding_times) > 1:
                returns = [pos.get("pnl_usd", 0) for pos in closed_positions]
                avg_return = sum(returns) / len(returns)
                return_std = (sum((r - avg_return) ** 2 for r in returns) / len(returns)) ** 0.5
                sharpe_ratio = avg_return / return_std if return_std > 0 else 0
            else:
                sharpe_ratio = 0.0
            
            return TradingStats(
                total_trades=total_trades,
                winning_trades=winning_trades,
                losing_trades=losing_trades,
                win_rate=win_rate,
                total_profit=total_profit,
                total_loss=total_loss,
                net_pnl=net_pnl,
                max_drawdown=max_drawdown,
                sharpe_ratio=sharpe_ratio,
                avg_trade_duration=avg_trade_duration
            )
            
        except Exception as e:
            logger.error(f"Failed to get performance metrics: {e}")
            return TradingStats()
    
    def get_position_by_token(self, token_address: str) -> Optional[Position]:
        """Get open position by token address"""
        return self.open_positions.get(token_address)
    
    def get_position_by_id(self, position_id: str) -> Optional[Position]:
        """Get position by ID (searches both open and database)"""
        # First check open positions
        for position in self.open_positions.values():
            if position.id == position_id:
                return position
        
        # If not found in open positions, would need to query database
        # This is async so we'll return None here - caller should use db.get_position_by_id
        return None
    
    async def force_close_position(self, token_address: str, reason: str = "Force closed") -> bool:
        """
        Force close a position without executing a trade (emergency use)
        
        Args:
            token_address: Token address of position to close
            reason: Reason for force closing
            
        Returns:
            True if successfully closed
        """
        try:
            if token_address not in self.open_positions:
                logger.warning(f"Position not found for token: {token_address}")
                return False
            
            position = self.open_positions[token_address]
            
            # Mark as closed without trade
            position.status = PositionStatus.CLOSED.value
            position.sell_timestamp = datetime.now().isoformat()
            # Keep current values as final values
            
            # Remove from open positions
            del self.open_positions[token_address]
            
            # Update in database
            await self.db.store_position(position)
            
            logger.warning(f"⚠️  Force closed position: {position.token_symbol} - {reason}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to force close position: {e}")
            return False
    
    async def _get_sol_price_estimate(self) -> float:
        """Get SOL price estimate (simplified for demo)"""
        # In a real implementation, you'd fetch this from a price API
        # For now, use a reasonable estimate
        return 100.0  # $100 per SOL
    
    async def _simulate_price_movement(self, position: Position) -> float:
        """Simulate realistic price movement for demo purposes"""
        # Generate realistic price movement based on time held and volatility
        try:
            holding_time_hours = self._calculate_holding_time(position)
            
            # Base volatility (2% per hour, compounding)
            base_volatility = 0.02
            time_factor = min(holding_time_hours / 24.0, 1.0)  # Max 1 day effect
            
            # Random walk with slight positive bias (to simulate market growth)
            price_change = random.gauss(0.001, base_volatility) * time_factor  # Small positive bias
            
            # Apply change to original buy price
            new_price = position.buy_price_usd * (1 + price_change)
            
            # Ensure price doesn't go negative
            return max(new_price, position.buy_price_usd * 0.1)  # Min 10% of buy price
            
        except Exception as e:
            logger.error(f"Error simulating price movement: {e}")
            return position.buy_price_usd
    
    def _calculate_holding_time(self, position: Position) -> float:
        """Calculate holding time in hours"""
        try:
            buy_time = datetime.fromisoformat(position.buy_timestamp)
            current_time = datetime.now()
            return (current_time - buy_time).total_seconds() / 3600
        except Exception as e:
            logger.error(f"Error calculating holding time: {e}")
            return 0.0
    
    async def _update_statistics_on_close(self, pnl_usd: float, holding_time_hours: float):
        """Update statistics when a position is closed"""
        try:
            # Update P&L statistics
            if pnl_usd > 0:
                self.total_profits += pnl_usd
                self.winning_trades += 1
            elif pnl_usd < 0:
                self.total_losses += abs(pnl_usd)
                self.losing_trades += 1
            else:
                self.break_even_trades += 1
            
            # Update average holding time
            total_closed_trades = self.winning_trades + self.losing_trades + self.break_even_trades
            self.avg_holding_time = ((self.avg_holding_time * (total_closed_trades - 1)) + holding_time_hours) / total_closed_trades
            
        except Exception as e:
            logger.error(f"Error updating statistics: {e}")
    
    async def _recalculate_statistics(self):
        """Recalculate all statistics from database (used during initialization)"""
        try:
            closed_positions = await self.db.get_all_positions("closed")
            
            self.total_profits = sum(pos.get("pnl_usd", 0) for pos in closed_positions if pos.get("pnl_usd", 0) > 0)
            self.total_losses = sum(abs(pos.get("pnl_usd", 0)) for pos in closed_positions if pos.get("pnl_usd", 0) < 0)
            self.winning_trades = len([pos for pos in closed_positions if pos.get("pnl_usd", 0) > 0])
            self.losing_trades = len([pos for pos in closed_positions if pos.get("pnl_usd", 0) < 0])
            self.break_even_trades = len([pos for pos in closed_positions if pos.get("pnl_usd", 0) == 0])
            self.total_trades_executed = len(closed_positions) + len(self.open_positions)
            
        except Exception as e:
            logger.error(f"Error recalculating statistics: {e}")
    
    def get_manager_stats(self) -> Dict:
        """Get position manager statistics"""
        try:
            total_closed_trades = self.winning_trades + self.losing_trades + self.break_even_trades
            win_rate = (self.winning_trades / max(1, total_closed_trades)) * 100
            
            return {
                "total_trades_executed": self.total_trades_executed,
                "open_positions": len(self.open_positions),
                "closed_trades": total_closed_trades,
                "winning_trades": self.winning_trades,
                "losing_trades": self.losing_trades,
                "break_even_trades": self.break_even_trades,
                "win_rate": win_rate,
                "total_profits": self.total_profits,
                "total_losses": self.total_losses,
                "net_pnl": self.total_profits - self.total_losses,
                "avg_holding_time_hours": self.avg_holding_time,
                "max_concurrent_positions": self.max_concurrent_positions
            }
        except Exception as e:
            logger.error(f"Error getting manager stats: {e}")
            return {}
