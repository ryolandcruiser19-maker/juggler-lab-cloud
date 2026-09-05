import sqlite3

from pathlib import Path
from datetime import datetime

import pandas as pd



# ==============================
# DB設定
# ==============================

BASE_DIR = Path(__file__).resolve().parent.parent

DB_PATH = (
    BASE_DIR
    /
    "database"
    /
    "juggler.db"
)



# ==============================
# メイン処理
# ==============================

def create_machine_tail_analysis():


    conn = sqlite3.connect(
        DB_PATH
    )


    df = pd.read_sql(

        """
        SELECT

            台番号,

            BB,

            RB,

            G数,

            合成確率,

            評価

        FROM daily_data

        """,

        conn

    )


    print(
        "対象件数:",
        len(df)
    )



    if df.empty:

        print(
            "対象データなし"
        )

        conn.close()

        return



    # ==============================
    # 台番号末尾取得
    # ==============================

    df["台末尾"] = (

        df["台番号"]
        %
        10

    )



    # ==============================
    # 全体高評価率
    # ==============================

    total_high_count = (

        df["評価"]

        .isin(
            [
                "◎",
                "○",
                "△"
            ]
        )

        .sum()

    )


    total_rate = (

        total_high_count

        /

        len(df)

        *

        100

    )



    results = []



    # ==============================
    # 末尾別集計
    # ==============================

    for tail, group in df.groupby(
        "台末尾"
    ):


        count = len(group)



        high_count = (

            group["評価"]

            .isin(
                [
                    "◎",
                    "○",
                    "△"
                ]
            )

            .sum()

        )



        high_rate = (

            high_count

            /

            count

            *

            100

        )



        diff = (

            high_rate

            -

            total_rate

        )



        # ==============================
        # 傾向判定
        # ==============================

        if (

            count >= 100

            and

            diff >= 5

        ):

            trend = 1

        else:

            trend = 0



        strength = max(
            diff,
            0
        ) / 10



        results.append(

            (

                int(tail),

                int(count),

                int(high_count),

                round(
                    high_rate,
                    2
                ),

                round(
                    group["BB"]
                    .mean(),
                    2
                ),

                round(
                    group["RB"]
                    .mean(),
                    2
                ),

                round(
                    group["G数"]
                    .mean(),
                    1
                ),

                round(
                    group["合成確率"]
                    .dropna()
                    .mean(),
                    1
                )
                if group["合成確率"]
                .notna()
                .any()
                else None,

                round(
                    diff,
                    2
                ),

                trend,

                round(
                    strength,
                    2
                ),

                datetime.now()
                .strftime(
                    "%Y-%m-%d"
                )

            )

        )



    # ==============================
    # DB登録
    # ==============================

    cursor = conn.cursor()



    cursor.execute(
        """
        DELETE FROM machine_tail_analysis
        """
    )



    cursor.executemany(

        """

        INSERT INTO machine_tail_analysis

        (

            台末尾,

            台数,

            高評価数,

            高評価率,

            平均BB,

            平均RB,

            平均G数,

            平均合成確率,

            全体平均との差,

            傾向有効,

            傾向強度,

            最終更新日

        )

        VALUES

        (?,?,?,?,?,?,?,?,?,?,?,?)

        """,

        results

    )



    conn.commit()

    conn.close()



    print(
        "machine_tail_analysis 完了"
    )



# ==============================
# 実行
# ==============================

if __name__ == "__main__":

    create_machine_tail_analysis()