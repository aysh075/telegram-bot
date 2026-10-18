import sqlite3
from datetime import datetime

def init_db():
    conn = sqlite3.connect("bot_database.db")
    cursor = conn.cursor()

# 1. İstifadəçinin FSM mərhələlərini saxlayan cədvəl (əvvəlki addımdan)
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS user_states (
            user_id INTEGER PRIMARY KEY,
            state TEXT,
            habit_name TEXT,
            habit_frequency TEXT,
            habit_time TEXT
        )
    ''')

# 2. VƏRDİŞLƏR CƏDVƏLİ (İzolyasiya üçün user_id ilə bağlayırıq)
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS habits (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        name TEXT,
        frequency TEXT,
        time TEXT
    )
''')

# 3. YERİNƏ YETİRİLMƏ TARİXÇƏSİ CƏDVƏLİ (İkiqat klik qoruması üçün)
# UNIQUE(habit_id, date) indeksi bazada eyni gündə 2-ci qeydin qarşısını alır
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS habit_logs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        habit_id INTEGER,
        date TEXT,
        UNIQUE(habit_id, date) ON CONFLICT IGNORE
        )
    ''')

    conn.commit()
    conn.close()

# FSM funksiyaları
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

# YENİ: Vərdişləri bazaya tam qeyd edən funksiya
def add_habit_to_db(user_id, name, frequency, time):
    conn = sqlite3.connect("bot_database.db")
    cursor = conn.cursor()
    cursor.execute("INSERT INTO habits (user_id, name, frequency, time) VALUES (?, ?, ?, ?)", (user_id, name, frequency, time))
    conn.commit()
    conn.close()

# YENİ: Yalnız konkret istifadəçinin vərdişlərini gətirən funksiya (Məlumat İZOLYASİYASI)
def get_user_habits(user_id):
    conn = sqlite3.connect("bot_database.db")
    cursor = conn.cursor()
    cursor.execute("SELECT id, name FROM habits WHERE user_id = ?", (user_id,))
    habits = cursor.fetchall()
    conn.close()
    return habits

# YENİ: Vərdişin bu gün yerinə yetirilib-yetirilmədiyini yoxlayan funksiya
def is_habit_done_today(habit_id):
    today = datetime.now().strftime("%Y-%m-%d")
    conn = sqlite3.connect("bot_database.db")
    cursor = conn.cursor()
    cursor.execute("SELECT id FROM habit_logs WHERE habit_id = ? AND date = ?", (habit_id, today))
    row = cursor.fetchone()
    conn.close()
    return row is not None

# YENİ: Vərdişi tamamlandı olaraq işarələyən funksiya (Qoruma ilə)
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