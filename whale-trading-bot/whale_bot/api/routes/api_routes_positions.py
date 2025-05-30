"""
Position Routes
==============
API endpoints for managing and viewing trading positions
"""

import logging
from datetime import datetime
from aiohttp import web

logger = logging.getLogger(__name__)


async def get_positions(request):
    """Get all positions with optional filtering"""
    try:
        db = request.app['db']
        
        # Get query parameters
        status = request.query.get('status')  # open, closed, all
        limit = min(int(request.query.get('limit', 100)), 500)
        
        # Get positions based on status filter
        if status and status != 'all':
            positions = await db.get_all_positions(status)
        else:
            positions = await db.get_all_positions()
        
        # Apply limit
        positions = positions[:limit]
        
        # Calculate summary statistics
        open_positions = [p for p in positions if p.get('status') == 'open']
        closed_positions = [p for p in positions if p.get('status') == 'closed']
        
        total_unrealized_pnl = sum(p.get('pnl_usd', 0) for p in open_positions)
        total_realized_pnl = sum(p.get('pnl_usd', 0) for p in closed_positions)
        
        summary = {
            "total_positions": len(positions),
            "open_positions": len(open_positions),
            "closed_positions": len(closed_positions),
            "total_unrealized_pnl": total_unrealized_pnl,
            "total_realized_pnl": total_realized_pnl,
            "net_pnl": total_unrealized_pnl + total_realized_pnl
        }
        
        return web.json_response({
            "success": True,
            "data": {
                "positions": positions,
                "summary": summary,
                "count": len(positions)
            },
            "timestamp": datetime.now().isoformat()
        })
        
    except Exception as e:
        logger.error(f"Get positions error: {e}")
        return web.json_response({
            "success": False,
            "error": str(e)
        }, status=500)


async def get_position_by_id(request):
    """Get specific position by ID"""
    try:
        db = request.app['db']
        position_id = request.match_info['position_id']
        
        position = await db.get_position_by_id(position_id)
        
        if not position:
            return web.json_response({
                "success": False,
                "error": "Position not found"
            }, status=404)
        
        # Convert Position object to dict if needed
        if hasattr(position, '__dict__'):
            position_data = position.__dict__
        else:
            position_data = position
        
        return web.json_response({
            "success": True,
            "data": position_data,
            "timestamp": datetime.now().isoformat()
        })
        
    except Exception as e:
        logger.error(f"Get position by ID error: {e}")
        return web.json_response({
            "success": False,
            "error": str(e)
        }, status=500)


async def get_open_positions(request):
    """Get only open positions"""
    try:
        position_manager = request.app['position_manager']
        
        # Get open positions from position manager
        open_positions = list(position_manager.open_positions.values())
        
        # Convert to serializable format
        positions_data = []
        for pos in open_positions:
            pos_dict = {
                "id": pos.id,
                "token_address": pos.token_address,
                "token_symbol": pos.token_symbol,
                "token_name": pos.token_name,
                "buy_amount_sol": pos.buy_amount_sol,
                "buy_amount_usd": pos.buy_amount_usd,
                "token_amount": pos.token_amount,
                "buy_price_usd": pos.buy_price_usd,
                "current_price_usd": pos.current_price_usd,
                "current_value_usd": pos.current_value_usd,
                "pnl_usd": pos.pnl_usd,
                "pnl_percentage": pos.pnl_percentage,
                "buy_timestamp": pos.buy_timestamp,
                "buy_transaction_id": pos.buy_transaction_id,
                "status": pos.status
            }
            positions_data.append(pos_dict)
        
        # Calculate totals
        total_invested = sum(p["buy_amount_usd"] for p in positions_data)
        total_current_value = sum(p["current_value_usd"] for p in positions_data)
        total_pnl = sum(p["pnl_usd"] for p in positions_data)
        
        return web.json_response({
            "success": True,
            "data": {
                "positions": positions_data,
                "summary": {
                    "count": len(positions_data),
                    "total_invested_usd": total_invested,
                    "total_current_value_usd": total_current_value,
                    "total_pnl_usd": total_pnl,
                    "total_pnl_percentage": (total_pnl / total_invested * 100) if total_invested > 0 else 0
                }
            },
            "timestamp": datetime.now().isoformat()
        })
        
    except Exception as e:
        logger.error(f"Get open positions error: {e}")
        return web.json_response({
            "success": False,
            "error": str(e)
        }, status=500)


async def close_position(request):
    """Force close a position (emergency action)"""
    try:
        position_manager = request.app['position_manager']
        trader = request.app['trader']
        
        position_id = request.match_info['position_id']
        data = await request.json()
        reason = data.get('reason', 'Manual close via API')
        
        # Find the position
        position = None
        for pos in position_manager.open_positions.values():
            if pos.id == position_id:
                position = pos
                break
        
        if not position:
            return web.json_response({
                "success": False,
                "error": "Position not found"
            }, status=404)
        
        # Execute sell trade
        try:
            trade_result = await trader.sell_token_for_sol(
                token_address=position.token_address,
                token_amount=position.token_amount
            )
            
            if trade_result.success:
                # Close position normally
                success = await position_manager.close_position(position, trade_result, reason)
                
                return web.json_response({
                    "success": True,
                    "message": f"Position {position_id} closed successfully",
                    "data": {
                        "position_id": position_id,
                        "transaction_id": trade_result.transaction_id,
                        "sol_received": trade_result.output_amount,
                        "reason": reason
                    },
                    "timestamp": datetime.now().isoformat()
                })
            else:
                # Force close without trade if sell failed
                success = await position_manager.force_close_position(
                    position.token_address, 
                    f"{reason} (sell failed: {trade_result.error_message})"
                )
                
                return web.json_response({
                    "success": success,
                    "message": f"Position {position_id} force closed (sell failed)",
                    "data": {
                        "position_id": position_id,
                        "reason": reason,
                        "sell_error": trade_result.error_message
                    },
                    "timestamp": datetime.now().isoformat()
                })
                
        except Exception as trade_error:
            # Force close if any error occurs
            success = await position_manager.force_close_position(
                position.token_address, 
                f"{reason} (error: {str(trade_error)})"
            )
            
            return web.json_response({
                "success": success,
                "message": f"Position {position_id} force closed due to error",
                "data": {
                    "position_id": position_id,
                    "reason": reason,
                    "error": str(trade_error)
                },
                "timestamp": datetime.now().isoformat()
            })
        
    except Exception as e:
        logger.error(f"Close position error: {e}")
        return web.json_response({
            "success": False,
            "error": str(e)
        }, status=500)


async def get_portfolio_summary(request):
    """Get comprehensive portfolio summary"""
    try:
        position_manager = request.app['position_manager']
        trader = request.app['trader']
        
        # Get portfolio summary from position manager
        portfolio_summary = await position_manager.get_portfolio_summary()
        
        # Get performance metrics
        performance_metrics = await position_manager.get_performance_metrics()
        
        # Get wallet balances
        try:
            sol_balance = await trader.get_sol_balance()
            token_balances = await trader.get_token_accounts()
        except Exception as e:
            logger.warning(f"Failed to get wallet balances: {e}")
            sol_balance = 0.0
            token_balances = {}
        
        portfolio_data = {
            "summary": portfolio_summary,
            "performance": {
                "total_trades": performance_metrics.total_trades,
                "winning_trades": performance_metrics.winning_trades,
                "losing_trades": performance_metrics.losing_trades,
                "win_rate": performance_metrics.win_rate,
                "total_profit": performance_metrics.total_profit,
                "total_loss": performance_metrics.total_loss,
                "net_pnl": performance_metrics.net_pnl,
                "max_drawdown": performance_metrics.max_drawdown,
                "avg_trade_duration": performance_metrics.avg_trade_duration
            },
            "wallet": {
                "sol_balance": sol_balance,
                "token_balances": token_balances,
                "address": trader.wallet_address
            }
        }
        
        return web.json_response({
            "success": True,
            "data": portfolio_data,
            "timestamp": datetime.now().isoformat()
        })
        
    except Exception as e:
        logger.error(f"Get portfolio summary error: {e}")
        return web.json_response({
            "success": False,
            "error": str(e)
        }, status=500)


def setup_position_routes(app):
    """Setup position-related routes"""
    app.router.add_get('/api/positions', get_positions)
    app.router.add_get('/api/positions/open', get_open_positions)
    app.router.add_get('/api/positions/{position_id}', get_position_by_id)
    app.router.add_post('/api/positions/{position_id}/close', close_position)
    app.router.add_get('/api/portfolio', get_portfolio_summary)
    
    logger.info("✅ Position routes configured")
