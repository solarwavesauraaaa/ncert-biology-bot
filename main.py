import os
import google.generativeai as genai
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes

# Environment variables se Keys read karenge (Security ke liye)
TELEGRAM_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
GEMINI_KEY = os.getenv("GEMINI_API_KEY")

genai.configure(api_key=GEMINI_KEY)

system_instruction = (
    "You are a strict NCERT Biology expert for Class 11th and 12th NEET students. "
    "Only answer questions covered in Class 11 & 12 NCERT Biology. "
    "If a topic is not in official NCERT, reply strictly: "
    "'Yeh official Class 11th & 12th NCERT Biology me nahi hai.'"
)

model = genai.GenerativeModel(
    model_name="gemini-1.5-flash",
    system_instruction=system_instruction
)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Namaste! Mai NCERT Class 11th & 12th Biology Bot hu. Koi bhi question poochho!")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_query = update.message.text
    try:
        response = model.generate_content(user_query)
        await update.message.reply_text(response.text)
    except Exception as e:
        await update.message.reply_text("Kuchh error aaya, kripya dubara try karein.")

if __name__ == "__main__":
    app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), handle_message))
    
    print("NCERT Bot is running 24/7 on Render...")
    app.run_polling()