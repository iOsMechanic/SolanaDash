"""
Health Routes
============
Health check and system status API endpoints
"""

import logging
from datetime import datetime
from aiohttp import web

logger = logging.getLogger(__name__)


async def health_check(request):
    """Basic health check endpoint"""
    try:
        # Get dependencies from app
        db = request.app['db']
        trader = request.app['trader']
        whale_monitor = request.app['whale_monitor']
        server = request.app['server']
        
        # Test database connection
        try:
            await db.client.admin.command('ping')
            db_status = "connected"
        except Exception as e:
            db_status = f"error: {str(e)}"
        
        # Get wallet balance
        try:
            sol_balance = await trader.get_sol_balance()
            wallet_status = "connected"
        except Exception as e:
            sol_balance = 0.0
            wallet_status = f"error: {str(e)}"
        
        # Get whale monitor status
        monitor_stats = whale_monitor.get_monitor_stats()
        
        # Get server stats
        server_stats = server.get_server_stats()
        
        health_data = {
            "status": "healthy",
            "timestamp": datetime.now().isoformat(),
            "services": {
                "database": {
                    "status": db_status,
                    "database_name": db.db_name
                },
                "wallet": {
                    "status": wallet_status,
                    "address": trader.wallet_address,
                    "sol_balance": sol_balance
                },
                "whale_monitor": {
                    "status": "active",
                    "demo_mode": whale_monitor.demo_mode,
                    "success_rate": monitor_stats.get("success_rate", 0)
                },
                "api_server": {
                    "status": "running",
                    "uptime_hours": server_stats.get("uptime_hours", 0),
                    "request_count": server_stats.get("request_count", 0)
                }
            }
        }
        
        # Determine overall health status
        if db_status != "connected" or wallet_status != "connected":
            health_data["status"] = "degraded"
        
        return web.json_response({
            "success": True,
            "data": health_data
        })
        
    except Exception as e:
        logger.error(f"Health check error: {e}")
        return web.json_response({
            "success": False,
            "status": "error",
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }, status=500)


async def detailed_health(request):
    """Detailed health check with component diagnostics"""
    try:
        db = request.app['db']
        trader = request.app['trader']
        position_manager = request.app['position_manager']
        whale_monitor = request.app['whale_monitor']
        strategy = request.app['strategy']
        
        # Database health
        try:
            db_info = await db.get_database_info()
            db_health = {
                "status": "healthy",
                "info": db_info
            }
        except Exception as e:
            db_health = {
                "status": "error",
                "error": str(e)
            }
        
        # Trading health
        try:
            trading_stats = await trader.get_trading_stats()
            trading_health = {
                "status": "healthy",
                "stats": trading_stats
            }
        except Exception as e:
            trading_health = {
                "status": "error",
                "error": str(e)
            }
        
        # Position management health
        try:
            position_stats = position_manager.get_manager_stats()
            position_health = {
                "status": "healthy",
                "stats": position_stats
            }
        except Exception as e:
            position_health = {
                "status": "error",
                "error": str(e)
            }
        
        # Strategy health
        try:
            strategy_stats = strategy.get_strategy_stats()
            strategy_health = {
                "status": "healthy",
                "stats": strategy_stats
            }
        except Exception as e:
            strategy_health = {
                "status": "error",
                "error": str(e)
            }
        
        # Monitor health
        monitor_stats = whale_monitor.get_monitor_stats()
        monitor_health = {
            "status": "healthy" if monitor_stats.get("success_rate", 0) > 50 else "degraded",
            "stats": monitor_stats
        }
        
        detailed_health = {
            "timestamp": datetime.now().isoformat(),
            "overall_status": "healthy",  # Will be updated based on components
            "components": {
                "database": db_health,
                "trading": trading_health,
                "positions": position_health,
                "strategy": strategy_health,
                "monitoring": monitor_health
            }
        }
        
        # Determine overall status
        component_statuses = [comp["status"] for comp in detailed_health["components"].values()]
        if "error" in component_statuses:
            detailed_health["overall_status"] = "error"
        elif "degraded" in component_statuses:
            detailed_health["overall_status"] = "degraded"
        
        return web.json_response({
            "success": True,
            "data": detailed_health
        })
        
    except Exception as e:
        logger.error(f"Detailed health check error: {e}")
        return web.json_response({
            "success": False,
            "error": str(e)
        }, status=500)


async def system_info(request):
    """Get system information and configuration"""
    try:
        import platform
        import psutil
        import os
        
        system_info = {
            "system": {
                "platform": platform.platform(),
                "python_version": platform.python_version(),
                "architecture": platform.architecture()[0]
            },
            "process": {
                "pid": os.getpid(),
                "memory_mb": psutil.Process().memory_info().rss / 1024 / 1024,
                "cpu_percent": psutil.Process().cpu_percent()
            },
            "environment": {
                "node_env": os.getenv("NODE_ENV", "development"),
                "log_level": os.getenv("LOG_LEVEL", "INFO")
            }
        }
        
        return web.json_response({
            "success": True,
            "data": system_info
        })
        
    except Exception as e:
        logger.error(f"System info error: {e}")
        return web.json_response({
            "success": False,
            "error": str(e)
        }, status=500)


def setup_health_routes(app):
    """Setup health check routes"""
    app.router.add_get('/api/health', health_check)
    app.router.add_get('/api/health/detailed', detailed_health)
    app.router.add_get('/api/system', system_info)
    
    logger.info("✅ Health routes configured")
