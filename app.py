# app.py
import os
import re
import json
import asyncio
from flask import Flask, request
from telegram import Update, ReplyKeyboardRemove
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    ConversationHandler,
    ContextTypes,
    filters,
)
from dotenv import load_dotenv
import requests
from datetime import datetime

# ========== Load env ==========
load_dotenv()
TOKEN = os.getenv("TELEGRAM_TOKEN")
PORT = int(os.environ.get("PORT", 10000))
GOOGLE_SHEET_WEBAPP_URL = os.getenv("GOOGLE_SHEET_WEBAPP_URL")  # must be your Apps Script WebApp URL

# ========== Local storage ==========
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
def is_valid_email(email_str: str) -> bool:
    pattern = r"^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$"
    return re.match(pattern, email_str) is not None

def post_to_sheet(payload: dict, timeout: int = 15) -> bool:
    """
    POST JSON to Google Apps Script Web App.
    Return True on 200 OK + "Success" in response (best-effort).
    """
    if not GOOGLE_SHEET_WEBAPP_URL:
        print("⚠️ GOOGLE_SHEET_WEBAPP_URL not set")
        return False
    try:
        resp = requests.post(GOOGLE_SHEET_WEBAPP_URL, json=payload, timeout=timeout)
        print(f"📤 Sheet POST status: {resp.status_code} - {resp.text[:200]}")
        return resp.status_code == 200
    except Exception as e:
        print("❌ post_to_sheet error:", e)
        return False

# ========== Telegram conversation states ==========
ASK_NAME, ASK_EMAIL = range(2)

# ========== Flask app (Render) ==========
flask_app = Flask(__name__)

# ========== Telegram Handlers ==========
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("👋 سلام! لطفاً نام خود را وارد کنید:")
    return ASK_NAME

async def ask_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    name = update.message.text.strip()
    context.user_data["name"] = name
    await update.message.reply_text("خیلی خوب 🌟 حالا لطفاً ایمیل خود را وارد کنید:")
    return ASK_EMAIL

async def ask_email(update: Update, context: ContextTypes.DEFAULT_TYPE):
    email_input = update.message.text.strip().lower()
    name = context.user_data.get("name", "").strip()

    if not is_valid_email(email_input):
        await update.message.reply_text("❌ ایمیل معتبر نیست. لطفاً دوباره وارد کنید:")
        return ASK_EMAIL

    # prepare lead record
    lead = {
        "name": name,
        "email": email_input,
        "user_id": update.effective_user.id if update.effective_user else None,
        "username": update.effective_user.username if update.effective_user else None,
        "status": "Validated",
        "created_at": datetime.utcnow().isoformat() + "Z"
    }

    # save locally
    leads = load_leads()
    leads.append(lead)
    try:
        save_leads(leads)
        print(f"💾 Saved locally: {lead}")
    except Exception as e:
        print("⚠️ Failed to save local lead:", e)

    # post to Google Sheet (best-effort)
    posted = post_to_sheet({
        "name": lead["name"],
        "email": lead["email"],
        "username": lead["username"] or "",
        "user_id": lead["user_id"] or "",
        "status": lead["status"],
    })

    if posted:
        await update.message.reply_text(
            f"✅ ایمیل شما ({email_input}) معتبر است و ثبت شد.\n"
            "ممنون! ما ممکن است بعداً با شما تماس بگیریم."
        )
    else:
        await update.message.reply_text(
            f"✅ ایمیل شما ({email_input}) معتبر است و در سیستم محلی ذخیره شد.\n"
            "اما در ارسال به Google Sheet مشکلی پیش آمد. لطفاً بعداً بررسی خواهم کرد."
        )

    return ConversationHandler.END

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("گفت‌وگو لغو شد.", reply_markup=ReplyKeyboardRemove())
    return ConversationHandler.END

# ========== Build Telegram Application ==========
application = Application.builder().token(TOKEN).build()

conv_handler = ConversationHandler(
    entry_points=[CommandHandler("start", start)],
    states={
        ASK_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, ask_name)],
        ASK_EMAIL: [MessageHandler(filters.TEXT & ~filters.COMMAND, ask_email)],
    },
    fallbacks=[CommandHandler("cancel", cancel)],
)

application.add_handler(conv_handler)

# ========== Flask webhook route ==========
@flask_app.route(f"/{TOKEN}", methods=["POST"])
async def webhook():
    try:
        update = Update.de_json(request.get_json(force=True), application.bot)
        await application.process_update(update)
    except Exception as e:
        print("❌ Webhook processing error:", e)
    return "ok"

@flask_app.route("/")
def index():
    return "✅ Email Validation + Sheet Bot is running"

# ========== Set webhook on startup ==========
async def set_webhook():
    # change this to your actual Render URL if different
    root_url = os.getenv("ROOT_URL", "https://digitalmarketingbiz-bot.onrender.com")
    webhook_url = f"{root_url}/{TOKEN}"
    await application.bot.set_webhook(webhook_url)
    print(f"✅ Webhook set to: {webhook_url}")

# ========== Entry point ==========
if __name__ == "__main__":
    print("🚀 Starting Email Validation + Sheet Bot (webhook mode)...")
    asyncio.run(set_webhook())
    flask_app.run(host="0.0.0.0", port=PORT)
