import os
import asyncio
from google import genai
from groq import Groq
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes

# Environment Variables
TELEGRAM_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
GROQ_KEY = os.getenv("GROQ_API_KEY")
RENDER_EXTERNAL_URL = os.getenv("RENDER_EXTERNAL_URL")

# Modern Hinglish NCERT Prompt Definition with Custom Symbol Framing & Witty Trolling Mode
NCERT_PROMPT = (
    "You are an expert NCERT Biology mentor for NEET Class 11th & 12th aspirants.\n\n"
    "CRITICAL LANGUAGE RULE (MODERN HINGLISH ONLY):\n"
    "- Write strictly in natural, modern, chat-style Hinglish used by Indian students.\n"
    "- DO NOT use difficult/pure Hindi words like 'Urja', 'Sankrit', 'Jeevbhautik', 'Prasarakshan', 'Pachan', 'Aavshyakta', 'Peshi'.\n"
    "- ALWAYS replace pure Hindi vocabulary with common English/Hinglish terms: "
    "Use 'Energy' (not Urja), 'Store' (not Sankrit), 'Digestive system/Digestion' (not Pachan), "
    "'Process' (not Prakriya), 'Required' (not Aavshyakta), 'Muscle contraction' (not Peshi sankuchan), "
    "'Nerve signal' (not Signal prasarakshan).\n\n"
    "CRITICAL INTERACTIVE VISUAL FORMATTING SYMBOLS:\n"
    "- Main Headers/Titles: Start with '⦿ <b>TITLE</b>'\n"
    "- Sub-headers/Categories: Start with '◘ <b>Sub-header</b>'\n"
    "- Major Step-by-Step Points: Use numbered symbols '➊', '➋', '➌', '➍', '➎'\n"
    "- Primary Bullet Points: Use '‣ '\n"
    "- Explanations/Direct Points: Use '➡ '\n"
    "- Important Notes/Tips: Use '♫ <b>Note:</b>'\n\n"
    "CRITICAL FORMATTING & EXPLANATION STYLE:\n"
    "- Frame every response in a clean, highly detailed, point-wise manner using the exact symbols specified above.\n"
    "- Break down complex mechanisms, functions, or concepts into clean points with <b>bold key terms</b>.\n"
    "- Whenever a question involves comparisons, types, or opposing processes, naturally present them using point-by-point differences.\n"
    "- Keep explanations conceptually rich and directly grounded in Class 11th and 12th NCERT Biology.\n\n"
    "CRITICAL WITTY TROLLING / OFF-TOPIC HANDLING RULE:\n"
    "- If the user asks something completely unrelated to Biology/NEET (e.g., flirting, personal questions, sports, casual chat, unexpected random stuff):\n"
    "  1. DO NOT give a dry robot refusal. Instead, troll/roast them wittily in Hinglish using biological metaphors!\n"
    "  2. Examples of biological banter: 'Dil me 4 chambers hote hain, faltu baaton ki jagah nahi!', 'Yeh bakchodi NEET ke syllabus me nahi hai, GOC aur Krebs cycle padh lo!', 'Mera Heart-rate normal hai, tumhara Dopamine level high lag raha hai.'\n"
    "  3. Frame the roast neatly using the custom symbols (⦿ <b>OFF-TOPIC DETECTED!</b>, ➊ <b>Status</b>, ➋ <b>Advice</b>, ♫ <b>Note</b>).\n"
    "  4. Keep the roast funny and clean—NO explicit/vulgar swear words so we avoid Telegram bans.\n\n"
    "CRITICAL HTML FORMATTING RULES FOR TELEGRAM:\n"
    "1. Do NOT use markdown asterisks (* or **) or hashtags (###).\n"
    "2. For bold text, ONLY use HTML tags like <b>text</b>.\n\n"
    "Question: "
)

async def startbioguru(update: Update, context: ContextTypes.DEFAULT_TYPE):
    welcome_msg = (
        "🌿 <b>Welcome to Bio Guru NCERT Assistant!</b> 🌿\n\n"
        "Mai NEET Class 11th & 12th Biology doubts solve karne ke liye aapka dedicated bot hu.\n\n"
        "📌 <b>Group me doubt poochne ke tareeke:</b>\n"
        "➊ <code>/ask Krebs cycle kya hai?</code>\n"
        "➋ Bot ko mention karke: <code>@ncertbiologybot Krebs cycle?</code>\n"
        "➌ Direct Message (DM) me bina kisi command ke poochhein!\n"
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
            print(f"❌ FAIL [Key #{index}]: {key[:10]}...{key[-5:]} -> {e}")

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

    # Retrieve multiple comma-separated Gemini keys
    gemini_keys_raw = os.getenv("GEMINI_API_KEYS", "") or os.getenv("GEMINI_API_KEY", "")
    gemini_keys = [k.strip() for k in gemini_keys_raw.split(",") if k.strip()]

    # --- LEVEL 1: GEMINI MULTI-KEY ROTATION WITH FAST TIMEOUT ---
    for index, key in enumerate(gemini_keys, start=1):
        try:
            def call_gemini():
                client = genai.Client(api_key=key)
                return client.models.generate_content(
                    model='gemini-2.0-flash',
                    contents=full_prompt,
                )
            
            # Strict 4-second timeout to avoid long waiting on dead keys
            response = await asyncio.wait_for(asyncio.to_thread(call_gemini), timeout=4.0)
            if response and response.text:
                text_to_send = response.text
                break  # Stop trying as soon as one key succeeds
        except Exception as gemini_error:
            print(f"❌ FAIL [Key #{index}]: {key[:10]}...{key[-5:]} -> {gemini_error}")
            continue

    # GROQ Fallback Prompt Instruction
    groq_system_instructions = (
        "You are a witty biology mentor bot. For biology questions, reply with NCERT concept points using HTML tags like <b>bold</b>. "
        "For non-biology/off-topic questions or flirting, troll the user playfully using biology metaphors in Hinglish! "
        "Format using symbols: '⦿' for titles, '◘' for subheaders, '➊', '➋' for main points, '‣' for bullets, '➡' for details, and '♫' for notes."
    )

    # --- LEVEL 2: GROQ - LLAMA 3.3 (Fallback if all Gemini keys fail) ---
    if not text_to_send and GROQ_KEY:
        try:
            def call_groq_llama():
                groq_client = Groq(api_key=GROQ_KEY.strip())
                chat_completion = groq_client.chat.completions.create(
                    messages=[
                        {"role": "system", "content": groq_system_instructions},
                        {"role": "user", "content": full_prompt}
                    ],
                    model="llama-3.3-70b-versatile",
                    max_tokens=1000,
                    temperature=0.4,
                )
                return chat_completion.choices[0].message.content

            text_to_send = await asyncio.wait_for(asyncio.to_thread(call_groq_llama), timeout=6.0)
        except Exception as llama_error:
            print(f"LLAMA ERROR (Fallback to DeepSeek): {llama_error}")

    # --- LEVEL 3: GROQ - DEEPSEEK R1 ---
    if not text_to_send and GROQ_KEY:
        try:
            def call_groq_deepseek():
                groq_client = Groq(api_key=GROQ_KEY.strip())
                chat_completion = groq_client.chat.completions.create(
                    messages=[
                        {"role": "system", "content": groq_system_instructions},
                        {"role": "user", "content": full_prompt}
                    ],
                    model="deepseek-r1-distill-llama-70b",
                    max_tokens=1000,
                    temperature=0.4,
                )
                return chat_completion.choices[0].message.content

            text_to_send = await asyncio.wait_for(asyncio.to_thread(call_groq_deepseek), timeout=8.0)
        except Exception as deepseek_error:
            print(f"DEEPSEEK ERROR: {deepseek_error}")

    # --- SEND RESPONSE TO USER ---
    if text_to_send:
        if "<think>" in text_to_send and "</think>" in text_to_send:
            text_to_send = text_to_send.split("</think>")[-1].strip()

        try:
            await update.message.reply_text(text_to_send, parse_mode='HTML')
        except Exception:
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
    app.add_handler(CommandHandler("testkeys", testkeys))
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
