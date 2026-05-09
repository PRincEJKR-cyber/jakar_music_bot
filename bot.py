import logging
import os
import asyncio
import aiohttp
import yt_dlp
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, MessageHandler,
    filters, ContextTypes, CallbackQueryHandler
)

BOT_TOKEN = "8729876434:AAEtQnFpVANWXrBvg3360q1JfFvLYTljwQI"
AUDD_API_KEY = "test"

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = (
        "👋 Salom! Men <b>Jakar Music Bot</b>man!\n\n"
        "🎵 <b>Nima qila olaman:</b>\n"
        "• Qo'shiq matni → qo'shiq nomini topaman\n"
        "• YouTube link → video/audio yuklayman\n"
        "• Instagram link → video/reel yuklayman\n\n"
        "📌 <b>Foydalanish:</b>\n"
        "• Qo'shiq matnini yuboring\n"
        "• Yoki link yuboring (YouTube, Instagram)\n\n"
        "❓ Yordam: /help"
    )
    await update.message.reply_text(text, parse_mode="HTML")

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = (
        "📖 <b>Qo'llanma:</b>\n\n"
        "🎵 <b>Qo'shiq topish:</b>\n"
        "Qo'shiq matnidan bir necha qatorni yuboring\n\n"
        "📥 <b>Video yuklab olish:</b>\n"
        "YouTube, Instagram yoki boshqa link yuboring\n\n"
        "⚙️ <b>Komandalar:</b>\n"
        "/start - Botni boshlash\n"
        "/help - Yordam\n"
    )
    await update.message.reply_text(text, parse_mode="HTML")
  async def find_song_by_lyrics(lyrics: str):
    url = "https://api.audd.io/findLyrics/"
    params = {"api_token": AUDD_API_KEY, "q": lyrics}
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, params=params, timeout=aiohttp.ClientTimeout(total=10)) as resp:
                data = await resp.json()
                if data.get("status") == "success" and data.get("result"):
                    return data["result"][0]
    except Exception as e:
        logger.error(f"AudD xatosi: {e}")
    return None

def download_video(url: str, output_path: str):
    ydl_opts = {
        "outtmpl": output_path + "/%(title)s.%(ext)s",
        "format": "best[filesize<50M]/best",
        "quiet": True,
        "no_warnings": True,
        "noplaylist": True,
    }
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            return ydl.prepare_filename(info)
    except Exception as e:
        logger.error(f"Yuklab olish xatosi: {e}")
        return None

def download_audio(url: str, output_path: str):
    ydl_opts = {
        "outtmpl": output_path + "/%(title)s.%(ext)s",
        "format": "bestaudio/best",
        "postprocessors": [{"key": "FFmpegExtractAudio", "preferredcodec": "mp3", "preferredquality": "192"}],
        "quiet": True,
        "no_warnings": True,
        "noplaylist": True,
    }
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            return output_path + f"/{info.get('title', 'audio')}.mp3"
    except Exception as e:
        logger.error(f"Audio xatosi: {e}")
        return None
      def is_youtube_link(text):
    return any(x in text for x in ["youtube.com", "youtu.be"])

def is_instagram_link(text):
    return "instagram.com" in text

def is_url(text):
    return text.startswith("http://") or text.startswith("https://")

async def download_and_send(update, context, url, format_type):
    output_path = "/tmp"
    loop = asyncio.get_event_loop()
    try:
        if format_type == "audio":
            filepath = await loop.run_in_executor(None, download_audio, url, output_path)
        else:
            filepath = await loop.run_in_executor(None, download_video, url, output_path)
        if filepath and os.path.exists(filepath):
            if os.path.getsize(filepath) > 50 * 1024 * 1024:
                await update.message.reply_text("❌ Fayl 50MB dan katta!")
                os.remove(filepath)
                return
            with open(filepath, "rb") as f:
                if format_type == "audio":
                    await update.message.reply_audio(f, caption="🎵 @Jakar_music_bot")
                else:
                    await update.message.reply_video(f, caption="🎬 @Jakar_music_bot")
            os.remove(filepath)
        else:
            await update.message.reply_text("❌ Yuklab olishda xatolik!")
    except Exception as e:
        logger.error(f"Xato: {e}")
        await update.message.reply_text("❌ Xatolik yuz berdi!")
      async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    if is_url(text):
        if is_youtube_link(text):
            keyboard = [[
                InlineKeyboardButton("🎵 MP3", callback_data=f"audio|{text}"),
                InlineKeyboardButton("🎬 MP4", callback_data=f"video|{text}"),
            ]]
            await update.message.reply_text("📥 Qanday formatda?", reply_markup=InlineKeyboardMarkup(keyboard))
        else:
            await update.message.reply_text("⏳ Yuklanmoqda...")
            await download_and_send(update, context, text, "video")
        return
    if len(text) > 10:
        await update.message.reply_text("🔍 Qo'shiq qidirilmoqda...")
        song = await find_song_by_lyrics(text)
        if song:
            await update.message.reply_text(
                f"🎵 <b>Topildi!</b>\n\n🎤 <b>Ijrochi:</b> {song.get('artist')}\n🎼 <b>Nomi:</b> {song.get('title')}",
                parse_mode="HTML"
            )
        else:
            await update.message.reply_text("😔 Qo'shiq topilmadi. Ko'proq matn yuboring.")
    else:
        await update.message.reply_text("❓ Link yoki qo'shiq matni yuboring!")

async def callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    format_type, url = query.data.split("|", 1)
    await query.edit_message_text("⏳ Yuklanmoqda...")
    await download_and_send(query, context, url, format_type)

def main():
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CallbackQueryHandler(callback_handler))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    print("✅ Bot ishga tushdi!")
    app.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()
