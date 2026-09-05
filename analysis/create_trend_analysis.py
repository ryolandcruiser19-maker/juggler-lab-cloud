import sqlite3
from pathlib import Path
import pandas as pd


BASE_DIR = Path(__file__).resolve().parent.parent

DB_PATH = (
    BASE_DIR
    / "database"
    / "juggler.db"
)


ANALYSIS_DAYS = 30



def create_trend_analysis():


    conn = sqlite3.connect(DB_PATH)



    # 最新日取得

    latest_date = pd.read_sql(
        """
        SELECT
            MAX(日付) AS 日付
        FROM daily_data
        """,
        conn
    ).iloc[0]["日付"]


    print(
        "分析日:",
        latest_date
    )



    # 過去30日取得

    df = pd.read_sql(
        """
        SELECT
            *
        FROM daily_data

        WHERE 日付 <= ?

        ORDER BY 日付 DESC

        """,
        conn,
        params=[
            latest_date
        ]
    )



    if df.empty:

        print(
            "分析対象なし"
        )

        conn.close()

        return



    # 日付数制限

    dates = (
        df["日付"]
        .drop_duplicates()
        .sort_values(
            ascending=False
        )
        .head(
            ANALYSIS_DAYS
        )
    )


    df = df[
        df["日付"]
        .isin(dates)
    ]



    result = []



    # 島別分析

    for target, group in df.groupby("島"):


        total_days = (
            group["日付"]
            .nunique()
        )


        high_count = (
            group["評価"]
            .eq("◎")
            .sum()
        )


        middle_count = (
            group["評価"]
            .eq("○")
            .sum()
        )


        avg_game = (
            group["G数"]
            .mean()
        )


        # 日別スコア

        score = (
            high_count * 10
            +
            middle_count * 5
        )


        # 期間補正

        trend_score = (
            score
            /
            max(total_days,1)
        )



        result.append(
            (
                latest_date,
                target,
                ANALYSIS_DAYS,
                total_days,
                int(high_count),
                int(middle_count),
                round(avg_game,1),
                round(score,1),
                round(trend_score,1)
            )
        )



    cursor = conn.cursor()



    for row in result:


        cursor.execute(
            """
            INSERT OR REPLACE INTO trend_analysis
            (
                分析日,
                対象,
                期間,
                総日数,
                ◎回数,
                ○回数,
                平均G数,
                平均スコア,
                傾向スコア
            )

            VALUES
            (?,?,?,?,?,?,?,?,?)

            """,
            row
        )



    conn.commit()

    conn.close()



    print(
        "trend_analysis登録完了"
    )


    print(
        f"{len(result)}対象登録"
    )



if __name__ == "__main__":

    create_trend_analysis()