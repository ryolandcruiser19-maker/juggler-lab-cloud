import sqlite3
from pathlib import Path
import pandas as pd


BASE_DIR = Path(__file__).resolve().parent.parent

DB_PATH = (
    BASE_DIR
    / "database"
    / "juggler.db"
)


def check_alignment():

    conn = sqlite3.connect(DB_PATH)


    df = pd.read_sql(
        """
        SELECT
            *
        FROM alignment_analysis
        ORDER BY
            並びスコア DESC
        """,
        conn
    )


    conn.close()


    print("=" * 60)

    print(
        "並び分析結果"
    )

    print("=" * 60)


    print(df)



if __name__ == "__main__":

    check_alignment()