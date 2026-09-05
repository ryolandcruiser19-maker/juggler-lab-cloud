import sqlite3
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent.parent

DB_PATH = (
    BASE_DIR
    / "database"
    / "juggler.db"
)



def create_machine_table():

    conn = sqlite3.connect(DB_PATH)

    cursor = conn.cursor()


    # ==============================
    # 台分析テーブル
    # ==============================

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS machine_analysis
        (

            日付 TEXT,

            台番号 INTEGER,

            機種 TEXT,

            島 TEXT,

            G数 INTEGER,

            合成確率 REAL,

            評価 TEXT,

            ◎回数 INTEGER,

            ○回数 INTEGER,

            評価スコア REAL,

            PRIMARY KEY
            (
                日付,
                台番号
            )

        )
        """
    )


    conn.commit()

    conn.close()


    print(
        "machine_analysisテーブル作成完了"
    )



if __name__ == "__main__":

    create_machine_table()