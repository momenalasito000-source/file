import telebot
import yt_dlp
import os
from keep_alive import keep_alive 

TOKEN = os.environ.get('TELEGRAM_TOKEN')
bot = telebot.TeleBot(TOKEN)

MAX_SIZE_BYTES = 50 * 1024 * 1024  # 50MB حد تيليجرام

@bot.message_handler(commands=['start'])
def send_welcome(message):
    bot.reply_to(message, "أهلاً بك! أرسل لي أي رابط من يوتيوب أو تيك توك وسأقوم بتحميله لك.")

@bot.message_handler(func=lambda message: True)
def download_video(message):
    url = message.text
    msg = bot.reply_to(message, "جاري معالجة الرابط والتحميل، يرجى الانتظار قليلاً... ⏳")
    
    ydl_opts = {
        'outtmpl': 'downloaded_video.%(ext)s',
        'format': f'best[ext=mp4][filesize<{MAX_SIZE_BYTES}]/best[filesize<{MAX_SIZE_BYTES}]/best[ext=mp4]/best',
        'cookiefile': 'cookies.txt' if os.path.exists('cookies.txt') else None,
        'extractor_args': {'youtube': {'player_client': ['android']}},
    }
    
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])
        
        for file in os.listdir('.'): 
            if file.startswith('downloaded_video'):
                file_size = os.path.getsize(file)
                if file_size > MAX_SIZE_BYTES:
                    os.remove(file)
                    bot.edit_message_text("❌ الفيديو كبير جداً (أكثر من 50MB) ولا يمكن إرساله عبر تيليجرام.", message.chat.id, msg.message_id)
                    return
                with open(file, 'rb') as video:
                    bot.send_video(message.chat.id, video)
                os.remove(file)
                bot.delete_message(message.chat.id, msg.message_id)
                break
                
    except Exception as e:
        bot.reply_to(message, f"Error details: {str(e)}")

keep_alive()
print("البوت يعمل الآن...")
bot.infinity_polling()