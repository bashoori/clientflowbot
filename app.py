import os
import re
import json
import asyncio
import requests
from datetime import datetime
from threading import Lock
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

# ========== Load Environment ==========
load_dotenv()
TOKEN = os.getenv("TELEGRAM_TOKEN")
GOOGLE_SHEET_WEBAPP_URL = os.getenv("GOOGLE_SHEET_WEBAPP_URL")
ROOT_URL = os.getenv("ROOT_URL", "https://digitalmarketingbiz-bot.onrender.com")
PORT = int(os.environ.get("PORT", 10000))

# ========== App Setup ==========
flask_app = Flask(__name__)
LEADS_FILE = "leads.json"
lock = Lock()

# ========== Helpers ==========
def load_leads():
    """Load leads from JSON file"""
    if not os.path.exists(LEADS_FILE):
        return []
    try:
        with open(LEADS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return []

def save_leads(leads):
    """Thread-safe save to JSON file"""
    with lock:
        with open(LEADS_FILE, "w", encoding="utf-8") as f:
            json.dump(leads, f, ensure_ascii=False, indent=2)

def is_valid_email(email: str) -> bool:
    """Basic email validation"""
    return re.match(r"^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$", email) is not None

def post_to_sheet(payload: dict, timeout: int = 15) -> bool:
    """Send data to Google Apps Script WebApp"""
    if not GOOGLE_SHEET_WEBAPP_URL:
        print("⚠️ GOOGLE_SHEET_WEBAPP_URL not set")
        return False
    try:
        resp = requests.post(GOOGLE_SHEET_WEBAPP_URL, json=payload, timeout=timeout)
        print(f"📤 POST → {resp.status_code} | {resp.text[:120]}")
        return resp.status_code == 200
    except Exception as e:
        print("❌ post_to_sheet error:", e)
        return False

# ========== Telegram Conversation States ==========
ASK_NAME, ASK_EMAIL = range(2)

# ========== Telegram Bot Logic ==========
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("👋 سلام! لطفاً نام خود را وارد کنید:")
    return ASK_NAME

async def ask_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["name"] = update.message.text.strip()
    await update.message.reply_text("خیلی هم عالی 🌟 حالا لطفاً ایمیل خود را وارد کنید:")
    return ASK_EMAIL

async def ask_email(update: Update, context: ContextTypes.DEFAULT_TYPE):
    email_input = update.message.text.strip().lower()
    name = context.user_data.get("name", "").strip()

    if not is_valid_email(email_input):
        await update.message.reply_text("❌ ایمیل معتبر نیست. لطفاً دوباره وارد کنید:")
        return ASK_EMAIL

    lead = {
        "name": name,
        "email": email_input,
        "user_id": update.effective_user.id if update.effective_user else "",
        "username": update.effective_user.username if update.effective_user else "",
        "status": "Validated",
        "created_at": datetime.utcnow().isoformat() + "Z"
    }

    leads = load_leads()
    leads.append(lead)
    save_leads(leads)
    print(f"💾 Saved locally: {lead}")

    posted = post_to_sheet(lead)
    if posted:
        await update.message.reply_text(
            f"✅ ایمیل شما ({email_input}) معتبر است و ثبت شد.\n"
            "ممنون! اطلاعات شما با موفقیت ذخیره شد."
        )
    else:
        await update.message.reply_text(
            f"✅ ایمیل شما ({email_input}) معتبر است و در سیستم محلی ذخیره شد.\n"
            "اما در ارسال به Google Sheet مشکلی پیش آمد."
        )

    return ConversationHandler.END

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("گفت‌وگو لغو شد.", reply_markup=ReplyKeyboardRemove())
    return ConversationHandler.END

# ========== Telegram Bot Setup ==========
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

# ========== Flask Routes ==========
@flask_app.route(f"/{TOKEN}", methods=["POST"])
def webhook():
    """Sync-safe Telegram webhook endpoint for Render"""
    try:
        update_json = request.get_json(force=True)
        update = Update.de_json(update_json, application.bot)
        asyncio.run(application.process_update(update))
    except Exception as e:
        print(f"❌ Webhook error: {e}")
    return "ok"

@flask_app.route("/")
def index():
    """Simple health check"""
    return f"✅ Bot running — {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')}"

# ========== Webhook Setup ==========
async def ensure_webhook():
    current = await application.bot.get_webhook_info()
    desired = f"{ROOT_URL}/{TOKEN}"
    if current.url != desired:
        await application.bot.set_webhook(desired)
        print(f"✅ Webhook set to: {desired}")
    else:
        print(f"ℹ️ Webhook already set to: {desired}")

# ========== Main ==========
if __name__ == "__main__":
    print("🚀 Starting Email Validation + Sheet Bot (Render)...")

    async def main():
        await ensure_webhook()
        flask_app.run(host="0.0.0.0", port=PORT)

    asyncio.run(main())
