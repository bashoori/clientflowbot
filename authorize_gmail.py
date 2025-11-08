import os
import smtplib
from email.message import EmailMessage
from dotenv import load_dotenv

# ======== Load environment variables ========
load_dotenv()

SMTP_EMAIL = os.getenv("SMTP_EMAIL")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD")

# ======== Gmail sending function ========
def send_welcome_email(name: str, recipient_email: str) -> bool:
    """
    Sends a simple welcome email to the new lead.
    Uses Gmail's SMTP with an App Password (recommended).
    """
    if not SMTP_EMAIL or not SMTP_PASSWORD:
        print("❌ Missing SMTP_EMAIL or SMTP_PASSWORD in environment.")
        return False

    msg = EmailMessage()
    msg["Subject"] = "🎉 Welcome to Digital Marketing Business"
    msg["From"] = f"Digital Marketing Business <{SMTP_EMAIL}>"
    msg["To"] = recipient_email

    msg.set_content(
        f"""سلام {name} 👋

به دنیای دیجیتال مارکتینگ خوش آمدی! 🚀  
ما خوشحالیم که همراه ما هستی.

📘 گام بعدی:
لطفاً ایمیل‌های آموزشی ما را دنبال کن — 
اگر در Inbox پیدایش نکردی، حتماً پوشه‌ی Spam را هم بررسی کن
و آن را به عنوان «Not Spam» علامت بزن تا ایمیل‌های بعدی را از دست ندهی.

با آرزوی موفقیت،  
تیم Digital Marketing Business
"""
    )

    try:
        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as smtp:
            smtp.login(SMTP_EMAIL, SMTP_PASSWORD)
            smtp.send_message(msg)
        print(f"✅ Welcome email sent successfully to {recipient_email}")
        return True

    except Exception as e:
        print(f"❌ Error sending email to {recipient_email}: {e}")
        return False
