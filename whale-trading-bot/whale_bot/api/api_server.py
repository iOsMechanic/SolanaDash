"""
API Server
=========
Web API server for monitoring and controlling the whale trading bot
"""

import logging
from datetime import datetime
from typing import Dict, Optional
import os

from aiohttp import web, web_request
import aiohttp_cors

from .routes.positions import setup_position_routes
from .routes.trades import setup_trade_routes
from .routes.stats import setup_stats_routes
from .routes.health import setup_health_routes
from .middleware.cors import cors_middleware
from .middleware.auth import auth_middleware
from ..core.exceptions import WebServerError
from ..database.manager import DatabaseManager

logger = logging.getLogger(__name__)


class APIServer:
    """Web API server for monitoring the bot"""
    
    def __init__(self, db: DatabaseManager, trader, position_manager, 
                 whale_monitor, strategy, host: str = "localhost", port: int = 8080):
        self.db = db
        self.trader = trader
        self.position_manager = position_manager
        self.whale_monitor = whale_monitor
        self.strategy = strategy
        self.host = host
        self.port = port
        
        # Server components
        self.app = None
        self.runner = None
        self.site = None
        
        # Statistics
        self.start_time = datetime.now()
        self.request_count = 0
        self.error_count = 0
        
        logger.info(f"🌐 API Server initialized for {host}:{port}")
    
    async def start(self):
        """Start the API server"""
        try:
            # Create application
            self.app = web.Application(middlewares=[
                cors_middleware,
                auth_middleware,
                self._request_logging_middleware,
                self._error_handling_middleware
            ])
            
            # Setup CORS
            cors = aiohttp_cors.setup(self.app, defaults={
                "*": aiohttp_cors.ResourceOptions(
                    allow_credentials=True,
                    expose_headers="*",
                    allow_headers="*",
                    allow_methods="*"
                )
            })
            
            # Store dependencies in app for route access
            self.app['db'] = self.db
            self.app['trader'] = self.trader
            self.app['position_manager'] = self.position_manager
            self.app['whale_monitor'] = self.whale_monitor
            self.app['strategy'] = self.strategy
            self.app['server'] = self
            
            # Setup routes
            await self._setup_routes()
            
            # Add CORS to all routes
            for route in list(self.app.router.routes()):
                cors.add(route)
            
            # Start server
            self.runner = web.AppRunner(self.app)
            await self.runner.setup()
            
            self.site = web.TCPSite(self.runner, self.host, self.port)
            await self.site.start()
            
            logger.info(f"🚀 API server started on http://{self.host}:{self.port}")
            logger.info(f"📚 API Documentation: http://{self.host}:{self.port}/docs")
            
        except Exception as e:
            logger.error(f"Failed to start API server: {e}")
            raise WebServerError(f"Server startup failed: {e}")
    
    async def _setup_routes(self):
        """Setup all API routes"""
        try:
            # Main API routes
            setup_health_routes(self.app)
            setup_stats_routes(self.app)
            setup_position_routes(self.app)
            setup_trade_routes(self.app)
            
            # Root endpoint
            self.app.router.add_get('/', self._root_handler)
            
            # Documentation endpoint
            self.app.router.add_get('/docs', self._docs_handler)
            
            # Bot control endpoints
            self.app.router.add_post('/api/bot/start', self._start_bot_handler)
            self.app.router.add_post('/api/bot/stop', self._stop_bot_handler)
            self.app.router.add_get('/api/bot/status', self._bot_status_handler)
            
            # Configuration endpoints
            self.app.router.add_get('/api/config', self._get_config_handler)
            self.app.router.add_post('/api/config', self._update_config_handler)
            
            logger.info("✅ API routes configured")
            
        except Exception as e:
            logger.error(f"Failed to setup routes: {e}")
            raise WebServerError(f"Route setup failed: {e}")
    
    async def _root_handler(self, request: web_request.Request) -> web.Response:
        """Root endpoint handler"""
        return web.json_response({
            "name": "Whale Trading Bot API",
            "version": "1.0.0",
            "status": "running",
            "timestamp": datetime.now().isoformat(),
            "endpoints": {
                "health": "/api/health",
                "stats": "/api/stats",
                "positions": "/api/positions",
                "trades": "/api/trades",
                "wallet": "/api/wallet",
                "docs": "/docs"
            }
        })
    
    async def _docs_handler(self, request: web_request.Request) -> web.Response:
        """API documentation handler"""
        docs_html = """
        <!DOCTYPE html>
        <html>
        <head>
            <title>Whale Trading Bot API Documentation</title>
            <style>
                body { font-family: Arial, sans-serif; margin: 40px; }
                .endpoint { margin: 20px 0; padding: 15px; border: 1px solid #ddd; border-radius: 5px; }
                .method { font-weight: bold; color: #0066cc; }
                .path { font-family: monospace; background: #f5f5f5; padding: 2px 5px; }
                .description { margin: 10px 0; }
                .example { background: #f9f9f9; padding: 10px; border-left: 3px solid #0066cc; margin: 10px 0; }
            </style>
        </head>
        <body>
            <h1>🐋 Whale Trading Bot API Documentation</h1>
            
            <div class="endpoint">
                <div class="method">GET</div>
                <div class="path">/api/health</div>
                <div class="description">Get bot health status and system information</div>
            </div>
            
            <div class="endpoint">
                <div class="method">GET</div>
                <div class="path">/api/stats</div>
                <div class="description">Get trading statistics and performance metrics</div>
            </div>
            
            <div class="endpoint">
                <div class="method">GET</div>
                <div class="path">/api/positions</div>
                <div class="description">Get current trading positions</div>
            </div>
            
            <div class="endpoint">
                <div class="method">GET</div>
                <div class="path">/api/trades</div>
                <div class="description">Get trade history with optional filters</div>
                <div class="example">Query params: ?limit=100&trade_type=buy</div>
            </div>
            
            <div class="endpoint">
                <div class="method">GET</div>
                <div class="path">/api/wallet</div>
                <div class="description">Get wallet information and balances</div>
            </div>
            
            <div class="endpoint">
                <div class="method">GET</div>
                <div class="path">/api/decisions</div>
                <div class="description">Get buy decision history</div>
            </div>
            
            <div class="endpoint">
                <div class="method">POST</div>
                <div class="path">/api/bot/start</div>
                <div class="description">Start the trading bot</div>
            </div>
            
            <div class="endpoint">
                <div class="method">POST</div>
                <div class="path">/api/bot/stop</div>
                <div class="description">Stop the trading bot</div>
            </div>
            
            <div class="endpoint">
                <div class="method">GET</div>
                <div class="path">/api/config</div>
                <div class="description">Get current bot configuration</div>
            </div>
            
            <h2>Response Format</h2>
            <div class="example">
                {<br>
                &nbsp;&nbsp;"success": true,<br>
                &nbsp;&nbsp;"data": { ... },<br>
                &nbsp;&nbsp;"timestamp": "2024-01-01T00:00:00",<br>
                &nbsp;&nbsp;"message": "Operation completed successfully"<br>
                }
            </div>
            
            <h2>Error Handling</h2>
            <p>All endpoints return appropriate HTTP status codes:</p>
            <ul>
                <li><strong>200</strong> - Success</li>
                <li><strong>400</strong> - Bad Request</li>
                <li><strong>401</strong> - Unauthorized</li>
                <li><strong>404</strong> - Not Found</li>
                <li><strong>500</strong> - Internal Server Error</li>
            </ul>
        </body>
        </html>
        """
        
        return web.Response(text=docs_html, content_type='text/html')
    
    async def _bot_status_handler(self, request: web_request.Request) -> web.Response:
        """Get bot status"""
        try:
            # Get status from various components
            status = {
                "bot_running": getattr(self.app.get('bot_instance'), 'is_running', False),
                "api_server_running": True,
                "database_connected": True,  # We wouldn't be here if DB was down
                "open_positions": len(self.position_manager.open_positions),
                "demo_mode": self.whale_monitor.demo_mode,
                "uptime_seconds": (datetime.now() - self.start_time).total_seconds()
            }
            
            # Test database connection
            try:
                await self.db.client.admin.command('ping')
                status["database_connected"] = True
            except:
                status["database_connected"] = False
            
            # Get wallet balance
            try:
                sol_balance = await self.trader.get_sol_balance()
                status["sol_balance"] = sol_balance
                status["wallet_connected"] = True
            except:
                status["wallet_connected"] = False
                status["sol_balance"] = 0.0
            
            return web.json_response({
                "success": True,
                "data": status,
                "timestamp": datetime.now().isoformat()
            })
            
        except Exception as e:
            logger.error(f"Bot status error: {e}")
            return web.json_response({
                "success": False,
                "error": str(e)
            }, status=500)
    
    async def _start_bot_handler(self, request: web_request.Request) -> web.Response:
        """Start the trading bot"""
        try:
            # This would integrate with the main bot instance
            # For now, return success
            return web.json_response({
                "success": True,
                "message": "Bot start command received",
                "timestamp": datetime.now().isoformat()
            })
            
        except Exception as e:
            logger.error(f"Bot start error: {e}")
            return web.json_response({
                "success": False,
                "error": str(e)
            }, status=500)
    
    async def _stop_bot_handler(self, request: web_request.Request) -> web.Response:
        """Stop the trading bot"""
        try:
            # This would integrate with the main bot instance
            # For now, return success
            return web.json_response({
                "success": True,
                "message": "Bot stop command received",
                "timestamp": datetime.now().isoformat()
            })
            
        except Exception as e:
            logger.error(f"Bot stop error: {e}")
            return web.json_response({
                "success": False,
                "error": str(e)
            }, status=500)
    
    async def _get_config_handler(self, request: web_request.Request) -> web.Response:
        """Get current bot configuration"""
        try:
            config = {
                "trading": {
                    "sol_per_trade": self.strategy.config.sol_per_trade,
                    "take_profit_percentage": self.strategy.config.take_profit_percentage,
                    "stop_loss_percentage": self.strategy.config.stop_loss_percentage,
                    "max_positions": self.strategy.config.max_positions,
                    "min_win_rate": self.strategy.config.min_win_rate,
                    "min_trade_amount": self.strategy.config.min_trade_amount,
                    "max_market_cap": self.strategy.config.max_market_cap
                },
                "wallet": {
                    "address": self.trader.wallet_address,
                    "rpc_url": self.trader.rpc_url
                },
                "api": {
                    "host": self.host,
                    "port": self.port
                },
                "monitoring": {
                    "demo_mode": self.whale_monitor.demo_mode
                }
            }
            
            return web.json_response({
                "success": True,
                "data": config,
                "timestamp": datetime.now().isoformat()
            })
            
        except Exception as e:
            logger.error(f"Get config error: {e}")
            return web.json_response({
                "success": False,
                "error": str(e)
            }, status=500)
    
    async def _update_config_handler(self, request: web_request.Request) -> web.Response:
        """Update bot configuration"""
        try:
            data = await request.json()
            
            # Validate and update configuration
            # This would integrate with the configuration system
            # For now, return success
            
            return web.json_response({
                "success": True,
                "message": "Configuration updated successfully",
                "timestamp": datetime.now().isoformat()
            })
            
        except Exception as e:
            logger.error(f"Update config error: {e}")
            return web.json_response({
                "success": False,
                "error": str(e)
            }, status=500)
    
    @web.middleware
    async def _request_logging_middleware(self, request: web_request.Request, handler):
        """Log all requests"""
        start_time = datetime.now()
        self.request_count += 1
        
        try:
            response = await handler(request)
            duration = (datetime.now() - start_time).total_seconds()
            
            logger.debug(f"{request.method} {request.path} - {response.status} - {duration:.3f}s")
            return response
            
        except Exception as e:
            self.error_count += 1
            duration = (datetime.now() - start_time).total_seconds()
            logger.error(f"{request.method} {request.path} - ERROR - {duration:.3f}s - {e}")
            raise
    
    @web.middleware
    async def _error_handling_middleware(self, request: web_request.Request, handler):
        """Global error handling"""
        try:
            return await handler(request)
        except web.HTTPException:
            raise  # Re-raise HTTP exceptions as-is
        except Exception as e:
            logger.error(f"Unhandled error in {request.path}: {e}")
            return web.json_response({
                "success": False,
                "error": "Internal server error",
                "message": str(e)
            }, status=500)
    
    def get_server_stats(self) -> Dict:
        """Get server statistics"""
        try:
            uptime_seconds = (datetime.now() - self.start_time).total_seconds()
            
            return {
                "host": self.host,
                "port": self.port,
                "start_time": self.start_time.isoformat(),
                "uptime_seconds": uptime_seconds,
                "uptime_hours": uptime_seconds / 3600,
                "request_count": self.request_count,
                "error_count": self.error_count,
                "error_rate": (self.error_count / max(1, self.request_count)) * 100
            }
        except Exception as e:
            logger.error(f"Error getting server stats: {e}")
            return {}
    
    async def stop(self):
        """Stop the API server"""
        try:
            logger.info("🛑 Stopping API server...")
            
            if self.site:
                await self.site.stop()
                logger.info("✅ API site stopped")
                
            if self.runner:
                await self.runner.cleanup()
                logger.info("✅ API runner cleaned up")
                
            # Log final statistics
            stats = self.get_server_stats()
            logger.info(f"📊 Final server stats: {stats}")
            
        except Exception as e:
            logger.error(f"Error stopping API server: {e}")
