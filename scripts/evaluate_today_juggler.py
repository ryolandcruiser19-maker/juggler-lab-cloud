import json
import pandas as pd
from pathlib import Path


# ==================================
# パス設定
# ==================================

project_root = Path(__file__).resolve().parent.parent


threshold_file = (
    project_root
    /
    "data"
    /
    "juggler_threshold.json"
)


input_file = (
    project_root
    /
    "data"
    /
    "juggler_today_20260719_221255.csv"
)


output_file = (
    project_root
    /
    "data"
    /
    "juggler_today_20260719_evaluated.csv"
)



# ==================================
# 閾値読み込み
# ==================================

with open(
    threshold_file,
    "r",
    encoding="utf-8"
) as f:

    thresholds = json.load(f)



# ==================================
# P's CUBE機種名 → DB基準機種名変換
# ==================================

machine_name_map = {

    "ミラクルジャグラー":
        "ウルトラミラクルジャグラー",

    "ハッピージャグラー":
        "ハッピージャグラーVⅢ",

    "ハッピージャグラーVIII":
        "ハッピージャグラーVⅢ"

}



def normalize_machine_name(name):

    return machine_name_map.get(
        name,
        name
    )



# ==================================
# 評価関数
# ==================================

def evaluate_probability(
        probability,
        threshold):


    if probability <= threshold["excellent"]:
        return "◎"


    elif probability <= threshold["good"]:
        return "○"


    elif probability <= threshold["normal"]:
        return "△"


    else:
        return "－"



# ==================================
# 合成確率変換
# ==================================

def convert_probability(value):


    if pd.isna(value):
        return None


    if isinstance(
        value,
        (int,float)
    ):

        return float(value)



    text = str(value)


    text = (
        text
        .replace(
            "1/",
            ""
        )
        .strip()
    )


    return float(text)



# ==================================
# メイン
# ==================================

def main():


    print("="*60)

    print(
        "ジャグラー評価処理開始"
    )

    print("="*60)



    df = pd.read_csv(
        input_file,
        dtype={
            "台番号":str
        }
    )



    evaluations = []



    for index,row in df.iterrows():


        try:

            probability = convert_probability(
                row["合成確率"]
            )


            machine_name = normalize_machine_name(
                row["機種"]
            )


            threshold = thresholds[
                machine_name
            ]


            evaluation = evaluate_probability(
                probability,
                threshold
            )


        except Exception as e:


            print(
                "評価失敗:",
                row["台番号"],
                row["機種"],
                e
            )


            evaluation = "－"



        evaluations.append(
            evaluation
        )



    df["評価"] = evaluations



    df.to_csv(
        output_file,
        index=False,
        encoding="utf-8-sig"
    )



    print()

    print(
        df[
            [
                "台番号",
                "機種",
                "合成確率",
                "評価"
            ]
        ]
        .head(20)
    )


    print()

    print(
        "保存完了:"
    )

    print(
        output_file
    )


    print("="*60)



if __name__ == "__main__":

    main()