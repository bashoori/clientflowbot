import os
import re
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
from authorize_gmail import send_welcome_email  # ✅ Ensure this file exists

# ========== Load environment variables ==========
load_dotenv()
TOKEN = os.getenv("TELEGRAM_TOKEN")
PORT = int(os.environ.get("PORT", 10000))

# ========== Telegram conversation states ==========
ASK_NAME, ASK_EMAIL = range(2)

# ========== Helper: validate email ==========
def is_valid_email(email_str: str) -> bool:
    pattern = r"^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$"
    return re.match(pattern, email_str) is not None

# ========== Flask app (for Render hosting) ==========
flask_app = Flask(__name__)

# ========== Telegram Bot Logic ==========
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("👋 سلام! لطفاً نام خود را وارد کنید:")
    return ASK_NAME

async def ask_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    name = update.message.text.strip()
    context.user_data["name"] = name
    await update.message.reply_text("خیلی هم عالی 🌟 حالا لطفاً ایمیل خود را وارد کنید:")
    return ASK_EMAIL

async def ask_email(update: Update, context: ContextTypes.DEFAULT_TYPE):
    email_input = update.message.text.strip()
    name = context.user_data.get("name")

    if not is_valid_email(email_input):
        await update.message.reply_text("❌ ایمیل معتبر نیست. لطفاً دوباره وارد کنید:")
        return ASK_EMAIL

    await update.message.reply_text(
        f"✅ ایمیل شما ({email_input}) معتبر است.\n"
        "در حال ارسال ایمیل خوش‌آمدگویی هستم..."
    )

    try:
        sent = send_welcome_email(name, email_input)
        await asyncio.sleep(1)

        if sent:
            await update.message.reply_text(
                "📬 ایمیل خوش‌آمدگویی برای شما ارسال شد!\n"
                "اگر در Inbox نبود، لطفاً پوشه‌ی Spam را هم بررسی کنید."
            )
        else:
            await update.message.reply_text(
                "⚠️ مشکلی در ارسال ایمیل پیش آمد. لطفاً بعداً امتحان کنید."
            )
    except Exception as e:
        print("❌ Email sending error:", e)
        await update.message.reply_text(
            "⚠️ مشکلی در ارسال ایمیل پیش آمد. لطفاً بعداً امتحان کنید."
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

# ========== Flask Routes ==========
@flask_app.route(f"/{TOKEN}", methods=["POST"])
async def webhook():
    """Handle incoming Telegram updates via webhook"""
    try:
        update = Update.de_json(request.get_json(force=True), application.bot)
        await application.process_update(update)
    except Exception as e:
        print("❌ Webhook error:", e)
    return "ok"

@flask_app.route("/")
def index():
    return "✅ Digital Marketing Bot is alive!"

# ========== Webhook Setup ==========
async def set_webhook():
    webhook_url = f"https://digitalmarketingbiz-bot.onrender.com/{TOKEN}"
    await application.bot.set_webhook(webhook_url)
    print(f"✅ Webhook set to: {webhook_url}")

# ========== Entry Point ==========
if __name__ == "__main__":
    print("🚀 Starting Digital Marketing Bot (Webhook Mode)...")
    asyncio.run(set_webhook())
    flask_app.run(host="0.0.0.0", port=PORT)
