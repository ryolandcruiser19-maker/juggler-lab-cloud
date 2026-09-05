import sqlite3
from pathlib import Path
import pandas as pd


BASE_DIR = Path(__file__).resolve().parent.parent

DB_PATH = (
    BASE_DIR
    / "database"
    / "juggler.db"
)


def check_machine_pattern():

    conn = sqlite3.connect(DB_PATH)


    print("=" * 60)
    print("machine_pattern_analysis確認")
    print("=" * 60)


    df = pd.read_sql(
        """
        SELECT
            *
        FROM machine_pattern_analysis
        ORDER BY
            傾向スコア DESC
        """,
        conn
    )


    print(df.head(30))


    print()

    print(
        "登録台数:",
        len(df)
    )


    print()

    print(
        "【指定台確認】"
    )


    target = df[
        df["台番号"]
        .isin(
            [
                969,
                981,
                1024
            ]
        )
    ]


    print(target)


    conn.close()



if __name__ == "__main__":

    check_machine_pattern()