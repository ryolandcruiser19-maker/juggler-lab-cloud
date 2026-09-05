import sqlite3
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent.parent

DB_PATH = (
    BASE_DIR
    / "database"
    / "juggler.db"
)


def create_prediction_score_table():

    conn = sqlite3.connect(DB_PATH)

    cursor = conn.cursor()


    cursor.execute(
        """
        DROP TABLE IF EXISTS prediction_score
        """
    )


    cursor.execute(
        """
        CREATE TABLE prediction_score
        (

            日付 TEXT,

            台番号 INTEGER,

            機種 TEXT,

            島 TEXT,


            基礎台評価 REAL,

            最近傾向評価 REAL,

            島評価 REAL,

            並び評価 REAL,


            イベント補正 REAL,

            使用済補正 REAL,

            前日補正 REAL,

            予想頻度補正 REAL,

            店舗状態補正 REAL,


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
        "prediction_scoreテーブル再作成完了"
    )


if __name__ == "__main__":

    create_prediction_score_table()