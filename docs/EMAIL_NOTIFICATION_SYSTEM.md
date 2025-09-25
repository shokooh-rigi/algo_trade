# 📧 Email Notification System

## 🎯 Overview

The email notification system automatically sends email alerts when trading deals are generated. The system is fully integrated with the Django admin interface and provides comprehensive configuration options.

## ✨ Features

### 📬 **Automatic Deal Notifications**
- **Real-time Alerts**: Email sent immediately when a new deal is created
- **Detailed Information**: Complete deal details including risk management
- **HTML & Plain Text**: Both HTML and plain text email formats
- **Professional Templates**: Well-formatted email templates with styling

### ⚙️ **Admin Configuration**
- **Easy Setup**: Configure everything through Django Admin
- **Default Settings**: Pre-configured with your email (shokoohrigi22@gmail.com)
- **SMTP Support**: Full SMTP server configuration
- **Enable/Disable**: Toggle notifications on/off

### 🛡️ **Security & Reliability**
- **Error Handling**: Comprehensive error handling and logging
- **Fail-Safe**: System continues working even if email fails
- **Secure Storage**: Email credentials stored securely in database

## 🚀 **How It Works**

### 1. **Deal Generation Flow**
```
Strategy Generates Signal
         ↓
Deal Created in Database
         ↓
Email Notification Triggered
         ↓
Email Sent to Admin
```

### 2. **Email Content**
```
📧 Subject: 🚀 New Trading Deal Generated - BTCUSDT

📊 Deal Information:
- Deal ID: 12345678-abcd-efgh-ijkl-123456789012
- Strategy: BreakoutStrategy
- Market: BTCUSDT
- Provider: WALLEX

💰 Trade Details:
- Side: BUY
- Price: $42,150.00
- Quantity: 0.00100000
- Status: STARTED

🛡️ Risk Management:
- Stop Loss: $41,950.00
- Take Profit: $42,450.00
- Trailing Stop: Disabled

⏰ Generated at: 2024-01-15 14:30:00 UTC
```

## 📋 **Configuration Guide**

### Step 1: Access Django Admin
1. Navigate to: http://localhost:8000/admin/
2. Login with your admin credentials
3. Go to: **Admin System Configs**

### Step 2: Configure Email Settings
```
📧 Email Notifications Section:
✅ Email notifications enabled: True
📧 Admin email: shokoohrigi22@gmail.com
📧 From email: noreply@algo-trade.com

🔧 Email Server Settings:
🌐 Email host: smtp.gmail.com
🔌 Email port: 587
🔒 Use TLS: True
👤 Email host user: your_gmail@gmail.com
🔑 Email host password: your_app_password
```

### Step 3: Gmail App Password Setup
For Gmail, you need to create an App Password:

1. **Enable 2-Factor Authentication** on your Gmail account
2. **Generate App Password**:
   - Go to Google Account settings
   - Security → 2-Step Verification → App passwords
   - Select "Mail" and generate password
   - Use this password in "Email host password"

### Step 4: Environment Variables (Optional)
You can also set email credentials via environment variables:
```bash
EMAIL_HOST_USER=your_gmail@gmail.com
EMAIL_HOST_PASSWORD=your_app_password
DEFAULT_FROM_EMAIL=noreply@algo-trade.com
```

## 🔧 **Technical Implementation**

### Files Created/Modified:

#### 1. **NotificationService** (`algo/services/notification_service.py`)
- Main service for sending email notifications
- Handles HTML and plain text email formatting
- Error handling and logging
- Configuration management

#### 2. **AdminSystemConfig Model** (`algo/models.py`)
- Added email configuration fields:
  - `email_notifications_enabled`
  - `admin_email` (default: shokoohrigi22@gmail.com)
  - `from_email`
  - `email_host`
  - `email_port`
  - `email_use_tls`
  - `email_host_user`
  - `email_host_password`

#### 3. **Strategy Processor Integration** (`algo/services/strategy_processor_service.py`)
- Added deal creation from strategy signals
- Integrated email notification trigger
- Enhanced error handling

#### 4. **Django Settings** (`algo_trade/settings.py`)
- Added email backend configuration
- SMTP settings
- Default email configuration

#### 5. **Admin Interface** (`algo/admin.py`)
- Enhanced admin interface with email settings
- Organized fieldsets for easy configuration
- Help text and descriptions

#### 6. **Database Migration** (`algo/migrations/0007_add_email_notification_fields.py`)
- Migration for new email configuration fields

## 📊 **Email Templates**

### HTML Email Template
- Professional styling with CSS
- Color-coded trade sides (green for BUY, red for SELL)
- Organized sections for deal info, trade details, and risk management
- Responsive design

### Plain Text Email Template
- Clean, readable format
- All essential information included
- Fallback for email clients that don't support HTML

## 🧪 **Testing**

### Test Script (`test_email_notifications.py`)
Run the test script to verify everything is working:

```bash
cd /Users/wallex/PycharmProjects/algo_trade
python test_email_notifications.py
```

The test will:
1. ✅ Check email configuration
2. ✅ Create a test deal
3. ✅ Send test email notification
4. ✅ Clean up test data

### Manual Testing
1. **Create a Strategy Config** in Django Admin
2. **Activate the Strategy**
3. **Wait for Signal Generation**
4. **Check Your Email** for notifications

## 📈 **Notification Types**

### 1. **Deal Notifications** (Implemented)
- Sent when new deals are created
- Complete deal information
- Risk management details

### 2. **Strategy Status Notifications** (Available)
- Strategy start/stop events
- Error notifications
- Performance updates

### 3. **Emergency Notifications** (Available)
- Kill switch activation
- System errors
- Critical alerts

## 🔍 **Monitoring & Logs**

### Log Messages
The system logs all email activities:
```
INFO: Deal notification sent successfully for deal 12345678-abcd...
ERROR: Failed to send deal notification: SMTP connection failed
WARNING: Email notifications disabled, skipping notification
```

### Admin Monitoring
- View email settings in Django Admin
- Monitor deal creation and notifications
- Check system logs for email status

## ⚡ **Performance**

### Asynchronous Processing
- Email sending doesn't block deal processing
- Fail-safe: Trading continues even if email fails
- Efficient error handling

### Resource Usage
- Minimal impact on system performance
- Lightweight email templates
- Optimized database queries

## 🛠️ **Troubleshooting**

### Common Issues

#### 1. **No Emails Received**
- ✅ Check `email_notifications_enabled` is True
- ✅ Verify admin email address
- ✅ Check spam/junk folder
- ✅ Verify SMTP credentials

#### 2. **SMTP Authentication Failed**
- ✅ Use Gmail App Password (not regular password)
- ✅ Enable 2-Factor Authentication on Gmail
- ✅ Check email host and port settings

#### 3. **Emails Not Sending**
- ✅ Check Django logs for errors
- ✅ Verify internet connection
- ✅ Test SMTP settings manually
- ✅ Check firewall/security settings

#### 4. **HTML Formatting Issues**
- ✅ Check email client HTML support
- ✅ Verify CSS styling
- ✅ Test with different email clients

### Debug Commands
```bash
# Check email configuration
python manage.py shell
>>> from algo.models import AdminSystemConfig
>>> config = AdminSystemConfig.get_instance()
>>> print(config.admin_email)

# Test email sending
python test_email_notifications.py

# Check logs
docker-compose logs django_app | grep -i email
```

## 📚 **Future Enhancements**

### Planned Features
- 📊 **Email Templates**: Multiple template options
- 🔔 **Notification Types**: SMS, Slack, Discord integration
- 📈 **Performance Reports**: Weekly/monthly email reports
- 🎯 **Filtered Notifications**: Customizable notification rules
- 📱 **Mobile Notifications**: Push notifications for mobile apps

### Customization Options
- 🎨 **Custom Templates**: HTML email template customization
- ⏰ **Scheduling**: Batch notifications and digest emails
- 🔍 **Filtering**: Notification rules based on deal criteria
- 📊 **Analytics**: Email delivery and open rate tracking

## 🎉 **Summary**

The email notification system is now **fully operational** with:

✅ **Automatic deal notifications** sent to shokoohrigi22@gmail.com
✅ **Professional email templates** with complete deal information
✅ **Admin configuration** through Django Admin interface
✅ **Comprehensive error handling** and logging
✅ **Test script** for verification
✅ **Security best practices** implemented

**Your trading platform will now send you email alerts every time a new deal is generated!** 📧🚀

---

*For support or questions about the email notification system, check the logs or run the test script for diagnostics.*
