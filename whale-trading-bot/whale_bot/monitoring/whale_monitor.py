"""
Whale Monitor
============
Monitors whale transactions from AssetDash API and generates demo data
"""

import asyncio
import aiohttp
import logging
import time
import random
from datetime import datetime, timedelta
from typing import Dict, List, Optional

from ..core.models import WhaleTransaction
from ..core.exceptions import WhaleDataError, APIError
from ..core.constants import APIEndpoints, RateLimits, TimeConstants

logger = logging.getLogger(__name__)


class WhaleMonitor:
    """Monitors whale transactions from AssetDash API"""
    
    def __init__(self, api_token: str = ""):
        self.api_base_url = APIEndpoints.ASSETDASH_BASE
        self.api_token = api_token
        self.session = None
        self.demo_mode = not bool(api_token)
        
        # Rate limiting
        self.last_request_time = 0
        self.request_interval = 60 / RateLimits.ASSETDASH_RPM  # Convert RPM to seconds between requests
        
        # Statistics
        self.successful_requests = 0
        self.api_errors = 0
        self.total_transactions_fetched = 0
        
        # Demo data management
        self.demo_counter = 0
        
        logger.info(f"🐋 Whale Monitor initialized (Demo: {self.demo_mode})")
        if self.demo_mode:
            logger.info("💡 Set ASSETDASH_TOKEN environment variable for live data")
    
    async def initialize(self):
        """Initialize HTTP session and test API connection"""
        try:
            headers = {
                "Content-Type": "application/json",
                "User-Agent": "ModularTradingBot/1.0"
            }
            
            if self.api_token:
                headers["Authorization"] = f"Bearer {self.api_token}"
            
            timeout = aiohttp.ClientTimeout(total=TimeConstants.API_TIMEOUT)
            self.session = aiohttp.ClientSession(headers=headers, timeout=timeout)
            
            if not self.demo_mode:
                await self._test_api_connection()
            
            logger.info("✅ Whale Monitor initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize whale monitor: {e}")
            raise APIError(f"Initialization failed: {e}")
    
    async def _test_api_connection(self):
        """Test API connection with AssetDash"""
        try:
            logger.info("🔗 Testing AssetDash API connection...")
            
            url = f"{self.api_base_url}{APIEndpoints.WHALE_TRANSACTIONS}"
            params = {"page": 1, "limit": 1}
            
            async with self.session.get(url, params=params) as response:
                if response.status == 200:
                    logger.info("✅ AssetDash API connection successful")
                    self.successful_requests += 1
                elif response.status == 401:
                    logger.error("❌ AssetDash API authentication failed - check your token")
                    logger.error("💡 Get your token from: https://app.assetdash.com/")
                    self.demo_mode = True
                elif response.status == 429:
                    logger.warning("⚠️  API rate limited - will adjust request frequency")
                    self.request_interval *= 2  # Double the interval
                else:
                    logger.warning(f"⚠️  AssetDash API returned status {response.status}")
                    self.api_errors += 1
                    
        except Exception as e:
            logger.error(f"❌ Failed to connect to AssetDash API: {e}")
            logger.info("📊 Switching to demo mode")
            self.demo_mode = True
    
    async def fetch_whale_transactions(self, limit: int = 20, page: int = 1) -> List[WhaleTransaction]:
        """
        Fetch whale transactions from API or generate demo data
        
        Args:
            limit: Number of transactions to fetch
            page: Page number for pagination
            
        Returns:
            List of WhaleTransaction objects
        """
        try:
            if self.demo_mode:
                return await self._generate_demo_transactions(limit)
            
            return await self._fetch_real_transactions(limit, page)
            
        except Exception as e:
            logger.error(f"Failed to fetch whale transactions: {e}")
            # Fallback to demo data on error
            return await self._generate_demo_transactions(limit)
    
    async def _fetch_real_transactions(self, limit: int, page: int) -> List[WhaleTransaction]:
        """Fetch real transactions from AssetDash API"""
        try:
            # Apply rate limiting
            await self._apply_rate_limit()
            
            url = f"{self.api_base_url}{APIEndpoints.WHALE_TRANSACTIONS}"
            params = {
                "page": page,
                "limit": limit
            }
            
            async with self.session.get(url, params=params) as response:
                self.last_request_time = time.time()
                
                if response.status == 200:
                    data = await response.json()
                    transactions = []
                    
                    for tx_data in data.get("transactions", []):
                        try:
                            transaction = self._parse_transaction(tx_data)
                            transactions.append(transaction)
                        except Exception as e:
                            logger.warning(f"Failed to parse transaction: {e}")
                            continue
                    
                    self.successful_requests += 1
                    self.total_transactions_fetched += len(transactions)
                    logger.info(f"✅ Fetched {len(transactions)} whale transactions from API")
                    return transactions
                    
                elif response.status == 401:
                    logger.error("🔑 API authentication failed - switching to demo mode")
                    self.demo_mode = True
                    return await self._generate_demo_transactions(limit)
                    
                elif response.status == 429:
                    logger.warning("⚠️  Rate limited - increasing request interval")
                    self.request_interval *= 1.5
                    self.api_errors += 1
                    return []
                    
                else:
                    self.api_errors += 1
                    error_text = await response.text()
                    logger.error(f"❌ API request failed: {response.status} - {error_text}")
                    return []
                    
        except asyncio.TimeoutError:
            logger.error("❌ API request timed out")
            self.api_errors += 1
            return []
        except Exception as e:
            logger.error(f"❌ API request failed: {e}")
            self.api_errors += 1
            raise WhaleDataError(f"Failed to fetch whale transactions: {e}")
    
    async def _generate_demo_transactions(self, limit: int) -> List[WhaleTransaction]:
        """Generate realistic demo whale transactions for testing"""
        try:
            self.demo_counter += 1
            
            demo_tokens = [
                {
                    'symbol': 'BONK', 
                    'name': 'Bonk', 
                    'address': 'DezXAZ8z7PnrnRJjz3wXBoRgixCa6xjnB7YaB1pPB263'
                },
                {
                    'symbol': 'WIF', 
                    'name': 'dogwifhat', 
                    'address': 'EKpQGSJtjMFqKZ9KQanSqYXRcF8fBopzLHYxdM65zcjm'
                },
                {
                    'symbol': 'POPCAT', 
                    'name': 'Popcat', 
                    'address': '7GCihgDB8fe6KNjn2MYtkzZcRjQy3t9GHdC8uHYmW2hr'
                },
                {
                    'symbol': 'MEW', 
                    'name': 'cat in a dogs world', 
                    'address': 'MEW1gQWJ3nEXg2qgNMZT4PoG9JzfMWuEYqKV3tFH1dJv'
                },
                {
                    'symbol': 'PEPE', 
                    'name': 'Pepe', 
                    'address': '6GCihgDB8fe6KNjn2MYtkzZcRjQy3t9GHdC8uHYmW2hr'
                },
                {
                    'symbol': 'JUP', 
                    'name': 'Jupiter', 
                    'address': 'JUPyiwrYJFskUPiHa7hkeR8VUtAeFoSYbKedZNsDvCN'
                }
            ]
            
            transactions = []
            num_transactions = min(random.randint(2, 6), limit)  # Generate 2-6 transactions
            
            for i in range(num_transactions):
                token = random.choice(demo_tokens)
                
                # Create realistic distribution of transaction quality
                transaction_quality = random.random()
                
                if transaction_quality > 0.7:  # 30% high quality (likely to trigger buys)
                    win_rate = random.randint(70, 95)
                    trade_amount = random.randint(2000, 10000)
                    market_cap = random.randint(5_000_000, 80_000_000)
                    rugcheck_status = random.choice(['good', 'good', 'warning'])  # Weighted towards good
                    trade_size = random.choice(['medium', 'large', 'large'])  # Weighted towards larger
                    
                elif transaction_quality > 0.4:  # 30% medium quality
                    win_rate = random.randint(50, 75)
                    trade_amount = random.randint(800, 3000)
                    market_cap = random.randint(10_000_000, 150_000_000)
                    rugcheck_status = random.choice(['good', 'warning', 'warning'])
                    trade_size = random.choice(['small', 'medium', 'medium'])
                    
                else:  # 40% low quality (likely to be rejected)
                    win_rate = random.randint(20, 60)
                    trade_amount = random.randint(100, 1200)
                    market_cap = random.randint(1_000_000, 200_000_000)
                    rugcheck_status = random.choice(['warning', 'danger', 'unknown'])
                    trade_size = random.choice(['small', 'small', 'medium'])
                
                # Ensure some transactions are sells to test filtering
                transaction_type = "buy" if random.random() > 0.2 else "sell"  # 80% buys, 20% sells
                
                transaction = WhaleTransaction(
                    id=f"demo_{self.demo_counter}_{i}_{int(time.time())}",
                    timestamp=self._generate_realistic_timestamp(),
                    transaction_type=transaction_type,
                    token_id=f"token_{token['symbol'].lower()}_{i}",
                    token_name=token['name'],
                    token_symbol=token['symbol'],
                    token_address=token['address'],
                    trade_size=trade_size,
                    trade_amount=trade_amount,
                    win_rate=win_rate,
                    token_market_cap=market_cap,
                    rugcheck_status=rugcheck_status,
                    is_token_first_seen=random.choice([True, False]),
                    logo_url=f"https://example.com/logos/{token['symbol'].lower()}.png"
                )
                
                transactions.append(transaction)
            
            self.total_transactions_fetched += len(transactions)
            logger.info(f"🎯 Generated {len(transactions)} realistic demo transactions")
            
            # Log quality distribution for debugging
            quality_info = self._analyze_demo_quality(transactions)
            logger.debug(f"Demo quality distribution: {quality_info}")
            
            return transactions
            
        except Exception as e:
            logger.error(f"Failed to generate demo transactions: {e}")
            return []
    
    def _parse_transaction(self, tx_data: Dict) -> WhaleTransaction:
        """Parse transaction from AssetDash API response"""
        try:
            swap_token = tx_data.get("swap_token", {})
            
            return WhaleTransaction(
                id=tx_data.get("id", ""),
                timestamp=tx_data.get("timestamp", ""),
                transaction_type=tx_data.get("transaction_type", ""),
                token_id=swap_token.get("id", ""),
                token_name=swap_token.get("name", ""),
                token_symbol=swap_token.get("symbol", ""),
                token_address=swap_token.get("token_address", ""),
                trade_size=tx_data.get("trade_size", ""),
                trade_amount=float(tx_data.get("trade_amount_rounded", 0)),
                win_rate=float(tx_data.get("win_rate", 0)),
                token_market_cap=float(tx_data.get("token_market_cap", 0)),
                rugcheck_status=swap_token.get("rugcheck_status", "unknown"),
                is_token_first_seen=bool(tx_data.get("is_token_first_seen", False)),
                logo_url=swap_token.get("logo_url", "")
            )
            
        except Exception as e:
            logger.error(f"Failed to parse transaction data: {e}")
            raise WhaleDataError(f"Transaction parsing failed: {e}")
    
    def _generate_realistic_timestamp(self) -> str:
        """Generate realistic timestamp (recent past)"""
        # Generate timestamp between 1 minute and 6 hours ago
        minutes_ago = random.randint(1, 360)
        timestamp = datetime.now() - timedelta(minutes=minutes_ago)
        return timestamp.isoformat()
    
    def _analyze_demo_quality(self, transactions: List[WhaleTransaction]) -> Dict:
        """Analyze the quality distribution of demo transactions"""
        try:
            total = len(transactions)
            if total == 0:
                return {}
            
            high_quality = len([tx for tx in transactions 
                              if tx.win_rate >= 70 and tx.trade_amount >= 2000 
                              and tx.rugcheck_status == 'good' and tx.transaction_type == 'buy'])
            
            medium_quality = len([tx for tx in transactions 
                                if 50 <= tx.win_rate < 70 and tx.transaction_type == 'buy'])
            
            buys = len([tx for tx in transactions if tx.transaction_type == 'buy'])
            
            return {
                "total": total,
                "high_quality": high_quality,
                "medium_quality": medium_quality,
                "buy_transactions": buys,
                "estimated_triggers": high_quality  # Rough estimate of likely buy signals
            }
            
        except Exception as e:
            logger.error(f"Error analyzing demo quality: {e}")
            return {}
    
    async def _apply_rate_limit(self):
        """Apply rate limiting to API requests"""
        try:
            current_time = time.time()
            time_since_last = current_time - self.last_request_time
            
            if time_since_last < self.request_interval:
                sleep_time = self.request_interval - time_since_last
                logger.debug(f"Rate limiting: sleeping {sleep_time:.2f}s")
                await asyncio.sleep(sleep_time)
                
        except Exception as e:
            logger.error(f"Error in rate limiting: {e}")
    
    async def get_trending_tokens(self, limit: int = 50) -> List[Dict]:
        """
        Get trending tokens from AssetDash (if available)
        
        Args:
            limit: Number of trending tokens to fetch
            
        Returns:
            List of trending token data
        """
        try:
            if self.demo_mode:
                return self._generate_demo_trending_tokens(limit)
            
            await self._apply_rate_limit()
            
            url = f"{self.api_base_url}{APIEndpoints.TRENDING_TOKENS}"
            params = {"limit": limit}
            
            async with self.session.get(url, params=params) as response:
                if response.status == 200:
                    data = await response.json()
                    return data.get("items", [])
                else:
                    logger.warning(f"Failed to get trending tokens: {response.status}")
                    return []
                    
        except Exception as e:
            logger.error(f"Failed to get trending tokens: {e}")
            return []
    
    def _generate_demo_trending_tokens(self, limit: int) -> List[Dict]:
        """Generate demo trending tokens data"""
        demo_tokens = [
            {"symbol": "BONK", "name": "Bonk", "price_change_24h": 15.2},
            {"symbol": "WIF", "name": "dogwifhat", "price_change_24h": 8.7},
            {"symbol": "POPCAT", "name": "Popcat", "price_change_24h": -3.1},
            {"symbol": "MEW", "name": "cat in a dogs world", "price_change_24h": 22.5},
            {"symbol": "JUP", "name": "Jupiter", "price_change_24h": 5.8}
        ]
        
        return demo_tokens[:limit]
    
    def get_monitor_stats(self) -> Dict:
        """Get whale monitor statistics"""
        try:
            uptime_hours = 0
            if hasattr(self, '_start_time'):
                uptime_hours = (time.time() - self._start_time) / 3600
            
            success_rate = 0
            total_requests = self.successful_requests + self.api_errors
            if total_requests > 0:
                success_rate = (self.successful_requests / total_requests) * 100
            
            return {
                "demo_mode": self.demo_mode,
                "successful_requests": self.successful_requests,
                "api_errors": self.api_errors,
                "total_requests": total_requests,
                "success_rate": success_rate,
                "total_transactions_fetched": self.total_transactions_fetched,
                "current_request_interval": self.request_interval,
                "uptime_hours": uptime_hours
            }
        except Exception as e:
            logger.error(f"Error getting monitor stats: {e}")
            return {}
    
    async def test_connection(self) -> bool:
        """Test API connection and return status"""
        try:
            if self.demo_mode:
                return True
            
            await self._test_api_connection()
            return self.successful_requests > self.api_errors
            
        except Exception as e:
            logger.error(f"Connection test failed: {e}")
            return False
    
    def reset_stats(self):
        """Reset monitoring statistics"""
        self.successful_requests = 0
        self.api_errors = 0
        self.total_transactions_fetched = 0
        self.demo_counter = 0
        self._start_time = time.time()
        logger.info("✅ Whale monitor statistics reset")
    
    async def close(self):
        """Close HTTP session and cleanup resources"""
        try:
            if self.session:
                await self.session.close()
                logger.info("✅ Whale Monitor HTTP session closed")
        except Exception as e:
            logger.error(f"Error closing whale monitor: {e}")
