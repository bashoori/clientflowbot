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

# Load environment variables
load_dotenv()
TOKEN = os.getenv("TELEGRAM_TOKEN")

DATA_FILE = "leads.json"
PDF_PATH = "docs/franchise_intro.pdf"  # مسیر فایل PDF معرفی فرانچایز

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
        "👋 سلام و خوش‌آمد به دنیای **فرانچایز دیجیتال مارکتینگ**!\n\n"
        "ما به شما کمک می‌کنیم تا با آموزش اصول حرفه‌ای دیجیتال مارکتینگ، "
        "بتوانید درآمد مستقل آنلاین خود را از طریق بیزنس فرانچایز ما شروع کنید. 💼💻\n\n"
        "اگر دوست دارید جزئیات بیشتری درباره این فرصت یادگیری و همکاری بدانید، "
        "لطفاً *نام* خود را وارد کنید:"
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
        f"✅ ممنون {name}!\n"
        f"ایمیل شما ({email}) با موفقیت ثبت شد.\n\n"
        "در حال ارسال فایل معرفی فرانچایز دیجیتال مارکتینگ هستم... 📩",
        reply_markup=ReplyKeyboardRemove()
    )

    # Send PDF file if exists
    if os.path.exists(PDF_PATH):
        await update.message.reply_document(
            document=open(PDF_PATH, "rb"),
            filename="Franchise_Intro.pdf",
            caption="📘 این فایل شامل اطلاعات کامل فرانچایز دیجیتال مارکتینگ ماست.\n"
                    "می‌تونی در هر زمان از طریق این فایل اطلاعات کامل‌تری کسب کنی 🌱"
        )
    else:
        await update.message.reply_text("⚠️ فایل معرفی هنوز در دسترس نیست، لطفاً بعداً دوباره امتحان کنید.")

    return ConversationHandler.END

# ---- Cancel ----
async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("گفت‌وگو لغو شد.", reply_markup=ReplyKeyboardRemove())
    return ConversationHandler.END

# ---- Main ----
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
