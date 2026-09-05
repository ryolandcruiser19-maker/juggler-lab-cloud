import sqlite3
from pathlib import Path


DB_PATH = Path(__file__).resolve().parent / "juggler.db"


conn = sqlite3.connect(DB_PATH)

cursor = conn.cursor()


cursor.execute(
    """
    SELECT
        日付,
        台番号,
        信頼度補正,
        島
    FROM juggler_data
    WHERE 台番号 = 969
    ORDER BY 日付
    """
)


rows = cursor.fetchall()


for row in rows:
    print(row)


conn.close()