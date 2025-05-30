import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock
from whale_bot.core.models import TradingConfig

@pytest.fixture
def trading_config():
    return TradingConfig()

@pytest.fixture
def mock_db():
    return AsyncMock()

@pytest.fixture
def mock_trader():
    return AsyncMock()

@pytest.fixture
def event_loop():
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()
