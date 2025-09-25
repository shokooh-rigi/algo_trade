from django.urls import path
from .views import (
    health_check,
    AdminDashboardView,
    SystemHealthView,
    RiskDashboardView,
    EmergencyControlsView,
    StrategyManagementView
)

urlpatterns = [
    path('health/', health_check, name='health_check'),
    path('admin/dashboard/', AdminDashboardView.as_view(), name='admin_dashboard'),
    path('admin/system-health/', SystemHealthView.as_view(), name='system_health'),
    path('admin/risk-dashboard/', RiskDashboardView.as_view(), name='risk_dashboard'),
    path('admin/emergency-controls/', EmergencyControlsView.as_view(), name='emergency_controls'),
    path('admin/strategy-management/', StrategyManagementView.as_view(), name='strategy_management'),
]
