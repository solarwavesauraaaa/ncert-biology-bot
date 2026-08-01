import os
import asyncio
import logging
from google import genai
from groq import Groq
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes

# ========== LOGGING SETUP ==========
logging.basicConfig(
    format='%(asctime)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Environment Variables
TELEGRAM_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
GROQ_KEY = os.getenv("GROQ_API_KEY")
RENDER_EXTERNAL_URL = os.getenv("RENDER_EXTERNAL_URL")

# ========== IMPROVED: SHORT & CRISP NCERT PROMPT ==========
NCERT_PROMPT = (
    "You are an expert NCERT Biology mentor for NEET Class 11th & 12th.\n\n"
    "STRICT RULES:\n"
    "1. Answer ONLY from NCERT textbook (Class 11 & 12)\n"
    "2. Write in MODERN HINGLISH (allowed to use English words like 'Energy', 'Process', 'Digestion')\n"
    "3. Use these symbols for formatting:\n"
    "   ⦿ for main titles\n"
    "   ◘ for sub-headers\n"
    "   ➊,➋,➌ for steps\n"
    "   ‣ for bullet points\n"
    "   ➡ for explanations\n"
    "   ♫ for important notes\n"
    "4. Use <b>bold</b> for key biological terms\n"
    "5. Be DETAILED and CONCEPTUAL with NCERT content\n"
    "6. If question is NOT Biology/NEET related, troll wittily using biology metaphors\n\n"
    "USER QUESTION: "
)

async def startbioguru(update: Update, context: ContextTypes.DEFAULT_TYPE):
    welcome_msg = (
        "🌿 <b>Welcome to Bio Guru NCERT Assistant!</b> 🌿\n\n"
        "Hare Krishna, mai NEET Class 11th & 12th Biology doubts solve karne ke liye aapka dedicated bot hu.\n\n"
        "📌 <b>Group me doubt poochne ke tareeke:</b>\n"
        "➊ <code>/ask Krebs cycle kya hai?</code>\n"
        "➋ Bot ko mention karke: <code>@ncertbiologybot Krebs cycle?</code>\n"
        "➌ Direct Message (DM) me bina kisi command ke poochhe!\n"
    )
    if update.message:
        try:
            await update.message.reply_text(welcome_msg, parse_mode='HTML')
        except Exception:
            await update.message.reply_text(welcome_msg)

async def testkeys(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message:
        return
        
    await update.message.reply_text("🔍 Testing all Gemini keys... Please wait!")
    
    gemini_keys_raw = os.getenv("GEMINI_API_KEYS", "") or os.getenv("GEMINI_API_KEY", "")
    gemini_keys = [k.strip() for k in gemini_keys_raw.split(",") if k.strip()]
    
    if not gemini_keys:
        await update.message.reply_text("❌ Koi Gemini API Key nahi mili! Environment variable check karein.")
        return

    working_count = 0
    failed_keys = []

    for index, key in enumerate(gemini_keys, start=1):
        try:
            def call_gemini():
                client = genai.Client(api_key=key)
                return client.models.generate_content(
                    model='gemini-2.0-flash',
                    contents="Say Hi",
                )
            res = await asyncio.wait_for(asyncio.to_thread(call_gemini), timeout=3.0)
            if res and res.text:
                working_count += 1
        except Exception as e:
            failed_keys.append(f"Key #{index} ({key[:8]}...{key[-4:]})")
            logger.error(f"❌ FAIL [Key #{index}]: {key[:10]}...{key[-5:]} -> {e}")

    report = (
        f"<b>📊 API Keys Test Report:</b>\n\n"
        f"✅ <b>Working Keys:</b> {working_count}/{len(gemini_keys)}\n"
        f"❌ <b>Failed Keys:</b> {len(failed_keys)}\n\n"
        f"Check Render terminal logs for exact details of failed keys!"
    )
    try:
        await update.message.reply_text(report, parse_mode='HTML')
    except Exception:
        await update.message.reply_text(report)

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.message.text:
        return

    chat_type = update.message.chat.type
    user_text = update.message.text
    bot_username = context.bot.username
    username = update.message.from_user.username or "Unknown"

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

    logger.info(f"📩 NEW QUERY from @{username}: {user_query[:50]}...")
    
    # ========== FIX: Better prompt construction ==========
    full_prompt = f"{NCERT_PROMPT}{user_query}"
    text_to_send = None
    model_used = None

    # ========== LEVEL 1: DEEPSEEK R1 (PRIORITY) ==========
    if GROQ_KEY:
        try:
            logger.info("🔄 Trying DeepSeek R1...")
            
            def call_deepseek():
                groq_client = Groq(api_key=GROQ_KEY.strip())
                chat_completion = groq_client.chat.completions.create(
                    messages=[
                        {"role": "system", "content": "You are a strict NCERT Biology mentor. Give accurate NCERT-based answers only."},
                        {"role": "user", "content": full_prompt}
                    ],
                    model="deepseek-r1-distill-llama-70b",
                    max_tokens=1500,  # 🔥 FIX: More tokens for detailed answers
                    temperature=0.1,   # 🔥 FIX: Lower temperature for accuracy
                )
                return chat_completion.choices[0].message.content

            text_to_send = await asyncio.wait_for(asyncio.to_thread(call_deepseek), timeout=10.0)
            if text_to_send:
                model_used = "🚀 DeepSeek R1"
                logger.info(f"✅ SUCCESS: Response from {model_used}")
        except asyncio.TimeoutError:
            logger.warning("⏰ DeepSeek R1 TIMEOUT (10s)")
        except Exception as deepseek_error:
            logger.error(f"❌ DeepSeek R1 ERROR: {deepseek_error}")

    # ========== LEVEL 2: LLAMA 3.3 (if DeepSeek fails) ==========
    if not text_to_send and GROQ_KEY:
        try:
            logger.info("🔄 Trying Llama 3.3...")
            
            def call_llama():
                groq_client = Groq(api_key=GROQ_KEY.strip())
                chat_completion = groq_client.chat.completions.create(
                    messages=[
                        {"role": "system", "content": "You are a strict NCERT Biology mentor. Give accurate NCERT-based answers only."},
                        {"role": "user", "content": full_prompt}
                    ],
                    model="llama-3.3-70b-versatile",
                    max_tokens=1500,  # 🔥 FIX: More tokens
                    temperature=0.1,   # 🔥 FIX: Lower temperature
                )
                return chat_completion.choices[0].message.content

            text_to_send = await asyncio.wait_for(asyncio.to_thread(call_llama), timeout=8.0)
            if text_to_send:
                model_used = "🦙 Llama 3.3"
                logger.info(f"✅ SUCCESS: Response from {model_used}")
        except asyncio.TimeoutError:
            logger.warning("⏰ Llama 3.3 TIMEOUT (8s)")
        except Exception as llama_error:
            logger.error(f"❌ Llama 3.3 ERROR: {llama_error}")

    # ========== LEVEL 3: GEMINI (Last Resort) ==========
    if not text_to_send:
        gemini_keys_raw = os.getenv("GEMINI_API_KEYS", "") or os.getenv("GEMINI_API_KEY", "")
        gemini_keys = [k.strip() for k in gemini_keys_raw.split(",") if k.strip()]

        for index, key in enumerate(gemini_keys, start=1):
            try:
                logger.info(f"🔄 Trying Gemini (Key #{index})...")
                
                def call_gemini():
                    client = genai.Client(api_key=key)
                    return client.models.generate_content(
                        model='gemini-2.0-flash',
                        contents=full_prompt,
                    )
                
                response = await asyncio.wait_for(asyncio.to_thread(call_gemini), timeout=5.0)
                if response and response.text:
                    text_to_send = response.text
                    model_used = f"🤖 Gemini (Key #{index})"
                    logger.info(f"✅ SUCCESS: Response from {model_used}")
                    break
            except asyncio.TimeoutError:
                logger.warning(f"⏰ Gemini Key #{index} TIMEOUT (5s)")
            except Exception as gemini_error:
                logger.error(f"❌ GEMINI FAIL [Key #{index}]: {gemini_error}")
                continue

    # ========== SEND RESPONSE TO USER ==========
    if text_to_send:
        # Remove thinking tags if present
        if "<think>" in text_to_send and "</think>" in text_to_send:
            text_to_send = text_to_send.split("</think>")[-1].strip()

        try:
            await update.message.reply_text(text_to_send, parse_mode='HTML')
            logger.info(f"📤 Response sent to @{username} (Model: {model_used})")
        except Exception as e:
            logger.error(f"❌ Failed to send response: {e}")
            clean_text = text_to_send.replace('<b>', '').replace('</b>', '').replace('<code>', '').replace('</code>', '')
            await update.message.reply_text(clean_text)
    else:
        logger.error(f"❌ ALL MODELS FAILED for @{username}")
        await update.message.reply_text("Server me koi dikkat aayi hai, kripya thodi der baad try karein.")

def main():
    if not TELEGRAM_TOKEN:
        logger.critical("❌ TELEGRAM_BOT_TOKEN environment variable is not set!")
        return

    port = int(os.environ.get("PORT", 8080))
    app = ApplicationBuilder().token(TELEGRAM_TOKEN.strip()).build()

    # Handlers
    app.add_handler(CommandHandler("startbioguru", startbioguru))
    app.add_handler(CommandHandler("testkeys", testkeys))
    app.add_handler(CommandHandler("ask", handle_message))
    app.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), handle_message))

    # Deployment mode selector
    if RENDER_EXTERNAL_URL:
        webhook_url = f"{RENDER_EXTERNAL_URL.rstrip('/')}/{TELEGRAM_TOKEN.strip()}"
        logger.info(f"🚀 Starting Webhook on Port {port} -> {webhook_url}")
        app.run_webhook(
            listen="0.0.0.0",
            port=port,
            url_path=TELEGRAM_TOKEN.strip(),
            webhook_url=webhook_url,
            drop_pending_updates=True
        )
    else:
        logger.info("🚀 Starting Polling Mode locally...")
        app.run_polling(drop_pending_updates=True)

if __name__ == "__main__":
    main()
