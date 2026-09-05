import sqlite3
from pathlib import Path
from datetime import datetime
import pandas as pd


BASE_DIR = Path(__file__).resolve().parent.parent

DB_PATH = (
    BASE_DIR
    / "database"
    / "juggler.db"
)


ANALYSIS_DAYS = 180



def judge_holdover(count, rate):

    if count < 5:
        return "データ不足"

    if rate >= 50:
        return "据え置き強い"

    if rate >= 30:
        return "据え置き傾向あり"

    if rate >= 20:
        return "普通"

    return "据え置き弱い"



def confidence(count):

    if count >= 50:
        return "高"

    if count >= 20:
        return "中"

    if count >= 5:
        return "低"

    return "不足"



def create_holdover_analysis():


    conn = sqlite3.connect(DB_PATH)


    df = pd.read_sql(
        """
        SELECT

            日付,
            台番号,
            機種,
            島,
            評価

        FROM daily_data

        ORDER BY 日付

        """,
        conn
    )


    if df.empty:

        print(
            "daily_dataなし"
        )

        return



    df["日付"] = pd.to_datetime(
        df["日付"]
    )


    latest = df["日付"].max()


    start = latest - pd.Timedelta(
        days=ANALYSIS_DAYS
    )


    df = df[
        df["日付"] >= start
    ]



    print(
        "分析期間:",
        df["日付"].min(),
        "〜",
        latest
    )



    result = []



    for machine_no, group in df.groupby("台番号"):


        group = group.sort_values(
            "日付"
        )


        hold_count = 0
        success_count = 0

        strong_before = 0
        strong_after = 0



        records = group.to_dict(
            "records"
        )



        for i in range(
            len(records)-1
        ):


            today = records[i]

            tomorrow = records[i+1]


            # 翌日データのみ対象

            if (
                tomorrow["日付"]
                -
                today["日付"]
            ).days != 1:

                continue



            if today["評価"] in (
                "◎",
                "○"
            ):

                hold_count += 1


                strong_before += 1


                if tomorrow["評価"] in (
                    "◎",
                    "○"
                ):

                    success_count += 1


                    strong_after += 1



        if hold_count == 0:

            continue



        rate = (
            success_count
            /
            hold_count
            *
            100
        )



        latest_row = group.iloc[-1]



        result.append(
            (

                int(machine_no),

                latest_row["機種"],

                latest_row["島"],

                ANALYSIS_DAYS,

                hold_count,

                success_count,

                round(rate,1),

                strong_before,

                strong_after,

                datetime.now()
                .strftime("%Y-%m-%d"),

                hold_count,

                confidence(
                    hold_count
                ),

                judge_holdover(
                    hold_count,
                    rate
                )

            )
        )



    cursor = conn.cursor()



    cursor.execute(
        """
        DELETE FROM machine_holdover_analysis
        """
    )



    cursor.executemany(
        """
        INSERT INTO machine_holdover_analysis
        (

            台番号,
            機種,
            島,
            分析期間,
            前日高評価回数,
            翌日高評価回数,
            据え置き率,
            前日◎回数,
            翌日◎回数,
            更新日,
            有効データ数,
            信頼度,
            据え置き判定

        )

        VALUES
        (
            ?,?,?,?,?,?,?,?,?,?,?,?,?
        )

        """,
        result
    )



    conn.commit()

    conn.close()



    print(
        "machine_holdover_analysis更新完了"
    )

    print(
        len(result),
        "台登録"
    )




if __name__ == "__main__":

    create_holdover_analysis()