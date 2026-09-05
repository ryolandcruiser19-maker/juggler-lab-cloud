import sqlite3
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent.parent

DB_PATH = (
    BASE_DIR
    / "database"
    / "juggler.db"
)


def create_alignment_table():

    conn = sqlite3.connect(DB_PATH)

    cursor = conn.cursor()


    # 既存削除
    cursor.execute(
        """
        DROP TABLE IF EXISTS alignment_analysis
        """
    )


    # 作成

    cursor.execute(
        """
        CREATE TABLE alignment_analysis
        (

            日付 TEXT,

            島 TEXT,

            開始台番号 INTEGER,

            終了台番号 INTEGER,

            台数 INTEGER,

            ◎台数 INTEGER,

            ○台数 INTEGER,

            平均G数 REAL,

            平均合成確率 REAL,

            並びスコア REAL,

            判定 TEXT,


            PRIMARY KEY
            (
                日付,
                島,
                開始台番号
            )

        )
        """
    )


    conn.commit()

    conn.close()


    print(
        "alignment_analysisテーブル作成完了"
    )



if __name__ == "__main__":

    create_alignment_table()