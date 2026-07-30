import os
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler
from google import genai
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes

# Dummy Web Server to satisfy Render Port requirement
class DummyServer(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"NCERT Bot is Live!")

def run_dummy_server():
    port = int(os.environ.get("PORT", 8080))
    server = HTTPServer(("0.0.0.0", port), DummyServer)
    server.serve_forever()

threading.Thread(target=run_dummy_server, daemon=True).start()

# Read Environment Variables
TELEGRAM_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
GEMINI_KEY = os.getenv("GEMINI_API_KEY")

# Initialize Gemini Client with new SDK
client = genai.Client(api_key=GEMINI_KEY)

NCERT_PROMPT = (
    "You are a strict NCERT Biology expert for Class 11th and 12th NEET students. "
    "Only answer questions strictly covered in Class 11 and Class 12 NCERT Biology textbooks. "
    "If a topic or question is NOT present in official NCERT Biology, you MUST reply strictly: "
    "'Yeh official Class 11th & 12th NCERT Biology me nahi hai.'\n\n"
    "Question: "
)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Namaste! Mai NCERT Class 11th & 12th Biology Bot hu. NCERT Biology se juda koi bhi question poochhein!")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_query = update.message.text
    try:
        full_prompt = f"{NCERT_PROMPT}{user_query}"
        
        # New Google GenAI API Call
        response = client.models.generate_content(
            model='gemini-2.5-flash',
            contents=full_prompt,
        )
        
        if response.text:
            await update.message.reply_text(response.text)
        else:
            await update.message.reply_text("Kripya apna sawal thoda spasht (clear) karke poochhein.")
            
    except Exception as e:
        print(f"Gemini API Error: {e}")
        await update.message.reply_text("Server me koi dikkat aayi hai, kripya thodi der baad try karein.")

if __name__ == "__main__":
    app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), handle_message))
    
    print("NCERT Bot running successfully on Render...")
    app.run_polling()
