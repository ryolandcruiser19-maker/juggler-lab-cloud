import sqlite3
from pathlib import Path
import pandas as pd
from datetime import datetime


BASE_DIR = Path(__file__).resolve().parent.parent

DB_PATH = (
    BASE_DIR
    / "database"
    / "juggler.db"
)



def judge_condition(score):

    if score >= 25:
        return "A"

    elif score >= 15:
        return "B"

    elif score >= 8:
        return "C"

    else:
        return "D"



def recommend_count(score):

    if score >= 30:
        return 8

    elif score >= 20:
        return 5

    elif score >= 10:
        return 3

    else:
        return 0



def create_store_condition_analysis():


    conn = sqlite3.connect(DB_PATH)



    # 最新日

    latest = pd.read_sql(
        """
        SELECT MAX(日付) AS 日付
        FROM daily_data
        """,
        conn
    ).iloc[0]["日付"]



    print(
        "分析日:",
        latest
    )



    # 過去180日

    df = pd.read_sql(
        """
        SELECT

            日付,
            評価,
            G数

        FROM daily_data

        WHERE

        date(日付)
        >=
        date(?,'-180 day')

        """,

        conn,

        params=[
            latest
        ]

    )



    if df.empty:

        print(
            "データなし"
        )

        conn.close()
        return



    total = len(df)



    high = df[
        df["評価"]
        .isin(
            [
                "◎",
                "○"
            ]
        )
    ]



    high_rate = (
        len(high)
        /
        total
        *
        100
    )



    # 直近7日

    recent = df[
        pd.to_datetime(df["日付"])
        >=
        (
            pd.to_datetime(latest)
            -
            pd.Timedelta(days=7)
        )
    ]



    recent_high = recent[
        recent["評価"]
        .isin(
            [
                "◎",
                "○"
            ]
        )
    ]



    recent_rate = (
        len(recent_high)
        /
        len(recent)
        *
        100
    )



    # 平均ゲーム数

    avg_game = (
        df["G数"]
        .mean()
    )



    # 店舗期待度スコア

    score = (

        high_rate
        *
        0.5

        +

        recent_rate
        *
        0.3

        +

        min(avg_game / 10000, 1)
        *
        20

    )



    score = round(
        score,
        2
    )



    condition = judge_condition(score)

    count = recommend_count(score)



    cursor = conn.cursor()



    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS store_condition_analysis
        (

            日付 TEXT PRIMARY KEY,

            過去180日高評価率 REAL,

            直近7日高評価率 REAL,

            平均G数 REAL,

            店舗スコア REAL,

            店舗期待度 TEXT,

            推奨予想台数 INTEGER

        )

        """
    )



    cursor.execute(
        """
        INSERT OR REPLACE INTO store_condition_analysis

        VALUES

        (?,?,?,?,?,?,?)

        """,

        (

            latest,

            round(high_rate,1),

            round(recent_rate,1),

            round(avg_game,1),

            score,

            condition,

            count

        )

    )



    conn.commit()



    print("----------------")

    print(
        "過去180日高評価率:",
        round(high_rate,1),
        "%"
    )

    print(
        "直近7日高評価率:",
        round(recent_rate,1),
        "%"
    )

    print(
        "店舗スコア:",
        score
    )

    print(
        "期待度:",
        condition
    )

    print(
        "推奨予想台数:",
        count
    )



    conn.close()



if __name__ == "__main__":

    create_store_condition_analysis()