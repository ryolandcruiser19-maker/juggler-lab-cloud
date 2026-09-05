"""
ジャグラーラボ
Phase2 日次データ登録処理

評価済みCSV
    ↓
daily_data(SQLite)

用途:
・分析用テーブル更新
・将来のStreamlit表示用データ
"""


import sqlite3

import pandas as pd

from pathlib import Path



# ==================================
# パス設定
# ==================================

BASE_DIR = (
    Path(__file__)
    .resolve()
    .parent
    .parent
)


DB_PATH = (
    BASE_DIR
    /
    "database"
    /
    "juggler.db"
)


DATA_DIR = (
    BASE_DIR
    /
    "data"
)



# ==================================
# 最新評価CSV取得
# ==================================

def get_latest_csv():


    files = sorted(
        DATA_DIR.glob(
            "juggler_lab_*.csv"
        )
    )


    if not files:

        return None


    return files[-1]



# ==================================
# 登録処理
# ==================================

def import_daily_data():


    csv_file = get_latest_csv()


    if csv_file is None:

        print(
            "評価CSVがありません"
        )

        return



    print(
        "読込:",
        csv_file.name
    )



    df = pd.read_csv(

        csv_file,

        encoding="utf-8-sig",

        dtype={
            "台番号": str
        }

    )



    conn = sqlite3.connect(
        DB_PATH
    )


    cursor = conn.cursor()



    insert_count = 0



    print(
        "daily_data登録開始"
    )



    for _, row in df.iterrows():


        # --------------------------
        # 既存削除
        # --------------------------

        cursor.execute(

            """
            DELETE FROM daily_data
            WHERE 日付 = ?
            AND 店舗 = ?
            AND 台番号 = ?
            """,

            (

                row["日付"],

                row["店舗"],

                int(row["台番号"])

            )

        )



        # --------------------------
        # 登録
        # --------------------------

        cursor.execute(

            """
            INSERT INTO daily_data
            (
                日付,
                店舗,
                機種,
                台番号,
                BB,
                RB,
                G数,
                合成確率,
                評価,
                信頼度補正,
                イベント種別,
                備考,
                島
            )

            VALUES
            (
                ?,?,?,?,?,?,?,?,?,?,?,?,?
            )

            """,

            (

                row["日付"],

                row["店舗"],

                row["機種"],

                int(row["台番号"]),

                int(row["BB"]),

                int(row["RB"]),

                int(row["G数"]),

                float(row["合成確率"]),

                row["評価"],

                row["信頼度補正"],

                row["イベント種別"],

                row["備考"],

                row["島"]

            )

        )


        insert_count += 1



    conn.commit()

    conn.close()



    print(
        "daily_data登録完了"
    )

    print(
        f"登録件数: {insert_count}件"
    )



# ==================================
# 実行
# ==================================

if __name__ == "__main__":

    import_daily_data()