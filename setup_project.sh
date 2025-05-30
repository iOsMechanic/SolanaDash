#!/bin/bash
# Setup script for whale trading bot project structure

echo "Setting up Whale Trading Bot Project Structure"
echo "=================================================="

# Create main project directory
PROJECT_NAME="whale-trading-bot"
mkdir -p $PROJECT_NAME
cd $PROJECT_NAME

echo " Creating folder structure..."

# Create main directories
mkdir -p scripts
mkdir -p config
mkdir -p whale_bot/{core,database/{migrations,models},trading,monitoring,api/{routes,middleware},utils}
mkdir -p tests/{unit/{test_trading,test_database,test_monitoring},integration,fixtures}
mkdir -p docs
mkdir -p frontend/{src/{components,pages,utils},public}
mkdir -p deployment/{docker,kubernetes,terraform}
mkdir -p logs

echo "Creating __init__.py files..."

# Create __init__.py files
touch scripts/__init__.py
touch config/__init__.py
touch whale_bot/__init__.py
touch whale_bot/core/__init__.py./se
touch whale_bot/database/__init__.py
touch whale_bot/database/migrations/__init__.py
touch whale_bot/database/models/__init__.py
touch whale_bot/trading/__init__.py
touch whale_bot/monitoring/__init__.py
touch whale_bot/api/__init__.py
touch whale_bot/api/routes/__init__.py
touch whale_bot/api/middleware/__init__.py
touch whale_bot/utils/__init__.py
touch tests/__init__.py
touch tests/unit/__init__.py
touch tests/unit/test_trading/__init__.py
touch tests/unit/test_database/__init__.py
touch tests/unit/test_monitoring/__init__.py
touch tests/integration/__init__.py
touch tests/fixtures/__init__.py

echo "⚙️ Creating configuration files..."

# Create requirements.txt
cat > requirements.txt << 'EOF'
# Core dependencies
aiohttp==3.9.1
motor==3.3.2
pymongo==4.6.1

# Solana dependencies
solders==0.20.1
solana==0.32.0
base58==2.1.1

# Data processing
pandas==2.1.4
numpy==1.25.2

# Configuration
python-dotenv==1.0.0
pydantic==2.5.2
pydantic-settings==2.1.0

# Testing
pytest==7.4.3
pytest-asyncio==0.21.1
pytest-mock==3.12.0
pytest-cov==4.1.0

# Development
black==23.12.1
flake8==6.1.0
mypy==1.8.0
pre-commit==3.6.0

# Monitoring
prometheus-client==0.19.0
structlog==23.2.0
EOF

# Create .env.example
cat > .env.example << 'EOF'
# Required - Solana wallet private key in base58 format
SOLANA_PRIVATE_KEY=your_base58_private_key_here

# Optional - Trading configuration
SOL_PER_TRADE=0.1
TAKE_PROFIT_PERCENTAGE=50.0
STOP_LOSS_PERCENTAGE=20.0
MAX_POSITIONS=5

# Optional - Strategy parameters
MIN_WIN_RATE=60.0
MIN_TRADE_AMOUNT=1000.0
MAX_MARKET_CAP=100000000.0

# Optional - Database configuration
MONGODB_URI=mongodb://localhost:27017/
MONGODB_DATABASE=whale_trading

# Optional - API configuration
ASSETDASH_TOKEN=your_assetdash_api_token
API_PORT=8080
API_HOST=localhost

# Optional - Solana RPC
SOLANA_RPC_URL=https://api.mainnet-beta.solana.com

# Optional - Logging
LOG_LEVEL=INFO
LOG_FILE=logs/whale_bot.log
EOF

# Create .gitignore
cat > .gitignore << 'EOF'
# Python
__pycache__/
*.py[cod]
*$py.class
*.so
.Python
build/
develop-eggs/
dist/
downloads/
eggs/
.eggs/
lib/
lib64/
parts/
sdist/
var/
wheels/
*.egg-info/
.installed.cfg
*.egg

# Virtual environments
venv/
env/
ENV/

# Environment variables
.env
.env.local
.env.production

# IDE
.vscode/
.idea/
*.swp
*.swo

# Logs
logs/
*.log

# Database
*.db
*.sqlite3

# OS
.DS_Store
Thumbs.db

# Test coverage
.coverage
htmlcov/
.pytest_cache/

# Secrets
*.pem
*.key
wallet.json
private_keys/

# Node modules
node_modules/
npm-debug.log*
yarn-debug.log*
yarn-error.log*
EOF

# Create setup.py
cat > setup.py << 'EOF'
from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

with open("requirements.txt", "r", encoding="utf-8") as fh:
    requirements = [line.strip() for line in fh if line.strip() and not line.startswith("#")]

setup(
    name="whale-trading-bot",
    version="1.0.0",
    author="Your Name",
    author_email="your.email@example.com",
    description="Automated Solana trading bot that follows whale transactions",
    long_description=long_description,
    long_description_content_type="text/markdown",
    packages=find_packages(),
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Financial and Insurance Industry",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
    ],
    python_requires=">=3.9",
    install_requires=requirements,
    entry_points={
        "console_scripts": [
            "whale-bot=whale_bot.main:main",
        ],
    },
)
EOF

# Create Dockerfile
cat > Dockerfile << 'EOF'
FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Create logs directory
RUN mkdir -p logs

# Install package
RUN pip install -e .

# Expose API port
EXPOSE 8080

# Default command
CMD ["python", "-m", "whale_bot.main"]
EOF

# Create docker-compose.yml
cat > docker-compose.yml << 'EOF'
version: '3.8'

services:
  mongodb:
    image: mongo:7.0
    container_name: whale_bot_mongodb
    restart: unless-stopped
    ports:
      - "27017:27017"
    environment:
      MONGO_INITDB_ROOT_USERNAME: admin
      MONGO_INITDB_ROOT_PASSWORD: password123
      MONGO_INITDB_DATABASE: whale_trading
    volumes:
      - mongodb_data:/data/db
    networks:
      - whale_bot_network

  whale_bot:
    build: .
    container_name: whale_trading_bot
    restart: unless-stopped
    depends_on:
      - mongodb
    environment:
      - MONGODB_URI=mongodb://admin:password123@mongodb:27017/whale_trading?authSource=admin
    env_file:
      - .env
    volumes:
      - ./logs:/app/logs
    networks:
      - whale_bot_network

volumes:
  mongodb_data:

networks:
  whale_bot_network:
    driver: bridge
EOF

# Create basic README.md
cat > README.md << 'EOF'
#  Whale Trading Bot

Automated Solana trading bot that follows whale transactions and executes trades based on successful patterns.

## ✨ Features

-  **Whale Transaction Monitoring** - Tracks large trades from successful wallets
-  **Automated Trading** - Executes buy/sell orders on Solana via Jupiter
-  **Position Management** - Manages multiple positions with P&L tracking
-  **Risk Management** - Stop losses, take profits, position limits
-  **MongoDB Storage** - Persistent data storage for trades and positions
-  **Web API** - RESTful API for monitoring and control
-  **Real-time Monitoring** - Live position tracking and alerts

## 🚀 Quick Start

1. **Clone and setup:**
   ```bash
   git clone <your-repo>
   cd whale-trading-bot
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   pip install -r requirements.txt
   ```

2. **Configure environment:**
   ```bash
   cp .env.example .env
   # Edit .env with your settings
   ```

3. **Setup wallet:**
   ```bash
   python scripts/setup_wallet.py
   ```

4. **Start MongoDB:**
   ```bash
   docker-compose up -d mongodb
   ```

5. **Run the bot:**
   ```bash
   python scripts/run_bot.py
   ```

## 📚 Documentation

- [Setup Guide](docs/SETUP.md)
- [API Documentation](docs/API.md)
- [Trading Strategy](docs/TRADING_STRATEGY.md)
- [Deployment Guide](docs/DEPLOYMENT.md)

## Disclaimer

This software is for educational purposes. Trading cryptocurrencies involves substantial risk. Only use funds you can afford to lose.
EOF

echo "📚 Creating documentation files..."

# Create docs
mkdir -p docs

cat > docs/SETUP.md << 'EOF'
# Setup Guide

## Prerequisites

- Python 3.9+
- MongoDB
- Solana wallet with SOL

## Installation

1. Clone repository
2. Install dependencies: `pip install -r requirements.txt`
3. Configure `.env` file
4. Setup wallet: `python scripts/setup_wallet.py`
5. Start services: `docker-compose up -d`
6. Run bot: `python scripts/run_bot.py`

## Configuration

See `.env.example` for all available options.
EOF

cat > docs/API.md << 'EOF'
# API Documentation

## Endpoints

### GET /api/positions
Get current trading positions

### GET /api/trades  
Get trade history

### GET /api/stats
Get trading statistics

### GET /api/wallet
Get wallet information

### GET /api/health
Health check
EOF

echo "🧪 Creating test files..."

# Create conftest.py
cat > tests/conftest.py << 'EOF'
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
EOF

# Create sample test
cat > tests/unit/test_trading/test_strategy.py << 'EOF'
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
EOF

echo "🔧 Creating utility scripts..."

# Create run script
cat > scripts/run_bot.py << 'EOF'
#!/usr/bin/env python3
"""Main entry point for running the whale trading bot"""

import asyncio
import sys
import os
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

async def main():
    try:
        from whale_bot.main import ModularTradingBot
        
        bot = ModularTradingBot()
        await bot.initialize()
        await bot.run_trading_loop()
        
    except KeyboardInterrupt:
        print("👋 Bot stopped by user")
    except Exception as e:
        print(f"💥 Error: {e}")
        raise
    finally:
        if 'bot' in locals():
            await bot.cleanup()

if __name__ == "__main__":
    asyncio.run(main())
EOF

# Create wallet setup script
cat > scripts/setup_wallet.py << 'EOF'
#!/usr/bin/env python3
"""Wallet setup utility"""

import json
import base58
from solders.keypair import Keypair

def generate_wallet():
    keypair = Keypair()
    public_key = str(keypair.pubkey())
    private_key_base58 = base58.b58encode(bytes(keypair)).decode()
    
    print(f" New wallet generated:")
    print(f"   Address: {public_key}")
    print(f"   Private Key: {private_key_base58}")
    print(f"   Add to .env: SOLANA_PRIVATE_KEY={private_key_base58}")
    
    return {"address": public_key, "private_key": private_key_base58}

if __name__ == "__main__":
    generate_wallet()
EOF

# Make scripts executable
chmod +x scripts/run_bot.py
chmod +x scripts/setup_wallet.py

echo "Project structure created successfully!"
echo ""
echo " Next steps:"
echo "1. cd $PROJECT_NAME"
echo "2. python -m venv venv"
echo "3. source venv/bin/activate"
echo "4. pip install -r requirements.txt"
echo "5. cp .env.example .env"
echo "6. python scripts/setup_wallet.py"
echo "7. Edit .env with your wallet private key"
echo "8. docker-compose up -d mongodb"
echo "9. python scripts/run_bot.py"
echo ""
echo "🎉 Happy trading!"
