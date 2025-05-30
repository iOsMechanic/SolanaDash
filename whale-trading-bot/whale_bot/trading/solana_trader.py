"""
Solana Trader
============
Handles Solana blockchain interactions and trading via Jupiter aggregator
"""

import asyncio
import aiohttp
import logging
import time
import base64
from typing import Dict, Optional

import base58
from solders.keypair import Keypair
from solders.pubkey import Pubkey
from solders.transaction import VersionedTransaction
from solana.rpc.async_api import AsyncClient
from solana.rpc.commitment import Confirmed, Finalized
from solana.rpc.types import TxOpts

from ..core.models import TradingConfig, TradeExecution
from ..core.exceptions import (
    SolanaRPCError, InsufficientFundsError, InvalidTokenError, 
    JupiterAPIError, TransactionError
)
from ..core.constants import TokenAddresses, APIEndpoints, TimeConstants

logger = logging.getLogger(__name__)


class SolanaTrader:
    """Handles Solana blockchain interactions and trading"""
    
    def __init__(self, private_key_base58: str, config: TradingConfig, 
                 rpc_url: str = "https://api.mainnet-beta.solana.com"):
        self.config = config
        self.rpc_url = rpc_url
        self.client = AsyncClient(rpc_url)
        
        # Setup wallet
        try:
            private_key_bytes = base58.b58decode(private_key_base58)
            self.keypair = Keypair.from_bytes(private_key_bytes)
            self.wallet_address = str(self.keypair.pubkey())
            logger.info(f"✅ Solana wallet initialized: {self.wallet_address}")
        except Exception as e:
            logger.error(f"❌ Failed to initialize wallet: {e}")
            raise InvalidTokenError(f"Invalid private key: {e}")
        
        # Jupiter API
        self.jupiter_api_url = APIEndpoints.JUPITER_V6
        
        # Rate limiting
        self.last_request_time = 0
        self.request_interval = 0.1  # 100ms between requests
        
        # Statistics
        self.successful_trades = 0
        self.failed_trades = 0
        self.total_fees_paid = 0.0
    
    async def get_sol_balance(self) -> float:
        """Get SOL balance of wallet"""
        try:
            response = await self.client.get_balance(self.keypair.pubkey())
            if response.value is not None:
                return float(response.value) / 1_000_000_000  # Convert lamports to SOL
            return 0.0
        except Exception as e:
            logger.error(f"Failed to get SOL balance: {e}")
            raise SolanaRPCError(f"Failed to get balance: {e}")
    
    async def get_token_balance(self, token_address: str) -> float:
        """Get token balance for specific token"""
        try:
            # Handle SOL balance
            if token_address == TokenAddresses.SOL:
                return await self.get_sol_balance()
            
            response = await self.client.get_token_accounts_by_owner(
                self.keypair.pubkey(),
                {"mint": Pubkey.from_string(token_address)}
            )
            
            if response.value:
                token_account = response.value[0].pubkey
                balance_response = await self.client.get_token_account_balance(token_account)
                if balance_response.value:
                    return float(balance_response.value.amount) / (10 ** balance_response.value.decimals)
            
            return 0.0
        except Exception as e:
            logger.error(f"Failed to get token balance for {token_address}: {e}")
            return 0.0
    
    async def get_token_accounts(self) -> Dict[str, float]:
        """Get all token accounts and balances"""
        try:
            balances = {}
            
            # Get SOL balance
            balances[TokenAddresses.SOL] = await self.get_sol_balance()
            
            # Get all token accounts
            response = await self.client.get_token_accounts_by_owner(
                self.keypair.pubkey(),
                {"programId": Pubkey.from_string("TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA")}
            )
            
            if response.value:
                for account_info in response.value:
                    try:
                        # Get balance for each token account
                        balance_response = await self.client.get_token_account_balance(account_info.pubkey)
                        if balance_response.value and float(balance_response.value.amount) > 0:
                            # Get mint address from account data
                            account_data = await self.client.get_account_info(account_info.pubkey)
                            if account_data.value and account_data.value.data:
                                # Parse token account data to get mint (simplified)
                                # In a full implementation, you'd properly parse the account data
                                mint = "unknown"
                                balance = float(balance_response.value.amount) / (10 ** balance_response.value.decimals)
                                balances[mint] = balance
                    except Exception as e:
                        logger.debug(f"Error getting token account balance: {e}")
                        continue
            
            return balances
            
        except Exception as e:
            logger.error(f"Failed to get token accounts: {e}")
            return {TokenAddresses.SOL: await self.get_sol_balance()}
    
    async def _rate_limit(self):
        """Apply rate limiting to requests"""
        current_time = time.time()
        time_since_last = current_time - self.last_request_time
        if time_since_last < self.request_interval:
            await asyncio.sleep(self.request_interval - time_since_last)
        self.last_request_time = time.time()
    
    async def _get_jupiter_quote(self, input_mint: str, output_mint: str, amount: int) -> Optional[Dict]:
        """Get swap quote from Jupiter"""
        try:
            await self._rate_limit()
            
            params = {
                "inputMint": input_mint,
                "outputMint": output_mint,
                "amount": amount,
                "slippageBps": self.config.slippage_bps,
                "onlyDirectRoutes": "false",
                "asLegacyTransaction": "false"
            }
            
            async with aiohttp.ClientSession() as session:
                url = f"{self.jupiter_api_url}{APIEndpoints.JUPITER_QUOTE}"
                async with session.get(url, params=params) as response:
                    if response.status == 200:
                        return await response.json()
                    else:
                        error_text = await response.text()
                        logger.error(f"Jupiter quote failed: {response.status} - {error_text}")
                        return None
                        
        except Exception as e:
            logger.error(f"Failed to get Jupiter quote: {e}")
            raise JupiterAPIError(f"Quote request failed: {e}")
    
    async def _get_jupiter_swap_transaction(self, quote: Dict) -> Optional[str]:
        """Get swap transaction from Jupiter"""
        try:
            await self._rate_limit()
            
            swap_request = {
                "quoteResponse": quote,
                "userPublicKey": self.wallet_address,
                "wrapAndUnwrapSol": True,
                "dynamicComputeUnitLimit": True,
                "prioritizationFeeLamports": int(self.config.priority_fee * 1_000_000_000)
            }
            
            async with aiohttp.ClientSession() as session:
                url = f"{self.jupiter_api_url}{APIEndpoints.JUPITER_SWAP}"
                async with session.post(
                    url,
                    json=swap_request,
                    headers={"Content-Type": "application/json"}
                ) as response:
                    if response.status == 200:
                        result = await response.json()
                        return result.get("swapTransaction")
                    else:
                        error_text = await response.text()
                        logger.error(f"Jupiter swap failed: {response.status} - {error_text}")
                        return None
                        
        except Exception as e:
            logger.error(f"Failed to get Jupiter swap transaction: {e}")
            raise JupiterAPIError(f"Swap transaction request failed: {e}")
    
    async def _execute_swap_transaction(self, transaction_data: str) -> Optional[str]:
        """Execute the swap transaction"""
        try:
            # Decode and sign transaction
            transaction_bytes = base64.b64decode(transaction_data)
            transaction = VersionedTransaction.from_bytes(transaction_bytes)
            
            # Sign transaction
            transaction.sign([self.keypair])
            
            # Send transaction
            opts = TxOpts(skip_preflight=False, preflight_commitment=Confirmed)
            response = await self.client.send_transaction(transaction, opts)
            
            if response.value:
                tx_id = str(response.value)
                logger.info(f"✅ Transaction sent: {tx_id}")
                
                # Wait for confirmation
                if await self._wait_for_confirmation(tx_id):
                    return tx_id
                else:
                    raise TransactionError("Transaction confirmation failed")
            else:
                raise TransactionError("Failed to send transaction")
                
        except Exception as e:
            logger.error(f"Failed to execute swap transaction: {e}")
            raise TransactionError(f"Transaction execution failed: {e}")
    
    async def _wait_for_confirmation(self, tx_id: str, timeout: int = TimeConstants.TRANSACTION_TIMEOUT) -> bool:
        """Wait for transaction confirmation"""
        try:
            start_time = time.time()
            while time.time() - start_time < timeout:
                response = await self.client.get_signature_statuses([tx_id])
                if response.value and response.value[0]:
                    status = response.value[0]
                    if status.confirmation_status:
                        if status.err:
                            logger.error(f"❌ Transaction failed: {status.err}")
                            return False
                        else:
                            logger.info(f"✅ Transaction confirmed: {tx_id}")
                            return True
                
                await asyncio.sleep(2)
            
            logger.warning(f"⏰ Transaction confirmation timeout: {tx_id}")
            return False
            
        except Exception as e:
            logger.error(f"Failed to wait for confirmation: {e}")
            return False
    
    async def buy_token_with_sol(self, token_address: str, sol_amount: float) -> TradeExecution:
        """Buy token with SOL"""
        try:
            logger.info(f"🛒 Buying {sol_amount} SOL worth of {token_address}")
            
            # Validate inputs
            if sol_amount <= 0:
                raise ValueError("SOL amount must be positive")
            
            if not token_address:
                raise ValueError("Token address cannot be empty")
            
            # Check SOL balance
            sol_balance = await self.get_sol_balance()
            if sol_balance < sol_amount + self.config.priority_fee:
                raise InsufficientFundsError(
                    f"Insufficient SOL balance: {sol_balance:.4f} < {sol_amount + self.config.priority_fee:.4f}"
                )
            
            sol_lamports = int(sol_amount * 1_000_000_000)
            
            # Get quote from Jupiter
            quote = await self._get_jupiter_quote(
                input_mint=TokenAddresses.SOL,
                output_mint=token_address,
                amount=sol_lamports
            )
            
            if not quote:
                return TradeExecution(
                    success=False, transaction_id="", token_address=token_address,
                    input_amount=sol_amount, output_amount=0, price_per_token=0,
                    slippage=0, fees=0, error_message="Failed to get quote from Jupiter"
                )
            
            output_amount = float(quote["outAmount"])
            price_impact = float(quote.get("priceImpactPct", 0))
            
            logger.info(f"   📊 Quote: {output_amount} tokens, Price Impact: {price_impact:.2f}%")
            
            # Get and execute swap transaction
            swap_transaction = await self._get_jupiter_swap_transaction(quote)
            if not swap_transaction:
                return TradeExecution(
                    success=False, transaction_id="", token_address=token_address,
                    input_amount=sol_amount, output_amount=0, price_per_token=0,
                    slippage=price_impact, fees=0, error_message="Failed to get swap transaction"
                )
            
            tx_id = await self._execute_swap_transaction(swap_transaction)
            if not tx_id:
                return TradeExecution(
                    success=False, transaction_id="", token_address=token_address,
                    input_amount=sol_amount, output_amount=0, price_per_token=0,
                    slippage=price_impact, fees=0, error_message="Transaction execution failed"
                )
            
            # Calculate metrics
            token_decimals = 6  # Most tokens use 6 decimals, could be made configurable
            actual_token_amount = output_amount / (10 ** token_decimals)
            price_per_token = sol_amount / actual_token_amount if actual_token_amount > 0 else 0
            
            # Update statistics
            self.successful_trades += 1
            self.total_fees_paid += self.config.priority_fee
            
            logger.info(f"✅ Buy successful: {actual_token_amount:.6f} tokens at {price_per_token:.8f} SOL each")
            
            return TradeExecution(
                success=True, transaction_id=tx_id, token_address=token_address,
                input_amount=sol_amount, output_amount=actual_token_amount,
                price_per_token=price_per_token, slippage=price_impact,
                fees=self.config.priority_fee, error_message=""
            )
            
        except (InsufficientFundsError, ValueError) as e:
            logger.error(f"❌ Buy validation failed: {e}")
            self.failed_trades += 1
            return TradeExecution(
                success=False, transaction_id="", token_address=token_address,
                input_amount=sol_amount, output_amount=0, price_per_token=0,
                slippage=0, fees=0, error_message=str(e)
            )
        except Exception as e:
            logger.error(f"❌ Buy token failed: {e}")
            self.failed_trades += 1
            return TradeExecution(
                success=False, transaction_id="", token_address=token_address,
                input_amount=sol_amount, output_amount=0, price_per_token=0,
                slippage=0, fees=0, error_message=str(e)
            )
    
    async def sell_token_for_sol(self, token_address: str, token_amount: float) -> TradeExecution:
        """Sell token for SOL"""
        try:
            logger.info(f"💰 Selling {token_amount} of {token_address}")
            
            # Validate inputs
            if token_amount <= 0:
                raise ValueError("Token amount must be positive")
            
            if not token_address:
                raise ValueError("Token address cannot be empty")
            
            # Check token balance
            token_balance = await self.get_token_balance(token_address)
            if token_balance < token_amount:
                raise InsufficientFundsError(
                    f"Insufficient token balance: {token_balance:.6f} < {token_amount:.6f}"
                )
            
            token_decimals = 6  # Most tokens use 6 decimals
            token_lamports = int(token_amount * (10 ** token_decimals))
            
            # Get quote from Jupiter
            quote = await self._get_jupiter_quote(
                input_mint=token_address,
                output_mint=TokenAddresses.SOL,
                amount=token_lamports
            )
            
            if not quote:
                return TradeExecution(
                    success=False, transaction_id="", token_address=token_address,
                    input_amount=token_amount, output_amount=0, price_per_token=0,
                    slippage=0, fees=0, error_message="Failed to get sell quote from Jupiter"
                )
            
            sol_output = float(quote["outAmount"]) / 1_000_000_000  # Convert lamports to SOL
            price_impact = float(quote.get("priceImpactPct", 0))
            
            logger.info(f"   📊 Sell Quote: {sol_output:.6f} SOL, Price Impact: {price_impact:.2f}%")
            
            # Get and execute swap transaction
            swap_transaction = await self._get_jupiter_swap_transaction(quote)
            if not swap_transaction:
                return TradeExecution(
                    success=False, transaction_id="", token_address=token_address,
                    input_amount=token_amount, output_amount=0, price_per_token=0,
                    slippage=price_impact, fees=0, error_message="Failed to get sell swap transaction"
                )
            
            tx_id = await self._execute_swap_transaction(swap_transaction)
            if not tx_id:
                return TradeExecution(
                    success=False, transaction_id="", token_address=token_address,
                    input_amount=token_amount, output_amount=0, price_per_token=0,
                    slippage=price_impact, fees=0, error_message="Sell transaction execution failed"
                )
            
            # Calculate price per token
            price_per_token = sol_output / token_amount if token_amount > 0 else 0
            
            # Update statistics
            self.successful_trades += 1
            self.total_fees_paid += self.config.priority_fee
            
            logger.info(f"✅ Sell successful: {sol_output:.6f} SOL at {price_per_token:.8f} SOL per token")
            
            return TradeExecution(
                success=True, transaction_id=tx_id, token_address=token_address,
                input_amount=token_amount, output_amount=sol_output,
                price_per_token=price_per_token, slippage=price_impact,
                fees=self.config.priority_fee, error_message=""
            )
            
        except (InsufficientFundsError, ValueError) as e:
            logger.error(f"❌ Sell validation failed: {e}")
            self.failed_trades += 1
            return TradeExecution(
                success=False, transaction_id="", token_address=token_address,
                input_amount=token_amount, output_amount=0, price_per_token=0,
                slippage=0, fees=0, error_message=str(e)
            )
        except Exception as e:
            logger.error(f"❌ Sell token failed: {e}")
            self.failed_trades += 1
            return TradeExecution(
                success=False, transaction_id="", token_address=token_address,
                input_amount=token_amount, output_amount=0, price_per_token=0,
                slippage=0, fees=0, error_message=str(e)
            )
    
    async def get_trading_stats(self) -> Dict:
        """Get trading statistics"""
        try:
            sol_balance = await self.get_sol_balance()
            return {
                "wallet_address": self.wallet_address,
                "sol_balance": sol_balance,
                "successful_trades": self.successful_trades,
                "failed_trades": self.failed_trades,
                "total_trades": self.successful_trades + self.failed_trades,
                "success_rate": (self.successful_trades / max(1, self.successful_trades + self.failed_trades)) * 100,
                "total_fees_paid": self.total_fees_paid,
                "sol_per_trade": self.config.sol_per_trade,
                "max_slippage_bps": self.config.slippage_bps
            }
        except Exception as e:
            logger.error(f"Failed to get trading stats: {e}")
            return {}
    
    async def validate_token_address(self, token_address: str) -> bool:
        """Validate if token address is valid and tradeable"""
        try:
            # Try to get a small quote to see if token is tradeable
            quote = await self._get_jupiter_quote(
                input_mint=TokenAddresses.SOL,
                output_mint=token_address,
                amount=1000000  # 0.001 SOL
            )
            return quote is not None
        except Exception as e:
            logger.error(f"Token validation failed: {e}")
            return False
    
    async def close(self):
        """Close Solana client and cleanup resources"""
        try:
            await self.client.close()
            logger.info("✅ Solana client closed")
        except Exception as e:
            logger.error(f"Error closing Solana client: {e}")
