#!/usr/bin/env python
"""
Test script for email notifications system.
Run this to test if email notifications are working correctly.
"""

import os
import django
import sys

# Add the project directory to the Python path
sys.path.append('/Users/wallex/PycharmProjects/algo_trade')

# Set up Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'algo_trade.settings')
django.setup()

from algo.models import Deal, AdminSystemConfig
from algo.services.notification_service import NotificationService
from algo.strategies.enums import ProcessedSideEnum
from decimal import Decimal
import uuid


def test_email_configuration():
    """Test email configuration in admin settings."""
    print("🔧 Testing Email Configuration...")
    
    try:
        system_config = AdminSystemConfig.get_instance()
        
        print(f"✅ Email notifications enabled: {system_config.email_notifications_enabled}")
        print(f"✅ Admin email: {system_config.admin_email}")
        print(f"✅ From email: {system_config.from_email}")
        print(f"✅ Email host: {system_config.email_host}")
        print(f"✅ Email port: {system_config.email_port}")
        print(f"✅ Use TLS: {system_config.email_use_tls}")
        
        return True
        
    except Exception as e:
        print(f"❌ Error getting email configuration: {e}")
        return False


def create_test_deal():
    """Create a test deal for email notification."""
    print("\n📊 Creating Test Deal...")
    
    try:
        # Create a test deal
        test_deal = Deal.objects.create(
            client_deal_id=uuid.uuid4(),
            strategy_name="BreakoutStrategy",
            provider_name="WALLEX",
            market_symbol="BTCUSDT",
            side="BUY",
            price=Decimal("42150.00"),
            quantity=Decimal("0.001"),
            status="STARTED",
            is_active=True,
            is_processed=False,
            stop_loss_price=Decimal("41950.00"),
            take_profit_price=Decimal("42450.00"),
            trailing_stop_enabled=False
        )
        
        print(f"✅ Test deal created: {test_deal.client_deal_id}")
        return test_deal
        
    except Exception as e:
        print(f"❌ Error creating test deal: {e}")
        return None


def test_notification_service(deal):
    """Test the notification service."""
    print("\n📧 Testing Notification Service...")
    
    try:
        notification_service = NotificationService()
        
        # Test if email notifications are enabled
        if not notification_service._is_email_notifications_enabled():
            print("⚠️  Email notifications are disabled in admin settings")
            return False
        
        # Test email configuration
        email_config = notification_service._get_email_config()
        if not email_config:
            print("❌ Email configuration not found")
            return False
        
        print(f"✅ Email config loaded: {email_config['admin_email']}")
        
        # Test sending notification
        print("📤 Attempting to send test email notification...")
        success = notification_service.send_deal_notification(deal)
        
        if success:
            print("✅ Email notification sent successfully!")
            print(f"📧 Email sent to: {email_config['admin_email']}")
            return True
        else:
            print("❌ Failed to send email notification")
            return False
            
    except Exception as e:
        print(f"❌ Error testing notification service: {e}")
        return False


def cleanup_test_deal(deal):
    """Clean up the test deal."""
    print("\n🧹 Cleaning up test deal...")
    
    try:
        if deal:
            deal.delete()
            print("✅ Test deal cleaned up")
    except Exception as e:
        print(f"⚠️  Error cleaning up test deal: {e}")


def main():
    """Main test function."""
    print("🚀 Email Notification System Test")
    print("=" * 50)
    
    # Test 1: Email Configuration
    config_ok = test_email_configuration()
    if not config_ok:
        print("\n❌ Email configuration test failed. Please check admin settings.")
        return
    
    # Test 2: Create Test Deal
    test_deal = create_test_deal()
    if not test_deal:
        print("\n❌ Failed to create test deal.")
        return
    
    # Test 3: Notification Service
    notification_ok = test_notification_service(test_deal)
    
    # Cleanup
    cleanup_test_deal(test_deal)
    
    # Summary
    print("\n" + "=" * 50)
    print("📋 Test Summary:")
    print(f"✅ Email Configuration: {'PASS' if config_ok else 'FAIL'}")
    print(f"✅ Test Deal Creation: {'PASS' if test_deal else 'FAIL'}")
    print(f"✅ Email Notification: {'PASS' if notification_ok else 'FAIL'}")
    
    if config_ok and test_deal and notification_ok:
        print("\n🎉 All tests passed! Email notifications are working.")
        print("\n📧 To configure email settings:")
        print("1. Go to Django Admin: http://localhost:8000/admin/")
        print("2. Navigate to: Admin System Configs")
        print("3. Configure email settings in the 'Email Notifications' section")
        print("4. Set your email server credentials in 'Email Server Settings'")
    else:
        print("\n⚠️  Some tests failed. Please check the configuration.")
        print("\n🔧 Troubleshooting:")
        print("1. Ensure email settings are configured in Django Admin")
        print("2. Check SMTP server settings (host, port, credentials)")
        print("3. Verify email_notifications_enabled is set to True")
        print("4. Check Django logs for detailed error messages")


if __name__ == "__main__":
    main()
