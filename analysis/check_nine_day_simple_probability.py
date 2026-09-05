import os
import pandas as pd
import numpy as np

# ============================================================
# 設定
# ============================================================

BASE_DIR = os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    "backtest_output"
)

INPUT_FILE = os.path.join(
    BASE_DIR,
    "nine_day_transition_pairs.csv"
)

OUTPUT_DETAIL = os.path.join(
    BASE_DIR,
    "nine_day_simple_probability_detail.csv"
)

OUTPUT_SUMMARY = os.path.join(
    BASE_DIR,
    "nine_day_simple_probability_summary.csv"
)

OUTPUT_DAILY = os.path.join(
    BASE_DIR,
    "nine_day_simple_probability_daily.csv"
)

# 最低サンプル数
MIN_SAMPLE = 1

# Laplace smoothing
# 1,1 の場合
# 2/2 → 75%
# 0/2 → 25%
SMOOTH_ALPHA = 1.0
SMOOTH_BETA = 1.0

TOP_N = 3


# ============================================================
# 共通関数
# ============================================================

def safe_float(value, default=0.0):
    try:
        if pd.isna(value):
            return default
        return float(value)
    except Exception:
        return default


def parse_bool(value):
    return int(safe_float(value, 0) > 0)


def smoothed_rate(success_count, sample_count):
    """
    Laplace smoothing

    success_count / sample_count をそのまま使わず、
    alpha=1, beta=1 の簡易平滑化を行う。
    """
    if sample_count <= 0:
        return 0.0

    return (
        success_count + SMOOTH_ALPHA
    ) / (
        sample_count + SMOOTH_ALPHA + SMOOTH_BETA
    ) * 100.0


def raw_rate(success_count, sample_count):
    if sample_count <= 0:
        return np.nan

    return success_count / sample_count * 100.0


# ============================================================
# データ読み込み
# ============================================================

print("=" * 80)
print("9の日 Simple Probability Model")
print("=" * 80)

print(f"INPUT: {INPUT_FILE}")

if not os.path.exists(INPUT_FILE):
    raise FileNotFoundError(
        f"入力ファイルが見つかりません: {INPUT_FILE}"
    )

df = pd.read_csv(INPUT_FILE)

print(f"行数: {len(df):,}")
print(f"列数: {len(df.columns)}")

required_columns = [
    "previous_date",
    "current_date",
    "transition_type",
    "from_island",
    "to_island",
    "from_was_strong",
    "from_was_candidate_plus",
    "to_is_strong",
    "to_is_candidate_plus",
]

missing = [
    c for c in required_columns
    if c not in df.columns
]

if missing:
    raise ValueError(
        f"必要カラムがありません: {missing}"
    )


# ============================================================
# 日付変換
# ============================================================

df["previous_date"] = pd.to_datetime(
    df["previous_date"]
)

df["current_date"] = pd.to_datetime(
    df["current_date"]
)

for col in [
    "from_was_strong",
    "from_was_candidate_plus",
    "to_is_strong",
    "to_is_candidate_plus",
]:
    df[col] = df[col].apply(parse_bool)


# ============================================================
# 基本情報
# ============================================================

islands = sorted(
    df["to_island"].dropna().unique()
)

target_dates = sorted(
    df["current_date"].dropna().unique()
)

print()
print("=" * 80)
print("基本情報")
print("=" * 80)

print(f"島数: {len(islands)}")
print(f"検証対象日数: {len(target_dates)}")

print()
print("島:")
for island in islands:
    print(f"  - {island}")


# ============================================================
# 全体の実績確率
# ============================================================

baseline = []

for island in islands:

    island_df = df[
        df["to_island"] == island
    ]

    strong_sample = len(island_df)
    strong_count = int(
        island_df["to_is_strong"].sum()
    )

    candidate_count = int(
        island_df["to_is_candidate_plus"].sum()
    )

    baseline.append({
        "島": island,
        "全体サンプル数": strong_sample,
        "全体強い回数": strong_count,
        "全体候補以上回数": candidate_count,
        "全体強い率": raw_rate(
            strong_count,
            strong_sample
        ),
        "全体候補以上率": raw_rate(
            candidate_count,
            strong_sample
        ),
    })

baseline_df = pd.DataFrame(baseline)


# ============================================================
# Walk-forward予測
# ============================================================

detail_rows = []
daily_rows = []

for target_date in target_dates:

    # --------------------------------------------------------
    # target_date より前のデータだけ使用
    # --------------------------------------------------------

    history = df[
        df["current_date"] < target_date
    ].copy()

    # 今回の予測対象日に対応する前回状態
    current_pairs = df[
        df["current_date"] == target_date
    ].copy()

    if current_pairs.empty:
        continue

    # --------------------------------------------------------
    # 各島について予測
    # --------------------------------------------------------

    predictions = []

    for island in islands:

        # 過去に同じ島が「to_island」だった遷移
        island_history = history[
            history["to_island"] == island
        ]

        # ================================================
        # 前回強かったケース
        # ================================================

        prev_strong = island_history[
            island_history["from_was_strong"] == 1
        ]

        strong_sample = len(prev_strong)

        strong_success = int(
            prev_strong["to_is_strong"].sum()
        )

        strong_candidate_success = int(
            prev_strong["to_is_candidate_plus"].sum()
        )

        strong_raw_rate = raw_rate(
            strong_success,
            strong_sample
        )

        strong_candidate_raw_rate = raw_rate(
            strong_candidate_success,
            strong_sample
        )

        strong_smoothed_rate = smoothed_rate(
            strong_success,
            strong_sample
        )

        strong_candidate_smoothed_rate = smoothed_rate(
            strong_candidate_success,
            strong_sample
        )

        # ================================================
        # 前回強くなかったケース
        # ================================================

        prev_not_strong = island_history[
            island_history["from_was_strong"] == 0
        ]

        not_strong_sample = len(prev_not_strong)

        not_strong_success = int(
            prev_not_strong["to_is_strong"].sum()
        )

        not_strong_candidate_success = int(
            prev_not_strong["to_is_candidate_plus"].sum()
        )

        not_strong_raw_rate = raw_rate(
            not_strong_success,
            not_strong_sample
        )

        not_strong_candidate_raw_rate = raw_rate(
            not_strong_candidate_success,
            not_strong_sample
        )

        not_strong_smoothed_rate = smoothed_rate(
            not_strong_success,
            not_strong_sample
        )

        not_strong_candidate_smoothed_rate = smoothed_rate(
            not_strong_candidate_success,
            not_strong_sample
        )

        # ================================================
        # 今回の前回状態
        # ================================================

        current = current_pairs[
            current_pairs["from_island"] == island
        ]

        if current.empty:
            continue

        current_row = current.iloc[0]

        previous_was_strong = int(
            current_row["from_was_strong"]
        )

        previous_was_candidate = int(
            current_row["from_was_candidate_plus"]
        )

        # ================================================
        # 予測値
        # ================================================

        if previous_was_strong == 1:

            prediction_strong_rate = strong_smoothed_rate
            prediction_candidate_rate = (
                strong_candidate_smoothed_rate
            )

            condition = "前回強い"

            sample_count = strong_sample

        else:

            prediction_strong_rate = not_strong_smoothed_rate
            prediction_candidate_rate = (
                not_strong_candidate_smoothed_rate
            )

            condition = "前回強くない"

            sample_count = not_strong_sample

        # ================================================
        # 実績
        # ================================================

        actual_strong = int(
            current_row["to_is_strong"]
        )

        actual_candidate = int(
            current_row["to_is_candidate_plus"]
        )

        # ================================================
        # 単純スコア
        # ================================================

        # 今回の条件付き強い率を基本スコアにする
        prediction_score = prediction_strong_rate

        predictions.append({
            "予測日": target_date.strftime("%Y-%m-%d"),
            "島": island,
            "前回強い": previous_was_strong,
            "前回候補以上": previous_was_candidate,
            "条件": condition,
            "条件付き強い率": prediction_strong_rate,
            "条件付き候補以上率": prediction_candidate_rate,
            "条件付きサンプル数": sample_count,
            "実績強い": actual_strong,
            "実績候補以上": actual_candidate,
            "予測スコア": prediction_score,
            "全体強い率": baseline_df.loc[
                baseline_df["島"] == island,
                "全体強い率"
            ].iloc[0],
            "全体候補以上率": baseline_df.loc[
                baseline_df["島"] == island,
                "全体候補以上率"
            ].iloc[0],
            "前回強い→強い_raw": strong_raw_rate,
            "前回強い→候補以上_raw": strong_candidate_raw_rate,
            "前回強くない→強い_raw": not_strong_raw_rate,
            "前回強くない→候補以上_raw": not_strong_candidate_raw_rate,
            "前回強いサンプル": strong_sample,
            "前回強い成功": strong_success,
            "前回強くないサンプル": not_strong_sample,
            "前回強くない成功": not_strong_success,
        })

    # --------------------------------------------------------
    # TOP N
    # --------------------------------------------------------

    pred_df = pd.DataFrame(predictions)

    if pred_df.empty:
        continue

    pred_df = pred_df.sort_values(
        [
            "予測スコア",
            "条件付き候補以上率",
            "条件付きサンプル数",
        ],
        ascending=[False, False, False]
    ).reset_index(drop=True)

    pred_df["予測順位"] = (
        np.arange(len(pred_df)) + 1
    )

    # --------------------------------------------------------
    # 詳細保存
    # --------------------------------------------------------

    detail_rows.extend(
        pred_df.to_dict("records")
    )

    # --------------------------------------------------------
    # TOP1 / TOP3評価
    # --------------------------------------------------------

    top1 = pred_df.head(1)
    top3 = pred_df.head(TOP_N)

    top1_strong = int(
        top1["実績強い"].max()
    )

    top1_candidate = int(
        top1["実績候補以上"].max()
    )

    top3_strong = int(
        top3["実績強い"].max()
    )

    top3_candidate = int(
        top3["実績候補以上"].max()
    )

    daily_rows.append({
        "予測日": target_date.strftime("%Y-%m-%d"),
        "TOP1": top1.iloc[0]["島"],
        "TOP1予測率": top1.iloc[0]["予測スコア"],
        "TOP1強い": top1_strong,
        "TOP1候補以上": top1_candidate,
        "TOP3": " / ".join(
            top3["島"].tolist()
        ),
        "TOP3強い": top3_strong,
        "TOP3候補以上": top3_candidate,
    })


# ============================================================
# DataFrame化
# ============================================================

detail_df = pd.DataFrame(detail_rows)
daily_df = pd.DataFrame(daily_rows)


# ============================================================
# サマリー
# ============================================================

summary_rows = []

if not daily_df.empty:

    total_days = len(daily_df)

    top1_strong_rate = (
        daily_df["TOP1強い"].mean() * 100
    )

    top1_candidate_rate = (
        daily_df["TOP1候補以上"].mean() * 100
    )

    top3_strong_rate = (
        daily_df["TOP3強い"].mean() * 100
    )

    top3_candidate_rate = (
        daily_df["TOP3候補以上"].mean() * 100
    )

    avg_top1_prediction_rate = (
        daily_df["TOP1予測率"].mean()
    )

    summary_rows.append({
        "モデル": "SIMPLE_CONDITIONAL",
        "検証日数": total_days,
        "TOP1強い全台系的中率": top1_strong_rate,
        "TOP1候補以上率": top1_candidate_rate,
        "TOP3強い全台系あり率": top3_strong_rate,
        "TOP3候補以上あり率": top3_candidate_rate,
        "平均TOP1予測確率": avg_top1_prediction_rate,
    })


summary_df = pd.DataFrame(summary_rows)


# ============================================================
# 保存
# ============================================================

detail_df.to_csv(
    OUTPUT_DETAIL,
    index=False,
    encoding="utf-8-sig"
)

summary_df.to_csv(
    OUTPUT_SUMMARY,
    index=False,
    encoding="utf-8-sig"
)

daily_df.to_csv(
    OUTPUT_DAILY,
    index=False,
    encoding="utf-8-sig"
)


# ============================================================
# 表示
# ============================================================

print()
print("=" * 80)
print("検証結果")
print("=" * 80)

if not summary_df.empty:

    print(
        summary_df.to_string(
            index=False
        )
    )

print()
print("=" * 80)
print("日別予測")
print("=" * 80)

if not daily_df.empty:
    print(
        daily_df.to_string(
            index=False
        )
    )

print()
print("=" * 80)
print("出力ファイル")
print("=" * 80)

print(OUTPUT_DETAIL)
print(OUTPUT_SUMMARY)
print(OUTPUT_DAILY)

print()
print("完了")