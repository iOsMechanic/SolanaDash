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
