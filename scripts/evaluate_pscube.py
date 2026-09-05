"""
ジャグラーラボ
P's CUBE一覧データ評価
DB形式変換

営業日は取得CSV名を基準とする
"""

import json
import os

from datetime import datetime, timedelta

import pandas as pd


# ==================================
# 基本設定
# ==================================

STORE_NAME = "ひまわりタワー"


BASE_DIR = os.path.dirname(
    os.path.dirname(
        os.path.abspath(__file__)
    )
)


DATA_DIR = os.path.join(
    BASE_DIR,
    "data"
)


# ==================================
# 最新CSV取得
# ==================================

def get_latest_csv():

    files = sorted(
        [
            f
            for f in os.listdir(DATA_DIR)
            if f.startswith("ps_cube_")
            and f.endswith(".csv")
        ]
    )


    if not files:

        return None


    return os.path.join(
        DATA_DIR,
        files[-1]
    )



# ==================================
# 営業日取得
# CSVファイル名基準
# ==================================

def get_business_date(csv_file):


    csv_time = datetime.fromtimestamp(
        os.path.getmtime(csv_file)
    )


    print(
        "CSV取得日時:",
        csv_time
    )


    if csv_time.hour < 9:


        business_date = (
            csv_time.date()
            -
            timedelta(days=1)
        )


    else:


        business_date = csv_time.date()



    return datetime.combine(
        business_date,
        datetime.min.time()
    )



# ==================================
# ファイル設定
# ==================================

INPUT_FILE = get_latest_csv()


if INPUT_FILE:

    BUSINESS_DATE = get_business_date(
        INPUT_FILE
    )


    DATE_TEXT = BUSINESS_DATE.strftime(
        "%Y%m%d"
    )


    DATE_DB = BUSINESS_DATE.strftime(
        "%Y-%m-%d"
    )


    OUTPUT_FILE = os.path.join(
        DATA_DIR,
        f"juggler_lab_{DATE_TEXT}.csv"
    )


else:

    BUSINESS_DATE = None
    DATE_TEXT = None
    DATE_DB = None
    OUTPUT_FILE = None



THRESHOLD_FILE = os.path.join(
    DATA_DIR,
    "juggler_threshold.json"
)


EVENT_CONFIG_FILE = os.path.join(
    DATA_DIR,
    "event_config.json"
)


ISLAND_CONFIG_FILE = os.path.join(
    DATA_DIR,
    "island_config.json"
)



# ==================================
# JSON読込
# ==================================

with open(
    THRESHOLD_FILE,
    "r",
    encoding="utf-8"
) as f:

    thresholds = json.load(f)



with open(
    EVENT_CONFIG_FILE,
    "r",
    encoding="utf-8"
) as f:

    event_config = json.load(f)



with open(
    ISLAND_CONFIG_FILE,
    "r",
    encoding="utf-8"
) as f:

    island_config = json.load(f)



# ==================================
# 機種名変換
# ==================================

MACHINE_NAME_MAP = {

    "ミラクルジャグラー":
        "ウルトラミラクルジャグラー",

    "ハッピージャグラー":
        "ハッピージャグラーVⅢ",

    "ハッピージャグラーVIII":
        "ハッピージャグラーVⅢ"

}



def normalize_machine_name(name):

    return MACHINE_NAME_MAP.get(
        name,
        name
    )



# ==================================
# 合成確率変換
# ==================================

def convert_probability(value):

    if pd.isna(value):

        return None


    text = str(value)


    text = (
        text
        .replace(
            "1/",
            ""
        )
        .strip()
    )


    try:

        return float(text)

    except:

        return None



# ==================================
# 評価
# ==================================

def evaluate_probability(
    probability,
    threshold
):

    if probability is None:

        return "－"


    if probability <= threshold["excellent"]:

        return "◎"


    elif probability <= threshold["good"]:

        return "○"


    elif probability <= threshold["normal"]:

        return "△"


    else:

        return "－"



# ==================================
# 信頼度補正
# ==================================

def confidence_rank(
    bb,
    rb,
    games
):

    total_bonus = bb + rb


    if total_bonus >= 50 or games >= 5000:

        return ""


    return "⚠️"



# ==================================
# イベント判定
# ==================================

def get_event_type(
    date,
    store
):

    special_events = event_config.get(
        "special_events",
        {}
    )


    date_text = date.strftime(
        "%Y-%m-%d"
    )


    if date_text in special_events:

        if store in special_events[date_text]:

            return special_events[date_text][store]



    config = event_config.get(
        "stores",
        {}
    ).get(
        store,
        {}
    )


    day = date.day
    month = date.month



    if config.get(
        "zoro_event",
        False
    ):

        if month == day:

            return "🎰ゾロ目"



    if day in config.get(
        "floor5_event_days",
        []
    ):

        return "🔥5Fフロア紹介"



    if day in config.get(
        "zero_event_days",
        []
    ):

        return "📈0イベント"



    return "📅通常"



# ==================================
# 島判定
# ==================================

def get_island(
    store,
    machine,
    machine_number
):

    store_data = island_config.get(
        "stores",
        {}
    ).get(
        store,
        {}
    )


    islands = store_data.get(
        "islands",
        {}
    )


    for island_name, data in islands.items():

        if data.get(
            "machine"
        ) != machine:

            continue


        if machine_number in data.get(
            "numbers",
            []
        ):

            return island_name


    return ""



# ==================================
# メイン
# ==================================

def main():


    print("=" * 60)

    print(
        "ジャグラーラボ 評価処理"
    )

    print("=" * 60)



    if INPUT_FILE is None:

        print(
            "評価対象CSVなし"
        )

        return



    print(
        "入力:",
        INPUT_FILE
    )


    print(
        "営業日:",
        DATE_DB
    )



    df = pd.read_csv(

        INPUT_FILE,

        dtype={
            "台番号": str
        }

    )



    event_type = get_event_type(
        BUSINESS_DATE,
        STORE_NAME
    )



    rows = []



    for _, row in df.iterrows():


        machine = normalize_machine_name(
            row["機種"]
        )


        probability = convert_probability(
            row["合成確率"]
        )



        threshold = thresholds.get(
            machine
        )


        if threshold:

            evaluation = evaluate_probability(
                probability,
                threshold
            )

        else:

            evaluation = "－"



        confidence = confidence_rank(

            int(row["BIG"]),

            int(row["REG"]),

            int(row["累計ゲーム"])

        )



        machine_number = int(
            row["台番号"]
        )



        rows.append({

            "日付":
                DATE_DB,

            "店舗":
                STORE_NAME,

            "機種":
                machine,

            "台番号":
                row["台番号"],

            "BB":
                row["BIG"],

            "RB":
                row["REG"],

            "G数":
                row["累計ゲーム"],

            "合成確率":
                probability,

            "評価":
                evaluation,

            "信頼度補正":
                confidence,

            "イベント種別":
                event_type,

            "備考":
                "",

            "島":
                get_island(
                    STORE_NAME,
                    machine,
                    machine_number
                )

        })



    result = pd.DataFrame(
        rows
    )


    result.to_csv(

        OUTPUT_FILE,

        index=False,

        encoding="utf-8-sig"

    )


    print()

    print(
        "評価完了"
    )


    print(
        "件数:",
        len(result)
    )


    print(
        "保存:",
        OUTPUT_FILE
    )


    print("=" * 60)



if __name__ == "__main__":

    main()