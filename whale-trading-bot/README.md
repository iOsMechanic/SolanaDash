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
