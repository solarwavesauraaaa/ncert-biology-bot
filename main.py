import os
import asyncio
from google import genai
from groq import Groq
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes

# Environment Variables
TELEGRAM_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
GEMINI_KEY = os.getenv("GEMINI_API_KEY")
GROQ_KEY = os.getenv("GROQ_API_KEY")
RENDER_EXTERNAL_URL = os.getenv("RENDER_EXTERNAL_URL")

# Modern Hinglish NCERT Prompt Definition with HTML Formatting
NCERT_PROMPT = (
    "You are an expert NCERT Biology mentor for NEET Class 11th & 12th aspirants.\n\n"
    "CRITICAL LANGUAGE RULE (MODERN HINGLISH ONLY):\n"
    "- Write strictly in natural, modern, chat-style Hinglish used by Indian students.\n"
    "- DO NOT use difficult/pure Hindi words like 'Urja', 'Sankrit', 'Jeevbhautik', 'Prasarakshan', 'Pachan', 'Aavshyakta', 'Peshi'.\n"
    "- ALWAYS replace pure Hindi vocabulary with common English/Hinglish terms: "
    "Use 'Energy' (not Urja), 'Store' (not Sankrit), 'Digestive system/Digestion' (not Pachan), "
    "'Process' (not Prakriya), 'Required' (not Aavshyakta), 'Muscle contraction' (not Peshi sankuchan), "
    "'Nerve signal' (not Signal prasarakshan).\n\n"
    "CRITICAL HTML FORMATTING RULES FOR TELEGRAM (STRICTLY FOLLOW):\n"
    "1. Do NOT use asterisks (*) or markdown hashtags (###).\n"
    "2. For bold text, ONLY use HTML tags like <b>text</b>.\n"
    "3. For bullet points, use clean emojis or dash like '• ' or '👉 '.\n"
    "4. Example output format:\n"
    "   <b>Plant hormones ke key steps:</b>\n"
    "   • <b>Auxin:</b> Plant growth aur cell elongation ko promote karta hai.\n"
    "   • <b>Gibberellin:</b> Stem elongation aur seed germination control karta hai.\n\n"
    "RESPONSE STRUCTURE:\n"
    "1. <b>Direct Definition:</b> Start with a clear 2-3 line simple definition.\n"
    "2. <b>Detailed Breakdown:</b> Key steps with <b>bullet points</b>.\n"
    "3. Scope: If outside NCERT Biology, reply ONLY: 'Yeh official Class 11th & 12th NCERT Biology me nahi hai.'\n\n"
    "Question: "
)

async def startbioguru(update: Update, context: ContextTypes.DEFAULT_TYPE):
    welcome_msg = (
        "🌿 <b>Welcome to Bio Guru NCERT Assistant!</b> 🌿\n\n"
        "Mai NEET Class 11th & 12th Biology doubts solve karne ke liye aapka dedicated bot hu.\n\n"
        "📌 <b>Group me doubt poochne ke tareeke:</b>\n"
        "1. <code>/ask Krebs cycle kya hai?</code>\n"
        "2. Bot ko mention karke: <code>@ncertbiologybot Krebs cycle?</code>\n"
        "3. Direct Message (DM) me bina kisi command ke poochhein!\n"
    )
    if update.message:
        try:
            await update.message.reply_text(welcome_msg, parse_mode='HTML')
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

    full_prompt = f"{NCERT_PROMPT}{user_query}"
    text_to_send = None

    # --- LEVEL 1: GEMINI API ---
    if GEMINI_KEY:
        try:
            def call_gemini():
                client = genai.Client(api_key=GEMINI_KEY.strip())
                return client.models.generate_content(
                    model='gemini-2.0-flash',
                    contents=full_prompt,
                )
            
            response = await asyncio.to_thread(call_gemini)
            if response and response.text:
                text_to_send = response.text
        except Exception as gemini_error:
            print(f"GEMINI ERROR (Fallback to Groq Llama): {gemini_error}")

    # --- LEVEL 2: GROQ - LLAMA 3.3 ---
    if not text_to_send and GROQ_KEY:
        try:
            def call_groq_llama():
                groq_client = Groq(api_key=GROQ_KEY.strip())
                chat_completion = groq_client.chat.completions.create(
                    messages=[
                        {"role": "system", "content": "You are a biology assistant that outputs clean text using HTML formatting (<b>bold</b>) instead of markdown asterisks."},
                        {"role": "user", "content": full_prompt}
                    ],
                    model="llama-3.3-70b-versatile",
                    max_tokens=1000,
                    temperature=0.3,
                )
                return chat_completion.choices[0].message.content

            text_to_send = await asyncio.to_thread(call_groq_llama)
        except Exception as llama_error:
            print(f"LLAMA ERROR (Fallback to DeepSeek): {llama_error}")

    # --- LEVEL 3: GROQ - DEEPSEEK R1 ---
    if not text_to_send and GROQ_KEY:
        try:
            def call_groq_deepseek():
                groq_client = Groq(api_key=GROQ_KEY.strip())
                chat_completion = groq_client.chat.completions.create(
                    messages=[
                        {"role": "system", "content": "You are a biology assistant that outputs clean text using HTML formatting (<b>bold</b>) instead of markdown asterisks."},
                        {"role": "user", "content": full_prompt}
                    ],
                    model="deepseek-r1-distill-llama-70b",
                    max_tokens=1000,
                    temperature=0.3,
                )
                return chat_completion.choices[0].message.content

            text_to_send = await asyncio.to_thread(call_groq_deepseek)
        except Exception as deepseek_error:
            print(f"DEEPSEEK ERROR: {deepseek_error}")

    # --- SEND RESPONSE TO USER ---
    if text_to_send:
        if "<think>" in text_to_send and "</think>" in text_to_send:
            text_to_send = text_to_send.split("</think>")[-1].strip()

        try:
            await update.message.reply_text(text_to_send, parse_mode='HTML')
        except Exception:
            # Clean HTML tags if parsing fails
            clean_text = text_to_send.replace('<b>', '').replace('</b>', '').replace('<code>', '').replace('</code>', '')
            await update.message.reply_text(clean_text)
    else:
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
