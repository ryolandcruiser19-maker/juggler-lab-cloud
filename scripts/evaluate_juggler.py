import json
import pandas as pd
from pathlib import Path

# プロジェクトのルートフォルダ
project_root = Path(__file__).resolve().parent.parent

# JSONファイルの場所
threshold_file = project_root / "data" / "juggler_threshold.json"

# 評価対象CSV
csv_file = project_root / "data" / "juggler_lab_20260712.csv"


# JSONを読み込む
with open(threshold_file, "r", encoding="utf-8") as f:
    thresholds = json.load(f)


def evaluate_probability(probability, threshold):
    """
    合成確率による評価判定
    """

    if probability <= threshold["excellent"]:
        return "◎"

    elif probability <= threshold["good"]:
        return "○"

    elif probability <= threshold["normal"]:
        return "△"

    else:
        return "－"


def convert_probability(probability):
    """
    合成確率を数値化
    """

    # すでに数値ならそのまま返す
    if isinstance(probability, (int, float)):
        return float(probability)

    # 文字なら "1/" を取り除いて数値化
    return float(str(probability).replace("1/", ""))


def evaluate_confidence(bb, rb, games):
    """
    信頼度補正判定

    判定基準：
    BB + RB >= 50
    または
    G数 >= 5000

    条件を満たす：
        空欄

    条件未達：
        ⚠️
    """

    total_bonus = bb + rb

    if total_bonus >= 50 or games >= 5000:
        return ""

    return "⚠️"


def main():

    # CSVを読み込む
    df = pd.read_csv(csv_file)


    # 評価・信頼度補正列を文字列型として固定
    df["評価"] = df["評価"].astype("object")

    if "信頼度補正" not in df.columns:
        df["信頼度補正"] = ""

    df["信頼度補正"] = df["信頼度補正"].astype("object")


    for i in range(len(df)):

        row = df.iloc[i]


        # 合成確率を数値化
        probability = convert_probability(
            row["合成確率"]
        )


        # 機種別閾値取得
        threshold = thresholds[row["機種"]]


        # 評価判定
        evaluation = evaluate_probability(
            probability,
            threshold
        )

        df.at[i, "評価"] = evaluation


        # 信頼度補正判定
        confidence = evaluate_confidence(
            int(row["BB"]),
            int(row["RB"]),
            int(row["G数"])
        )

        df.at[i, "信頼度補正"] = confidence



    # 確認表示
    print(
        df[
            [
                "台番号",
                "合成確率",
                "評価",
                "信頼度補正"
            ]
        ].head(10)
    )


    # 保存先
    output_file = (
        project_root
        / "data"
        / "juggler_lab_20260712_evaluated.csv"
    )


    # CSV保存
    df.to_csv(
        output_file,
        index=False,
        encoding="utf-8-sig"
    )


    print(f"保存しました：{output_file}")


if __name__ == "__main__":
    main()