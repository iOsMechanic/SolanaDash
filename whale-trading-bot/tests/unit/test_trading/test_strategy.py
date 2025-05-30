import pytest
from whale_bot.trading.strategy import TradingStrategy
from whale_bot.core.models import WhaleTransaction, TradingConfig

@pytest.mark.asyncio
async def test_should_buy_valid_transaction(trading_config):
    strategy = TradingStrategy(trading_config)
    
    transaction = WhaleTransaction(
        id="test",
        timestamp="2024-01-01T00:00:00",
        transaction_type="buy",
        token_id="test_token",
        token_name="Test Token",
        token_symbol="TEST",
        token_address="test_address",
        trade_size="large",
        trade_amount=2000.0,
        win_rate=75.0,
        token_market_cap=50_000_000,
        rugcheck_status="good",
        is_token_first_seen=False
    )
    
    should_buy, reason = await strategy.should_buy(transaction, {}, 1.0)
    assert should_buy == True
    assert "criteria passed" in reason.lower()
