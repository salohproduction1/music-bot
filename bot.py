import os
import re
import glob
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, CallbackQueryHandler, filters, ContextTypes

import yt_dlp

TOKEN = os.environ.get("TOKEN", "8937775934:AAGtrmcAKrER-V9oX2zI8jlVzVjBHYIf-aE")
FFMPEG_PATH = '/usr/bin'

user_search_results = {}

def safe_filename(name):
    return re.sub(r'[\\/*?:"<>|]', "_", name)[:50]

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🎵 Musik Bot!\n\n"
        "Qo'shiqchi yoki qo'shiq nomini yuboring\n\n"
        "📌 Misol:\n"
        "• Doston Ergashev\n"
        "• Drake\n"
        "• Кино\n\n"
        "Bot 10 ta variant chiqaradi, siz tanlaysiz! 🎧"
    )

async def search_music(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.message.text.strip()
    chat_id = update.message.chat_id
    msg = await update.message.reply_text(f"🔍 Qidiryapman: {query} ...")

    try:
        ydl_opts = {
            'quiet': True,
            'no_warnings': True,
            'extract_flat': 'in_playlist',
        }
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(f"ytsearch10:{query}", download=False)

        if not info or 'entries' not in info or not info['entries']:
            await msg.edit_text("❌ Hech narsa topilmadi.")
            return

        entries = [e for e in info['entries'] if e][:10]
        user_search_results[chat_id] = []
        keyboard = []

        for i, entry in enumerate(entries, 1):
            title = entry.get('title') or "Noma'lum"
            uploader = entry.get('uploader') or entry.get('channel') or "Noma'lum"
            duration = entry.get('duration') or 0
            mins = int(duration) // 60
            secs = int(duration) % 60
            video_id = entry.get('id') or ''

            user_search_results[chat_id].append({
                'title': title,
                'uploader': uploader,
                'id': video_id,
                'duration': f"{mins}:{secs:02d}"
            })

            btn_text = f"{i}. {title[:28]} ⏱{mins}:{secs:02d}"
            keyboard.append([InlineKeyboardButton(btn_text, callback_data=f"dl_{chat_id}_{i-1}")])

        keyboard.append([InlineKeyboardButton("❌ Bekor qilish", callback_data="cancel")])
        reply_markup = InlineKeyboardMarkup(keyboard)

        await msg.edit_text(
            f"🎵 '{query}' — {len(entries)} ta natija:\n👇 Birini tanlang:",
            reply_markup=reply_markup
        )

    except Exception as e:
        print(f"QIDIRUV XATOSI: {e}")
        await msg.edit_text(f"❌ Xato:\n{str(e)[:300]}")

async def download_selected(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if query.data == "cancel":
        await query.edit_message_text("❌ Bekor qilindi.")
        return

    try:
        parts = query.data.split("_")
        chat_id = int(parts[1])
        index = int(parts[2])
    except:
        await query.edit_message_text("❌ Xato. Qaytadan qidiring.")
        return

    if chat_id not in user_search_results or index >= len(user_search_results[chat_id]):
        await query.edit_message_text("❌ Xato. Qaytadan qidiring.")
        return

    song = user_search_results[chat_id][index]
    title = song['title']
    video_id = song['id']

    await query.edit_message_text(f"⬇️ Yuklanmoqda...\n🎵 {title}")

    safe_name = safe_filename(title)
    download_dir = os.path.join(os.getcwd(), "downloads")
    os.makedirs(download_dir, exist_ok=True)
    output_template = os.path.join(download_dir, f"{safe_name}.%(ext)s")

    ydl_opts = {
        'format': 'bestaudio/best',
        'outtmpl': output_template,
        'ffmpeg_location': FFMPEG_PATH,
        'postprocessors': [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'mp3',
            'preferredquality': '192',
        }],
        'quiet': False,
        'no_warnings': False,
    }

    try:
        video_url = f"https://www.youtube.com/watch?v={video_id}"
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([video_url])

        mp3_files = glob.glob(os.path.join(download_dir, "*.mp3"))
        if not mp3_files:
            await context.bot.send_message(chat_id, "❌ MP3 fayl topilmadi!")
            return

        mp3_file = max(mp3_files, key=os.path.getctime)
        file_size = os.path.getsize(mp3_file) / (1024 * 1024)

        if file_size > 50:
            await context.bot.send_message(chat_id, f"❌ Fayl juda katta: {file_size:.1f}MB")
            os.remove(mp3_file)
            return

        with open(mp3_file, 'rb') as audio:
            await context.bot.send_audio(
                chat_id=chat_id,
                audio=audio,
                title=title,
                performer=song.get('uploader', "Noma'lum"),
                caption=f"🎵 {title}\n👤 {song.get('uploader', '')}\n⏱ {song['duration']} | {file_size:.1f}MB"
            )

        os.remove(mp3_file)
        await context.bot.send_message(chat_id, "✅ Yuborildi! Yana qo'shiq nomini yuboring 🎧")

    except Exception as e:
        error_msg = str(e)
        print(f"YUKLASH XATOSI: {error_msg}")
        await context.bot.send_message(chat_id, f"❌ Xato:\n{error_msg[:300]}")

def main():
    app = ApplicationBuilder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(download_selected, pattern="^dl_|^cancel"))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, search_music))
    print("✅ Bot ishlamoqda...")
    app.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()
