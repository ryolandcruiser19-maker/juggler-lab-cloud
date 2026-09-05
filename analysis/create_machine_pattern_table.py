import sqlite3
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent.parent

DB_PATH = (
    BASE_DIR
    / "database"
    / "juggler.db"
)


def create_machine_pattern_table():

    conn = sqlite3.connect(DB_PATH)

    cursor = conn.cursor()


    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS machine_pattern_analysis
        (

            分析日 TEXT,

            台番号 INTEGER,

            機種 TEXT,

            島 TEXT,

            分析期間 INTEGER,

            対象日数 INTEGER,

            ◎回数 INTEGER,

            ○回数 INTEGER,

            ◎率 REAL,

            平均G数 REAL,

            平均合成確率 REAL,

            最高評価 TEXT,

            傾向スコア REAL,


            PRIMARY KEY
            (
                分析日,
                台番号,
                分析期間
            )

        )
        """
    )


    conn.commit()

    conn.close()


    print(
        "machine_pattern_analysisテーブル作成完了"
    )


if __name__ == "__main__":

    create_machine_pattern_table()