import requests

TOKEN = "7918658133:AAEsE36Pbnlj1QUsoAgfFbcxaKCwYzQqP3k"
WEBHOOK_URL = "https://digitalmarketingbiz-bot.onrender.com/" + TOKEN

requests.get(f"https://api.telegram.org/bot{TOKEN}/deleteWebhook")
requests.get(f"https://api.telegram.org/bot{TOKEN}/setWebhook?url={WEBHOOK_URL}")

print("✅ Webhook reset to:", WEBHOOK_URL)

