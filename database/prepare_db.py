import json
import pandas as pd
from pathlib import Path


# ==============================
# パス設定
# ==============================

BASE_DIR = Path(__file__).resolve().parent.parent

CONFIG_PATH = (
    BASE_DIR
    / "config"
    / "island_master_current.json"
)

CSV_DIR = BASE_DIR / "data"

OUTPUT_DIR = (
    BASE_DIR
    / "data"
    / "prepared"
)


# ==============================
# 島マスター読込
# ==============================

def load_island_master():

    with open(
        CONFIG_PATH,
        encoding="utf-8"
    ) as f:

        return json.load(f)



# ==============================
# 台番号から島取得
# ==============================

def get_island(
    store,
    machine_no,
    master
):

    islands = (
        master
        ["stores"]
        [store]
        ["islands"]
    )


    for island_name, data in islands.items():

        if machine_no in data["numbers"]:

            return island_name


    return ""



# ==============================
# 信頼度補正
# ==============================

def calc_confidence(
    bb,
    rb,
    games
):

    total = bb + rb


    if total >= 50 or games >= 5000:

        return "OK"


    return "NG"



# ==============================
# 最新CSV取得
# ==============================

def get_latest_csv():

    files = sorted(
        CSV_DIR.glob(
            "juggler_lab_*.csv"
        )
    )


    if not files:

        return None


    return files[-1]



# ==============================
# DB投入前加工
# ==============================

def prepare_csv(csv_file):


    print(f"読込: {csv_file.name}")


    df = pd.read_csv(
        csv_file,
        encoding="utf-8-sig"
    )


    print("\nCSV項目:")
    print(df.columns.tolist())



    master = load_island_master()



    # ------------------------------
    # 島補正
    # ------------------------------

    df["島"] = df.apply(

        lambda x:

        get_island(
            x["店舗"],
            int(x["台番号"]),
            master
        ),

        axis=1

    )



    # ------------------------------
    # 信頼度補正
    # ------------------------------

    df["信頼度補正"] = df.apply(

        lambda x:

        calc_confidence(
            int(x["BB"]),
            int(x["RB"]),
            int(x["G数"])
        ),

        axis=1

    )



    # ------------------------------
    # 出力
    # ------------------------------

    OUTPUT_DIR.mkdir(
        exist_ok=True
    )


    output_file = (

        OUTPUT_DIR
        /
        f"prepared_{csv_file.name}"

    )


    df.to_csv(

        output_file,

        index=False,

        encoding="utf-8-sig"

    )


    print("------------------------------")

    print(
        "保存:",
        output_file
    )

    print("------------------------------")


    return output_file



# ==============================
# 実行
# ==============================

if __name__ == "__main__":


    csv = get_latest_csv()


    if csv:

        prepare_csv(csv)


    else:

        print(
            "CSVがありません"
        )