import sqlite3
from datetime import datetime
import pandas as pd

DB_PATH = "users.db"

def init_db():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    # Создаём таблицу, если её нет (старые пользователи будут сохранены)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            username TEXT,
            reached_end INTEGER DEFAULT 0
        )
    """)
    # Проверяем, есть ли колонка date_added, если нет — добавляем
    cursor.execute("PRAGMA table_info(users)")
    columns = [info[1] for info in cursor.fetchall()]
    if "date_added" not in columns:
        cursor.execute("ALTER TABLE users ADD COLUMN date_added TEXT")
    conn.commit()
    conn.close()

def add_or_update_user(user):
    """Добавляет нового пользователя или обновляет username существующего"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO users (user_id, username, date_added)
        VALUES (?, ?, ?)
        ON CONFLICT(user_id) DO UPDATE SET username=excluded.username
    """, (user.id, user.username or "", datetime.now().isoformat()))
    conn.commit()
    conn.close()

def mark_reached_end(user_id):
    """Помечает, что пользователь дошёл до конца второго поста"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("UPDATE users SET reached_end=1 WHERE user_id=?", (user_id,))
    conn.commit()
    conn.close()

def get_all_users():
    """Возвращает список всех пользователей для рассылки"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT user_id FROM users")
    users = [{"user_id": row[0]} for row in cursor.fetchall()]
    conn.close()
    return users

def export_to_excel():
    """Экспорт статистики пользователей в Excel"""
    conn = sqlite3.connect(DB_PATH)
    df = pd.read_sql_query("SELECT * FROM users", conn)
    conn.close()
    filename = "stats.xlsx"
    df.to_excel(filename, index=False)
    return filename
