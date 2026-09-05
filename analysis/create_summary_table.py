import sqlite3
from pathlib import Path


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
# analysis_summary作成
# ==============================

def create_analysis_summary():

    conn = sqlite3.connect(
        DB_PATH
    )

    cursor = conn.cursor()


    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS analysis_summary
        (

            日付 TEXT PRIMARY KEY,

            総台数 INTEGER,

            ◎台数 INTEGER,

            ○台数 INTEGER,

            平均G数 REAL,

            平均合成確率 REAL,

            最高評価島 TEXT,

            最高島スコア REAL,

            強化機種 TEXT,

            コメント TEXT

        )
        """
    )


    conn.commit()

    conn.close()


    print(
        "analysis_summaryテーブル作成完了"
    )


# ==============================
# 実行
# ==============================

if __name__ == "__main__":

    create_analysis_summary()