# email_utils.py
from flask import current_app, url_for
import logging
import secrets
from datetime import datetime, timedelta
import smtplib
import socket
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Try to import Flask-Mail, but don't fail if it's not available
try:
    from flask_mail import Mail, Message

    mail = Mail()
    HAS_FLASK_MAIL = True
except ImportError:
    logger.warning("Flask-Mail not installed. Using development email mock.")
    HAS_FLASK_MAIL = False


    # Create mock classes
    class Mail:
        def __init__(self, app=None):
            pass

        def init_app(self, app):
            pass

        def send(self, msg):
            logger.info(f"📧 [MOCK] Would send email: {msg.subject}")
            return True


    class Message:
        def __init__(self, subject, recipients, html, sender=None):
            self.subject = subject
            self.recipients = recipients
            self.html = html
            self.sender = sender


    mail = Mail()


def get_base_url():
    """Get the base URL from config"""
    # First try SITE_URL from config
    site_url = current_app.config.get('SITE_URL')

    if site_url:
        return site_url.rstrip('/')

    # Fallback to Render URL
    return 'https://mymsce3.onrender.com'


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
        # Simple token for development
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
        # In development, accept any token
        logger.info(f"Token confirmed (dev mode): {token}")
        return "dev@example.com"


def send_verification_email(user):
    """Send email verification link with error handling"""
    try:
        token = generate_token(user.email)
        base_url = get_base_url()
        verify_url = f"{base_url}/verify-email/{token}"

        # Log the URL for debugging
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

        if HAS_FLASK_MAIL:
            # Get sender from config
            sender = current_app.config.get('MAIL_DEFAULT_SENDER', 'myMSCE <mymsce3@gmail.com>')

            # Create email message with explicit sender
            msg = Message(
                subject='Verify your myMSCE email',
                recipients=[user.email],
                html=html_content,
                sender=sender
            )

            # Try to send
            mail.send(msg)
            print(f"✅ Verification email sent to {user.email}")
            logger.info(f"Verification email sent to {user.email}")
        else:
            # Development mode - just log
            print("\n" + "🔥" * 50)
            print("VERIFICATION LINK FOR:", user.email)
            print(verify_url)
            print("🔥" * 50 + "\n")
            logger.info(f"Development mode: Verification email logged for {user.email}")

        return True

    except Exception as e:
        error_msg = f"Verification email sending failed: {str(e)}"
        print(f"❌ {error_msg}")
        logger.error(error_msg)
        return False
def send_welcome_email(user):
    """Send welcome email after verification with error handling"""
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

        if HAS_FLASK_MAIL:
            msg = Message(
                subject='Welcome to myMSCE!',
                recipients=[user.email],
                html=html_content
            )
            mail.send(msg)
            print(f"✅ Welcome email sent to {user.email}")
            logger.info(f"Welcome email sent to {user.email}")

    except Exception as e:
        error_msg = f"Welcome email sending failed for {user.email}: {str(e)}"
        print(f"❌ {error_msg}")
        logger.error(error_msg)

def send_password_reset_code_email(user, code):
    """Send password reset code via email"""
    try:
        base_url = get_base_url()
        
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
                
                <p style="margin-bottom: 20px;">Use the code below to reset your password. This code will expire in 15 minutes.</p>
                
                <div style="text-align: center; margin: 30px 0;">
                    <div style="background: #fff; padding: 20px; border-radius: 12px; border: 2px solid #fbbf24; display: inline-block;">
                        <span style="font-size: 36px; font-weight: 800; letter-spacing: 8px; color: #1a2b4c;">{code}</span>
                    </div>
                </div>
                
                <p style="color: #666; font-size: 14px;">Enter this code on the password reset page to continue.</p>
                
                <hr style="border: none; border-top: 1px solid #ddd; margin: 20px 0;">
                
                <p style="color: #999; font-size: 12px; text-align: center;">If you didn't request a password reset, please ignore this email.</p>
            </div>
        </body>
        </html>
        '''
        
        if HAS_FLASK_MAIL:
            msg = Message(
                subject='Password Reset Code - myMSCE',
                recipients=[user.email],
                html=html_content
            )
            mail.send(msg)
            print(f"✅ Reset code sent to {user.email}")
            return True
        else:
            print(f"📧 [MOCK] Reset code for {user.email}: {code}")
            return True
            
    except Exception as e:
        print(f"❌ Failed to send reset code: {e}")
        return False

def send_payment_confirmation_email(user, payment):
    """Send payment confirmation email with error handling"""
    try:
        base_url = get_base_url()
        dashboard_url = f"{base_url}/dashboard"

        print(f"💰 Sending payment confirmation email to {user.email}")
        logger.info(f"Sending payment confirmation email to {user.email}")

        # Format the values in Python first
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
                            <td style="padding: 8px 0;">MWK {payment.amount:,}</td>
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

                <p style="margin-bottom: 20px;">You now have full access to all {subscription_form_upper} lessons and materials.</p>

                <div style="text-align: center; margin: 30px 0;">
                    <a href="{dashboard_url}" style="background: #3498db; color: white; padding: 12px 30px; text-decoration: none; border-radius: 5px; font-weight: 600; display: inline-block;">Go to Dashboard</a>
                </div>

                <hr style="border: none; border-top: 1px solid #ddd; margin: 20px 0;">

                <p style="color: #999; font-size: 12px; text-align: center;">Best regards,<br>The myMSCE Team</p>
            </div>
        </body>
        </html>
        '''

        if HAS_FLASK_MAIL:
            msg = Message(
                subject='Payment Confirmed - myMSCE Subscription',
                recipients=[user.email],
                html=html_content
            )
            mail.send(msg)
            print(f"✅ Payment confirmation email sent to {user.email}")
            logger.info(f"Payment confirmation email sent to {user.email}")

    except Exception as e:
        error_msg = f"Payment confirmation email sending failed for {user.email}: {str(e)}"
        print(f"❌ {error_msg}")
        logger.error(error_msg)


def send_password_reset_code(user, code):
    """Send 6-digit password reset code via email"""
    try:
        base_url = get_base_url()
        
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
        
        if HAS_FLASK_MAIL:
            msg = Message(
                subject='Password Reset Code - myMSCE',
                recipients=[user.email],
                html=html_content
            )
            mail.send(msg)
            print(f"✅ Reset code sent to {user.email}")
            return True
        else:
            print(f"\n📧 [MOCK] Reset code for {user.email}: {code}\n")
            return True
            
    except Exception as e:
        print(f"❌ Failed to send reset code: {e}")
        return False


def send_verification_code(user, code):
    """Send 6-digit verification code via email"""
    try:
        base_url = get_base_url()
        
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
        
        if HAS_FLASK_MAIL:
            msg = Message(
                subject='Verify your email - myMSCE',
                recipients=[user.email],
                html=html_content
            )
            mail.send(msg)
            print(f"✅ Verification code sent to {user.email}")
            return True
        else:
            print(f"\n📧 [MOCK] Verification code for {user.email}: {code}\n")
            return True
            
    except Exception as e:
        print(f"❌ Failed to send verification code: {e}")
        return False

def test_smtp_connection():
    """Test SMTP connection configuration"""
    from flask import current_app

    try:
        print("Testing SMTP connection...")
        server = smtplib.SMTP(
            current_app.config['MAIL_SERVER'],
            current_app.config['MAIL_PORT'],
            timeout=10
        )
        server.starttls()
        server.login(
            current_app.config['MAIL_USERNAME'],
            current_app.config['MAIL_PASSWORD']
        )
        server.quit()
        print("✅ SMTP connection successful!")
        return True, "SMTP connection successful!"
    except smtplib.SMTPAuthenticationError as e:
        error_msg = f"Authentication failed: {str(e)}"
        print(f"❌ {error_msg}")
        return False, error_msg
    except socket.timeout:
        error_msg = "Connection timeout"
        print(f"❌ {error_msg}")
        return False, error_msg
    except socket.error as e:
        error_msg = f"Network error: {str(e)}"
        print(f"❌ {error_msg}")
        return False, error_msg
    except Exception as e:
        error_msg = f"Error: {str(e)}"
        print(f"❌ {error_msg}")
        return False, error_msg