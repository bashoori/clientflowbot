import os
import json
import re
import smtplib
import imaplib
import email
import asyncio
import requests
from email.message import EmailMessage
from telegram import Update, ReplyKeyboardRemove
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    filters,
    ContextTypes,
    ConversationHandler,
)
from dotenv import load_dotenv

# ========== Load environment variables ==========
load_dotenv()
TOKEN = os.getenv("TELEGRAM_TOKEN")
SMTP_EMAIL = os.getenv("SMTP_EMAIL")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD")
GOOGLE_SHEET_URL = os.getenv("GOOGLE_SHEET_WEBAPP_URL")

DATA_FILE = "leads.json"
PDF_PATH = "docs/franchise_intro.pdf"

# ========== Helper Functions ==========
def save_data(data):
    with open(DATA_FILE, "w") as f:
        json.dump(data, f, indent=2)

def load_data():
    if not os.path.exists(DATA_FILE):
        with open(DATA_FILE, "w") as f:
            json.dump([], f)
        return []
    with open(DATA_FILE, "r") as f:
        try:
            return json.load(f)
        except json.JSONDecodeError:
            return []

def normalize_email(raw: str) -> str:
    return raw.replace("\u200c", "").replace("\u200f", "").strip().lower()

def is_valid_email(email_str: str) -> bool:
    pattern = r"^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$"
    return re.match(pattern, email_str) is not None

# ========== Send Email ==========
def send_email(name, recipient_email):
    msg = EmailMessage()
    msg["Subject"] = "ClientFlow Email Verification"
    msg["From"] = SMTP_EMAIL
    msg["To"] = recipient_email
    msg.set_content(
        f"Hello {name},\n\n"
        "This is a verification email from ClientFlow Digital Marketing.\n"
        "If you received this, it means your email address is working correctly.\n\n"
        "Thank you!\nClientFlow Team"
    )
    try:
        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as smtp:
            smtp.login(SMTP_EMAIL, SMTP_PASSWORD)
            smtp.send_message(msg)
        print(f"✅ Verification email sent to {recipient_email}")
        return True
    except Exception as e:
        print("Error sending email:", e)
        return False

# ========== Check Gmail Bounce ==========
def check_bounce_messages(target_email):
    """Check Gmail inbox for bounce messages related to the given email."""
    try:
        mail = imaplib.IMAP4_SSL("imap.gmail.com")
        mail.login(SMTP_EMAIL, SMTP_PASSWORD)
        mail.select("inbox")

        result, data = mail.search(None, '(FROM "mailer-daemon@googlemail.com" SINCE "1-Nov-2025")')
        if result != "OK":
            return False

        for num in data[0].split()[-10:]:
            result, msg_data = mail.fetch(num, "(RFC822)")
            if result != "OK":
                continue

            msg = email.message_from_bytes(msg_data[0][1])
            body = ""

            if msg.is_multipart():
                for part in msg.walk():
                    if part.get_content_type() == "text/plain":
                        try:
                            body += part.get_payload(decode=True).decode(errors="ignore")
                        except Exception:
                            continue
            else:
                body += msg.get_payload(decode=True).decode(errors="ignore")

            body_lower = body.lower()
            if target_email.lower() in body_lower and (
                "address not found" in body_lower
                or "no such user" in body_lower
                or "5.1.1" in body_lower
                or "does not exist" in body_lower
            ):
                print(f"🚨 Bounce detected for {target_email}")
                return True
        return False
    except Exception as e:
        print("Error checking Gmail:", e)
        return False

# ========== Conversation States ==========
ASK_NAME, ASK_EMAIL = range(2)

# ========== Telegram Bot Logic ==========
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = (
        "👋 سلام! خوش آمدید به دنیای **دیجیتال مارکتینگ حرفه‌ای**.\n\n"
        "ما یک فرانچایز بیزنس آنلاین در زمینه آموزش دیجیتال مارکتینگ ارائه می‌دهیم، "
        "که با آن می‌توانید مهارت‌های بازاریابی دیجیتال را یاد بگیرید و "
        "درآمد خود را از طریق سیستم آموزش و فروش ما آغاز کنید. 💼💻\n\n"
        "اگر دوست دارید توضیحات اولیه را برای شما ارسال کنیم، لطفاً نام خود را وارد کنید:"
    )
    await update.message.reply_text(text, parse_mode="Markdown")
    return ASK_NAME


async def ask_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["name"] = update.message.text.strip()
    await update.message.reply_text("خیلی خوب 🌟 حالا لطفاً ایمیل خود را وارد کنید:")
    return ASK_EMAIL


async def ask_email(update: Update, context: ContextTypes.DEFAULT_TYPE):
    email_input = normalize_email(update.message.text)
    name = context.user_data.get("name")

    if not is_valid_email(email_input):
        await update.message.reply_text("❌ ایمیل معتبر نیست. لطفاً مثل example@gmail.com وارد کنید:")
        return ASK_EMAIL

    leads = load_data()
    lead_record = {
        "name": name,
        "email": email_input,
        "user_id": update.effective_user.id,
        "username": update.effective_user.username,
        "status": "Pending"
    }
    leads.append(lead_record)
    save_data(leads)

    # Save to Google Sheet (initially Pending)
    try:
        payload = {
            "name": name,
            "email": email_input,
            "username": update.effective_user.username or "",
            "user_id": update.effective_user.id,
            "status": "Pending",
        }
        requests.post(GOOGLE_SHEET_URL, json=payload, timeout=10)
    except Exception as e:
        print(f"❌ Failed to send to Google Sheet: {e}")

    await update.message.reply_text(
        f"📧 در حال بررسی ایمیل ({email_input}) هستم، لطفاً صبر کنید...",
        reply_markup=ReplyKeyboardRemove(),
    )

    # Send verification email
    sent = send_email(name, email_input)
    if not sent:
        await update.message.reply_text("⚠️ ارسال ایمیل ناموفق بود. لطفاً بعداً دوباره امتحان کنید.")
        return ConversationHandler.END

    # Wait and check if bounced
    await asyncio.sleep(60)
    bounced = check_bounce_messages(email_input)

    # Update status in local data
    for lead in leads:
        if lead["email"] == email_input:
            lead["status"] = "Invalid" if bounced else "Verified"
            break
    save_data(leads)

    # Send status update to Google Sheet
    try:
        payload["status"] = "Invalid" if bounced else "Verified"
        requests.post(GOOGLE_SHEET_URL, json=payload, timeout=10)
    except Exception as e:
        print(f"⚠️ Couldn't update status in Google Sheet: {e}")

    if bounced:
        await update.message.reply_text(
            "❌ متأسفانه ایمیلی که وارد کردید وجود ندارد یا در دسترس نیست.\n"
            "لطفاً ایمیل صحیح خود را دوباره وارد کنید:"
        )
        return ASK_EMAIL

    # Send PDF only if verified
    await update.message.reply_text("✅ ایمیل شما تأیید شد! در حال ارسال فایل آموزشی هستم...")

    if os.path.exists(PDF_PATH) and os.path.getsize(PDF_PATH) > 0:
        await update.message.reply_document(
            document=open(PDF_PATH, "rb"),
            filename="Franchise_Intro.pdf",
            caption="📘 فایل معرفی فرانچایز دیجیتال مارکتینگ 👇",
        )
    else:
        await update.message.reply_text("⚠️ فایل معرفی در حال حاضر در دسترس نیست.")

    await update.message.reply_text("🎉 تبریک! ایمیل شما تأیید و ثبت شد 🌍")
    return ConversationHandler.END


async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("گفت‌وگو لغو شد.", reply_markup=ReplyKeyboardRemove())
    return ConversationHandler.END


# ========== Main ==========
def main():
    app = ApplicationBuilder().token(TOKEN).build()

    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            ASK_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, ask_name)],
            ASK_EMAIL: [MessageHandler(filters.TEXT & ~filters.COMMAND, ask_email)],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )

    app.add_handler(conv_handler)
    app.run_polling()


if __name__ == "__main__":
    main()
