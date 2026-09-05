"""
ジャグラーラボ
raw_data登録処理

取得したP's CUBEデータを
リアルタイム履歴として保存する

CSV
 ↓
raw_data(SQLite)

"""


import sqlite3
import pandas as pd

from pathlib import Path
from datetime import datetime


from business_date import (
    get_business_date
)



# ==================================
# パス設定
# ==================================

BASE_DIR = Path(__file__).resolve().parent.parent


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


STORE_NAME = "ひまわりタワー"



# ==================================
# 最新CSV取得
# ==================================

def get_latest_csv():


    files = sorted(
        DATA_DIR.glob(
            "ps_cube_*.csv"
        )
    )


    if not files:

        return None


    return files[-1]



# ==================================
# 営業日取得
# business_date.py利用
# ==================================

def get_csv_business_date(csv_file):


    return (
        get_business_date()
        .strftime(
            "%Y-%m-%d"
        )
    )



# ==================================
# raw_data登録
# ==================================

def import_raw_data():


    csv_file = get_latest_csv()


    if csv_file is None:

        print(
            "CSVがありません"
        )

        return



    print(
        "読込:",
        csv_file.name
    )



    df = pd.read_csv(

        csv_file,

        encoding="utf-8-sig"

    )



    conn = sqlite3.connect(
        DB_PATH
    )


    cursor = conn.cursor()



    insert_count = 0

    skip_count = 0

    error_count = 0



    get_time = datetime.now().strftime(
        "%Y-%m-%d %H:%M:%S"
    )



    business_date = get_csv_business_date(
        csv_file
    )



    for _, row in df.iterrows():


        try:


            cursor.execute(
                """
                INSERT OR IGNORE INTO raw_data
                (
                    取得日時,
                    日付,
                    店舗,
                    機種,
                    台番号,
                    BB,
                    RB,
                    G数,
                    合成確率,
                    最終ゲーム,
                    BIG過去最高,
                    作成日時,
                    営業日,
                    取得種別
                )

                VALUES
                (
                    ?,?,?,?,?,?,?,?,?,?,?,?,?,?
                )

                """,

                (

                    get_time,

                    business_date,

                    STORE_NAME,

                    row["機種"],

                    int(row["台番号"]),

                    int(row["BIG"]),

                    int(row["REG"]),

                    int(row["累計ゲーム"]),


                    float(
                        str(row["合成確率"])
                        .replace(
                            "1/",
                            ""
                        )
                    ),


                    int(row["最終ゲーム"]),


                    int(row["BIG過去最高"]),


                    get_time,


                    business_date,


                    "DAILY"

                )

            )


            if cursor.rowcount:

                insert_count += 1

            else:

                skip_count += 1



        except Exception as e:


            error_count += 1


            print(
                "登録エラー:",
                e
            )



    conn.commit()

    conn.close()



    print("------------------------------")

    print(
        "raw_data登録完了"
    )

    print(
        "営業日:",
        business_date
    )

    print(
        "登録件数:",
        insert_count
    )

    print(
        "重複:",
        skip_count
    )

    print(
        "エラー:",
        error_count
    )

    print("------------------------------")



# ==================================
# 実行
# ==================================

if __name__ == "__main__":

    import_raw_data()