import sqlite3
from pathlib import Path
import pandas as pd


BASE_DIR = Path(__file__).resolve().parent.parent

DB_PATH = (
    BASE_DIR
    / "database"
    / "juggler.db"
)


def check_island_trend():

    conn = sqlite3.connect(DB_PATH)


    df = pd.read_sql(
        """
        SELECT
            *
        FROM island_trend_analysis
        ORDER BY
            平均評価スコア DESC
        """,
        conn
    )


    conn.close()


    print("=" * 60)

    print(
        "島別過去傾向分析"
    )

    print("=" * 60)


    print(df)



if __name__ == "__main__":

    check_island_trend()