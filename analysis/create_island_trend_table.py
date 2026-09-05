import sqlite3
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent.parent

DB_PATH = (
    BASE_DIR
    / "database"
    / "juggler.db"
)


def create_table():

    conn = sqlite3.connect(DB_PATH)

    cursor = conn.cursor()


    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS island_trend_analysis
        (

            島 TEXT PRIMARY KEY,

            総日数 INTEGER,

            総台数 INTEGER,

            平均G数 REAL,

            ◎台数 INTEGER,

            ○台数 INTEGER,

            ◎率 REAL,

            平均評価スコア REAL,

            更新日 TEXT

        )
        """
    )


    conn.commit()

    conn.close()


    print(
        "island_trend_analysis作成完了"
    )


if __name__ == "__main__":

    create_table()