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
    "nine_day_simple_probability_compare_detail.csv"
)

OUTPUT_SUMMARY = os.path.join(
    BASE_DIR,
    "nine_day_simple_probability_compare_summary.csv"
)

# 確率の最低サンプル数
MIN_SAMPLE = 1

# 確率の下限・上限
EPS = 0.0001


# ============================================================
# 共通関数
# ============================================================

def safe_float(v, default=0.0):
    try:
        if pd.isna(v):
            return default
        return float(v)
    except Exception:
        return default


def calc_rate(df, condition_col):
    if len(df) == 0:
        return np.nan

    return df[condition_col].mean()


def clamp_probability(v):
    if pd.isna(v):
        return 0.0

    return max(EPS, min(1.0 - EPS, float(v)))


# ============================================================
# データ読み込み
# ============================================================

print("=" * 80)
print("9の日 Simple Probability Model 比較")
print("=" * 80)

print(f"INPUT: {INPUT_FILE}")

if not os.path.exists(INPUT_FILE):
    raise FileNotFoundError(
        f"入力ファイルがありません: {INPUT_FILE}"
    )

df = pd.read_csv(INPUT_FILE)

print(f"行数: {len(df):,}")
print(f"列数: {len(df.columns)}")

required_cols = [
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
    c for c in required_cols
    if c not in df.columns
]

if missing:
    raise ValueError(
        f"必要カラムがありません: {missing}"
    )


# ============================================================
# 型変換
# ============================================================

df["previous_date"] = pd.to_datetime(
    df["previous_date"]
)

df["current_date"] = pd.to_datetime(
    df["current_date"]
)

for c in [
    "from_was_strong",
    "from_was_candidate_plus",
    "to_is_strong",
    "to_is_candidate_plus",
]:
    df[c] = pd.to_numeric(
        df[c],
        errors="coerce"
    ).fillna(0).astype(int)


# ============================================================
# 島一覧・検証日
# ============================================================

islands = sorted(
    df["to_island"].dropna().unique()
)

analysis_dates = sorted(
    df["current_date"].dropna().unique()
)

print()
print("=" * 80)
print("基本情報")
print("=" * 80)

print(f"島数: {len(islands)}")
print(f"検証対象日数: {len(analysis_dates)}")

print()
print("島:")

for island in islands:
    print(f"  - {island}")


# ============================================================
# モデル定義
#
# A = 無条件確率
# B = 前回その島が強い場合の条件付き確率
# C = 前回その島が候補以上の場合の条件付き確率
# D = SIMPLE_CONDITIONAL
#
# D:
#   前回強い       -> B
#   前回候補以上   -> C
#   それ以外       -> A
# ============================================================

def get_probability_A(history, island):
    """
    A:
    その島が次回「強い全台系」になる無条件確率
    """

    x = history[
        history["to_island"] == island
    ]

    if len(x) < MIN_SAMPLE:
        return np.nan

    return x["to_is_strong"].mean()


def get_probability_B(history, island):
    """
    B:
    前回その島が「強い全台系」だった場合、
    次回も「強い全台系」になる確率
    """

    x = history[
        (history["from_island"] == island)
        &
        (history["to_island"] == island)
        &
        (history["from_was_strong"] == 1)
    ]

    if len(x) < MIN_SAMPLE:
        return np.nan

    return x["to_is_strong"].mean()


def get_probability_C(history, island):
    """
    C:
    前回その島が「候補以上」だった場合、
    次回も「候補以上」になる確率
    """

    x = history[
        (history["from_island"] == island)
        &
        (history["to_island"] == island)
        &
        (history["from_was_candidate_plus"] == 1)
    ]

    if len(x) < MIN_SAMPLE:
        return np.nan

    return x["to_is_candidate_plus"].mean()


# ============================================================
# Walk-Forward検証
# ============================================================

detail_rows = []

print()
print("=" * 80)
print("Walk-Forward検証開始")
print("=" * 80)

for current_date in analysis_dates:

    # --------------------------------------------------------
    # 現在日より前だけを使用
    # --------------------------------------------------------

    history = df[
        df["current_date"] < current_date
    ].copy()

    current = df[
        df["current_date"] == current_date
    ].copy()

    if len(current) == 0:
        continue

    # --------------------------------------------------------
    # 前回状態
    # --------------------------------------------------------

    previous_date_values = sorted(
        history["current_date"].unique()
    )

    if len(previous_date_values) == 0:
        continue

    previous_date = previous_date_values[-1]

    previous = history[
        history["current_date"] == previous_date
    ]

    # 島ごとの前回状態
    previous_state = {}

    for island in islands:

        p = previous[
            previous["to_island"] == island
        ]

        if len(p) == 0:
            previous_state[island] = {
                "strong": 0,
                "candidate_plus": 0
            }
        else:
            row = p.iloc[0]

            previous_state[island] = {
                "strong": int(
                    row["to_is_strong"]
                ),
                "candidate_plus": int(
                    row["to_is_candidate_plus"]
                )
            }

    # --------------------------------------------------------
    # 各島の確率を計算
    # --------------------------------------------------------

    for island in islands:

        p_a = get_probability_A(
            history,
            island
        )

        p_b = get_probability_B(
            history,
            island
        )

        p_c = get_probability_C(
            history,
            island
        )

        state = previous_state[island]

        # ----------------------------------------------------
        # D = SIMPLE_CONDITIONAL
        # ----------------------------------------------------

        if state["strong"] == 1 and not pd.isna(p_b):
            p_d = p_b
            conditional_type = "前回強い→B"

        elif (
            state["candidate_plus"] == 1
            and not pd.isna(p_c)
        ):
            p_d = p_c
            conditional_type = "前回候補以上→C"

        else:
            p_d = p_a
            conditional_type = "通常→A"

        # ----------------------------------------------------
        # 実績
        # ----------------------------------------------------

        actual = current[
            current["to_island"] == island
        ]

        if len(actual) == 0:
            actual_strong = 0
            actual_candidate = 0
        else:
            row = actual.iloc[0]

            actual_strong = int(
                row["to_is_strong"]
            )

            actual_candidate = int(
                row["to_is_candidate_plus"]
            )

        detail_rows.append({
            "予測日": current_date.strftime("%Y-%m-%d"),
            "前回日": previous_date.strftime("%Y-%m-%d"),
            "島": island,

            "前回強い": state["strong"],
            "前回候補以上": state["candidate_plus"],

            "A_無条件確率": p_a * 100
            if not pd.isna(p_a) else np.nan,

            "B_前回強い条件付き": p_b * 100
            if not pd.isna(p_b) else np.nan,

            "C_前回候補以上条件付き": p_c * 100
            if not pd.isna(p_c) else np.nan,

            "D_SIMPLE_CONDITIONAL": p_d * 100
            if not pd.isna(p_d) else np.nan,

            "D適用条件": conditional_type,

            "実績強い": actual_strong,
            "実績候補以上": actual_candidate,
        })


detail_df = pd.DataFrame(detail_rows)


# ============================================================
# モデルごとの順位評価
# ============================================================

result_rows = []

model_columns = {
    "A_UNCONDITIONAL": "A_無条件確率",
    "B_PREVIOUS_STRONG": "B_前回強い条件付き",
    "C_PREVIOUS_CANDIDATE": "C_前回候補以上条件付き",
    "D_SIMPLE_CONDITIONAL": "D_SIMPLE_CONDITIONAL",
}


for model_name, score_col in model_columns.items():

    daily_results = []

    for prediction_date, day_df in detail_df.groupby(
        "予測日"
    ):

        day_df = day_df.copy()

        # NaNは除外
        day_df = day_df[
            day_df[score_col].notna()
        ]

        if len(day_df) == 0:
            continue

        # 高い順
        day_df = day_df.sort_values(
            score_col,
            ascending=False
        ).reset_index(drop=True)

        top1 = day_df.iloc[0]
        top3 = day_df.head(3)

        top1_strong = int(
            top1["実績強い"] == 1
        )

        top1_candidate = int(
            top1["実績候補以上"] == 1
        )

        top3_strong = int(
            top3["実績強い"].max() == 1
        )

        top3_candidate = int(
            top3["実績候補以上"].max() == 1
        )

        daily_results.append({
            "モデル": model_name,
            "予測日": prediction_date,
            "TOP1": top1["島"],
            "TOP1予測率": top1[score_col],
            "TOP1強い": top1_strong,
            "TOP1候補以上": top1_candidate,
            "TOP3": " / ".join(
                top3["島"].tolist()
            ),
            "TOP3強い": top3_strong,
            "TOP3候補以上": top3_candidate,
        })

    daily_df = pd.DataFrame(daily_results)

    if len(daily_df) == 0:
        continue

    result_rows.append({
        "モデル": model_name,
        "検証日数": len(daily_df),

        "TOP1強い全台系的中率":
            daily_df["TOP1強い"].mean() * 100,

        "TOP1候補以上率":
            daily_df["TOP1候補以上"].mean() * 100,

        "TOP3強い全台系あり率":
            daily_df["TOP3強い"].mean() * 100,

        "TOP3候補以上あり率":
            daily_df["TOP3候補以上"].mean() * 100,

        "平均TOP1予測確率":
            daily_df["TOP1予測率"].mean(),

        "TOP1ガール島回数":
            (daily_df["TOP1"] == "ガール島").sum(),

        "TOP1ガール島率":
            (
                daily_df["TOP1"] == "ガール島"
            ).mean() * 100,
    })


summary_df = pd.DataFrame(
    result_rows
)


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


# ============================================================
# 表示
# ============================================================

print()
print("=" * 80)
print("検証結果")
print("=" * 80)

if len(summary_df) > 0:

    print(
        summary_df.to_string(
            index=False
        )
    )

print()
print("=" * 80)
print("モデル別TOP1結果")
print("=" * 80)

for model_name in model_columns.keys():

    x = detail_df.copy()

    score_col = model_columns[model_name]

    x = x[
        x[score_col].notna()
    ]

    rows = []

    for prediction_date, day_df in x.groupby(
        "予測日"
    ):

        day_df = day_df.sort_values(
            score_col,
            ascending=False
        )

        if len(day_df) == 0:
            continue

        top1 = day_df.iloc[0]

        rows.append({
            "予測日":
                prediction_date,
            "TOP1":
                top1["島"],
            "予測率":
                top1[score_col],
            "強い":
                top1["実績強い"],
            "候補以上":
                top1["実績候補以上"],
        })

    tmp = pd.DataFrame(rows)

    print()
    print(f"--- {model_name} ---")

    if len(tmp) > 0:
        print(
            tmp.to_string(
                index=False
            )
        )


# ============================================================
# 確率の比較
# ============================================================

print()
print("=" * 80)
print("条件付き確率のサンプル状況")
print("=" * 80)

for island in islands:

    x = detail_df[
        detail_df["島"] == island
    ]

    # B
    b = df[
        (df["from_island"] == island)
        &
        (df["to_island"] == island)
        &
        (df["from_was_strong"] == 1)
    ]

    # C
    c = df[
        (df["from_island"] == island)
        &
        (df["to_island"] == island)
        &
        (df["from_was_candidate_plus"] == 1)
    ]

    print(
        f"{island:12s} "
        f"B n={len(b):2d} "
        f"C n={len(c):2d}"
    )


print()
print("=" * 80)
print("出力ファイル")
print("=" * 80)

print(OUTPUT_DETAIL)
print(OUTPUT_SUMMARY)

print()
print("完了")