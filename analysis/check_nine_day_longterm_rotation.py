# -*- coding: utf-8 -*-

"""
================================================================================
9 DAY LONG-TERM ISLAND ROTATION ANALYSIS
================================================================================

目的
--------------------------------------------------------------------------------
簡易データを含む全期間について、

    9の日の島の強さ
    ↓
    前回9の日
    前々回9の日
    3回前9の日

との関係を検証する。

重要
--------------------------------------------------------------------------------
・△以上率の分母 = その日の島台数
・簡易データ期間でも△以上率を利用
・◎○は存在する期間のみ利用
・strong判定は詳細データ期間のみ
・欠損島を0扱いしない
================================================================================
"""

import sqlite3
import pandas as pd
import numpy as np
from pathlib import Path


# =============================================================================
# SETTINGS
# =============================================================================

DB_PATH = Path(
    r"C:\Users\sphs4\OneDrive\デスクトップ\ジャグラーラボ\database\juggler.db"
)

OUTPUT_DIR = Path(
    r"C:\Users\sphs4\OneDrive\デスクトップ\ジャグラーラボ"
    r"analysis\backtest_output"
)

OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

START_DATE = "2025-12-01"
END_DATE = "2026-08-15"


# =============================================================================
# HELPER
# =============================================================================

def safe_numeric(series):
    return pd.to_numeric(series, errors="coerce")


# =============================================================================
# DB LOAD
# =============================================================================

print("=" * 80)
print("9 DAY LONG-TERM ISLAND ROTATION ANALYSIS")
print("=" * 80)

print()
print("DB読み込み")
print("-" * 80)

conn = sqlite3.connect(DB_PATH)

df = pd.read_sql_query(
    """
    SELECT *
    FROM daily_data
    WHERE 日付 >= ?
      AND 日付 <= ?
    """,
    conn,
    params=[START_DATE, END_DATE]
)

conn.close()

print("rows:", len(df))
print("columns:")
print(df.columns.tolist())


# =============================================================================
# DATE
# =============================================================================

df["日付"] = pd.to_datetime(df["日付"], errors="coerce")

df = df.dropna(subset=["日付", "島"])


# =============================================================================
# NUMERIC
# =============================================================================

for col in ["BB", "RB", "G数", "合成確率"]:
    if col in df.columns:
        df[col] = safe_numeric(df[col])


# =============================================================================
# EVALUATION
# =============================================================================

df["評価"] = df["評価"].fillna("").astype(str)


# =============================================================================
# NINE DAYS
# =============================================================================

nine_dates = sorted(
    df.loc[df["日付"].dt.day.isin([9, 19, 29]), "日付"]
    .drop_duplicates()
    .tolist()
)

print()
print("9の日")
print("-" * 80)

print("nine days:", len(nine_dates))

for i, d in enumerate(nine_dates, 1):

    n_islands = df.loc[
        df["日付"] == d,
        "島"
    ].nunique()

    print(
        f"{i:2d}: {d.strftime('%Y-%m-%d')} "
        f"islands={n_islands}"
    )


# =============================================================================
# DAILY × ISLAND
# =============================================================================

print()
print("日付×島集計")
print("-" * 80)


records = []

for (date, island), g in df.groupby(["日付", "島"]):

    island_size = len(g)

    # ------------------------------------------------------------
    # △以上
    #
    # 評価が △ / ○ / ◎
    # ------------------------------------------------------------

    triangle_plus = g["評価"].isin(
        ["△", "○", "◎"]
    ).sum()

    triangle_plus_rate = (
        triangle_plus / island_size * 100
        if island_size > 0
        else np.nan
    )

    # ------------------------------------------------------------
    # ◎
    # ------------------------------------------------------------

    star_count = (g["評価"] == "◎").sum()

    star_rate = (
        star_count / island_size * 100
        if island_size > 0
        else np.nan
    )

    # ------------------------------------------------------------
    # ◎ + ○
    # ------------------------------------------------------------

    star_circle_count = g["評価"].isin(
        ["◎", "○"]
    ).sum()

    star_circle_rate = (
        star_circle_count / island_size * 100
        if island_size > 0
        else np.nan
    )

    # ------------------------------------------------------------
    # G数
    # ------------------------------------------------------------

    avg_games = g["G数"].mean()

    records.append({
        "日付": date,
        "島": island,
        "island_size": island_size,

        "triangle_plus_count": triangle_plus,
        "triangle_plus_rate": triangle_plus_rate,

        "star_count": star_count,
        "star_rate": star_rate,

        "star_circle_count": star_circle_count,
        "star_circle_rate": star_circle_rate,

        "avg_games": avg_games,
    })


island_daily = pd.DataFrame(records)

print("日付×島 rows:", len(island_daily))


# =============================================================================
# NINE DAY DATA
# =============================================================================

nine_df = island_daily[
    island_daily["日付"].isin(nine_dates)
].copy()

nine_df = nine_df.sort_values(
    ["島", "日付"]
).reset_index(drop=True)


# =============================================================================
# NINE-DAY HISTORY
# =============================================================================

print()
print("9の日履歴作成")
print("-" * 80)


history_records = []

for island, g in nine_df.groupby("島"):

    g = g.sort_values("日付").reset_index(drop=True)

    for i in range(len(g)):

        row = g.iloc[i]

        current_date = row["日付"]

        current_triangle_rate = row[
            "triangle_plus_rate"
        ]

        # --------------------------------------------------------
        # previous nine
        # --------------------------------------------------------

        if i >= 1:

            prev = g.iloc[i - 1]

            prev_date = prev["日付"]

            prev_triangle_rate = prev[
                "triangle_plus_rate"
            ]

            triangle_lift = (
                current_triangle_rate
                - prev_triangle_rate
                if pd.notna(prev_triangle_rate)
                and pd.notna(current_triangle_rate)
                else np.nan
            )

        else:

            prev_date = pd.NaT
            prev_triangle_rate = np.nan
            triangle_lift = np.nan

        # --------------------------------------------------------
        # previous 2
        # --------------------------------------------------------

        if i >= 2:

            prev2 = g.iloc[i - 2]

            prev2_date = prev2["日付"]

            prev2_triangle_rate = prev2[
                "triangle_plus_rate"
            ]

        else:

            prev2_date = pd.NaT
            prev2_triangle_rate = np.nan

        # --------------------------------------------------------
        # previous 3
        # --------------------------------------------------------

        if i >= 3:

            prev3 = g.iloc[i - 3]

            prev3_date = prev3["日付"]

            prev3_triangle_rate = prev3[
                "triangle_plus_rate"
            ]

        else:

            prev3_date = pd.NaT
            prev3_triangle_rate = np.nan

        # --------------------------------------------------------
        # rate categories
        # --------------------------------------------------------

        def rate_class(x):

            if pd.isna(x):
                return "判定不能"

            if x <= 10:
                return "0-10%"

            if x <= 20:
                return "10-20%"

            if x <= 30:
                return "20-30%"

            if x <= 50:
                return "30-50%"

            return "50%以上"

        # --------------------------------------------------------
        # strong
        #
        # 詳細データ期間のみ参考値として作成。
        #
        # 簡易データ期間では評価の情報量が不足しているため、
        # triangle_plus_rateだけでstrong判定しない。
        # --------------------------------------------------------

        current_strong = np.nan

        # 評価列が存在し、◎○が取得されている場合のみ判定
        current_rows = df[
            (df["日付"] == current_date)
            & (df["島"] == island)
        ]

        if len(current_rows) > 0:

            # ◎○の存在確認
            evaluation_values = set(
                current_rows["評価"].dropna().astype(str)
            )

            if "◎" in evaluation_values or "○" in evaluation_values:

                # 既存の全台系判定とは別に、
                # ここでは「△以上率」を出力し、
                # strongは後段で必要に応じて付与する。
                pass

        history_records.append({

            "日付": current_date,
            "島": island,

            "island_size":
                row["island_size"],

            "triangle_plus_rate":
                current_triangle_rate,

            "prev_date":
                prev_date,

            "prev_triangle_plus_rate":
                prev_triangle_rate,

            "prev2_date":
                prev2_date,

            "prev2_triangle_plus_rate":
                prev2_triangle_rate,

            "prev3_date":
                prev3_date,

            "prev3_triangle_plus_rate":
                prev3_triangle_rate,

            "triangle_lift":
                triangle_lift,

            "prev_rate_class":
                rate_class(prev_triangle_rate),

            "prev2_rate_class":
                rate_class(prev2_triangle_rate),

            "prev3_rate_class":
                rate_class(prev3_triangle_rate),
        })


history_df = pd.DataFrame(history_records)


# =============================================================================
# CURRENT NINE DAY DISTRIBUTION
# =============================================================================

print()
print("=" * 80)
print("RESULT")
print("=" * 80)


def show_rate_analysis(title, series):

    print()
    print(title)
    print("-" * 80)

    result = []

    for category, g in series:

        values = g["triangle_plus_rate"].dropna()

        if len(values) == 0:
            continue

        result.append({
            "condition": category,
            "total": len(values),
            "avg_current_triangle_rate":
                values.mean(),
            "median_current_triangle_rate":
                values.median(),
        })

    result_df = pd.DataFrame(result)

    if len(result_df) > 0:
        print(
            result_df.to_string(index=False)
        )

    return result_df


# =============================================================================
# 1. PREVIOUS RATE CLASS
# =============================================================================

print()
print("1. 前回9日の△以上率")
print("-" * 80)

prev_analysis = (
    history_df
    .dropna(subset=["prev_triangle_plus_rate"])
    .groupby("prev_rate_class")
    .agg(
        total=("triangle_plus_rate", "count"),
        current_avg_triangle_rate=(
            "triangle_plus_rate",
            "mean"
        ),
        current_median_triangle_rate=(
            "triangle_plus_rate",
            "median"
        ),
        avg_lift=(
            "triangle_lift",
            "mean"
        )
    )
    .reset_index()
)

print(prev_analysis.to_string(index=False))


# =============================================================================
# 2. PREVIOUS2 RATE
# =============================================================================

print()
print("2. 前々回9日の△以上率")
print("-" * 80)

prev2_analysis = (
    history_df
    .dropna(subset=["prev2_triangle_plus_rate"])
    .groupby("prev2_rate_class")
    .agg(
        total=("triangle_plus_rate", "count"),
        current_avg_triangle_rate=(
            "triangle_plus_rate",
            "mean"
        ),
        current_median_triangle_rate=(
            "triangle_plus_rate",
            "median"
        ),
        avg_lift=(
            "triangle_lift",
            "mean"
        )
    )
    .reset_index()
)

print(prev2_analysis.to_string(index=False))


# =============================================================================
# 3. PREVIOUS3 RATE
# =============================================================================

print()
print("3. 3回前9日の△以上率")
print("-" * 80)

prev3_analysis = (
    history_df
    .dropna(subset=["prev3_triangle_plus_rate"])
    .groupby("prev3_rate_class")
    .agg(
        total=("triangle_plus_rate", "count"),
        current_avg_triangle_rate=(
            "triangle_plus_rate",
            "mean"
        ),
        current_median_triangle_rate=(
            "triangle_plus_rate",
            "median"
        ),
        avg_lift=(
            "triangle_lift",
            "mean"
        )
    )
    .reset_index()

print(prev3_analysis.to_string(index=False))


# =============================================================================
# 4. PREVIOUS → CURRENT LIFT
# =============================================================================

print()
print("4. 前回→今回 LIFT")
print("-" * 80)

lift_df = history_df.dropna(
    subset=[
        "prev_triangle_plus_rate",
        "triangle_plus_rate"
    ]
).copy()

lift_df["prev_rate_band"] = pd.cut(
    lift_df["prev_triangle_plus_rate"],
    bins=[-0.001, 10, 20, 30, 50, 100.001],
    labels=[
        "0-10%",
        "10-20%",
        "20-30%",
        "30-50%",
        "50%以上"
    ]
)

lift_analysis = (
    lift_df
    .groupby(
        "prev_rate_band",
        observed=True
    )
    .agg(
        total=("triangle_lift", "count"),
        avg_lift=("triangle_lift", "mean"),
        median_lift=("triangle_lift", "median"),
        positive_lift_rate=(
            "triangle_lift",
            lambda x: (x > 0).mean() * 100
        ),
        current_avg_rate=(
            "triangle_plus_rate",
            "mean"
        )
    )
    .reset_index()
)

print(
    lift_analysis.to_string(index=False)
)


# =============================================================================
# 5. TWO-PERIOD PATTERN
# =============================================================================

print()
print("5. 前々回 → 前回 → 今回")
print("-" * 80)

pattern_df = history_df.dropna(
    subset=[
        "prev2_triangle_plus_rate",
        "prev_triangle_plus_rate",
        "triangle_plus_rate"
    ]
).copy()


def pattern_class(x):

    if pd.isna(x):
        return "NA"

    if x <= 20:
        return "低"

    if x <= 50:
        return "中"

    return "高"


pattern_df["prev2_class"] = (
    pattern_df["prev2_triangle_plus_rate"]
    .apply(pattern_class)
)

pattern_df["prev_class"] = (
    pattern_df["prev_triangle_plus_rate"]
    .apply(pattern_class)
)

pattern_df["pattern"] = (
    pattern_df["prev2_class"]
    + " → "
    + pattern_df["prev_class"]
)


pattern_analysis = (
    pattern_df
    .groupby("pattern")
    .agg(
        total=("triangle_plus_rate", "count"),
        current_avg_rate=(
            "triangle_plus_rate",
            "mean"
        ),
        avg_lift=(
            "triangle_lift",
            "mean"
        ),
        positive_lift_rate=(
            "triangle_lift",
            lambda x: (x > 0).mean() * 100
        )
    )
    .reset_index()
)

print(
    pattern_analysis.to_string(index=False)
)


# =============================================================================
# 6. LOW → LOW → CURRENT
# =============================================================================

print()
print("6. 2回連続低調島")
print("-" * 80)

low_low = pattern_df[
    (pattern_df["prev2_triangle_plus_rate"] <= 20)
    &
    (pattern_df["prev_triangle_plus_rate"] <= 20)
]

if len(low_low) > 0:

    print(
        "対象:",
        len(low_low)
    )

    print(
        "今回平均△以上率:",
        round(
            low_low["triangle_plus_rate"].mean(),
            2
        )
    )

    print(
        "今回中央値:",
        round(
            low_low["triangle_plus_rate"].median(),
            2
        )
    )

    print(
        "平均LIFT:",
        round(
            low_low["triangle_lift"].mean(),
            2
        )
    )


# =============================================================================
# 7. STRONG PERIOD ONLY
# =============================================================================

print()
print("7. 詳細データ期間のstrong参考分析")
print("-" * 80)

print(
    "この項目では、簡易データ期間を"
    "strong判定には使用しません。"
)

print(
    "まず△以上率による長期ローテーションを確認し、"
    "その後、詳細データ期間のstrongと結合します。"
)


# =============================================================================
# SAVE
# =============================================================================

print()
print("=" * 80)
print("SAVE")
print("=" * 80)

detail_path = (
    OUTPUT_DIR
    / "nine_day_longterm_rotation_detail.csv"
)

summary_path = (
    OUTPUT_DIR
    / "nine_day_longterm_rotation_summary.csv"
)

history_df.to_csv(
    detail_path,
    index=False,
    encoding="utf-8-sig"
)

summary_frames = []

prev_analysis["analysis"] = "previous_nine_rate"
prev2_analysis["analysis"] = "previous2_nine_rate"
prev3_analysis["analysis"] = "previous3_nine_rate"
lift_analysis["analysis"] = "previous_to_current_lift"
pattern_analysis["analysis"] = "prev2_prev_current_pattern"

for x in [
    prev_analysis,
    prev2_analysis,
    prev3_analysis,
    lift_analysis,
    pattern_analysis
]:

    summary_frames.append(x)

summary_df = pd.concat(
    summary_frames,
    ignore_index=True,
    sort=False
)

summary_df.to_csv(
    summary_path,
    index=False,
    encoding="utf-8-sig"
)

print("detail :", detail_path)
print("summary:", summary_path)

print()
print("=" * 80)
print("ANALYSIS END")
print("=" * 80)