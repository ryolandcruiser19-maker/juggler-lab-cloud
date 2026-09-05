import sqlite3
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent.parent

DB_PATH = (
    BASE_DIR
    / "database"
    / "juggler.db"
)


conn = sqlite3.connect(DB_PATH)

cursor = conn.cursor()


print("=== テーブル一覧 ===")

cursor.execute(
    """
    SELECT name
    FROM sqlite_master
    WHERE type='table'
    """
)

for row in cursor.fetchall():
    print(row)



print("\n=== island_analysis構造 ===")

cursor.execute(
    """
    PRAGMA table_info(island_analysis)
    """
)

for row in cursor.fetchall():
    print(row)



print("\n=== 最新データ ===")

cursor.execute(
    """
    SELECT *
    FROM island_analysis
    ORDER BY 日付 DESC
    LIMIT 5
    """
)

for row in cursor.fetchall():
    print(row)



conn.close()