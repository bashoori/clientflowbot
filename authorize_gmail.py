# authorize_gmail.py
import os
import smtplib
from email.message import EmailMessage
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

SMTP_EMAIL = os.getenv("SMTP_EMAIL")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD")

def send_welcome_email(name: str, recipient_email: str) -> bool:
    """
    Send a simple welcome email to a verified user using Gmail SMTP.
    Requires environment variables:
    - SMTP_EMAIL
    - SMTP_PASSWORD  (App Password from Gmail)
    """
    msg = EmailMessage()
    msg["Subject"] = "Welcome to Digital Marketing Business 🌟"
    msg["From"] = f"Digital Marketing Business <{SMTP_EMAIL}>"
    msg["To"] = recipient_email

    msg.set_content(
        f"Hello {name},\n\n"
        "Welcome to the Digital Marketing Business community! 🎉\n"
        "You're now part of a network that helps you learn, grow, and build your own online brand.\n\n"
        "If you don’t see this email in your inbox, please check your Spam folder and mark it as 'Not Spam'.\n\n"
        "Best,\nDigital Marketing Business Team"
    )

    try:
        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as smtp:
            smtp.login(SMTP_EMAIL, SMTP_PASSWORD)
            smtp.send_message(msg)
        print(f"✅ Welcome email sent to {recipient_email}")
        return True
    except Exception as e:
        print("❌ Email sending error:", e)
        return False
