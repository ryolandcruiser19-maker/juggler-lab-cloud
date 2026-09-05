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


print("=== machine_analysis構造 ===")


cursor.execute(
    """
    PRAGMA table_info(machine_analysis)
    """
)


for row in cursor.fetchall():

    print(row)



print()


print("=== 最新データ ===")


cursor.execute(
    """
    SELECT
        *
    FROM machine_analysis
    WHERE 日付 = '2026-08-02'
    ORDER BY 評価スコア DESC
    LIMIT 20
    """
)


for row in cursor.fetchall():

    print(row)



conn.close()