import sqlite3
from datetime import datetime

def init_db():
    # Миграции теперь запускаются отдельно, но оставим для совместимости
    pass

def get_user_data(user_id):
    conn = sqlite3.connect("bot_database.db")
    cursor = conn.cursor()
    cursor.execute("SELECT state, habit_name, habit_frequency, habit_time FROM user_states WHERE user_id = ?", (user_id,))
    row = cursor.fetchone()
    conn.close()
    if row:
        return {"state": row[0], "name": row[1], "frequency": row[2], "time": row[3]}
    return {"state": None, "name": None, "frequency": None, "time": None}

def update_user_state(user_id, state=None, name=None, frequency=None, time=None):
    conn = sqlite3.connect("bot_database.db")
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO user_states (user_id, state, habit_name, habit_frequency, habit_time)
        VALUES (?, ?, ?, ?, ?)
        ON CONFLICT(user_id) DO UPDATE SET
            state = COALESCE(?, state),
            habit_name = COALESCE(?, habit_name),
            habit_frequency = COALESCE(?, habit_frequency),
            habit_time = COALESCE(?, habit_time)
    ''', (user_id, state, name, frequency, time, state, name, frequency, time))
    conn.commit()
    conn.close()

def clear_user_state(user_id):
    conn = sqlite3.connect("bot_database.db")
    cursor = conn.cursor()
    cursor.execute("DELETE FROM user_states WHERE user_id = ?", (user_id,))
    conn.commit()
    conn.close()

# Изменено: теперь сохраняется и часовой пояс (по умолчанию UTC+3 или вводится пользователем)
def add_habit_to_db(user_id, name, frequency, time, timezone_offset=0):
    conn = sqlite3.connect("bot_database.db")
    cursor = conn.cursor()
    cursor.execute("INSERT INTO habits (user_id, name, frequency, time, timezone_offset) VALUES (?, ?, ?, ?, ?)",(user_id, name, frequency, time, timezone_offset))
    conn.commit()
    conn.close()

def get_user_habits(user_id):
    conn = sqlite3.connect("bot_database.db")
    cursor = conn.cursor()
    cursor.execute("SELECT id, name FROM habits WHERE user_id = ?", (user_id,))
    habits = cursor.fetchall()
    conn.close()
    return habits

def is_habit_done_today(habit_id):
    today = datetime.now().strftime("%Y-%m-%d")
    conn = sqlite3.connect("bot_database.db")
    cursor = conn.cursor()
    cursor.execute("SELECT id FROM habit_logs WHERE habit_id = ? AND date = ?", (habit_id, today))
    row = cursor.fetchone()
    conn.close()
    return row is not None

def log_habit_completion(habit_id):
    today = datetime.now().strftime("%Y-%m-%d")
    conn = sqlite3.connect("bot_database.db")
    cursor = conn.cursor()
    try:
        cursor.execute("INSERT INTO habit_logs (habit_id, date) VALUES (?, ?)", (habit_id, today))
        conn.commit()
        success = True
    except sqlite3.IntegrityError:
        success = False
    conn.close()
    return success

def check_habit_owner(habit_id, user_id):
    conn = sqlite3.connect("bot_database.db")
    cursor = conn.cursor()
    cursor.execute("SELECT id FROM habits WHERE id = ? AND user_id = ?", (habit_id, user_id))
    row = cursor.fetchone()
    conn.close()
    return row is not None

# Новое: получение всех привычек вместе с часовым поясом и их id
def get_all_habits_for_reminders():
    conn = sqlite3.connect("bot_database.db")
    cursor = conn.cursor()
    cursor.execute("SELECT id, user_id, name, time, timezone_offset FROM habits")
    rows = cursor.fetchall()
    conn.close()
    return rows

# Новое: удаление всех напоминаний пользователя одной командой (Критерий 4)
def delete_all_user_habits(user_id):
    conn = sqlite3.connect("bot_database.db")
    cursor = conn.cursor()
    cursor.execute("DELETE FROM habits WHERE user_id = ?", (user_id,))
    conn.commit()
    conn.close()
