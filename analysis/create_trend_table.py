import sqlite3
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent.parent

DB_PATH = (
    BASE_DIR
    / "database"
    / "juggler.db"
)


def create_trend_table():

    conn = sqlite3.connect(DB_PATH)

    cursor = conn.cursor()


    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS trend_analysis
        (

            分析日 TEXT,

            対象 TEXT,

            期間 INTEGER,

            総日数 INTEGER,

            ◎回数 INTEGER,

            ○回数 INTEGER,

            平均G数 REAL,

            平均スコア REAL,

            傾向スコア REAL,


            PRIMARY KEY
            (
                分析日,
                対象
            )

        )
        """
    )


    conn.commit()

    conn.close()


    print(
        "trend_analysisテーブル作成完了"
    )


if __name__ == "__main__":

    create_trend_table()