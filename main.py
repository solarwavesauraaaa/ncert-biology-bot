try:
        full_prompt = f"{NCERT_PROMPT}{user_query}"
        
        # Fresh client call inside thread to avoid loop binding issues
        def generate_ai_response():
            local_client = genai.Client(api_key=GEMINI_KEY.strip())
            return local_client.models.generate_content(
                model='gemini-2.5-flash',
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
        # Logs detailed exception type and traceback
        print(f"CRITICAL ERROR LOG: {type(e).__name__} - {e}")
        await update.message.reply_text("Server me koi dikkat aayi hai, kripya thodi der baad try karein.")
