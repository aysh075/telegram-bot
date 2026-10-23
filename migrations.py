import sqlite3

DB_NAME = "bot_database.db"

def run_migrations():
    print("⏳ Запуск миграций базы данных для 7-го этапа...")
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS user_states (
            user_id INTEGER PRIMARY KEY,
            state TEXT,
            habit_name TEXT,
            habit_frequency TEXT,
            habit_time TEXT
        )
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS habits (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            name TEXT,
            frequency TEXT,
            time TEXT,
            timezone_offset INTEGER DEFAULT 0,
            is_active INTEGER DEFAULT 1
        )
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS habit_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            habit_id INTEGER,
            date TEXT,
            UNIQUE(habit_id, date) ON CONFLICT IGNORE
        )
    ''')

    cursor.execute("CREATE INDEX IF NOT EXISTS idx_habits_user ON habits(user_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_logs_date ON habit_logs(date)")

    conn.commit()
    conn.close()
    print("✅ Миграции успешно применены!")

if __name__ == "__main__":
    run_migrations()