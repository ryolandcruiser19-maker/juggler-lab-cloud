import sqlite3
from pathlib import Path
import pandas as pd


BASE_DIR = Path(__file__).resolve().parent.parent

DB_PATH = (
    BASE_DIR
    / "database"
    / "juggler.db"
)



def create_pattern_analysis():

    conn = sqlite3.connect(DB_PATH)


    df = pd.read_sql(
        """
        SELECT

            日付,
            台番号,
            機種,
            島,
            評価,
            G数

        FROM daily_data

        """,
        conn
    )


    if df.empty:

        print("データなし")
        conn.close()
        return



    print(
        "分析件数:",
        len(df)
    )


    # 日付型

    df["日付"] = pd.to_datetime(
        df["日付"]
    )


    # 曜日

    weekday_map = {
        0:"月",
        1:"火",
        2:"水",
        3:"木",
        4:"金",
        5:"土",
        6:"日"
    }


    df["曜日"] = (
        df["日付"]
        .dt
        .weekday
        .map(weekday_map)
    )


    # 台番号末尾

    df["末尾"] = (
        df["台番号"]
        %
        10
    )



    # 高評価フラグ

    df["高評価"] = (
        df["評価"]
        .isin(
            [
                "◎",
                "○"
            ]
        )
        .astype(int)
    )



    cursor = conn.cursor()



    # ==========================
    # 曜日分析
    # ==========================

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS weekday_analysis
        (

            曜日 TEXT PRIMARY KEY,

            台数 INTEGER,

            高評価数 INTEGER,

            高評価率 REAL,

            平均G数 REAL

        )

        """
    )



    weekday_result = (

        df

        .groupby("曜日")

        .agg(

            台数=("台番号","count"),

            高評価数=("高評価","sum"),

            高評価率=("高評価","mean"),

            平均G数=("G数","mean")

        )

        .reset_index()

    )



    cursor.execute(
        "DELETE FROM weekday_analysis"
    )


    for _, r in weekday_result.iterrows():


        cursor.execute(

            """
            INSERT INTO weekday_analysis

            VALUES

            (?,?,?,?,?)

            """,

            (

                r["曜日"],

                int(r["台数"]),

                int(r["高評価数"]),

                round(
                    r["高評価率"]*100,
                    1
                ),

                round(
                    r["平均G数"],
                    1
                )

            )

        )



    # ==========================
    # 台番号末尾分析
    # ==========================


    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS number_tail_analysis
        (

            末尾 INTEGER PRIMARY KEY,

            台数 INTEGER,

            高評価数 INTEGER,

            高評価率 REAL,

            平均G数 REAL

        )

        """
    )


    tail_result = (

        df

        .groupby("末尾")

        .agg(

            台数=("台番号","count"),

            高評価数=("高評価","sum"),

            高評価率=("高評価","mean"),

            平均G数=("G数","mean")

        )

        .reset_index()

    )



    cursor.execute(
        "DELETE FROM number_tail_analysis"
    )



    for _, r in tail_result.iterrows():


        cursor.execute(

            """
            INSERT INTO number_tail_analysis

            VALUES

            (?,?,?,?,?)

            """,

            (

                int(r["末尾"]),

                int(r["台数"]),

                int(r["高評価数"]),

                round(
                    r["高評価率"]*100,
                    1
                ),

                round(
                    r["平均G数"],
                    1
                )

            )

        )



    conn.commit()


    print("----------------")

    print(
        "曜日分析完了"
    )

    print(
        weekday_result
    )


    print("----------------")

    print(
        "末尾分析完了"
    )

    print(
        tail_result
    )



    conn.close()



if __name__ == "__main__":

    create_pattern_analysis()