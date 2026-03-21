import telebot
import yt_dlp
import os
from keep_alive import keep_alive 

TOKEN = os.environ.get('BOT_TOKEN')
bot = telebot.TeleBot(TOKEN)

# دالة بتجيب كل القنوات من 1 لـ 10 من إعدادات ريندر
def get_required_channels():
    channels = []
    for i in range(1, 11):
        ch = os.environ.get(f'CHANNEL_{i}')
        if ch:
            channels.append(ch)
    return channels

# دالة بتفحص المستخدم وتطلع القنوات اللي لسه مشتركش فيها
def get_unsubscribed_channels(user_id):
    channels = get_required_channels()
    unsubscribed = []
    for channel in channels:
        try:
            status = bot.get_chat_member(channel, user_id).status
            if status not in ['member', 'administrator', 'creator']:
                unsubscribed.append(channel)
        except Exception as e:
            print(f"Error checking sub for {channel}: {e}")
            unsubscribed.append(channel) 
    return unsubscribed

@bot.message_handler(commands=['start'])
def send_welcome(message):
    unsub = get_unsubscribed_channels(message.from_user.id)
    if unsub:
        # تجميع القنوات اللي ناقصة في رسالة واحدة
        channels_list = "\n".join([f"🔗 {ch}" for ch in unsub])
        bot.reply_to(message, f"عذراً عزيزي ✋\nيجب عليك الاشتراك في قنوات البوت أولاً لتتمكن من استخدامه.\n\n{channels_list}\n\nبعد الاشتراك أرسل /start")
        return
        
    bot.reply_to(message, "أهلاً بك! أرسل لي أي رابط من يوتيوب أو تيك توك وسأقوم بتحميله لك.")

@bot.message_handler(func=lambda message: True)
def download_video(message):
    unsub = get_unsubscribed_channels(message.from_user.id)
    if unsub:
        channels_list = "\n".join([f"🔗 {ch}" for ch in unsub])
        bot.reply_to(message, f"عذراً عزيزي ✋\nيجب عليك الاشتراك في قنوات البوت أولاً لتتمكن من التحميل.\n\n{channels_list}\n\nبعد الاشتراك أرسل الرابط مجدداً.")
        return

    url = message.text
    msg = bot.reply_to(message, "جاري معالجة الرابط والتحميل، يرجى الانتظار قليلاً... ⏳")
    
    ydl_opts = {
        'outtmpl': 'downloaded_video.%(ext)s',
        'format': 'best[ext=mp4]/best'
    }
    
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])
        
        for file in os.listdir('.'):
            if file.startswith('downloaded_video'):
                with open(file, 'rb') as video:
                    bot.send_video(message.chat.id, video)
                os.remove(file)
                bot.delete_message(message.chat.id, msg.message_id)
                break
                
    except Exception as e:
        bot.reply_to(message, f"حدث خطأ أثناء التحميل، تأكد من الرابط.")

keep_alive()
print("البوت يعمل الآن...")
bot.infinity_polling()
