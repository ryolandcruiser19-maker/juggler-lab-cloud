import sqlite3
import os


DB_PATH = "database/juggler.db"


def create_prediction_history_table():

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS prediction_history(

            日付 TEXT,
            台番号 INTEGER,
            機種 TEXT,
            島 TEXT,

            順位 INTEGER,

            総合スコア REAL,

            採用フラグ INTEGER DEFAULT 0,

            実績評価 TEXT,

            備考 TEXT,

            PRIMARY KEY(日付, 台番号)

        )
        """
    )

    conn.commit()
    conn.close()

    print("prediction_historyテーブル作成完了")


if __name__ == "__main__":
    create_prediction_history_table()