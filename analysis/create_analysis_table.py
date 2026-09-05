import sqlite3
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent.parent

DB_PATH = (
    BASE_DIR
    / "database"
    / "juggler.db"
)


def create_analysis_tables():

    conn = sqlite3.connect(DB_PATH)

    cursor = conn.cursor()


    # ==============================
    # 島分析テーブル
    # ==============================

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS island_analysis
        (

            日付 TEXT,

            島 TEXT,

            台数 INTEGER,

            平均G数 REAL,

            平均合成確率 REAL,

            ◎台数 INTEGER,

            ○台数 INTEGER,

            評価スコア REAL,

            PRIMARY KEY
            (
                日付,
                島
            )

        )
        """
    )


    conn.commit()

    conn.close()


    print(
        "analysisテーブル作成完了"
    )


if __name__ == "__main__":

    create_analysis_tables()