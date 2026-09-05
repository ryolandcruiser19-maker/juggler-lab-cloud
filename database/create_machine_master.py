# create_machine_master.py
#
# machine_config.json から台マスタCSVを作成する
#
# 入力:
#   database/machine_config.json
#
# 出力:
#   database/machine_master.csv
#
# 1台1行形式


import json
import csv
from pathlib import Path


# ==============================
# パス設定
# ==============================

BASE_DIR = Path(__file__).resolve().parent

CONFIG_FILE = BASE_DIR.parent / "config" / "island_master_current.json"

OUTPUT_FILE = BASE_DIR / "machine_master.csv"


# ==============================
# JSON読み込み
# ==============================

def load_config():

    if not CONFIG_FILE.exists():
        raise FileNotFoundError(
            f"設定ファイルがありません: {CONFIG_FILE}"
        )

    with open(
        CONFIG_FILE,
        "r",
        encoding="utf-8"
    ) as f:
        return json.load(f)



# ==============================
# マスタ作成
# ==============================

def create_machine_master(config):

    machines = []


    stores = config.get("stores")

    if not stores:
        raise ValueError(
            "stores が存在しません"
        )


    # 店舗
    for store_name, store_data in stores.items():

        islands = store_data.get("islands")

        if not islands:
            continue


        # 島
        for island_name, island_data in islands.items():

            machine_name = island_data.get(
                "machine"
            )

            numbers = island_data.get(
                "numbers",
                []
            )


            if not machine_name:
                print(
                    f"機種名なし: {store_name} {island_name}"
                )
                continue


            # 台番号展開
            for number in numbers:

                machines.append(
                    {
                        "store": store_name,
                        "island": island_name,
                        "machine": machine_name,
                        "machine_no": number
                    }
                )


    return machines



# ==============================
# CSV保存
# ==============================

def save_csv(machines):

    fieldnames = [
        "store",
        "island",
        "machine",
        "machine_no"
    ]


    with open(
        OUTPUT_FILE,
        "w",
        encoding="utf-8-sig",
        newline=""
    ) as f:

        writer = csv.DictWriter(
            f,
            fieldnames=fieldnames
        )

        writer.writeheader()

        writer.writerows(
            machines
        )



# ==============================
# main
# ==============================

def main():

    print(
        "machine master 作成開始"
    )


    config = load_config()


    machines = create_machine_master(
        config
    )


    save_csv(
        machines
    )


    print(
        f"作成完了: {OUTPUT_FILE}"
    )

    print(
        f"登録台数: {len(machines)}台"
    )



if __name__ == "__main__":

    main()