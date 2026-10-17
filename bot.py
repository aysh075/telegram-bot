import telebot
import os
import logging
import re
from dotenv import load_dotenv
from database import init_db, get_user_data, update_user_state, clear_user_state


logging.basicConfig(
    level=logging.ERROR,
    format='%(asctime)s - %(levelname)s - %(message)s',
    filename='bot_errors.log'
)

load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN")
bot = telebot.TeleBot(BOT_TOKEN)

init_db()


@bot.message_handler(commands=['start', 'help'])
def send_welcome(message):
    try:
        clear_user_state(message.from_user.id) # Hər ehtimala qarşı köhnə yarımçıq qalan state-i silirik
        help_text = (
            "Привет! Я помогу тебе сформировать полезные привычки.\n\n"
            "📌 Чтобы начать создание привычки, введи команду: /add\n"
            "📌 В любой момент вы можете отменить процесс командой: /cancel"
        )
        bot.reply_to(message, help_text)
    except Exception as e:
        logging.error(f"Ошибка в команде start/help: {e}")


@bot.message_handler(commands=['cancel'])
def cancel_process(message):
    try:
        user_id = message.from_user.id
        user_data = get_user_data(user_id)

        if user_data["state"]:
            clear_user_state(user_id)
            bot.reply_to(message, "❌ Процесс создания привычки отменен. Мы вернулись в обычный режим.")
        else:
            bot.reply_to(message, "У вас нет активного процесса создания привычки, который можно было бы отменить.")
    except Exception as e:
        logging.error(f"Ошибка в команде cancel: {e}")


@bot.message_handler(commands=['add'])
def start_add_habit(message):
    try:
        user_id = message.from_user.id
        
        update_user_state(user_id, state="WAITING_NAME")
        bot.reply_to(message, "📝 Шаг 1/3: Введите название новой привычки (например: Чтение книг, Спорт):")
    except Exception as e:
        logging.error(f"Ошибка в начале команды add: {e}")


@bot.message_handler(func=lambda message: True)
def handle_dialogue(message):
    try:
        user_id = message.from_user.id
        user_data = get_user_data(user_id)
        current_state = user_data["state"]

        
        if not current_state:
            bot.reply_to(message, "Я вижу твое сообщение, но давай начнем с главного: введи команду /add, чтобы завести привычку!")
            return

        text = message.text.strip() if message.text else ""

        
        if current_state == "WAITING_NAME":
            if not text or text.startswith('/'):
                bot.reply_to(message, "❌ Название привычки не может быть пустым или командой. Пожалуйста, введите нормальное название:")
                return

            
            update_user_state(user_id, state="WAITING_FREQUENCY", name=text)
            bot.reply_to(message, "🔄 Шаг 2/3: Как часто вы хотите этим заниматься? (например: Каждый день, 3 раза в неделю):")

        
        elif current_state == "WAITING_FREQUENCY":
            if not text or text.startswith('/'):
                bot.reply_to(message, "❌ Пожалуйста, укажите частоту выполнения (например: Каждый день):")
                return

            update_user_state(user_id, state="WAITING_TIME", frequency=text)
            bot.reply_to(message, "🕒 Шаг 3/3: Укажите время для напоминания в формате ЧЧ:ММ (например: 08:30 или 21:00):")

        
        elif current_state == "WAITING_TIME":
            
            time_match = re.match(r"^([01]?[0-9]|2[0-3]):[0-5][0-9]$", text)

            if not time_match:
                bot.reply_to(message, "❌ Неверный формат времени! Пожалуйста, введите время строго в формате ЧЧ:ММ (например: 15:45 или 09:00):")
                return

            
            update_user_state(user_id, time=text)

        
            final_data = get_user_data(user_id)
            success_text = (
                "🎉 Отлично! Привычка успешно настроена и сохранена в базе данных!\n\n"
                f"📋 **Название:** {final_data['name']}\n"
                f"🔄 **Частота:** {final_data['frequency']}\n"
                f"🕒 **Время напоминания:** {final_data['time']}\n\n"
                "Я буду следить за твоим прогрессом!"
            )
            bot.reply_to(message, success_text, parse_mode="Markdown")

        
            clear_user_state(user_id)

    except Exception as e:
        logging.error(f"Критическая ошибка в диалоге: {e}")

if __name__ == "__main__":
    print("Бот успешно запущен...")
    bot.infinity_polling()