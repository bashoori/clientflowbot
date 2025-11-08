# app.py
import os
import re
import json
import asyncio
import requests
from datetime import datetime
from flask import Flask, request

from telegram import Update, ReplyKeyboardMarkup, ReplyKeyboardRemove
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    ConversationHandler,
    ContextTypes,
    filters,
)

# ========== Config (from env) ==========
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
GOOGLE_SHEET_WEBAPP_URL = os.getenv("GOOGLE_SHEET_WEBAPP_URL")  # Apps Script WebApp URL
ROOT_URL = os.getenv("ROOT_URL", "https://digitalmarketingbiz-bot.onrender.com")
PORT = int(os.getenv("PORT", "10000"))

if not TELEGRAM_TOKEN:
    raise RuntimeError("Missing TELEGRAM_TOKEN environment variable")

# ========== Local file for backup ==========
LEADS_FILE = "leads.json"

def load_leads():
    if not os.path.exists(LEADS_FILE):
        return []
    try:
        with open(LEADS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return []

def save_leads(leads):
    with open(LEADS_FILE, "w", encoding="utf-8") as f:
        json.dump(leads, f, ensure_ascii=False, indent=2)

# ========== Helpers ==========
def normalize_email(raw: str) -> str:
    if not raw:
        return ""
    # remove common zero-width / bidi characters and whitespace, then lowercase
    cleaned = raw.replace("\u200c", "").replace("\u200f", "").strip().lower()
    return cleaned

# A reasonably strict regex for validating typical emails; we normalize before testing.
EMAIL_RE = re.compile(r"^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$")

def is_valid_email(email_str: str) -> bool:
    if not email_str:
        return False
    email_str = email_str.strip()
    return EMAIL_RE.match(email_str) is not None

def post_to_sheet(payload: dict, timeout: int = 10) -> bool:
    """Best-effort post to Google Apps Script WebApp."""
    if not GOOGLE_SHEET_WEBAPP_URL:
        print("⚠️ GOOGLE_SHEET_WEBAPP_URL not set; skipping post_to_sheet")
        return False
    try:
        resp = requests.post(GOOGLE_SHEET_WEBAPP_URL, json=payload, timeout=timeout)
        print(f"📤 Sheet POST status: {resp.status_code} - {resp.text[:200]}")
        return resp.status_code == 200
    except Exception as e:
        print("❌ post_to_sheet error:", e)
        return False

# ========== Conversation states ==========
ASK_NAME, ASK_EMAIL = range(2)

# ========== Telegram handlers ==========
async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Send intro text + simple menu (Persian)."""
    intro = (
        "👋 سلام! خوش آمدید به Digital Marketing Business.\n\n"
        "ما آموزش و راه‌اندازی کسب‌وکار اینترنتی و دیجیتال مارکتینگ را ساده می‌کنیم.\n"
        "اگر دوست دارید اطلاعات اولیه را دریافت کنید یا ثبت نام کنید، یکی از گزینه‌ها را انتخاب کنید."
    )
    # small menu with two options (you can add another if you want)
    keyboard = ReplyKeyboardMarkup([["درباره ما", "ثبت نام"]], resize_keyboard=True, one_time_keyboard=True)
    await update.message.reply_text(intro, reply_markup=keyboard)

    # Do not start the conversation here — wait for user to press "ثبت نام"
    return

async def start_registration(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """User chose 'ثبت نام' — ask for name and start conversation."""
    await update.message.reply_text("خوب! لطفاً نام کامل خود را وارد کنید:", reply_markup=ReplyKeyboardRemove())
    return ASK_NAME

async def ask_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    name = update.message.text.strip()
    context.user_data["name"] = name
    await update.message.reply_text("خیلی خوب 🌟 حالا لطفاً ایمیل خود را وارد کنید:")
    return ASK_EMAIL

async def ask_email(update: Update, context: ContextTypes.DEFAULT_TYPE):
    raw_email = update.message.text.strip()
    email_norm = normalize_email(raw_email)
    name = context.user_data.get("name", "").strip()

    if not is_valid_email(email_norm):
        await update.message.reply_text("❌ ایمیل معتبر نیست. لطفاً دوباره وارد کنید یا /cancel برای خروج.")
        return ASK_EMAIL

    lead = {
        "name": name,
        "email": email_norm,
        "user_id": update.effective_user.id if update.effective_user else None,
        "username": update.effective_user.username if update.effective_user else None,
        "status": "Validated",
        "created_at": datetime.utcnow().isoformat() + "Z"
    }

    # Save local backup
    leads = load_leads()
    leads.append(lead)
    try:
        save_leads(leads)
        print("💾 Saved lead locally:", lead)
    except Exception as e:
        print("⚠️ Failed to save local lead:", e)

    # Try to post to sheet
    posted = post_to_sheet({
        "name": lead["name"],
        "email": lead["email"],
        "username": lead["username"] or "",
        "user_id": lead["user_id"] or "",
        "status": lead["status"],
    })

    if posted:
        await update.message.reply_text(
            f"✅ ایمیل شما ({email_norm}) معتبر است و ثبت شد. ممنون! ما ممکن است بعداً با شما تماس بگیریم."
        )
    else:
        await update.message.reply_text(
            f"✅ ایمیل شما ({email_norm}) معتبر است و به‌صورت محلی ذخیره شد.\n"
            "اما ارسال به Google Sheet با خطا مواجه شد — بعداً بررسی می‌کنم."
        )

    return ConversationHandler.END

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("گفت‌وگو لغو شد.", reply_markup=ReplyKeyboardRemove())
    return ConversationHandler.END

# ========== Build Application (telegram) ==========
application = Application.builder().token(TELEGRAM_TOKEN).build()

# Conversation: triggered by a message "ثبت نام" (we also add a regex to accept English "register" optionally)
conv_handler = ConversationHandler(
    entry_points=[
        MessageHandler(filters.Regex(r"^(ثبت نام|register|Register|Register)$"), start_registration)
    ],
    states={
        ASK_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, ask_name)],
        ASK_EMAIL: [MessageHandler(filters.TEXT & ~filters.COMMAND, ask_email)]
    },
    fallbacks=[CommandHandler("cancel", cancel)],
    name="registration_conv",
    persistent=False,
)

# top-level handlers
application.add_handler(conv_handler)
application.add_handler(CommandHandler("start", cmd_start))
application.add_handler(CommandHandler("cancel", cancel))

# ========== Flask app for webhook ==========
flask_app = Flask(__name__)

@flask_app.route("/", methods=["GET"])
def index():
    return f"✅ Bot running — {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')}"

@flask_app.route(f"/{TELEGRAM_TOKEN}", methods=["POST"])
def webhook():
    """Sync Flask route that forwards the update to telegram Application."""
    try:
        payload = request.get_json(force=True)
        update = Update.de_json(payload, application.bot)
        # Run the async process_update in a fresh event loop for this request.
        asyncio.run(application.process_update(update))
    except Exception as e:
        print("❌ Webhook processing error:", e)
    return "ok"

# ========== Initialize Application & set webhook (run at import time so Gunicorn workers are ready) ==========
def _startup_initialize_and_webhook():
    try:
        print("🔁 Initializing telegram Application...")
        # initialize internal structures
        asyncio.run(application.initialize())

        # set webhook URL for Telegram (so Telegram will POST to Render)
        webhook_url = f"{ROOT_URL.rstrip('/')}/{TELEGRAM_TOKEN}"
        print("🔁 Setting webhook to:", webhook_url)
        asyncio.run(application.bot.set_webhook(webhook_url))
        print("✅ Webhook set to:", webhook_url)
    except Exception as e:
        print("⚠️ Initialization / webhook error:", e)

# Initialize on import so Gunicorn workers are ready
_startup_initialize_and_webhook()

# ========== Run (only when executed directly; gunicorn will import module) ==========
if __name__ == "__main__":
    print("🚀 Starting Flask dev server (for local testing)...")
    flask_app.run(host="0.0.0.0", port=PORT, debug=False)
