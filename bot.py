import os
import json
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes
from dotenv import load_dotenv

# Load .env variables
load_dotenv()

TOKEN = os.getenv("TELEGRAM_TOKEN")
DATA_FILE = "customers.json"

# ----- helper functions -----
def save_data(data):
    with open(DATA_FILE, "w") as f:
        json.dump(data, f)

def load_data():
    if not os.path.exists(DATA_FILE):
        return []
    with open(DATA_FILE, "r") as f:
        return json.load(f)

# ----- commands -----
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "👋 Welcome to ClientCRM!\nUse /add <name> <phone> to add a client."
    )

async def add_customer(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if len(context.args) < 2:
        await update.message.reply_text("Usage: /add John 6041234567")
        return
    name, phone = context.args[0], context.args[1]
    data = load_data()
    data.append({"name": name, "phone": phone, "user": update.effective_user.id})
    save_data(data)
    await update.message.reply_text(f"✅ Added {name} ({phone})")

async def list_customers(update: Update, context: ContextTypes.DEFAULT_TYPE):
    data = [d for d in load_data() if d["user"] == update.effective_user.id]
    if not data:
        await update.message.reply_text("No clients yet.")
        return
    text = "\n".join([f"{i+1}. {c['name']} – {c['phone']}" for i, c in enumerate(data)])
    await update.message.reply_text(f"📋 Your clients:\n{text}")

def main():
    app = ApplicationBuilder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("add", add_customer))
    app.add_handler(CommandHandler("list", list_customers))
    app.run_polling()

if __name__ == "__main__":
    main()
