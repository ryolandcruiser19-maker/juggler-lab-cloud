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
# 曜日変換
# ==============================

WEEKDAY_MAP = {

    0: "月",
    1: "火",
    2: "水",
    3: "木",
    4: "金",
    5: "土",
    6: "日"

}



# ==============================
# メイン処理
# ==============================

def create_weekday_analysis():


    conn = sqlite3.connect(
        DB_PATH
    )


    df = pd.read_sql(

        """
        SELECT

            日付,
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
    # 日付 → 曜日
    # ==============================

    df["曜日番号"] = (
        pd.to_datetime(
            df["日付"]
        )
        .dt.weekday
    )


    df["曜日"] = (
        df["曜日番号"]
        .map(WEEKDAY_MAP)
    )



    results = []



    # ==============================
    # 曜日別集計
    # ==============================

    for weekday, group in df.groupby("曜日"):


        total = len(group)



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
            total
            *
            100

        )



        results.append(

            {

                "曜日": weekday,

                "総台数": total,

                "高評価台数": int(high_count),

                "高評価率": round(
                    high_rate,
                    2
                ),

                "平均BB": round(
                    group["BB"]
                    .mean(),
                    2
                ),

                "平均RB": round(
                    group["RB"]
                    .mean(),
                    2
                ),

                "平均G数": round(
                    group["G数"]
                    .mean(),
                    1
                ),

                "平均合成確率": round(
                    group["合成確率"]
                    .dropna()
                    .mean(),
                    1
                )
                if group["合成確率"]
                .notna()
                .any()
                else None

            }

        )



    result_df = pd.DataFrame(
        results
    )



    # ==============================
    # 傾向判定
    # ==============================

    average_rate = (
        result_df["高評価率"]
        .mean()
    )


    result_df["前日平均との差"] = (

        result_df["高評価率"]

        -

        average_rate

    ).round(2)



    max_diff = (

        result_df["高評価率"]
        .max()

        -

        result_df["高評価率"]
        .min()

    )



    # ==============================
    # 曜日別補正判定
    # ==============================

    # 平均より3%以上強い曜日だけ採用

    WEEKDAY_BIAS_THRESHOLD = 3.0



    result_df["傾向有効"] = (

        result_df["前日平均との差"]
        >=
        WEEKDAY_BIAS_THRESHOLD

    ).astype(int)



    result_df["傾向強度"] = (

        result_df["前日平均との差"]
        /
        10

    ).clip(
        0,
        1

    ).round(2)



    result_df["最終更新日"] = (
        datetime.now()
        .strftime(
            "%Y-%m-%d"
        )
    )



    # ==============================
    # DB登録
    # ==============================


    cursor = conn.cursor()



    cursor.execute(
        """
        DELETE FROM weekday_analysis
        """
    )



    cursor.executemany(

        """

        INSERT INTO weekday_analysis

        (

            曜日,

            総台数,

            高評価台数,

            高評価率,

            平均BB,

            平均RB,

            平均G数,

            平均合成確率,

            前日平均との差,

            傾向有効,

            傾向強度,

            最終更新日

        )

        VALUES

        (?,?,?,?,?,?,?,?,?,?,?,?)

        """,

        [

            (

                row["曜日"],

                int(row["総台数"]),

                int(row["高評価台数"]),

                row["高評価率"],

                row["平均BB"],

                row["平均RB"],

                row["平均G数"],

                row["平均合成確率"],

                row["前日平均との差"],

                row["傾向有効"],

                row["傾向強度"],

                row["最終更新日"]

            )

            for _, row in result_df.iterrows()

        ]

    )



    conn.commit()

    conn.close()



    print(
        "weekday_analysis 完了"
    )




# ==============================
# 実行
# ==============================

if __name__ == "__main__":

    create_weekday_analysis()