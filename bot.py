import telebot
import os
import logging
from dotenv import load_dotenv

# Səhvlərin loq faylına yazılması
logging.basicConfig(
    level=logging.ERROR,
    format='%(asctime)s - %(levelname)s - %(message)s',
    filename='bot_errors.log'
)

load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN")
bot = telebot.TeleBot(BOT_TOKEN)

# 1. /start və /help komandaları
@bot.message_handler(commands=['start', 'help'])
def send_welcome(message):
    try:
        help_text = (
            "Привет! Я помогу тебе сформировать полезные привычки и следить за ними каждый день.\n\n"
            "Чтобы начать, просто добавь новую цель. Например, напиши команду: /add чтение.\n"
            "После этого ты сможешь отмечать выполнение и смотреть свой прогресс!"
        )
        bot.reply_to(message, help_text)
    except Exception as e:
        logging.error(f"Ошибка в команде start/help: {e}")

# 2. Naməlum komandaların işlənməsi
@bot.message_handler(func=lambda message: message.text and message.text.startswith('/'))
def unknown_command(message):
    try:
        reply_text = (
            "Ой, я не знаю такой команды. 🧐\n"
            "Пожалуйста, проверь написание или введи /help, чтобы посмотреть, что я умею."
        )
        bot.reply_to(message, reply_text)
    except Exception as e:
        logging.error(f"Ошибка при обработке неизвестной команды: {e}")

# 3. Adi mətnlərin (komanda olmayan) işlənməsi
@bot.message_handler(func=lambda message: True)
def handle_text(message):
    try:
        reply_text = (
            "Я вижу твое сообщение, но пока умею работать только с привычками.\n"
            "Давай начнем с главного: введи команду /add и название привычки, чтобы завести её!"
        )
        bot.reply_to(message, reply_text)
    except Exception as e:
        logging.error(f"Критическая ошибка при обработке сообщения: {e}")

if __name__ == "__main__":
    print("Бот успешно запущен...")
    bot.infinity_polling()