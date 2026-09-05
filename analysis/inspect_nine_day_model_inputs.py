import os
import pandas as pd


BASE_DIR = r"C:\Users\sphs4\OneDrive\デスクトップ\ジャグラーラボ\analysis\backtest_output"


FILES = [
    "nine_day_rotation_weighted_detail.csv",
    "nine_day_rotation_weighted_summary.csv",
    "nine_day_rotation_weighted_daily.csv",
    "nine_day_transition_daily.csv",
    "nine_day_transition_features.csv",
    "nine_day_transition_pairs.csv",
]


def print_file_info(path):
    print("\n" + "=" * 80)
    print(os.path.basename(path))
    print("=" * 80)

    if not os.path.exists(path):
        print("ファイルなし")
        return None

    try:
        df = pd.read_csv(path, encoding="utf-8-sig")
    except UnicodeDecodeError:
        df = pd.read_csv(path, encoding="cp932")

    print(f"行数: {len(df):,}")
    print(f"列数: {len(df.columns):,}")

    print("\nカラム:")
    for col in df.columns:
        print(f"  - {col}")

    print("\n先頭5行:")
    print(df.head().to_string(index=False))

    return df


def main():

    print("=" * 80)
    print("9の日 Prediction Engine 統合前 入力構造確認")
    print("=" * 80)

    print(f"BASE_DIR: {BASE_DIR}")

    loaded = {}

    for filename in FILES:
        path = os.path.join(BASE_DIR, filename)
        loaded[filename] = print_file_info(path)

    # ------------------------------------------------------------
    # weighted_daily の確認
    # ------------------------------------------------------------

    weighted_daily = loaded.get("nine_day_rotation_weighted_daily.csv")

    if weighted_daily is not None and len(weighted_daily) > 0:

        print("\n" + "=" * 80)
        print("既存 weighted_daily のモデル列候補")
        print("=" * 80)

        cols = list(weighted_daily.columns)

        keywords = [
            "base",
            "recent",
            "rotation",
            "combined",
            "top",
            "score",
            "island",
            "strong",
            "candidate",
        ]

        for col in cols:
            col_lower = str(col).lower()

            if any(keyword in col_lower for keyword in keywords):
                print(f"  * {col}")

        # 日付列の候補
        date_candidates = [
            col for col in cols
            if any(x in str(col).lower() for x in ["date", "日付"])
        ]

        print("\n日付列候補:")
        for col in date_candidates:
            print(f"  - {col}")

        # モデル列の候補
        print("\n全カラム:")
        for col in cols:
            print(f"  - {col}")

    # ------------------------------------------------------------
    # transition_features の確認
    # ------------------------------------------------------------

    transition_features = loaded.get(
        "nine_day_transition_features.csv"
    )

    if transition_features is not None and len(transition_features) > 0:

        print("\n" + "=" * 80)
        print("遷移特徴量の基本構造")
        print("=" * 80)

        print("transition_type:")
        if "transition_type" in transition_features.columns:
            print(
                transition_features["transition_type"]
                .value_counts(dropna=False)
                .to_string()
            )

        print("\nfrom_island:")
        if "from_island" in transition_features.columns:
            print(
                transition_features["from_island"]
                .value_counts()
                .head(20)
                .to_string()
            )

        print("\nto_island:")
        if "to_island" in transition_features.columns:
            print(
                transition_features["to_island"]
                .value_counts()
                .head(20)
                .to_string()
            )

    # ------------------------------------------------------------
    # transition_daily の確認
    # ------------------------------------------------------------

    transition_daily = loaded.get(
        "nine_day_transition_daily.csv"
    )

    if transition_daily is not None and len(transition_daily) > 0:

        print("\n" + "=" * 80)
        print("遷移日次特徴量")
        print("=" * 80)

        print(
            transition_daily.head(20).to_string(index=False)
        )

    # ------------------------------------------------------------
    # 重要確認
    # ------------------------------------------------------------

    print("\n" + "=" * 80)
    print("次工程で必要な確認事項")
    print("=" * 80)

    print("""
1. 既存BASEがどのCSV・どのカラムから再現できるか
2. 既存BASEのTOP1/TOP3順位を再現できるか
3. 遷移特徴量をwalk-forwardで過去データだけから計算できるか
4. 9→19 / 19→29 / 29→9を別モデルとして扱えるか
5. 5回しかない遷移を過信しない平滑化方式を実装できるか
6. ガール島など特定島への予測集中を別指標として計測できるか
7. 最終的にPrediction Engineへ組み込む補正値を決められるか
""")

    print("\n確認完了。")
    print("この結果を貼り付けてください。")


if __name__ == "__main__":
    main()