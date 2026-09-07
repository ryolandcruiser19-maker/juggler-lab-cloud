import sqlite3
from pathlib import Path
import pandas as pd


# ==============================
# DB設定
# ==============================

BASE_DIR = Path(__file__).resolve().parent.parent

DB_PATH = Path("/app/data/juggler.db") if __import__("os").getenv("CLOUD_MODE") == "1" else BASE_DIR / "database" / "juggler.db"



# ==============================
# 並び分析作成
# ==============================

def create_alignment_analysis():


    conn = sqlite3.connect(DB_PATH)



    # ==========================
    # 最新営業日取得
    # ==========================

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



    # ==========================
    # 当日データ取得
    # ==========================

    df = pd.read_sql(
        """
        SELECT

            台番号,
            島,
            機種,
            G数,
            合成確率,
            評価

        FROM daily_data

        WHERE 日付 = ?

        ORDER BY
            島,
            台番号

        """,
        conn,
        params=[
            latest_date
        ]
    )



    if df.empty:


        print(
            "対象データなし"
        )


        conn.close()

        return



    results = []



    # ==========================
    # 島単位分析
    # ==========================


    for island, group in df.groupby("島"):



        group = (
            group
            .sort_values("台番号")
            .reset_index(drop=True)
        )



        # 3台単位スライド

        for i in range(
            len(group) - 2
        ):



            window = group.iloc[
                i:i+3
            ]



            high_count = (
                window["評価"]
                .isin(
                    [
                        "◎",
                        "○"
                    ]
                )
                .sum()
            )



            # 高評価2台以上

            if high_count < 2:

                continue



            save_alignment(

                results,

                latest_date,

                island,

                window

            )



    # ==========================
    # 重複削除
    # ==========================


    unique = {}



    for r in results:


        key = (

            r[1],   # 島

            r[2],   # 開始台

            r[3]    # 終了台

        )


        unique[key] = r



    results = list(
        unique.values()
    )



    # ==========================
    # DB保存
    # ==========================


    cursor = conn.cursor()



    cursor.execute(
        """
        DELETE FROM alignment_analysis

        WHERE 日付 = ?

        """,
        (
            latest_date,
        )
    )



    for row in results:


        cursor.execute(
            """
            INSERT INTO alignment_analysis
            (

            日付,
            島,
            開始台番号,
            終了台番号,
            台数,
            ◎台数,
            ○台数,
            平均G数,
            平均合成確率,
            並びスコア,
            判定

            )

            VALUES
            (?,?,?,?,?,?,?,?,?,?,?)

            """,
            row
        )



    conn.commit()

    conn.close()



    print(
        "並び分析登録完了"
    )


    print(
        len(results),
        "件登録"
    )

# ==============================
# 並びデータ作成
# ==============================


def save_alignment(
    results,
    date,
    island,
    rows
):


    df = pd.DataFrame(rows)



    # ◎数

    star_count = (
        df["評価"]
        .eq("◎")
        .sum()
    )



    # ○数

    circle_count = (
        df["評価"]
        .eq("○")
        .sum()
    )



    # ==========================
    # 並びスコア
    # ==========================

    score = int(

        star_count * 10

        +

        circle_count * 5

    )



    # ==========================
    # 判定
    # ==========================

    if star_count >= 3:

        judge = "強い並び"


    elif score >= 20:

        judge = "並び候補"


    else:

        judge = "弱い並び"




    # ==========================
    # 登録
    # ==========================

    results.append(

        (

            date,


            island,


            int(
                df.iloc[0]["台番号"]
            ),


            int(
                df.iloc[-1]["台番号"]
            ),


            len(df),



            int(
                star_count
            ),



            int(
                circle_count
            ),



            round(

                df["G数"]
                .mean(),

                1

            ),



            round(

                df["合成確率"]
                .dropna()
                .mean(),

                1

            )
            if df["合成確率"]
            .notna()
            .any()

            else None,



            int(score),


            judge

        )

    )




# ==============================
# 実行
# ==============================


if __name__ == "__main__":


    create_alignment_analysis()
