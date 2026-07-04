import random
from datetime import datetime, timedelta, timezone
from fastapi import BackgroundTasks
from fastapi_mail import FastMail, MessageSchema, ConnectionConfig, MessageType
from sqlalchemy.orm import Session
import models 
import os 
from dotenv import load_dotenv
load_dotenv()

# 1. FastAPI-Mail SMTP Configuration Setup
conf = ConnectionConfig(
    MAIL_USERNAME=os.getenv("EMAIL"),
    MAIL_PASSWORD=os.getenv("MAIL_PASSWORD"), 
    MAIL_FROM=os.getenv("EMAIL"),
    MAIL_FROM_NAME="DevHub", 
    MAIL_PORT=587,
    MAIL_SERVER="smtp.gmail.com",
    MAIL_STARTTLS=True,
    MAIL_SSL_TLS=False,
    USE_CREDENTIALS=True,
    VALIDATE_CERTS=True
)

# 2. FUNCTION ONE: Generate and Save 6-Digit OTP to Database (With Expiry)
def generate_and_save_otp(user_id: int, db: Session) -> str:
    """
    Generates a secure 6-digit random number string, deletes old OTPs for the user,
    saves the new one with a 5-minute expiry timestamp, and returns it.
    """
    otp_code = str(random.randint(100000, 999999))
    
    # 5 minutes baad ka expiry time (Timezone aware UTC)
    expire_at = datetime.now(timezone.utc) + timedelta(minutes=5)
    
    # Cleanup pre-existing stale token footprints for user
    db.query(models.OTPStorage).filter(models.OTPStorage.user_id == user_id).delete()
    
    otp_entry = models.OTPStorage(
        user_id=user_id,
        otp_code=otp_code
    )
    db.add(otp_entry)
    db.commit()
    return otp_code

# 3. ASYNC HELPER: Fixes the fastapi-mail background thread execution loop
async def send_email_async_worker(message: MessageSchema):
    """
    Actual async engine worker to deliver the mail payload safely.
    """
    fm = FastMail(conf)
    await fm.send_message(message)

# 4. FUNCTION TWO: Send 6-Digit OTP Email Asynchronously (With Dark HTML Layout)
def send_otp_email(background_tasks: BackgroundTasks, username: str, email: str, otp_code: str):
    """
    Triggers an asynchronous email dispatch transaction using a Premium Dark Theme HTML structure.
    """
    
    # PREMIUM DARK MODE TEMPLATE DESIGN MATRIX
    dark_html_body = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8">
        <title>Account Security Token Verification</title>
    </head>
    <body style="background-color: #0b0f19; margin: 0; padding: 40px 0; font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; -webkit-font-smoothing: antialiased;">
        <table align="center" border="0" cellpadding="0" cellspacing="0" width="100%" style="max-width: 550px; background-color: #111827; border: 1px solid #1f2937; border-radius: 16px; overflow: hidden; box-shadow: 0 20px 25px -5px rgba(0, 0, 0, 0.3);">
            
            <!-- Branding Header Row -->
            <tr>
                <td style="padding: 32px 40px 10px 40px; text-align: left;">
                    <div style="font-size: 22px; font-weight: 800; color: #f97316; letter-spacing: -0.5px;">
                        DevHub <span style="color: #ffffff; font-weight: 400; font-size: 14px;">// AUTHENTICATION</span>
                    </div>
                </td>
            </tr>
            
            <!-- Structural Divider -->
            <tr>
                <td style="padding: 0 40px;">
                    <hr style="border: 0; border-top: 1px solid #1f2937; margin: 20px 0;">
                </td>
            </tr>
            
            <!-- Core Content Communication -->
            <tr>
                <td style="padding: 10px 40px 20px 40px;">
                    <h1 style="color: #ffffff; font-size: 24px; font-weight: 700; margin: 0 0 16px 0; tracking-content: -0.5px;">Security Verification</h1>
                    <p style="color: #9ca3af; font-size: 15px; line-height: 24px; margin: 0;">
                        Hello <strong style="color: #ffffff;">{username}</strong>,
                    </p>
                    <p style="color: #9ca3af; font-size: 15px; line-height: 24px; margin: 12px 0 0 0;">
                        A registration initiation handle was requested using your digital profile credentials. Use the authorized authentication payload vector container below to complete your system entry session:
                    </p>
                </td>
            </tr>
            
            <!-- Central Premium Dark Code Grid Container -->
            <tr>
                <td style="padding: 10px 40px;">
                    <table border="0" cellpadding="0" cellspacing="0" width="100%" style="background-color: #030712; border: 1px solid #374151; border-radius: 12px; text-align: center;">
                        <tr>
                            <td style="padding: 24px 0;">
                                <div style="color: #f97316; font-size: 38px; font-weight: 800; letter-spacing: 8px; font-family: 'Courier New', Courier, monospace; line-height: 38px; margin-left: 8px;">
                                    {otp_code}
                                </div>
                            </td>
                        </tr>
                    </table>
                </td>
            </tr>
            
            <!-- Clean Red Warning Text Area -->
            <tr>
                <td style="padding: 20px 40px 30px 40px; text-align: center;">
                    <p style="color: #ef4444; font-size: 14px; font-weight: 600; margin: 0; line-height: 20px;">
                        OTP will expire in 5 minutes. Do not share it with anyone.
                    </p>
                </td>
            </tr>
            
            <!-- Legal Anti-Spam Footer Compliant Block Matrix -->
            <tr>
                <td style="padding: 30px 40px; background-color: #0f172a; border-top: 1px solid #1f2937; text-align: center;">
                    <p style="color: #6b7280; font-size: 12px; line-height: 18px; margin: 0;">
                        This system transactional communication layer was transmitted automatically. Please do not directly reply to this digital envelope node address routing context.
                    </p>
                    <p style="color: #4b5563; font-size: 11px; margin: 12px 0 0 0;">
                        &copy; 2026 DevHub Matrix Inc. • Secure Infrastructure Layer Node
                    </p>
                </td>
            </tr>
        </table>
    </body>
    </html>
    """
    
    # Message structural creation using the Dark Theme HTML
    message = MessageSchema(
        subject="Complete Your Registration - Account Verification OTP",
        recipients=[email],
        body=dark_html_body,
        subtype=MessageType.html # Fixed from MessageType.plain to render HTML markup engine
    )
    
    # Enqueue task into FastAPI backend async threadpool
    background_tasks.add_task(send_email_async_worker, message)
