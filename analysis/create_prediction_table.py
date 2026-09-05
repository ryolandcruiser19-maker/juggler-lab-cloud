import sqlite3
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent.parent

DB_PATH = (
    BASE_DIR
    / "database"
    / "juggler.db"
)


def create_prediction_table():

    conn = sqlite3.connect(DB_PATH)

    cursor = conn.cursor()


    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS prediction_score
        (

            日付 TEXT,

            台番号 INTEGER,

            機種 TEXT,

            島 TEXT,


            台番号実績 REAL,

            島評価 REAL,

            並び評価 REAL,

            イベント補正 REAL,


            使用済補正 REAL,

            前日補正 REAL,


            総合スコア REAL,


            判定 TEXT,


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
        "prediction_scoreテーブル作成完了"
    )


if __name__ == "__main__":

    create_prediction_table()