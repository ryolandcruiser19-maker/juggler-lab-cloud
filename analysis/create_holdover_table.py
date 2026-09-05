import sqlite3


DB_PATH = "database/juggler.db"


def create_holdover_table():

    conn = sqlite3.connect(DB_PATH)

    cursor = conn.cursor()


    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS machine_holdover_analysis
        (

            台番号 INTEGER PRIMARY KEY,

            機種 TEXT,

            島 TEXT,

            分析期間 INTEGER,

            前日高評価回数 INTEGER,

            翌日高評価回数 INTEGER,

            据え置き率 REAL,

            前日◎回数 INTEGER,

            翌日◎回数 INTEGER,

            更新日 TEXT

        )
        """
    )


    conn.commit()
    conn.close()


    print("machine_holdover_analysisテーブル作成完了")


if __name__ == "__main__":
    create_holdover_table()