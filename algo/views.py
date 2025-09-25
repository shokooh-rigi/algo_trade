import logging
from django.shortcuts import render
from django.http import JsonResponse
from django.contrib.admin.views.decorators import staff_member_required
from django.utils.decorators import method_decorator
from django.views import View
from django.db.models import Count, Sum, Avg
from django.utils import timezone
from datetime import timedelta
import json

from .models import Deal, Order, StrategyConfig, AdminSystemConfig
from .services.order_management_service import OrderManagementService
from .services.stop_order_monitor_service import StopOrderMonitorService
from .strategies.enums import StrategyState

logger = logging.getLogger(__name__)


def health_check(request):
    """Simple health check endpoint."""
    return JsonResponse({
        'status': 'healthy',
        'timestamp': timezone.now().isoformat(),
    })


@method_decorator(staff_member_required, name='dispatch')
class AdminDashboardView(View):
    """Enhanced admin dashboard with comprehensive trading metrics."""
    
    def get(self, request):
        """Render the admin dashboard."""
        context = self.get_dashboard_context()
        return render(request, 'admin/dashboard.html', context)
    
    def get_dashboard_context(self):
        """Get comprehensive dashboard context."""
        # Basic metrics
        total_deals = Deal.objects.count()
        active_deals = Deal.objects.filter(is_active=True).count()
        total_orders = Order.objects.count()
        active_strategies = StrategyConfig.objects.filter(is_active=True).count()
        
        # Time-based metrics
        today = timezone.now().date()
        week_ago = today - timedelta(days=7)
        month_ago = today - timedelta(days=30)
        
        deals_today = Deal.objects.filter(created_at__date=today).count()
        deals_this_week = Deal.objects.filter(created_at__date__gte=week_ago).count()
        deals_this_month = Deal.objects.filter(created_at__date__gte=month_ago).count()
        
        # Strategy performance
        strategy_performance = self.get_strategy_performance()
        
        # Risk metrics
        risk_metrics = self.get_risk_metrics()
        
        # Recent activity
        recent_deals = Deal.objects.filter(
            created_at__gte=timezone.now() - timedelta(hours=24)
        ).order_by('-created_at')[:10]
        
        # System health
        system_config = AdminSystemConfig.get_instance()
        
        return {
            'total_deals': total_deals,
            'active_deals': active_deals,
            'total_orders': total_orders,
            'active_strategies': active_strategies,
            'deals_today': deals_today,
            'deals_this_week': deals_this_week,
            'deals_this_month': deals_this_month,
            'strategy_performance': strategy_performance,
            'risk_metrics': risk_metrics,
            'recent_deals': recent_deals,
            'kill_switch_active': system_config.kill_switch,
            'system_health': 'healthy' if not system_config.kill_switch else 'emergency_stop',
        }
    
    def get_strategy_performance(self):
        """Get strategy performance metrics."""
        strategies = StrategyConfig.objects.filter(is_active=True)
        performance = []
        
        for strategy in strategies:
            deals = Deal.objects.filter(
                strategy_name=strategy.strategy,
                market_symbol=strategy.market.symbol,
                created_at__gte=timezone.now() - timedelta(days=30)
            )
            
            total_trades = deals.count()
            active_trades = deals.filter(is_active=True).count()
            processed_trades = deals.filter(is_processed=True).count()
            
            performance.append({
                'strategy': strategy.strategy,
                'market': strategy.market.symbol,
                'total_trades': total_trades,
                'active_trades': active_trades,
                'processed_trades': processed_trades,
                'state': strategy.state,
            })
        
        return performance
    
    def get_risk_metrics(self):
        """Get risk management metrics."""
        active_deals = Deal.objects.filter(is_active=True)
        
        return {
            'total_active_deals': active_deals.count(),
            'deals_with_stop_loss': active_deals.filter(stop_loss_price__isnull=False).count(),
            'deals_with_take_profit': active_deals.filter(take_profit_price__isnull=False).count(),
            'trailing_stops_active': active_deals.filter(trailing_stop_enabled=True).count(),
            'risk_coverage_percentage': self.calculate_risk_coverage(active_deals),
        }
    
    def calculate_risk_coverage(self, deals):
        """Calculate percentage of deals with risk management."""
        if not deals.exists():
            return 0
        
        protected_deals = deals.filter(
            stop_loss_price__isnull=False
        ).count()
        
        return round((protected_deals / deals.count()) * 100, 1)


@method_decorator(staff_member_required, name='dispatch')
class SystemHealthView(View):
    """System health monitoring API."""
    
    def get(self, request):
        """Get system health metrics."""
        try:
            metrics = {
                'timestamp': timezone.now().isoformat(),
                'status': 'healthy',
                'metrics': {
                    'total_deals': Deal.objects.count(),
                    'active_deals': Deal.objects.filter(is_active=True).count(),
                    'total_orders': Order.objects.count(),
                    'active_strategies': StrategyConfig.objects.filter(is_active=True).count(),
                    'kill_switch_active': AdminSystemConfig.get_instance().kill_switch,
                },
            }
            
            return JsonResponse(metrics)
            
        except Exception as e:
            logger.error(f"Error getting system health: {e}")
            return JsonResponse({
                'status': 'error',
                'message': str(e)
            }, status=500)


@method_decorator(staff_member_required, name='dispatch')
class RiskDashboardView(View):
    """Risk management dashboard API."""
    
    def get(self, request):
        """Get risk management metrics."""
        try:
            active_deals = Deal.objects.filter(is_active=True)
            
            risk_metrics = {
                'timestamp': timezone.now().isoformat(),
                'total_exposure': 0,
                'active_deals': active_deals.count(),
                'deals_with_stop_loss': active_deals.filter(stop_loss_price__isnull=False).count(),
                'deals_with_take_profit': active_deals.filter(take_profit_price__isnull=False).count(),
                'trailing_stops_active': active_deals.filter(trailing_stop_enabled=True).count(),
            }
            
            return JsonResponse(risk_metrics)
            
        except Exception as e:
            logger.error(f"Error getting risk metrics: {e}")
            return JsonResponse({
                'status': 'error',
                'message': str(e)
            }, status=500)


@method_decorator(staff_member_required, name='dispatch')
class EmergencyControlsView(View):
    """Emergency controls for system management."""
    
    def get(self, request):
        """Render emergency controls page."""
        system_config = AdminSystemConfig.get_instance()
        
        context = {
            'kill_switch_active': system_config.kill_switch,
            'active_strategies': StrategyConfig.objects.filter(is_active=True).count(),
            'active_deals': Deal.objects.filter(is_active=True).count(),
        }
        
        return render(request, 'admin/emergency_controls.html', context)


@method_decorator(staff_member_required, name='dispatch')
class StrategyManagementView(View):
    """Strategy management interface."""
    
    def get(self, request):
        """Get strategy management data."""
        strategies = StrategyConfig.objects.all()
        
        strategy_data = []
        for strategy in strategies:
            recent_deals = Deal.objects.filter(
                strategy_name=strategy.strategy,
                market_symbol=strategy.market.symbol,
                created_at__gte=timezone.now() - timedelta(days=7)
            )
            
            strategy_data.append({
                'id': strategy.id,
                'strategy': strategy.strategy,
                'market': strategy.market.symbol,
                'provider': strategy.store_client.provider,
                'is_active': strategy.is_active,
                'state': strategy.state,
                'recent_trades': recent_deals.count(),
                'active_trades': recent_deals.filter(is_active=True).count(),
            })
        
        return JsonResponse({
            'strategies': strategy_data
        })