"""
Database Manager
===============
Handles all MongoDB operations for the whale trading bot
"""

import logging
from datetime import datetime
from typing import Dict, List, Optional
from dataclasses import asdict

from motor.motor_asyncio import AsyncIOMotorClient
import pymongo

from ..core.models import (
    WhaleTransaction, BuyDecision, Position, TradeExecution, TradingStats
)
from ..core.exceptions import DatabaseError
from ..core.constants import Collections

logger = logging.getLogger(__name__)


class DatabaseManager:
    """Handles all MongoDB operations"""
    
    def __init__(self, mongo_uri: str, db_name: str):
        self.mongo_uri = mongo_uri
        self.db_name = db_name
        self.client = None
        self.db = None
        
        # Collections
        self.whale_transactions = None
        self.buy_decisions = None
        self.positions = None
        self.trades = None
        self.daily_stats = None
        self.alerts = None
    
    async def connect(self):
        """Connect to MongoDB"""
        try:
            self.client = AsyncIOMotorClient(self.mongo_uri)
            self.db = self.client[self.db_name]
            
            # Test connection
            await self.client.admin.command('ping')
            logger.info(f"✅ MongoDB connected: {self.db_name}")
            
            # Setup collections
            self.whale_transactions = self.db[Collections.WHALE_TRANSACTIONS]
            self.buy_decisions = self.db[Collections.BUY_DECISIONS]
            self.positions = self.db[Collections.POSITIONS]
            self.trades = self.db[Collections.TRADES]
            self.daily_stats = self.db[Collections.DAILY_STATS]
            self.alerts = self.db[Collections.ALERTS]
            
            # Create indexes
            await self._create_indexes()
            
        except Exception as e:
            logger.error(f"❌ MongoDB connection failed: {e}")
            raise DatabaseError(f"Failed to connect to database: {e}")
    
    async def _create_indexes(self):
        """Create database indexes for performance"""
        try:
            # Whale transactions indexes
            await self.whale_transactions.create_index("id", unique=True)
            await self.whale_transactions.create_index("timestamp")
            await self.whale_transactions.create_index("token_symbol")
            await self.whale_transactions.create_index("win_rate")
            await self.whale_transactions.create_index("trade_amount")
            await self.whale_transactions.create_index("processed_at")
            
            # Buy decisions indexes
            await self.buy_decisions.create_index("id", unique=True)
            await self.buy_decisions.create_index("decision_timestamp")
            await self.buy_decisions.create_index("whale_transaction_id")
            await self.buy_decisions.create_index("token_symbol")
            await self.buy_decisions.create_index("executed")
            
            # Positions indexes
            await self.positions.create_index("id", unique=True)
            await self.positions.create_index("token_address")
            await self.positions.create_index("status")
            await self.positions.create_index("buy_timestamp")
            await self.positions.create_index("sell_timestamp")
            
            # Trades indexes
            await self.trades.create_index("transaction_id", unique=True)
            await self.trades.create_index("token_address")
            await self.trades.create_index("trade_type")
            await self.trades.create_index("timestamp")
            await self.trades.create_index("position_id")
            
            # Daily stats indexes
            await self.daily_stats.create_index("date", unique=True)
            
            # Alerts indexes
            await self.alerts.create_index("timestamp")
            await self.alerts.create_index("type")
            
            logger.info("✅ Database indexes created")
            
        except Exception as e:
            logger.error(f"Failed to create indexes: {e}")
            raise DatabaseError(f"Failed to create database indexes: {e}")
    
    async def store_whale_transaction(self, transaction: WhaleTransaction) -> bool:
        """Store whale transaction"""
        try:
            doc = asdict(transaction)
            doc['processed_at'] = datetime.now()
            
            result = await self.whale_transactions.replace_one(
                {"id": transaction.id},
                doc,
                upsert=True
            )
            
            return result.upserted_id is not None or result.modified_count > 0
            
        except Exception as e:
            logger.error(f"Failed to store whale transaction: {e}")
            raise DatabaseError(f"Failed to store whale transaction: {e}")
    
    async def store_buy_decision(self, decision: BuyDecision) -> bool:
        """Store buy decision"""
        try:
            doc = asdict(decision)
            doc['created_at'] = datetime.now()
            
            result = await self.buy_decisions.replace_one(
                {"id": decision.id},
                doc,
                upsert=True
            )
            
            return result.upserted_id is not None or result.modified_count > 0
            
        except Exception as e:
            logger.error(f"Failed to store buy decision: {e}")
            raise DatabaseError(f"Failed to store buy decision: {e}")
    
    async def store_position(self, position: Position) -> bool:
        """Store position"""
        try:
            doc = asdict(position)
            doc['updated_at'] = datetime.now()
            
            result = await self.positions.replace_one(
                {"id": position.id},
                doc,
                upsert=True
            )
            
            return result.upserted_id is not None or result.modified_count > 0
            
        except Exception as e:
            logger.error(f"Failed to store position: {e}")
            raise DatabaseError(f"Failed to store position: {e}")
    
    async def store_trade(self, trade_result: TradeExecution, trade_type: str, 
                         whale_transaction_id: str = "", position_id: str = "") -> bool:
        """Store trade execution record"""
        try:
            trade_doc = {
                "transaction_id": trade_result.transaction_id,
                "trade_type": trade_type,
                "token_address": trade_result.token_address,
                "input_amount": trade_result.input_amount,
                "output_amount": trade_result.output_amount,
                "price_per_token": trade_result.price_per_token,
                "slippage": trade_result.slippage,
                "fees": trade_result.fees,
                "success": trade_result.success,
                "timestamp": datetime.now().isoformat(),
                "whale_transaction_id": whale_transaction_id,
                "position_id": position_id,
                "error_message": trade_result.error_message,
                "created_at": datetime.now()
            }
            
            result = await self.trades.insert_one(trade_doc)
            return result.inserted_id is not None
            
        except Exception as e:
            logger.error(f"Failed to store trade: {e}")
            raise DatabaseError(f"Failed to store trade: {e}")
    
    async def get_open_positions(self) -> List[Position]:
        """Get all open positions"""
        try:
            cursor = self.positions.find({"status": "open"})
            positions = []
            
            async for doc in cursor:
                doc.pop('_id', None)
                doc.pop('updated_at', None)
                positions.append(Position(**doc))
            
            return positions
            
        except Exception as e:
            logger.error(f"Failed to get open positions: {e}")
            raise DatabaseError(f"Failed to get open positions: {e}")
    
    async def get_position_by_id(self, position_id: str) -> Optional[Position]:
        """Get position by ID"""
        try:
            doc = await self.positions.find_one({"id": position_id})
            if doc:
                doc.pop('_id', None)
                doc.pop('updated_at', None)
                return Position(**doc)
            return None
            
        except Exception as e:
            logger.error(f"Failed to get position: {e}")
            raise DatabaseError(f"Failed to get position: {e}")
    
    async def get_position_by_token(self, token_address: str) -> Optional[Position]:
        """Get open position by token address"""
        try:
            doc = await self.positions.find_one({
                "token_address": token_address,
                "status": "open"
            })
            if doc:
                doc.pop('_id', None)
                doc.pop('updated_at', None)
                return Position(**doc)
            return None
            
        except Exception as e:
            logger.error(f"Failed to get position by token: {e}")
            raise DatabaseError(f"Failed to get position by token: {e}")
    
    async def get_recent_decisions(self, limit: int = 50) -> List[Dict]:
        """Get recent buy decisions"""
        try:
            cursor = self.buy_decisions.find().sort("decision_timestamp", -1).limit(limit)
            decisions = []
            
            async for doc in cursor:
                doc.pop('_id', None)
                doc.pop('created_at', None)
                decisions.append(doc)
            
            return decisions
            
        except Exception as e:
            logger.error(f"Failed to get decisions: {e}")
            raise DatabaseError(f"Failed to get decisions: {e}")
    
    async def get_recent_trades(self, limit: int = 100) -> List[Dict]:
        """Get recent trades"""
        try:
            cursor = self.trades.find().sort("timestamp", -1).limit(limit)
            trades = []
            
            async for doc in cursor:
                doc.pop('_id', None)
                doc.pop('created_at', None)
                trades.append(doc)
            
            return trades
            
        except Exception as e:
            logger.error(f"Failed to get trades: {e}")
            raise DatabaseError(f"Failed to get trades: {e}")
    
    async def get_all_positions(self, status: Optional[str] = None) -> List[Dict]:
        """Get all positions, optionally filtered by status"""
        try:
            query = {}
            if status:
                query["status"] = status
                
            cursor = self.positions.find(query).sort("buy_timestamp", -1)
            positions = []
            
            async for doc in cursor:
                doc.pop('_id', None)
                doc.pop('updated_at', None)
                positions.append(doc)
            
            return positions
            
        except Exception as e:
            logger.error(f"Failed to get positions: {e}")
            raise DatabaseError(f"Failed to get positions: {e}")
    
    async def get_trading_stats(self) -> Dict:
        """Get trading statistics"""
        try:
            # Get position stats
            closed_positions = await self.positions.find({"status": "closed"}).to_list(None)
            
            total_profit = sum(pos.get("pnl_usd", 0) for pos in closed_positions if pos.get("pnl_usd", 0) > 0)
            total_loss = sum(pos.get("pnl_usd", 0) for pos in closed_positions if pos.get("pnl_usd", 0) < 0)
            
            winning_trades = len([pos for pos in closed_positions if pos.get("pnl_usd", 0) > 0])
            losing_trades = len([pos for pos in closed_positions if pos.get("pnl_usd", 0) < 0])
            total_trades = len(closed_positions)
            
            win_rate = (winning_trades / total_trades * 100) if total_trades > 0 else 0
            
            # Calculate other metrics
            open_positions_count = await self.positions.count_documents({"status": "open"})
            total_decisions = await self.buy_decisions.count_documents({})
            
            return {
                "total_decisions": total_decisions,
                "total_trades": total_trades,
                "open_positions": open_positions_count,
                "winning_trades": winning_trades,
                "losing_trades": losing_trades,
                "win_rate": win_rate,
                "total_profit": total_profit,
                "total_loss": total_loss,
                "net_pnl": total_profit + total_loss
            }
            
        except Exception as e:
            logger.error(f"Failed to get stats: {e}")
            raise DatabaseError(f"Failed to get trading stats: {e}")
    
    async def update_daily_stats(self, date: str, stats: Dict) -> bool:
        """Update daily statistics"""
        try:
            stats_doc = {
                "date": date,
                "updated_at": datetime.now(),
                **stats
            }
            
            result = await self.daily_stats.replace_one(
                {"date": date},
                stats_doc,
                upsert=True
            )
            
            return result.upserted_id is not None or result.modified_count > 0
            
        except Exception as e:
            logger.error(f"Failed to update daily stats: {e}")
            raise DatabaseError(f"Failed to update daily stats: {e}")
    
    async def store_alert(self, alert_type: str, title: str, message: str, data: Dict = None) -> bool:
        """Store alert message"""
        try:
            alert_doc = {
                "type": alert_type,
                "title": title,
                "message": message,
                "data": data or {},
                "timestamp": datetime.now().isoformat(),
                "created_at": datetime.now()
            }
            
            result = await self.alerts.insert_one(alert_doc)
            return result.inserted_id is not None
            
        except Exception as e:
            logger.error(f"Failed to store alert: {e}")
            raise DatabaseError(f"Failed to store alert: {e}")
    
    async def get_recent_alerts(self, limit: int = 50) -> List[Dict]:
        """Get recent alerts"""
        try:
            cursor = self.alerts.find().sort("timestamp", -1).limit(limit)
            alerts = []
            
            async for doc in cursor:
                doc.pop('_id', None)
                doc.pop('created_at', None)
                alerts.append(doc)
            
            return alerts
            
        except Exception as e:
            logger.error(f"Failed to get alerts: {e}")
            raise DatabaseError(f"Failed to get alerts: {e}")
    
    async def cleanup_old_data(self, days_to_keep: int = 30):
        """Clean up old data to prevent database bloat"""
        try:
            from datetime import timedelta
            cutoff_date = datetime.now() - timedelta(days=days_to_keep)
            
            # Remove old whale transactions
            whale_result = await self.whale_transactions.delete_many({
                "processed_at": {"$lt": cutoff_date}
            })
            
            # Remove old alerts
            alerts_result = await self.alerts.delete_many({
                "created_at": {"$lt": cutoff_date}
            })
            
            logger.info(f"Cleaned up {whale_result.deleted_count} whale transactions and {alerts_result.deleted_count} alerts")
            
        except Exception as e:
            logger.error(f"Failed to cleanup old data: {e}")
    
    async def get_database_info(self) -> Dict:
        """Get database information and statistics"""
        try:
            db_stats = await self.db.command("dbStats")
            
            # Get collection counts
            collections_info = {}
            for collection_name in [Collections.WHALE_TRANSACTIONS, Collections.BUY_DECISIONS, 
                                   Collections.POSITIONS, Collections.TRADES, Collections.DAILY_STATS]:
                count = await self.db[collection_name].count_documents({})
                collections_info[collection_name] = count
            
            return {
                "database_name": self.db_name,
                "collections": collections_info,
                "total_size_mb": db_stats.get("dataSize", 0) / (1024 * 1024),
                "storage_size_mb": db_stats.get("storageSize", 0) / (1024 * 1024),
                "indexes": db_stats.get("indexes", 0),
                "objects": db_stats.get("objects", 0)
            }
            
        except Exception as e:
            logger.error(f"Failed to get database info: {e}")
            return {}
    
    async def close(self):
        """Close database connection"""
        if self.client:
            self.client.close()
            logger.info("✅ MongoDB connection closed")
