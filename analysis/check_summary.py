import sqlite3
from pathlib import Path
import pandas as pd


# ==============================
# パス設定
# ==============================

BASE_DIR = Path(__file__).resolve().parent.parent

DB_PATH = (
    BASE_DIR
    / "database"
    / "juggler.db"
)



# ==============================
# 確認
# ==============================

def check_summary():

    conn = sqlite3.connect(
        DB_PATH
    )


    df = pd.read_sql(
        """
        SELECT
            *
        FROM analysis_summary
        ORDER BY
            日付 DESC
        LIMIT 10
        """,
        conn
    )


    conn.close()


    print("=" * 60)

    print(
        "【分析サマリー】"
    )

    print()

    print(df.to_string(index=False))



# ==============================
# 実行
# ==============================

if __name__ == "__main__":

    check_summary()