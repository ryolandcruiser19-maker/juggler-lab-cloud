import sqlite3
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent.parent

DB_PATH = (
    BASE_DIR
    / "database"
    / "juggler.db"
)



def create_machine_history_table():

    conn = sqlite3.connect(DB_PATH)

    cursor = conn.cursor()


    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS machine_history_analysis
        (

            台番号 INTEGER,

            機種 TEXT,

            島 TEXT,

            稼働日数 INTEGER,

            累計G数 INTEGER,

            平均G数 REAL,

            平均合成確率 REAL,

            ◎回数 INTEGER,

            ○回数 INTEGER,

            高評価率 REAL,

            最終日 TEXT,

            最終評価 TEXT,

            PRIMARY KEY
            (
                台番号
            )

        )
        """
    )


    conn.commit()

    conn.close()


    print(
        "machine_history_analysisテーブル作成完了"
    )



if __name__ == "__main__":

    create_machine_history_table()