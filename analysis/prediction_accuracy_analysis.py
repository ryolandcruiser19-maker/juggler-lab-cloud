import sqlite3
from pathlib import Path
import pandas as pd


BASE_DIR = Path(__file__).resolve().parent.parent

DB_PATH = (
    BASE_DIR
    / "database"
    / "juggler.db"
)



def create_prediction_accuracy_analysis():


    conn = sqlite3.connect(DB_PATH)



    # ==========================
    # 予想履歴取得
    # ==========================

    prediction = pd.read_sql(
        """
        SELECT

            日付,
            台番号,
            順位,
            総合スコア

        FROM prediction_history

        """,
        conn
    )



    if prediction.empty:

        print(
            "prediction_historyなし"
        )

        conn.close()
        return



    # ==========================
    # 翌日実績取得
    # ==========================

    result = []


    for _,row in prediction.iterrows():


        date = row["日付"]

        machine_no = row["台番号"]



        next_day = pd.read_sql(
            """
            SELECT

                評価

            FROM daily_data

            WHERE

                台番号 = ?

            AND

                date(日付)
                =
                date(?,'+1 day')

            """,

            conn,

            params=[
                machine_no,
                date
            ]

        )



        if next_day.empty:

            actual = None

        else:

            actual = (
                next_day.iloc[0]["評価"]
            )



        hit = 0


        if actual in [
            "◎",
            "○"
        ]:

            hit = 1



        result.append(
            (

                date,

                machine_no,

                row["順位"],

                row["総合スコア"],

                actual,

                hit

            )
        )



    # ==========================
    # 保存
    # ==========================

    cursor = conn.cursor()


    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS prediction_accuracy_analysis
        (

            日付 TEXT,

            台番号 INTEGER,

            予想順位 INTEGER,

            総合スコア REAL,

            実績評価 TEXT,

            的中 INTEGER

        )

        """
    )



    cursor.execute(
        """
        DELETE FROM prediction_accuracy_analysis

        """
    )



    cursor.executemany(

        """
        INSERT INTO prediction_accuracy_analysis

        VALUES

        (?,?,?,?,?,?)

        """,

        result

    )



    conn.commit()



    # ==========================
    # 集計表示
    # ==========================


    df = pd.DataFrame(
        result,

        columns=[
            "日付",
            "台番号",
            "順位",
            "スコア",
            "実績",
            "的中"
        ]

    )


    print("--------------------")

    print(
        "分析対象:",
        len(df),
        "台"
    )


    print(
        "的中:",
        df["的中"].sum()
    )


    print(
        "的中率:",
        round(
            df["的中"].mean()*100,
            1
        ),
        "%"
    )



    print("--------------------")



    conn.close()



if __name__ == "__main__":

    create_prediction_accuracy_analysis()