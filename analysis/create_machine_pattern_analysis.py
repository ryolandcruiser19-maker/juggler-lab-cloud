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


def create_machine_pattern_analysis():

    conn = sqlite3.connect(DB_PATH)


    # ==============================
    # 分析日取得
    # ==============================

    analysis_date = pd.read_sql(
        """
        SELECT
            MAX(日付) AS 日付
        FROM daily_data
        """,
        conn
    ).iloc[0]["日付"]


    print(
        "分析日:",
        analysis_date
    )


    # ==============================
    # 過去データ取得
    # ==============================

    df = pd.read_sql(
        """
        SELECT
            日付,
            台番号,
            機種,
            島,
            G数,
            合成確率,
            評価
        FROM daily_data
        ORDER BY 日付
        """,
        conn
    )


    if df.empty:

        print(
            "データなし"
        )

        conn.close()

        return



    # ==============================
    # 台番号別集計
    # ==============================

    result = []


    for machine_no, group in df.groupby("台番号"):


        count = len(group)


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


        high_rate = (

            high_count
            /
            count
            *
            100

        )


        avg_game = (
            group["G数"]
            .mean()
        )


        avg_rate = (
            group["合成確率"]
            .dropna()
            .mean()
        )


        best_eval = "－"

        if high_count > 0:

            best_eval = "◎"

        elif middle_count > 0:

            best_eval = "○"



        score = (

            high_count * 10

            +

            middle_count * 5

        )


        latest = group.iloc[-1]


        result.append(
            (
                analysis_date,
                int(machine_no),
                latest["機種"],
                latest["島"],
                ANALYSIS_DAYS,
                count,
                int(high_count),
                int(middle_count),
                round(high_rate,2),
                round(avg_game,1),
                round(avg_rate,1)
                if pd.notna(avg_rate)
                else None,
                best_eval,
                float(score)
            )
        )



    # ==============================
    # 登録
    # ==============================

    cursor = conn.cursor()


    for row in result:


        cursor.execute(
            """
            INSERT OR REPLACE INTO
            machine_pattern_analysis
            (
                分析日,
                台番号,
                機種,
                島,
                分析期間,
                対象日数,
                ◎回数,
                ○回数,
                ◎率,
                平均G数,
                平均合成確率,
                最高評価,
                傾向スコア
            )

            VALUES
            (?,?,?,?,?,?,?,?,?,?,?,?,?)
            """,
            row
        )


    conn.commit()

    conn.close()


    print(
        "machine_pattern_analysis登録完了"
    )

    print(
        f"{len(result)}台登録"
    )



if __name__ == "__main__":

    create_machine_pattern_analysis()