import os
import logging
import requests
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ContextTypes,
    filters,
)

# Logging configuration
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)

# Fetch Environment Variables safely
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
TOGETHER_API_KEY = os.getenv("TOGETHER_API_KEY", "").strip()

MODELS = {
    "flux_real": {
        "name": "📸 Realism (FLUX.1)",
        "model_id": "black-forest-labs/FLUX.1-schnell",
        "prefix": "hyper-realistic photo, 8k resolution, realistic lighting, "
    },
    "anime": {
        "name": "🎨 Anime & Illustration",
        "model_id": "stabilityai/stable-diffusion-xl-base-1.0",
        "prefix": "masterpiece anime artwork, vibrant colors, detailed illustration, "
    },
    "art": {
        "name": "🖼️ Digital Art",
        "model_id": "black-forest-labs/FLUX.1-schnell",
        "prefix": "concept digital art, detailed painting, high artistic quality, "
    }
}

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if "selected_model" not in context.user_data:
        context.user_data["selected_model"] = "flux_real"

    keyboard = [
        [InlineKeyboardButton("📸 Photorealistic", callback_data="model_flux_real")],
        [InlineKeyboardButton("🎨 Anime & Illustration", callback_data="model_anime")],
        [InlineKeyboardButton("🖼️ Digital Art", callback_data="model_art")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    current_style = MODELS[context.user_data["selected_model"]]["name"]

    text = (
        "✨ **Welcome to OpenArt22_bot!** ✨\n\n"
        f"🎯 **Active Style:** {current_style}\n\n"
        "1. Select a style preset below.\n"
        "2. Type any prompt to generate your AI image!"
    )
    
    if update.message:
        await update.message.reply_text(text, parse_mode="Markdown", reply_markup=reply_markup)
    elif update.callback_query:
        await update.callback_query.message.edit_text(text, parse_mode="Markdown", reply_markup=reply_markup)

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    if query.data.startswith("model_"):
        selected_key = query.data.replace("model_", "")
        context.user_data["selected_model"] = selected_key
        await start(update, context)

async def generate_art(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_prompt = update.message.text.strip()
    if not user_prompt:
        await update.message.reply_text("Please enter a valid text prompt!")
        return

    selected_key = context.user_data.get("selected_model", "flux_real")
    model_info = MODELS[selected_key]
    full_prompt = f"{model_info['prefix']}{user_prompt}"

    status_msg = await update.message.reply_text(
        f"🎨 Generating image with **{model_info['name']}**...",
        parse_mode="Markdown"
    )

    try:
        url = "https://api.together.xyz/v1/images/generations"
        headers = {
            "Authorization": f"Bearer {TOGETHER_API_KEY}",
            "Content-Type": "application/json"
        }
        payload = {
            "model": model_info["model_id"],
            "prompt": full_prompt,
            "width": 1024,
            "height": 1024,
            "steps": 4,
            "n": 1,
            "response_format": "url"
        }

        response = requests.post(url, json=payload, headers=headers, timeout=60)
        data = response.json()

        if response.status_code == 200 and "data" in data and len(data["data"]) > 0:
            image_url = data["data"][0]["url"]
            await update.message.reply_photo(
                photo=image_url,
                caption=f"✨ **Prompt:** {user_prompt}\n🎭 **Style:** {model_info['name']}",
                parse_mode="Markdown"
            )
            await status_msg.delete()
        else:
            err_details = data.get("error", {}).get("message", "Generation failed.")
            await status_msg.edit_text(f"❌ Error: {err_details}")

    except Exception as e:
        logging.error(f"Generation error: {e}")
        await status_msg.edit_text("❌ Failed to process generation request.")

def main():
    if not TELEGRAM_BOT_TOKEN or not TOGETHER_API_KEY:
        logging.error("CRITICAL: TELEGRAM_BOT_TOKEN or TOGETHER_API_KEY is missing!")
        return

    app = Application.builder().token(TELEGRAM_BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(button_handler))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, generate_art))

    logging.info("OpenArt22_bot started successfully!")
    app.run_polling()

if __name__ == "__main__":
    main()
