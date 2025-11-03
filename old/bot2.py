import os
import json
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

# Load .env
load_dotenv()
TOKEN = os.getenv("TELEGRAM_TOKEN")

DATA_FILE = "leads.json"

# ---- Helper functions ----
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
            with open(DATA_FILE, "w") as fw:
                json.dump([], fw)
            return []

# Conversation states
ASK_NAME, ASK_EMAIL = range(2)

# ---- Start ----
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

# ---- Ask Name ----
async def ask_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["name"] = update.message.text.strip()
    await update.message.reply_text("خیلی عالی 🌟 حالا لطفاً ایمیل خودتون رو وارد کنید:")
    return ASK_EMAIL

# ---- Ask Email ----
async def ask_email(update: Update, context: ContextTypes.DEFAULT_TYPE):
    email = update.message.text.strip()
    name = context.user_data.get("name")

    leads = load_data()
    leads.append({
        "name": name,
        "email": email,
        "user_id": update.effective_user.id,
        "username": update.effective_user.username,
    })
    save_data(leads)

    await update.message.reply_text(
        f"✅ ممنون {name}!\nایمیل شما ({email}) با موفقیت ثبت شد.\n"
        "به‌زودی اطلاعات کامل فرانچایز دیجیتال مارکتینگ برای شما ارسال می‌شود. 🚀",
        reply_markup=ReplyKeyboardRemove()
    )
    return ConversationHandler.END

# ---- Cancel ----
async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("گفت‌وگو لغو شد.", reply_markup=ReplyKeyboardRemove())
    return ConversationHandler.END

# ---- Main App ----
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
