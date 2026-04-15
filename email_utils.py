# email_utils.py - Updated for SendGrid API (works on Render free tier)
from flask import current_app, url_for
import logging
import secrets
from datetime import datetime, timedelta
import os

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Try to import SendGrid
try:
    from sendgrid import SendGridAPIClient
    from sendgrid.helpers.mail import Mail, Email, To, Content, HtmlContent
    HAS_SENDGRID = True
    logger.info("✅ SendGrid imported successfully")
except ImportError:
    logger.warning("SendGrid not installed. Using development email mock.")
    HAS_SENDGRID = False

# Try to import Flask-Mail as fallback (for local development)
try:
    from flask_mail import Mail, Message
    HAS_FLASK_MAIL = True
except ImportError:
    HAS_FLASK_MAIL = False

# Mock mail for development
mail = None
if HAS_FLASK_MAIL:
    mail = Mail()


def get_base_url():
    """Get the base URL from config"""
    site_url = current_app.config.get('SITE_URL')
    if site_url:
        return site_url.rstrip('/')
    return 'https://mymsce-0sr3.onrender.com'


def site_url_for(endpoint, **kwargs):
    """Generate a URL using the site URL instead of localhost"""
    base_url = get_base_url()
    path = url_for(endpoint, **kwargs)
    return f"{base_url}{path}"


def generate_token(email):
    """Generate a secure token for email verification"""
    if HAS_FLASK_MAIL:
        from itsdangerous import URLSafeTimedSerializer
        serializer = URLSafeTimedSerializer(current_app.config['SECRET_KEY'])
        return serializer.dumps(email, salt='email-confirm')
    else:
        return secrets.token_urlsafe(32)


def confirm_token(token, expiration=3600):
    """Verify email token"""
    if HAS_FLASK_MAIL:
        from itsdangerous import URLSafeTimedSerializer
        serializer = URLSafeTimedSerializer(current_app.config['SECRET_KEY'])
        try:
            email = serializer.loads(token, salt='email-confirm', max_age=expiration)
            return email
        except:
            return False
    else:
        logger.info(f"Token confirmed (dev mode): {token}")
        return "dev@example.com"


def send_email_sendgrid(recipient, subject, html_content):
    """Send email using SendGrid API (works on Render free tier)"""
    if not HAS_SENDGRID:
        logger.warning("SendGrid not available, using mock mode")
        print(f"\n📧 [MOCK] Would send email to: {recipient}")
        print(f"   Subject: {subject}")
        print(f"   Content: {html_content[:200]}...\n")
        return True
    
    try:
        api_key = os.getenv('SENDGRID_API_KEY')
        if not api_key:
            logger.error("SENDGRID_API_KEY not set in environment variables")
            return False
        
        from_email = current_app.config.get('MAIL_DEFAULT_SENDER', 'myMSCE <noreply@mymsce.com>')
        
        message = Mail(
            from_email=from_email,
            to_emails=recipient,
            subject=subject,
            html_content=html_content
        )
        
        sg = SendGridAPIClient(api_key)
        response = sg.send(message)
        
        if response.status_code in [200, 202]:
            logger.info(f"✅ Email sent to {recipient} via SendGrid")
            print(f"✅ Email sent to {recipient}")
            return True
        else:
            logger.error(f"SendGrid returned status {response.status_code}: {response.body}")
            return False
            
    except Exception as e:
        logger.error(f"SendGrid error: {str(e)}")
        print(f"❌ SendGrid error: {str(e)}")
        return False


def send_verification_email(user):
    """Send email verification link"""
    try:
        token = generate_token(user.email)
        base_url = get_base_url()
        verify_url = f"{base_url}/verify-email/{token}"

        print(f"📧 Verification URL for {user.email}: {verify_url}")
        logger.info(f"Verification URL for {user.email}: {verify_url}")

        html_content = f'''
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
        </head>
        <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333; max-width: 600px; margin: 0 auto; padding: 20px;">
            <div style="background: linear-gradient(135deg, #2c3e50, #3498db); color: white; padding: 30px; text-align: center; border-radius: 10px 10px 0 0;">
                <h1 style="margin: 0; font-size: 28px;">myMSCE</h1>
                <p style="margin: 10px 0 0; opacity: 0.9;">Email Verification</p>
            </div>

            <div style="background: #f9f9f9; padding: 30px; border-radius: 0 0 10px 10px; border: 1px solid #ddd; border-top: none;">
                <h2 style="color: #2c3e50; margin-top: 0;">Welcome, {user.username}!</h2>

                <p style="margin-bottom: 20px;">Thank you for registering with myMSCE. Please verify your email address by clicking the button below:</p>

                <div style="text-align: center; margin: 30px 0;">
                    <a href="{verify_url}" style="background: #3498db; color: white; padding: 12px 30px; text-decoration: none; border-radius: 5px; font-weight: bold; display: inline-block;">Verify Email Address</a>
                </div>

                <p style="color: #666; font-size: 14px;">Or copy and paste this link in your browser:</p>
                <p style="background: #fff; padding: 10px; border: 1px solid #ddd; border-radius: 5px; word-break: break-all; font-size: 12px;">{verify_url}</p>

                <p style="color: #666; font-size: 14px; margin-top: 20px;">This link will expire in 1 hour for security reasons.</p>

                <hr style="border: none; border-top: 1px solid #ddd; margin: 20px 0;">

                <p style="color: #999; font-size: 12px; text-align: center;">If you didn't create an account with myMSCE, please ignore this email.</p>
            </div>
        </body>
        </html>
        '''

        return send_email_sendgrid(user.email, 'Verify your myMSCE email', html_content)

    except Exception as e:
        error_msg = f"Verification email sending failed: {str(e)}"
        print(f"❌ {error_msg}")
        logger.error(error_msg)
        return False


def send_welcome_email(user):
    """Send welcome email after verification"""
    try:
        base_url = get_base_url()
        login_url = f"{base_url}/login"

        print(f"🎉 Sending welcome email to {user.email}")
        logger.info(f"Sending welcome email to {user.email}")

        html_content = f'''
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
        </head>
        <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333; max-width: 600px; margin: 0 auto; padding: 20px;">
            <div style="background: linear-gradient(135deg, #27ae60, #2ecc71); color: white; padding: 30px; text-align: center; border-radius: 10px 10px 0 0;">
                <h1 style="margin: 0; font-size: 28px;">Welcome to myMSCE!</h1>
            </div>

            <div style="background: #f9f9f9; padding: 30px; border-radius: 0 0 10px 10px; border: 1px solid #ddd; border-top: none;">
                <h2 style="color: #2c3e50; margin-top: 0;">Hi {user.username}!</h2>

                <p style="margin-bottom: 20px;">Your email has been successfully verified. You can now login and start your MSCE preparation journey!</p>

                <div style="background: #fff; padding: 20px; border-radius: 5px; margin: 20px 0;">
                    <h3 style="color: #2c3e50; margin-top: 0;">What's next?</h3>
                    <ul style="padding-left: 20px;">
                        <li>Browse our free sample lessons</li>
                        <li>Choose a subscription plan that suits you</li>
                        <li>Access quality video lessons and materials</li>
                        <li>Track your progress</li>
                    </ul>
                </div>

                <div style="text-align: center; margin: 30px 0;">
                    <a href="{login_url}" style="background: #3498db; color: white; padding: 12px 30px; text-decoration: none; border-radius: 5px; font-weight: bold; display: inline-block;">Login to myMSCE</a>
                </div>

                <hr style="border: none; border-top: 1px solid #ddd; margin: 20px 0;">

                <p style="color: #999; font-size: 12px; text-align: center;">Best regards,<br>The myMSCE Team</p>
            </div>
        </body>
        </html>
        '''

        return send_email_sendgrid(user.email, 'Welcome to myMSCE!', html_content)

    except Exception as e:
        error_msg = f"Welcome email sending failed for {user.email}: {str(e)}"
        print(f"❌ {error_msg}")
        logger.error(error_msg)
        return False


def send_password_reset_code(user, code):
    """Send 6-digit password reset code via email"""
    try:
        html_content = f'''
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
        </head>
        <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333; max-width: 600px; margin: 0 auto; padding: 20px;">
            <div style="background: linear-gradient(135deg, #fbbf24, #f59e0b); color: #1a2b4c; padding: 30px; text-align: center; border-radius: 10px 10px 0 0;">
                <h1 style="margin: 0; font-size: 28px;">myMSCE</h1>
                <p style="margin: 10px 0 0;">Password Reset Code</p>
            </div>
            
            <div style="background: #f9f9f9; padding: 30px; border-radius: 0 0 10px 10px; border: 1px solid #ddd; border-top: none;">
                <h2 style="color: #1a2b4c; margin-top: 0;">Hi {user.username}!</h2>
                
                <p>Use the code below to reset your password. This code expires in <strong>15 minutes</strong>.</p>
                
                <div style="text-align: center; margin: 30px 0;">
                    <div style="background: #fff; padding: 20px; border-radius: 12px; border: 2px solid #fbbf24; display: inline-block;">
                        <span style="font-size: 36px; font-weight: 800; letter-spacing: 8px; color: #1a2b4c;">{code}</span>
                    </div>
                </div>
                
                <p style="color: #666; font-size: 14px;">Enter this code on the website to continue.</p>
                
                <hr style="border: none; border-top: 1px solid #ddd; margin: 20px 0;">
                
                <p style="color: #999; font-size: 12px; text-align: center;">If you didn't request this, please ignore this email.</p>
            </div>
        </body>
        </html>
        '''
        
        return send_email_sendgrid(user.email, 'Password Reset Code - myMSCE', html_content)
            
    except Exception as e:
        print(f"❌ Failed to send reset code: {e}")
        return False


def send_verification_code(user, code):
    """Send 6-digit verification code via email"""
    try:
        html_content = f'''
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
        </head>
        <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333; max-width: 600px; margin: 0 auto; padding: 20px;">
            <div style="background: linear-gradient(135deg, #fbbf24, #f59e0b); color: #1a2b4c; padding: 30px; text-align: center; border-radius: 10px 10px 0 0;">
                <h1 style="margin: 0; font-size: 28px;">myMSCE</h1>
                <p style="margin: 10px 0 0;">Email Verification Code</p>
            </div>
            
            <div style="background: #f9f9f9; padding: 30px; border-radius: 0 0 10px 10px; border: 1px solid #ddd; border-top: none;">
                <h2 style="color: #1a2b4c; margin-top: 0;">Welcome, {user.username}!</h2>
                
                <p>Use the code below to verify your email address. This code expires in <strong>15 minutes</strong>.</p>
                
                <div style="text-align: center; margin: 30px 0;">
                    <div style="background: #fff; padding: 20px; border-radius: 12px; border: 2px solid #fbbf24; display: inline-block;">
                        <span style="font-size: 36px; font-weight: 800; letter-spacing: 8px; color: #1a2b4c;">{code}</span>
                    </div>
                </div>
                
                <p style="color: #666; font-size: 14px;">Enter this code on the website to complete your registration.</p>
                
                <hr style="border: none; border-top: 1px solid #ddd; margin: 20px 0;">
                
                <p style="color: #999; font-size: 12px; text-align: center;">If you didn't create an account with myMSCE, please ignore this email.</p>
            </div>
        </body>
        </html>
        '''
        
        return send_email_sendgrid(user.email, 'Verify your email - myMSCE', html_content)
            
    except Exception as e:
        print(f"❌ Failed to send verification code: {e}")
        return False


def send_payment_confirmation_email(user, payment):
    """Send payment confirmation email"""
    try:
        base_url = get_base_url()
        dashboard_url = f"{base_url}/dashboard"

        subscription_form_upper = payment.subscription_form.upper() if payment.subscription_form else ''
        subscription_type_upper = payment.subscription_type.upper() if payment.subscription_type else ''

        html_content = f'''
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
        </head>
        <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333; max-width: 600px; margin: 0 auto; padding: 20px;">
            <div style="background: linear-gradient(135deg, #27ae60, #2ecc71); color: white; padding: 30px; text-align: center; border-radius: 10px 10px 0 0;">
                <h1 style="margin: 0; font-size: 28px;">Payment Successful!</h1>
            </div>

            <div style="background: #f9f9f9; padding: 30px; border-radius: 0 0 10px 10px; border: 1px solid #ddd; border-top: none;">
                <h2 style="color: #2c3e50; margin-top: 0;">Thank you for subscribing, {user.username}!</h2>

                <div style="background: #fff; padding: 20px; border-radius: 5px; margin: 20px 0;">
                    <h3 style="color: #2c3e50; margin-top: 0;">Payment Details:</h3>
                    <table style="width: 100%; border-collapse: collapse;">
                        <tr>
                            <td style="padding: 8px 0;"><strong>Amount:</strong></td>
                            <td style="padding: 8px 0;">MWK {payment.amount:,.0f}</td>
                        </tr>
                        <tr>
                            <td style="padding: 8px 0;"><strong>Subscription:</strong></td>
                            <td style="padding: 8px 0;">{subscription_form_upper} - {subscription_type_upper}</td>
                        </tr>
                        <tr>
                            <td style="padding: 8px 0;"><strong>Reference:</strong></td>
                            <td style="padding: 8px 0;">{payment.reference}</td>
                        </tr>
                        <tr>
                            <td style="padding: 8px 0;"><strong>Date:</strong></td>
                            <td style="padding: 8px 0;">{payment.completed_at.strftime('%Y-%m-%d %H:%M') if payment.completed_at else 'N/A'}</td>
                        </tr>
                    </table>
                </div>

                <div style="text-align: center; margin: 30px 0;">
                    <a href="{dashboard_url}" style="background: #3498db; color: white; padding: 12px 30px; text-decoration: none; border-radius: 5px; font-weight: 600; display: inline-block;">Go to Dashboard</a>
                </div>

                <hr style="border: none; border-top: 1px solid #ddd; margin: 20px 0;">

                <p style="color: #999; font-size: 12px; text-align: center;">Best regards,<br>The myMSCE Team</p>
            </div>
        </body>
        </html>
        '''

        return send_email_sendgrid(user.email, 'Payment Confirmed - myMSCE Subscription', html_content)

    except Exception as e:
        error_msg = f"Payment confirmation email failed: {str(e)}"
        print(f"❌ {error_msg}")
        logger.error(error_msg)
        return False


def test_smtp_connection():
    """Test email connection (now uses SendGrid)"""
    if HAS_SENDGRID:
        api_key = os.getenv('SENDGRID_API_KEY')
        if api_key:
            return True, "SendGrid API key is configured"
        else:
            return False, "SENDGRID_API_KEY not set"
    else:
        return False, "SendGrid not installed"