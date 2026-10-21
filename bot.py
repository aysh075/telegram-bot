import telebot
import os
import logging
import re
import time
import threading
import shutil
import schedule
from datetime import datetime, timedelta
from telebot import types
from dotenv import load_dotenv
from migrations import run_migrations
from database import (
    get_user_data, update_user_state, clear_user_state,
    add_habit_to_db, get_user_habits, is_habit_done_today, log_habit_completion,
    check_habit_owner, get_all_habits_for_reminders, delete_all_user_habits
)

logging.basicConfig(
    level=logging.ERROR,
    format='%(asctime)s - %(levelname)s - %(message)s',
    filename='bot_errors.log'
)

load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN")
bot = telebot.TeleBot(BOT_TOKEN)

run_migrations()

DB_NAME = "bot_database.db"
BACKUP_NAME = "bot_database_backup.db"

def create_backup():
    try:
        if os.path.exists(DB_NAME):
            shutil.copyfile(DB_NAME, BACKUP_NAME)
            current_time = time.strftime("%Y-%m-%d %H:%M:%S")
            print(f"💾 [{current_time}] Автоматическая резервная копия базы данных успешно создана.")
    except Exception as e:
        logging.error(f"Ошибка при создании бэкапа: {e}")

# Изменено: Умный расчет времени с учетом часового пояса пользователя (Критерии 1, 2, 3)
def send_reminders():
    try:
        utc_now = datetime.now(datetime.timezone.utc).replace(tzinfo=None)
        habits = get_all_habits_for_reminders()

        for habit_id, user_id, name, habit_time, tz_offset in habits:
            # Если привычка сегодня уже выполнена, то не шлем напоминание (Критерий 3)
            if is_habit_done_today(habit_id):
                continue

            # Вычисляем текущее местное время пользователя на основе серверного UTC
            user_local_time = utc_now + timedelta(hours=tz_offset)
            current_time_str = user_local_time.strftime("%H:%M")

            if habit_time == current_time_str:
                bot.send_message(
                    user_id,
                    f"🕒 Местное время {current_time_str}! Не забудь выполнить свою привычку: **{name}**!\nОтметь её через /list.",
                    parse_mode="Markdown"
                )
    except Exception as e:
        logging.error(f"Ошибка в отправке напоминаний: {e}")

def scheduler_loop():
    schedule.every().minute.do(send_reminders)
    schedule.every().hour.do(create_backup)
    create_backup()
    while True:
        schedule.run_pending()
        time.sleep(1)

@bot.message_handler(commands=['start', 'help'])
def send_welcome(message):
    try:
        clear_user_state(message.from_user.id)
        help_text = (
            "Привет! Я помогу тебе управлять полезными привычками с учетом твоего времени.\n\n"
            "📌 /add - Создать новую привычку\n"
            "📌 /list - Показать список привычек на сегодня\n"
            "📌 /off - Отключить все напоминания разом\n"
            "📌 /cancel - Отменить текущий диалог"
        )
        bot.reply_to(message, help_text)
    except Exception as e:
        logging.error(f"Ошибка в команде start/help: {e}")

# Новое: Отключение всех напоминаний одной командой (Критерий 4)
@bot.message_handler(commands=['off'])
def turn_off_all_reminders(message):
    try:
        user_id = message.from_user.id
        delete_all_user_habits(user_id)
        bot.reply_to(message, "📴 Все ваши привычки и напоминания успешно удалены одной командой!")
    except Exception as e:
        logging.error(f"Ошибка в команде /off: {e}")

@bot.message_handler(commands=['cancel'])
def cancel_process(message):
    try:
        user_id = message.from_user.id
        user_data = get_user_data(user_id)
        if user_data["state"]:
            clear_user_state(user_id)
            bot.reply_to(message, "❌ Процесс создания привычки отменен.")
        else:
            bot.reply_to(message, "У вас нет активного процесса создания привычки.")
    except Exception as e:
        logging.error(f"Ошибка в команде cancel: {e}")

@bot.message_handler(commands=['add'])
def start_add_habit(message):
    try:
        user_id = message.from_user.id
        update_user_state(user_id, state="WAITING_NAME")
        bot.reply_to(message, "📝 Шаг 1/4: Введите название новой привычки:")
    except Exception as e:
        logging.error(f"Ошибка в начале команды add: {e}")

@bot.message_handler(commands=['list'])
def list_habits(message):
    try:
        user_id = message.from_user.id
        habits = get_user_habits(user_id)

        if not habits:
            bot.reply_to(message, "У вас пока нет созданных привычек. Добавьте их с помощью /add!")
            return

        markup = types.InlineKeyboardMarkup()
        text_lines = ["📋 **Твои привычки на сегодня:**\n"]

        for index, habit in enumerate(habits, start=1):
            habit_id, name = habit
            done = is_habit_done_today(habit_id)
            status_emoji = "✅ отмечено" if done else "❌ нет"
            text_lines.append(f"{index}. {name} — {status_emoji}")

            if not done:
                button = types.InlineKeyboardButton(text=f"Отметить: {name}", callback_data=f"done_{habit_id}")
                markup.add(button)

        bot.send_message(message.chat.id, "\n".join(text_lines), reply_markup=markup, parse_mode="Markdown")
    except Exception as e:
        logging.error(f"Ошибка в команде list: {e}")

@bot.callback_query_handler(func=lambda call: call.data.startswith('done_'))
def handle_habit_click(call):
    try:
        user_id = call.from_user.id
        habit_id = int(call.data.split('_')[1])

        if not check_habit_owner(habit_id, user_id):
            bot.answer_callback_query(call.id, text="⚠️ Ошибка доступа!", show_alert=True)
            return

        if is_habit_done_today(habit_id):
            bot.answer_callback_query(call.id, text="⚠️ Эта привычка уже отмечена сегодня!", show_alert=True)
            return

        success = log_habit_completion(habit_id)

        if success:
            bot.answer_callback_query(call.id, text="🎉 Привычка успешно отмечена!")
            habits = get_user_habits(user_id)
            markup = types.InlineKeyboardMarkup()
            text_lines = ["📋 **Твои привычки на сегодня:**\n"]

            for index, habit in enumerate(habits, start=1):
                h_id, name = habit
                done = is_habit_done_today(h_id)
                status_emoji = "✅ отмечено" if done else "❌ нет"
                text_lines.append(f"{index}. {name} — {status_emoji}")
                if not done:
                    button = types.InlineKeyboardButton(text=f"Отметить: {name}", callback_data=f"done_{h_id}")
                    markup.add(button)

            bot.edit_message_text(
                chat_id=call.message.chat.id,
                message_id=call.message.id,
                text="\n".join(text_lines),
                reply_markup=markup,
                parse_mode="Markdown"
            )
    except Exception as e:
        logging.error(f"Ошибка в обработке клика кнопки: {e}")

@bot.message_handler(func=lambda message: message.text and message.text.startswith('/'))
def unknown_command(message):
    try:
        bot.reply_to(message, "Ой, я не знаю такой команды. 🧐 Введите /help для подсказки.")
    except Exception as e:
        logging.error(f"Ошибка неизвестной команды: {e}")

@bot.message_handler(func=lambda message: True)
def handle_dialogue(message):
    try:
        user_id = message.from_user.id
        user_data = get_user_data(user_id)
        current_state = user_data["state"]

        if not current_state:
            bot.reply_to(message, "Используйте /add, чтобы завести привычку!")
            return

        text = message.text.strip() if message.text else ""

        if current_state == "WAITING_NAME":
            if not text:
                bot.reply_to(message, "❌ Название не может быть пустым.")
                return
            update_user_state(user_id, state="WAITING_FREQUENCY", name=text)
            bot.reply_to(message, "🔄 Шаг 2/4: Как часто вы хотите этим заниматься?:")

        elif current_state == "WAITING_FREQUENCY":
            if not text:
                bot.reply_to(message, "❌ Укажите частоту:")
                return
            update_user_state(user_id, state="WAITING_TIME", frequency=text)
            bot.reply_to(message, "🕒 Шаг 3/4: Укажите местное время напоминания в формате ЧЧ:ММ:")

        elif current_state == "WAITING_TIME":
            time_match = re.match(r"^([0-1]?[0-9]|2[0-3]):[0-5][0-9]$", text)
            if not time_match:
                bot.reply_to(message, "❌ Неверный формат! Введите ЧЧ:ММ:")
                return
            update_user_state(user_id, state="WAITING_TZ", time=text)
            # Шаг 4: Явный запрос часового пояса у пользователя (Критерий 1)
            bot.reply_to(message, "🌍 Шаг 4/4: Введите смещение вашего часового пояса от UTC (например, +3 для Москвы, +4 для Баку, или -5 для Нью-Йорка):")

        elif current_state == "WAITING_TZ":
            # Валидация числового ввода часового пояса
            try:
                tz_offset = int(text.replace("+", ""))
                if not (-12 <= tz_offset <= 14):
                    raise ValueError
            except ValueError:
                bot.reply_to(message, "❌ Неверный часовой пояс! Введите число от -12 до +14:")
                return

            add_habit_to_db(user_id, user_data["name"], user_data["frequency"], user_data["time"], tz_offset)
            bot.reply_to(
                message,
                f"🎉 Привычка **{user_data['name']}** успешно создана! Напоминание придет в {user_data['time']} по вашему местному времени (UTC{text if tz_offset < 0 else '+' + str(tz_offset)}).",
                parse_mode="Markdown"
            )
            clear_user_state(user_id)

    except Exception as e:
        logging.error(f"Критическая ошибка в диалоге: {e}")

if __name__ == "__main__":
    threading.Thread(target=scheduler_loop,daemon=True).start()

    print("Бот успешно запущен...")
    bot.infinity_polling()