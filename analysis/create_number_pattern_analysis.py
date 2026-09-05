import sqlite3
from pathlib import Path
import pandas as pd


BASE_DIR = Path(__file__).resolve().parent.parent

DB_PATH = (
    BASE_DIR
    / "database"
    / "juggler.db"
)



def create_number_pattern_analysis():


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



    df["日付"] = pd.to_datetime(
        df["日付"]
    )


    # 台番号末尾

    df["台末尾"] = (
        df["台番号"]
        %
        10
    )


    # 日付末尾

    df["日付末尾"] = (
        df["日付"]
        .dt
        .day
        %
        10
    )


    # 月

    df["月"] = (
        df["日付"]
        .dt
        .strftime("%Y-%m")
    )



    # 高評価

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



    # =================================
    # 月別末尾分析
    # =================================


    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS monthly_tail_analysis
        (

            月 TEXT,

            台末尾 INTEGER,

            台数 INTEGER,

            高評価数 INTEGER,

            高評価率 REAL,

            平均G数 REAL,

            PRIMARY KEY
            (
                月,
                台末尾
            )

        )

        """
    )


    cursor.execute(
        "DELETE FROM monthly_tail_analysis"
    )



    monthly = (

        df

        .groupby(
            [
                "月",
                "台末尾"
            ]
        )

        .agg(

            台数=("台番号","count"),

            高評価数=("高評価","sum"),

            高評価率=("高評価","mean"),

            平均G数=("G数","mean")

        )

        .reset_index()

    )



    for _, r in monthly.iterrows():

        cursor.execute(

            """
            INSERT INTO monthly_tail_analysis

            VALUES

            (?,?,?,?,?,?)

            """,

            (

                r["月"],

                int(r["台末尾"]),

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



    # =================================
    # 日付末尾 × 台末尾
    # =================================


    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS date_tail_relation_analysis
        (

            日付末尾 INTEGER,

            台末尾 INTEGER,

            台数 INTEGER,

            高評価数 INTEGER,

            高評価率 REAL,

            PRIMARY KEY
            (
                日付末尾,
                台末尾
            )

        )

        """
    )



    cursor.execute(
        "DELETE FROM date_tail_relation_analysis"
    )



    relation = (

        df

        .groupby(
            [
                "日付末尾",
                "台末尾"
            ]
        )

        .agg(

            台数=("台番号","count"),

            高評価数=("高評価","sum"),

            高評価率=("高評価","mean")

        )

        .reset_index()

    )



    for _, r in relation.iterrows():


        cursor.execute(

            """
            INSERT INTO date_tail_relation_analysis

            VALUES

            (?,?,?,?,?)

            """,

            (

                int(r["日付末尾"]),

                int(r["台末尾"]),

                int(r["台数"]),

                int(r["高評価数"]),

                round(
                    r["高評価率"]*100,
                    1
                )

            )

        )



    # =================================
    # 機種別末尾分析
    # =================================


    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS machine_tail_analysis
        (

            機種 TEXT,

            台末尾 INTEGER,

            台数 INTEGER,

            高評価数 INTEGER,

            高評価率 REAL,

            平均G数 REAL,

            PRIMARY KEY
            (
                機種,
                台末尾
            )

        )

        """
    )


    cursor.execute(
        "DELETE FROM machine_tail_analysis"
    )



    machine_tail = (

        df

        .groupby(
            [
                "機種",
                "台末尾"
            ]
        )

        .agg(

            台数=("台番号","count"),

            高評価数=("高評価","sum"),

            高評価率=("高評価","mean"),

            平均G数=("G数","mean")

        )

        .reset_index()

    )



    for _, r in machine_tail.iterrows():

        cursor.execute(

            """
            INSERT INTO machine_tail_analysis

            VALUES

            (?,?,?,?,?,?)

            """,

            (

                r["機種"],

                int(r["台末尾"]),

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
        "月別末尾分析:",
        len(monthly),
        "件"
    )

    print(
        "日付末尾分析:",
        len(relation),
        "件"
    )

    print(
        "機種別末尾分析:",
        len(machine_tail),
        "件"
    )



    conn.close()



if __name__ == "__main__":

    create_number_pattern_analysis()