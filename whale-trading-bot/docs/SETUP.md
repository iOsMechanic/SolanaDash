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
