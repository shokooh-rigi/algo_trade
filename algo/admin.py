import logging
from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from django import forms
from django.core.exceptions import ValidationError
from pydantic import ValidationError as PydanticValidationError, BaseModel
from typing import Dict, Any

from .models import (
    Deal,
    Order,
    StoreClient,
    Asset,
    AccountBalance,
    Market,
    AdminSystemConfig,
    StrategyConfig,
)
from algo.forms import StrategyConfigAdminForm

logger = logging.getLogger(__name__)


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
    raw_id_fields = ('asset',)


@admin.register(Deal)
class DealAdmin(admin.ModelAdmin):
    """Admin configuration for the Deal model."""
    list_display = (
        'client_deal_id', 'strategy_name', 'provider_name', 'market_symbol',
        'side', 'status', 'is_processed', 'is_active', 'processed_side', 'created_at_display'
    )
    list_filter = (
        'strategy_name', 'provider_name', 'side', 'status', 'is_processed', 'is_active', 'processed_side'
    )
    search_fields = (
        'client_deal_id', 'market_symbol', 'strategy_name'
    )
    readonly_fields = (
        'client_deal_id', 'created_at', 'updated_at'
    )
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
    raw_id_fields = ('store_client', 'deal',)
    readonly_fields = (
        'orig_qty', 'orig_sum', 'executed_sum', 'executed_percent',
        'timestamp_created_at', 'created_at', 'updated_at'
    )
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
    fieldsets = (
        (None, {
            'fields': ('name', 'provider', 'user_id', 'title')
        }),
        ('API Credentials', {
            'fields': ('api_key', 'api_secret')
        }),
        ('Soft Delete', {
            'fields': ('is_deleted', 'deleted_at'),
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
    raw_id_fields = ('store_client', 'asset',)
    readonly_fields = (
        'created_at', 'updated_at'
    )
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
        'id', 'strategy', 'market', 'store_client', 'is_active', 'state', 'created_at'
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
    raw_id_fields = ('market', 'store_client')

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