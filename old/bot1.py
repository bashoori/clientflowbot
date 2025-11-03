import os
import json
import uuid
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

# ----- commands -----
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "👋 Welcome to ClientCRM!\n"
        "Use /add <name> <phone> to add a client.\n"
        "Use /list to see your clients."
    )

async def add_customer(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if len(context.args) < 2:
        await update.message.reply_text("Usage: /add John 6041234567")
        return

    name, phone = context.args[0], context.args[1]
    data = load_data()

    customer = {
        "id": str(uuid.uuid4()),  # Generate GUID
        "name": name,
        "phone": phone,
        "user": update.effective_user.id
    }

    data.append(customer)
    save_data(data)

    await update.message.reply_text(
        f"✅ Added {name} ({phone})\n🆔 ID: `{customer['id']}`",
        parse_mode="Markdown"
    )

async def list_customers(update: Update, context: ContextTypes.DEFAULT_TYPE):
    data = [d for d in load_data() if d["user"] == update.effective_user.id]
    if not data:
        await update.message.reply_text("No clients yet.")
        return

    text = "\n\n".join([
        f"{i+1}. *{c['name']}*\n📞 {c['phone']}" +
        (f"\n🆔 `{c['id']}`" if "id" in c else "")
        for i, c in enumerate(data)
    ])

    await update.message.reply_text(f"📋 *Your clients:*\n\n{text}", parse_mode="Markdown")


# ----- main -----
def main():
    app = ApplicationBuilder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("add", add_customer))
    app.add_handler(CommandHandler("list", list_customers))
    app.run_polling()

if __name__ == "__main__":
    main()
