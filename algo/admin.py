import logging
from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse, path
from django import forms
from django.core.exceptions import ValidationError
from django.http import HttpResponseRedirect, JsonResponse
from django.shortcuts import render
from django.contrib import messages
from django.utils import timezone
from django.db.models import Sum, Count, Avg
from django.db import transaction
from pydantic import ValidationError as PydanticValidationError, BaseModel
from typing import Dict, Any
import json

from .models import (
    Deal,
    Order,
    StoreClient,
    Asset,
    AccountBalance,
    Market,
    AdminSystemConfig, StrategyConfig,
)
from algo.forms import StrategyConfigAdminForm
from algo.strategies.enums import StrategyState
from algo.services.order_management_service import OrderManagementService
from algo.services.stop_order_monitor_service import StopOrderMonitorService

logger = logging.getLogger(__name__)


class AdminDashboard(admin.AdminSite):
    """Custom admin site with enhanced dashboard."""
    
    def index(self, request, extra_context=None):
        """Enhanced admin dashboard with trading metrics."""
        extra_context = extra_context or {}
        
        # Get system metrics
        total_deals = Deal.objects.count()
        active_deals = Deal.objects.filter(is_active=True).count()
        total_orders = Order.objects.count()
        active_strategies = StrategyConfig.objects.filter(is_active=True).count()
        
        # Get recent activity
        recent_deals = Deal.objects.filter(
            created_at__gte=timezone.now() - timezone.timedelta(hours=24)
        ).order_by('-created_at')[:10]
        
        # Get system health
        system_config = AdminSystemConfig.get_instance()
        kill_switch_active = system_config.kill_switch
        
        extra_context.update({
            'total_deals': total_deals,
            'active_deals': active_deals,
            'total_orders': total_orders,
            'active_strategies': active_strategies,
            'recent_deals': recent_deals,
            'kill_switch_active': kill_switch_active,
            'system_health': 'healthy' if not kill_switch_active else 'emergency_stop',
        })
        
        return super().index(request, extra_context)


# Create custom admin site instance
admin_site = AdminDashboard(name='admin')


class EmergencyControlsAdmin(admin.ModelAdmin):
    """Emergency controls for system management."""
    
    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path('kill-switch/', self.kill_switch_view, name='kill_switch'),
            path('system-health/', self.system_health_view, name='system_health'),
            path('risk-dashboard/', self.risk_dashboard_view, name='risk_dashboard'),
        ]
        return custom_urls + urls
    
    def kill_switch_view(self, request):
        """Emergency kill switch control."""
        if request.method == 'POST':
            action = request.POST.get('action')
            system_config = AdminSystemConfig.get_instance()
            
            if action == 'activate':
                system_config.kill_switch = True
                system_config.save()
                messages.error(request, "🚨 EMERGENCY STOP ACTIVATED - All trading halted!")
            elif action == 'deactivate':
                system_config.kill_switch = False
                system_config.save()
                messages.success(request, "✅ Emergency stop deactivated - Trading resumed!")
            
            return HttpResponseRedirect(request.path)
        
        system_config = AdminSystemConfig.get_instance()
        context = {
            'kill_switch_active': system_config.kill_switch,
            'active_strategies': StrategyConfig.objects.filter(is_active=True).count(),
            'active_deals': Deal.objects.filter(is_active=True).count(),
        }
        return render(request, 'admin/emergency_controls.html', context)
    
    def system_health_view(self, request):
        """System health monitoring."""
        # Get system metrics
        metrics = {
            'total_deals': Deal.objects.count(),
            'active_deals': Deal.objects.filter(is_active=True).count(),
            'total_orders': Order.objects.count(),
            'active_strategies': StrategyConfig.objects.filter(is_active=True).count(),
            'recent_errors': 0,  # Would need to implement error tracking
        }
        
        return JsonResponse(metrics)
    
    def risk_dashboard_view(self, request):
        """Risk management dashboard."""
        # Get risk metrics
        active_deals = Deal.objects.filter(is_active=True)
        
        risk_metrics = {
            'total_exposure': 0,  # Would need to calculate from positions
            'deals_with_stop_loss': active_deals.filter(stop_loss_price__isnull=False).count(),
            'deals_with_take_profit': active_deals.filter(take_profit_price__isnull=False).count(),
            'trailing_stops_active': active_deals.filter(trailing_stop_enabled=True).count(),
        }
        
        return JsonResponse(risk_metrics)


# Register emergency controls
admin_site.register(AdminSystemConfig, EmergencyControlsAdmin)


class OrderInline(admin.TabularInline):
    """Inline display for Orders within a Deal."""
    model = Order
    extra = 0
    fields = (
        'client_order_id', 'symbol', 'side', 'type', 'price', 'quantity',
        'executed_qty', 'status', 'active', 'should_cancel'
    )
    readonly_fields = (
        'client_order_id', 'symbol', 'side', 'type', 'price', 'quantity',
        'orig_qty', 'orig_sum', 'executed_price', 'executed_qty',
        'executed_sum', 'executed_percent', 'status', 'active',
        'timestamp_created_at', 'created_at', 'updated_at'
    )
    show_change_link = True


class AccountBalanceInline(admin.TabularInline):
    """Inline display for AccountBalances within a StoreClient."""
    model = AccountBalance
    extra = 0
    fields = ('asset', 'total_balance', 'unbalance_threshold')
    readonly_fields = ('created_at', 'updated_at')


@admin.register(Deal)
class DealAdmin(admin.ModelAdmin):
    """Admin configuration for the Deal model."""
    list_display = (
        'client_deal_id', 'strategy_name', 'provider_name', 'market_symbol',
        'side', 'status', 'is_processed', 'is_active', 'processed_side', 
        'risk_management_status', 'created_at_display'
    )
    list_filter = (
        'strategy_name', 'provider_name', 'side', 'status', 'is_processed', 
        'is_active', 'processed_side', 'trailing_stop_enabled'
    )
    search_fields = (
        'client_deal_id', 'market_symbol', 'strategy_name'
    )
    readonly_fields = (
        'client_deal_id', 'created_at', 'updated_at'
    )
    list_per_page = 25
    ordering = ['-created_at']
    actions = ['close_deal', 'activate_deal', 'deactivate_deal', 'cancel_stop_orders']
    
    fieldsets = (
        (None, {
            'fields': ('client_deal_id', 'strategy_name', 'provider_name', 'market_symbol')
        }),
        ('Deal Details', {
            'fields': ('side', 'price', 'quantity')
        }),
        ('Status & Control', {
            'fields': ('status', 'is_processed', 'is_active', 'processed_side')
        }),
        ('Risk Management', {
            'fields': ('stop_loss_price', 'take_profit_price', 'stop_loss_order_id', 
                      'take_profit_order_id', 'trailing_stop_enabled', 'trailing_stop_distance')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    inlines = [OrderInline]

    def created_at_display(self, obj):
        return obj.created_at.strftime("%Y-%m-%d %H:%M:%S")
    created_at_display.admin_order_field = 'created_at'
    created_at_display.short_description = 'Created At'
    
    def risk_management_status(self, obj):
        """Display risk management status with color coding."""
        if obj.stop_loss_price and obj.take_profit_price:
            return format_html(
                '<span style="color: green;">✓ Stop Loss & Take Profit</span>'
            )
        elif obj.stop_loss_price:
            return format_html(
                '<span style="color: orange;">⚠ Stop Loss Only</span>'
            )
        else:
            return format_html(
                '<span style="color: red;">✗ No Risk Management</span>'
            )
    risk_management_status.short_description = 'Risk Management'
    
    def close_deal(self, request, queryset):
        """Close selected deals manually."""
        closed_count = 0
        for deal in queryset:
            if deal.is_active:
                deal.is_active = False
                deal.status = StrategyState.STOPPED.value
                deal.save()
                closed_count += 1
        
        self.message_user(
            request,
            f"Successfully closed {closed_count} deals.",
            messages.SUCCESS
        )
    close_deal.short_description = "Close selected deals"
    
    def activate_deal(self, request, queryset):
        """Activate selected deals."""
        activated_count = 0
        for deal in queryset:
            if not deal.is_active:
                deal.is_active = True
                deal.save()
                activated_count += 1
        
        self.message_user(
            request,
            f"Successfully activated {activated_count} deals.",
            messages.SUCCESS
        )
    activate_deal.short_description = "Activate selected deals"
    
    def deactivate_deal(self, request, queryset):
        """Deactivate selected deals."""
        deactivated_count = 0
        for deal in queryset:
            if deal.is_active:
                deal.is_active = False
                deal.save()
                deactivated_count += 1
        
        self.message_user(
            request,
            f"Successfully deactivated {deactivated_count} deals.",
            messages.SUCCESS
        )
    deactivate_deal.short_description = "Deactivate selected deals"
    
    def cancel_stop_orders(self, request, queryset):
        """Cancel stop-loss and take-profit orders for selected deals."""
        cancelled_count = 0
        monitor_service = StopOrderMonitorService()
        
        for deal in queryset:
            if deal.stop_loss_order_id or deal.take_profit_order_id:
                if monitor_service.cancel_all_stop_orders(deal):
                    cancelled_count += 1
        
        self.message_user(
            request,
            f"Successfully cancelled stop orders for {cancelled_count} deals.",
            messages.SUCCESS
        )
    cancel_stop_orders.short_description = "Cancel stop orders for selected deals"


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    """Admin configuration for the Order model."""
    list_display = (
        'client_order_id', 'deal_link', 'store_client_link', 'symbol', 'side', 'status',
        'quantity', 'executed_qty', 'price', 'executed_price', 'active', 'should_cancel'
    )
    list_filter = (
        'status', 'side', 'type', 'active', 'should_cancel',
        'store_client__name', 'deal__strategy_name', 'deal__market_symbol'
    )
    search_fields = (
        'client_order_id', 'symbol', 'deal__client_deal_id', 'store_client__name'
    )
    readonly_fields = (
        'orig_qty', 'orig_sum', 'executed_sum', 'executed_percent',
        'timestamp_created_at', 'created_at', 'updated_at'
    )
    list_per_page = 25
    ordering = ['-created_at']
    fieldsets = (
        (None, {
            'fields': ('client_order_id', 'symbol', 'type', 'side', 'status', 'active', 'should_cancel')
        }),
        ('Quantities & Prices', {
            'fields': ('price', 'quantity', 'orig_qty', 'orig_sum', 'executed_price', 'executed_qty', 'executed_sum', 'executed_percent')
        }),
        ('Relationships', {
            'fields': ('store_client', 'deal')
        }),
        ('Timestamps', {
            'fields': ('timestamp_created_at', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

    def deal_link(self, obj):
        if obj.deal:
            link = reverse("admin:algo_deal_change", args=[obj.deal.pk])
            return format_html('<a href="{}">{}</a>', link, obj.deal.client_deal_id)
        return "-"
    deal_link.short_description = 'Deal'

    def store_client_link(self, obj):
        if obj.store_client:
            link = reverse("admin:algo_storeclient_change", args=[obj.store_client.pk])
            return format_html('<a href="{}">{}</a>', link, obj.store_client.name)
        return "-"
    store_client_link.short_description = 'Store Client'


@admin.register(StoreClient)
class StoreClientAdmin(admin.ModelAdmin):
    """Admin configuration for the StoreClient model."""
    list_display = (
        'name', 'provider', 'user_id', 'title', 'is_deleted', 'created_at_display'
    )
    list_filter = (
        'provider', 'is_deleted'
    )
    search_fields = (
        'name', 'api_key', 'title', 'user_id'
    )
    readonly_fields = (
        'user_id', 'created_at', 'updated_at', 'deleted_at'
    )
    list_per_page = 25
    ordering = ['name']
    fieldsets = (
        (None, {
            'fields': ('name', 'provider', 'user_id', 'title')
        }),
        ('API Credentials', {
            'fields': ('api_key', 'api_secret')
        }),
        ('Soft Delete Info', {
            'fields': ('deleted_at',),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    inlines = [AccountBalanceInline]

    def created_at_display(self, obj):
        return obj.created_at.strftime("%Y-%m-%d %H:%M:%S")
    created_at_display.admin_order_field = 'created_at'
    created_at_display.short_description = 'Created At'


@admin.register(Asset)
class AssetAdmin(admin.ModelAdmin):
    """Admin configuration for the Asset model."""
    list_display = (
        'name', 'provider', 'created_at_display'
    )
    list_filter = (
        'provider',
    )
    search_fields = (
        'name',
    )
    readonly_fields = (
        'created_at', 'updated_at'
    )
    list_per_page = 25
    ordering = ['name']
    fieldsets = (
        (None, {
            'fields': ('name', 'provider')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

    def created_at_display(self, obj):
        return obj.created_at.strftime("%Y-%m-%d %H:%M:%S")
    created_at_display.admin_order_field = 'created_at'
    created_at_display.short_description = 'Created At'


@admin.register(AccountBalance)
class AccountBalanceAdmin(admin.ModelAdmin):
    """Admin configuration for the AccountBalance model."""
    list_display = (
        'store_client_link', 'asset_link', 'total_balance', 'unbalance_threshold', 'created_at_display'
    )
    list_filter = (
        'store_client__name', 'asset__name'
    )
    search_fields = (
        'store_client__name', 'asset__name'
    )
    readonly_fields = (
        'created_at', 'updated_at'
    )
    list_per_page = 25
    ordering = ['store_client__name', 'asset__name']
    fieldsets = (
        (None, {
            'fields': ('store_client', 'asset', 'total_balance', 'unbalance_threshold')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

    def store_client_link(self, obj):
        if obj.store_client:
            link = reverse("admin:algo_storeclient_change", args=[obj.store_client.pk])
            return format_html('<a href="{}">{}</a>', link, obj.store_client.name)
        return "-"
    store_client_link.short_description = 'Store Client'

    def asset_link(self, obj):
        if obj.asset:
            link = reverse("admin:algo_asset_change", args=[obj.asset.pk])
            return format_html('<a href="{}">{}</a>', link, obj.asset.name)
        return "-"
    asset_link.short_description = 'Asset'

    def created_at_display(self, obj):
        return obj.created_at.strftime("%Y-%m-%d %H:%M:%S")
    created_at_display.admin_order_field = 'created_at'
    created_at_display.short_description = 'Created At'


@admin.register(Market)
class MarketAdmin(admin.ModelAdmin):
    """Admin configuration for the Market model."""
    list_display = (
        'symbol', 'provider', 'base_asset', 'quote_asset', 'min_qty', 'min_notional', 'created_at_display'
    )
    list_filter = (
        'provider', 'base_asset', 'quote_asset'
    )
    search_fields = (
        'symbol', 'fa_name', 'base_asset', 'quote_asset'
    )
    readonly_fields = (
        'timestamp_created_at', 'created_at', 'updated_at'
    )
    list_per_page = 25
    ordering = ['symbol']
    fieldsets = (
        (None, {
            'fields': ('symbol', 'provider', 'fa_name')
        }),
        ('Asset Details', {
            'fields': ('base_asset', 'base_asset_precision', 'quote_asset', 'quote_precision', 'fa_base_asset', 'fa_quote_asset')
        }),
        ('Trading Rules', {
            'fields': ('step_size', 'tick_size', 'min_qty', 'min_notional')
        }),
        ('Timestamps', {
            'fields': ('timestamp_created_at', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

    def created_at_display(self, obj):
        return obj.created_at.strftime("%Y-%m-%d %H:%M:%S")
    created_at_display.admin_order_field = 'created_at'
    created_at_display.short_description = 'Created At'


@admin.register(AdminSystemConfig)
class AdminSystemConfigAdmin(admin.ModelAdmin):
    """Admin configuration for the AdminSystemConfig model."""
    list_display = (
        'strategy_processor_batch_size', 'strategy_depth_orderbook',
        'wallex_tether_order_amount', 'put_same_order_base_in_every_order',
        'kill_switch', 'desired_balance_asset_in_usdt_tmn_market'
    )
    fieldsets = (
        (None, {
            'fields': ('strategy_processor_batch_size', 'strategy_depth_orderbook', 'wallex_tether_order_amount')
        }),
        ('Global Controls', {
            'fields': ('put_same_order_base_in_every_order', 'kill_switch', 'desired_balance_asset_in_usdt_tmn_market')
        }),
    )
    # Ensure only one instance can be managed
    def has_add_permission(self, request):
        return not AdminSystemConfig.objects.exists()

    def has_delete_permission(self, request, obj=None):
        return False # Prevent deletion of the single config instance.

@admin.register(StrategyConfig)
class StrategyConfigAdmin(admin.ModelAdmin):
    form = StrategyConfigAdminForm
    list_display = (
        'id', 'strategy', 'market', 'store_client', 'is_active', 'state', 
        'performance_summary', 'created_at'
    )
    list_filter = (
        'strategy', 'market__symbol', 'store_client', 'is_active', 'state'
    )
    search_fields = (
        'id', 'market__symbol', 'store_client__name'
    )
    readonly_fields = (
        'created_at', 'updated_at'
    )
    list_per_page = 25
    ordering = ['market__symbol', 'store_client__name']
    actions = ['start_strategy', 'stop_strategy', 'pause_strategy', 'reset_strategy']

    fieldsets = (
        (None, {
            'fields': ('strategy', 'market', 'store_client', 'state', 'is_active')
        }),
        ('Strategy Parameters', {
            'fields': ('strategy_configs', 'sensitivity_percent', 'need_historical_data', 'initial_history_period_days', 'resolution'),
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',),
        }),
    )
    
    def performance_summary(self, obj):
        """Display performance summary for the strategy."""
        try:
            # Get recent deals for this strategy
            recent_deals = Deal.objects.filter(
                strategy_name=obj.strategy,
                market_symbol=obj.market.symbol,
                created_at__gte=timezone.now() - timezone.timedelta(days=7)
            )
            
            if not recent_deals.exists():
                return format_html('<span style="color: gray;">No recent activity</span>')
            
            total_trades = recent_deals.count()
            active_trades = recent_deals.filter(is_active=True).count()
            
            return format_html(
                '<span style="color: blue;">{} trades ({} active)</span>',
                total_trades, active_trades
            )
        except Exception as e:
            return format_html('<span style="color: red;">Error: {}</span>', str(e))
    performance_summary.short_description = 'Performance (7d)'
    
    def start_strategy(self, request, queryset):
        """Start selected strategies."""
        started_count = 0
        for strategy in queryset:
            if not strategy.is_active:
                strategy.is_active = True
                strategy.state = StrategyState.RUNNING.value
                strategy.save()
                started_count += 1
        
        self.message_user(
            request,
            f"Successfully started {started_count} strategies.",
            messages.SUCCESS
        )
    start_strategy.short_description = "Start selected strategies"
    
    def stop_strategy(self, request, queryset):
        """Stop selected strategies."""
        stopped_count = 0
        for strategy in queryset:
            if strategy.is_active:
                strategy.is_active = False
                strategy.state = StrategyState.STOPPED.value
                strategy.save()
                stopped_count += 1
        
        self.message_user(
            request,
            f"Successfully stopped {stopped_count} strategies.",
            messages.SUCCESS
        )
    stop_strategy.short_description = "Stop selected strategies"
    
    def pause_strategy(self, request, queryset):
        """Pause selected strategies."""
        paused_count = 0
        for strategy in queryset:
            if strategy.is_active:
                strategy.is_active = False
                strategy.state = StrategyState.NOT_ORDERING.value
                strategy.save()
                paused_count += 1
        
        self.message_user(
            request,
            f"Successfully paused {paused_count} strategies.",
            messages.SUCCESS
        )
    pause_strategy.short_description = "Pause selected strategies"
    
    def reset_strategy(self, request, queryset):
        """Reset selected strategies."""
        reset_count = 0
        for strategy in queryset:
            strategy.state = StrategyState.STARTED.value
            strategy.save()
            reset_count += 1
        
        self.message_user(
            request,
            f"Successfully reset {reset_count} strategies.",
            messages.SUCCESS
        )
    reset_strategy.short_description = "Reset selected strategies"