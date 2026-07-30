import os
import asyncio
from google import genai
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes

# Environment Variables
TELEGRAM_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
GEMINI_KEY = os.getenv("GEMINI_API_KEY")
RENDER_EXTERNAL_URL = os.getenv("RENDER_EXTERNAL_URL")

# NCERT Prompt Definition
NCERT_PROMPT = (
    "You are a strict NCERT Biology expert for Class 11th and 12th NEET students. "
    "Only answer questions strictly covered in Class 11 and Class 12 NCERT Biology textbooks. "
    "If a user has a typo, correct it gently and answer based on NCERT. "
    "If a topic or question is NOT present in official NCERT Biology, reply strictly: "
    "'Yeh official Class 11th & 12th NCERT Biology me nahi hai.'\n\n"
    "LANGUAGE RULE: Write the entire response in natural, simple Hinglish (Hindi in Roman script with English bio terms).\n\n"
    "CRITICAL FORMATTING RULES FOR TELEGRAM:\n"
    "1. Do NOT use headers like ### or hashtags.\n"
    "2. Do NOT use horizontal lines like ---\n"
    "3. Do NOT use LaTeX, dollar signs ($ or $$), or backslashes.\n"
    "4. Use simple bold tags (**like this**) for key terms and title.\n"
    "5. Use clear numbered lists or bullet points.\n"
    "6. Write chemical terms simply (e.g., CO2, H+, NADH, FADH2, ATP).\n\n"
    "Question: "
)

async def startbioguru(update: Update, context: ContextTypes.DEFAULT_TYPE):
    welcome_msg = (
        "🌿 *Welcome to Bio Guru NCERT Assistant!* 🌿\n\n"
        "Mai NEET Class 11th & 12th Biology doubts solve karne ke liye aapka dedicated bot hu.\n\n"
        "📌 *Group me doubt poochne ke tareeke:*\n"
        "1. `/ask Krebs cycle kya hai?`\n"
        "2. Bot ko mention karke: `@ncertbiologybot Krebs cycle?`\n"
        "3. Direct Message (DM) me bina kisi command ke poochhein!\n"
    )
    if update.message:
        try:
            await update.message.reply_text(welcome_msg, parse_mode='Markdown')
        except Exception:
            await update.message.reply_text(welcome_msg)

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.message.text:
        return

    chat_type = update.message.chat.type
    user_text = update.message.text
    bot_username = context.bot.username

    # Group vs Private Chat handling
    if chat_type in ["group", "supergroup"]:
        is_asking = user_text.startswith("/ask")
        is_mentioned = bot_username and f"@{bot_username}" in user_text
        is_reply_to_bot = (
            update.message.reply_to_message and 
            update.message.reply_to_message.from_user.id == context.bot.id
        )

        if not (is_asking or is_mentioned or is_reply_to_bot):
            return

        user_query = user_text.replace("/ask", "").replace(f"@{bot_username}", "").strip()
    else:
        user_query = user_text.strip()

    if not user_query:
        await update.message.reply_text("Kripya apna question likhein! (e.g., /ask ATP kya hai?)")
        return

    if not GEMINI_KEY:
        await update.message.reply_text("GEMINI_API_KEY Missing! Kripya Render Environment Variables check karein.")
        return

    try:
        full_prompt = f"{NCERT_PROMPT}{user_query}"
        clean_key = GEMINI_KEY.strip()

        # Thread-safe execution of Gemini API request
        def generate_ai_response():
            client = genai.Client(api_key=clean_key)
            return client.models.generate_content(
                model='gemini-2.0-flash',
                contents=full_prompt,
            )

        response = await asyncio.to_thread(generate_ai_response)
        
        if response and response.text:
            text_to_send = response.text
            try:
                await update.message.reply_text(text_to_send, parse_mode='Markdown')
            except Exception:
                await update.message.reply_text(text_to_send)
        else:
            await update.message.reply_text("Kripya apna sawal thoda spasht (clear) karke poochhein.")
            
    except Exception as e:
        # Prints precise error details in Render Logs
        print(f"CRITICAL ERROR LOG: {type(e).__name__} - {e}")
        await update.message.reply_text("Server me koi dikkat aayi hai, kripya thodi der baad try karein.")

def main():
    if not TELEGRAM_TOKEN:
        print("CRITICAL ERROR: TELEGRAM_BOT_TOKEN environment variable is not set!")
        return

    port = int(os.environ.get("PORT", 8080))
    app = ApplicationBuilder().token(TELEGRAM_TOKEN.strip()).build()

    # Handlers
    app.add_handler(CommandHandler("start", startbioguru))
    app.add_handler(CommandHandler("startbioguru", startbioguru))
    app.add_handler(CommandHandler("ask", handle_message))
    app.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), handle_message))

    # Deployment mode selector
    if RENDER_EXTERNAL_URL:
        webhook_url = f"{RENDER_EXTERNAL_URL.rstrip('/')}/{TELEGRAM_TOKEN.strip()}"
        print(f"Starting Webhook on Port {port} -> {webhook_url}")
        app.run_webhook(
            listen="0.0.0.0",
            port=port,
            url_path=TELEGRAM_TOKEN.strip(),
            webhook_url=webhook_url,
            drop_pending_updates=True
        )
    else:
        print("Starting Polling Mode locally...")
        app.run_polling(drop_pending_updates=True)

if __name__ == "__main__":
    main()
