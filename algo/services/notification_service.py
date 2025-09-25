import logging
from django.core.mail import send_mail
from django.conf import settings
from django.template.loader import render_to_string
from django.utils import timezone
from typing import Dict, Any, Optional
import json

from algo.models import Deal, AdminSystemConfig

logger = logging.getLogger(__name__)


class NotificationService:
    """Service for sending notifications about trading events."""
    
    def __init__(self):
        self.system_config = AdminSystemConfig.get_instance()
    
    def send_deal_notification(self, deal: Deal) -> bool:
        """Send email notification when a new deal is generated."""
        try:
            # Check if email notifications are enabled
            if not self._is_email_notifications_enabled():
                logger.info("Email notifications are disabled. Skipping deal notification.")
                return False
            
            # Get email configuration
            email_config = self._get_email_config()
            if not email_config:
                logger.error("Email configuration not found. Cannot send notification.")
                return False
            
            # Prepare email content
            subject = f"🚀 New Trading Deal Generated - {deal.market_symbol}"
            message = self._create_deal_message(deal)
            html_message = self._create_deal_html_message(deal)
            
            # Send email
            success = send_mail(
                subject=subject,
                message=message,
                html_message=html_message,
                from_email=email_config['from_email'],
                recipient_list=[email_config['admin_email']],
                fail_silently=False
            )
            
            if success:
                logger.info(f"Deal notification sent successfully for deal {deal.client_deal_id}")
                return True
            else:
                logger.error(f"Failed to send deal notification for deal {deal.client_deal_id}")
                return False
                
        except Exception as e:
            logger.error(f"Error sending deal notification: {e}", exc_info=True)
            return False
    
    def send_strategy_status_notification(self, strategy_name: str, status: str, details: Dict[str, Any]) -> bool:
        """Send email notification about strategy status changes."""
        try:
            if not self._is_email_notifications_enabled():
                return False
            
            email_config = self._get_email_config()
            if not email_config:
                return False
            
            subject = f"📊 Strategy Status Update - {strategy_name}"
            message = self._create_strategy_status_message(strategy_name, status, details)
            
            success = send_mail(
                subject=subject,
                message=message,
                from_email=email_config['from_email'],
                recipient_list=[email_config['admin_email']],
                fail_silently=False
            )
            
            if success:
                logger.info(f"Strategy status notification sent for {strategy_name}")
                return True
            else:
                logger.error(f"Failed to send strategy status notification for {strategy_name}")
                return False
                
        except Exception as e:
            logger.error(f"Error sending strategy status notification: {e}", exc_info=True)
            return False
    
    def send_emergency_notification(self, event_type: str, message: str, details: Dict[str, Any]) -> bool:
        """Send emergency email notification."""
        try:
            email_config = self._get_email_config()
            if not email_config:
                return False
            
            subject = f"🚨 EMERGENCY ALERT - {event_type}"
            full_message = f"{message}\n\nDetails:\n{json.dumps(details, indent=2)}"
            
            success = send_mail(
                subject=subject,
                message=full_message,
                from_email=email_config['from_email'],
                recipient_list=[email_config['admin_email']],
                fail_silently=False
            )
            
            if success:
                logger.info(f"Emergency notification sent for {event_type}")
                return True
            else:
                logger.error(f"Failed to send emergency notification for {event_type}")
                return False
                
        except Exception as e:
            logger.error(f"Error sending emergency notification: {e}", exc_info=True)
            return False
    
    def _is_email_notifications_enabled(self) -> bool:
        """Check if email notifications are enabled."""
        try:
            return self.system_config.get_value("email_notifications_enabled", False)
        except Exception:
            return False
    
    def _get_email_config(self) -> Optional[Dict[str, str]]:
        """Get email configuration from system config."""
        try:
            admin_email = self.system_config.get_value("admin_email", "")
            from_email = self.system_config.get_value("from_email", settings.DEFAULT_FROM_EMAIL)
            
            if not admin_email:
                logger.error("Admin email not configured in system settings")
                return None
            
            return {
                'admin_email': admin_email,
                'from_email': from_email
            }
        except Exception as e:
            logger.error(f"Error getting email configuration: {e}")
            return None
    
    def _create_deal_message(self, deal: Deal) -> str:
        """Create plain text message for deal notification."""
        message = f"""
🚀 NEW TRADING DEAL GENERATED

Deal ID: {deal.client_deal_id}
Strategy: {deal.strategy_name}
Market: {deal.market_symbol}
Provider: {deal.provider_name}

Trade Details:
- Side: {deal.side}
- Price: ${deal.price:,.2f}
- Quantity: {deal.quantity:,.8f}
- Status: {deal.status}

Risk Management:
- Stop Loss: ${deal.stop_loss_price:,.2f if deal.stop_loss_price else 'Not Set'}
- Take Profit: ${deal.take_profit_price:,.2f if deal.take_profit_price else 'Not Set'}
- Trailing Stop: {'Enabled' if deal.trailing_stop_enabled else 'Disabled'}

Generated at: {deal.created_at.strftime('%Y-%m-%d %H:%M:%S UTC')}

---
Algorithmic Trading Platform
"""
        return message
    
    def _create_deal_html_message(self, deal: Deal) -> str:
        """Create HTML message for deal notification."""
        html_content = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <title>Trading Deal Notification</title>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 20px; }}
        .header {{ background-color: #007cba; color: white; padding: 20px; border-radius: 5px; }}
        .content {{ margin: 20px 0; }}
        .deal-info {{ background-color: #f8f9fa; padding: 15px; border-radius: 5px; margin: 10px 0; }}
        .risk-info {{ background-color: #e7f3ff; padding: 15px; border-radius: 5px; margin: 10px 0; }}
        .footer {{ color: #666; font-size: 12px; margin-top: 20px; }}
        .status-buy {{ color: #28a745; font-weight: bold; }}
        .status-sell {{ color: #dc3545; font-weight: bold; }}
    </style>
</head>
<body>
    <div class="header">
        <h1>🚀 New Trading Deal Generated</h1>
    </div>
    
    <div class="content">
        <div class="deal-info">
            <h3>Deal Information</h3>
            <p><strong>Deal ID:</strong> {deal.client_deal_id}</p>
            <p><strong>Strategy:</strong> {deal.strategy_name}</p>
            <p><strong>Market:</strong> {deal.market_symbol}</p>
            <p><strong>Provider:</strong> {deal.provider_name}</p>
        </div>
        
        <div class="deal-info">
            <h3>Trade Details</h3>
            <p><strong>Side:</strong> <span class="status-{'buy' if deal.side == 'BUY' else 'sell'}">{deal.side}</span></p>
            <p><strong>Price:</strong> ${deal.price:,.2f}</p>
            <p><strong>Quantity:</strong> {deal.quantity:,.8f}</p>
            <p><strong>Status:</strong> {deal.status}</p>
        </div>
        
        <div class="risk-info">
            <h3>Risk Management</h3>
            <p><strong>Stop Loss:</strong> ${deal.stop_loss_price:,.2f if deal.stop_loss_price else 'Not Set'}</p>
            <p><strong>Take Profit:</strong> ${deal.take_profit_price:,.2f if deal.take_profit_price else 'Not Set'}</p>
            <p><strong>Trailing Stop:</strong> {'Enabled' if deal.trailing_stop_enabled else 'Disabled'}</p>
        </div>
    </div>
    
    <div class="footer">
        <p>Generated at: {deal.created_at.strftime('%Y-%m-%d %H:%M:%S UTC')}</p>
        <p>Algorithmic Trading Platform</p>
    </div>
</body>
</html>
"""
        return html_content
    
    def _create_strategy_status_message(self, strategy_name: str, status: str, details: Dict[str, Any]) -> str:
        """Create message for strategy status notifications."""
        message = f"""
📊 STRATEGY STATUS UPDATE

Strategy: {strategy_name}
Status: {status}
Time: {timezone.now().strftime('%Y-%m-%d %H:%M:%S UTC')}

Details:
{json.dumps(details, indent=2)}

---
Algorithmic Trading Platform
"""
        return message
