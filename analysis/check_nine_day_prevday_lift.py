import sqlite3
import pandas as pd
import numpy as np
from pathlib import Path


# =============================================================================
# 設定
# =============================================================================

BASE_DIR = Path(r"C:\Users\sphs4\OneDrive\デスクトップ\ジャグラーラボ")

DB_PATH = BASE_DIR / "database" / "juggler.db"

OUTPUT_DIR = BASE_DIR / "analysis" / "backtest_output"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

DETAIL_PATH = OUTPUT_DIR / "nine_day_prevday_lift.csv"
SUMMARY_PATH = OUTPUT_DIR / "nine_day_prevday_lift_summary.csv"

START_DATE = "2026-03-01"
END_DATE = "2026-08-15"


# =============================================================================
# ユーティリティ
# =============================================================================

def safe_float(x):
    try:
        if pd.isna(x):
            return np.nan
        return float(x)
    except Exception:
        return np.nan


def safe_int(x):
    try:
        if pd.isna(x):
            return np.nan
        return int(x)
    except Exception:
        return np.nan


# =============================================================================
# DB読み込み
# =============================================================================

print("=" * 80)
print("9 DAY PREVIOUS-DAY LIFT ANALYSIS")
print("=" * 80)

print()
print("DB読み込み")
print("-" * 80)

conn = sqlite3.connect(DB_PATH)

# -------------------------------------------------------------------------
# DBの実際の列名を確認
# -------------------------------------------------------------------------

columns = pd.read_sql_query(
    "PRAGMA table_info(daily_data)",
    conn
)

print("daily_data columns:")
print(columns["name"].tolist())

# -------------------------------------------------------------------------
# 日付列を自動判定
# -------------------------------------------------------------------------

available_columns = columns["name"].tolist()

date_candidates = [
    "日付",
    "date",
    "営業日",
]

date_col = None

for c in date_candidates:
    if c in available_columns:
        date_col = c
        break

if date_col is None:
    raise RuntimeError(
        "daily_data に日付列が見つかりません。"
        f"利用可能列: {available_columns}"
    )

print(f"date column: {date_col}")


# =============================================================================
# 必要列確認
# =============================================================================

required_candidates = {
    "island": ["島", "island"],
    "machine": ["機種", "machine"],
    "evaluation": ["評価", "evaluation"],
    "games": ["G数", "累計ゲーム", "ゲーム数", "games"],
}

resolved = {}

for key, candidates in required_candidates.items():

    found = None

    for c in candidates:
        if c in available_columns:
            found = c
            break

    if found is None:
        print(f"WARNING: {key} column not found")

    resolved[key] = found


island_col = resolved["island"]
machine_col = resolved["machine"]
evaluation_col = resolved["evaluation"]
games_col = resolved["games"]

if island_col is None:
    raise RuntimeError("島列が見つかりません。")

if evaluation_col is None:
    raise RuntimeError("評価列が見つかりません。")


# =============================================================================
# データ取得
# =============================================================================

select_cols = [
    f'"{date_col}" AS 日付',
    f'"{island_col}" AS 島',
    f'"{evaluation_col}" AS 評価',
]

if machine_col:
    select_cols.append(f'"{machine_col}" AS 機種')

if games_col:
    select_cols.append(f'"{games_col}" AS G数')


sql = f"""
SELECT
    {", ".join(select_cols)}
FROM daily_data
WHERE "{date_col}" >= ?
  AND "{date_col}" <= ?
"""

df = pd.read_sql_query(
    sql,
    conn,
    params=[START_DATE, END_DATE]
)

conn.close()

print(f"rows: {len(df):,}")


# =============================================================================
# 前処理
# =============================================================================

df["日付"] = pd.to_datetime(df["日付"], errors="coerce")

df = df.dropna(subset=["日付", "島"])

df["評価"] = df["評価"].astype(str).str.strip()

if "G数" in df.columns:
    df["G数"] = pd.to_numeric(
        df["G数"],
        errors="coerce"
    )
else:
    df["G数"] = np.nan


# =============================================================================
# 9の日抽出
# =============================================================================

nine_dates = sorted(
    df.loc[
        df["日付"].dt.day.isin([9, 19, 29]),
        "日付"
    ].dt.normalize().unique()
)

print()
print("9の日")
print("-" * 80)

print(f"nine days: {len(nine_dates)}")

for i, d in enumerate(nine_dates, 1):

    d = pd.Timestamp(d)

    island_count = df.loc[
        df["日付"].dt.normalize() == d,
        "島"
    ].nunique()

    print(
        f"{i:2d}: {d.strftime('%Y-%m-%d')} "
        f"islands={island_count}"
    )


# =============================================================================
# 日付×島 集計
# =============================================================================

print()
print("日付×島集計")
print("-" * 80)


def aggregate_island(group):

    total = len(group)

    star_count = (
        (group["評価"] == "◎").sum()
    )

    circle_plus_count = (
        group["評価"].isin(["◎", "○"]).sum()
    )

    triangle_plus_count = (
        group["評価"].isin(["◎", "○", "△"]).sum()
    )

    games = pd.to_numeric(
        group["G数"],
        errors="coerce"
    )

    return pd.Series({

        "island_size": total,

        "star_count": star_count,

        "circle_plus_count": circle_plus_count,

        "triangle_plus_count": triangle_plus_count,

        "star_rate": (
            star_count / total * 100
            if total > 0 else np.nan
        ),

        "circle_plus_rate": (
            circle_plus_count / total * 100
            if total > 0 else np.nan
        ),

        "triangle_plus_rate": (
            triangle_plus_count / total * 100
            if total > 0 else np.nan
        ),

        "avg_games": games.mean(),

    })


island_daily = (
    df.groupby(
        [
            df["日付"].dt.normalize(),
            "島"
        ]
    )
    .apply(aggregate_island)
    .reset_index()
    .rename(columns={"日付": "日付"})
)


print(
    f"日付×島 rows: {len(island_daily):,}"
)


# =============================================================================
# 9の日 strong 判定
# =============================================================================
#
# ここでは既存の全台系判定ロジックを完全には再定義せず、
# 「9の日にその島がstrongだったか」を
# 評価データから判定する。
#
# 全台系の判定：
# 島内の △以上率が一定以上
#
# ただし、過去分析との整合性を優先して、
# strong 判定は「既存の分析CSV」があれば利用する。
#
# 今回はDBから再現可能な簡易strong判定として
# △以上率 >= 80% を採用。
#
# ※後で正式な全台系判定ロジックに接続可能。
# =============================================================================

STRONG_THRESHOLD = 80.0

island_daily["strong"] = (
    island_daily["triangle_plus_rate"]
    >= STRONG_THRESHOLD
)


# =============================================================================
# 前日データを結合
# =============================================================================

print()
print("前日データ結合")
print("-" * 80)


prev = island_daily.copy()

prev["prev_date"] = (
    prev["日付"] + pd.Timedelta(days=1)
)

prev = prev.rename(
    columns={
        "島": "島",

        "island_size": "prev_island_size",

        "star_count": "prev_star_count",
        "circle_plus_count": "prev_circle_plus_count",
        "triangle_plus_count": "prev_triangle_plus_count",

        "star_rate": "prev_star_rate",
        "circle_plus_rate": "prev_circle_plus_rate",
        "triangle_plus_rate": "prev_triangle_plus_rate",

        "avg_games": "prev_avg_games",

    }
)

prev_cols = [
    "prev_date",
    "島",

    "prev_island_size",

    "prev_star_count",
    "prev_circle_plus_count",
    "prev_triangle_plus_count",

    "prev_star_rate",
    "prev_circle_plus_rate",
    "prev_triangle_plus_rate",

    "prev_avg_games",
]

prev = prev[prev_cols]


# 9の日だけ
target = island_daily[
    island_daily["日付"].dt.day.isin([9, 19, 29])
].copy()

target = target.rename(
    columns={
        "strong": "target_strong"
    }
)

result = target.merge(
    prev,
    left_on=["日付", "島"],
    right_on=["prev_date", "島"],
    how="left"
)

result["target_strong"] = (
    result["target_strong"]
    .astype(int)
)


# =============================================================================
# 前日順位
# =============================================================================

print()
print("前日順位計算")
print("-" * 80)


rank_columns = [
    "prev_star_rate",
    "prev_circle_plus_rate",
    "prev_triangle_plus_rate",
    "prev_avg_games",
]


for col in rank_columns:

    rank_col = col + "_rank"

    result[rank_col] = (
        result.groupby("日付")[col]
        .rank(
            ascending=False,
            method="average"
        )
    )


rank_cols = [
    "prev_star_rate_rank",
    "prev_circle_plus_rate_rank",
    "prev_triangle_plus_rate_rank",
    "prev_avg_games_rank",
]

result["prev_rank_mean"] = (
    result[rank_cols]
    .mean(axis=1)
)


# =============================================================================
# 前日 ◎+○ 台数
# =============================================================================

result["prev_star_circle_count"] = (
    result["prev_star_count"]
    + result["prev_circle_plus_count"]
)


# =============================================================================
# 弱さスコア
# =============================================================================
#
# 「前日の島内が弱い」
# ＋
# 「他島と比較して弱い」
#
# を同時に評価する。
#
# 各項目について、値が小さいほど弱い。
#
# そのため percentile rank を使い、
# 低いほど weakness が大きくなるようにする。
# =============================================================================

weakness_components = []

for col in [
    "prev_star_rate",
    "prev_circle_plus_rate",
    "prev_triangle_plus_rate",
    "prev_avg_games",
]:

    percentile = (
        result.groupby("日付")[col]
        .rank(
            pct=True,
            ascending=True
        )
    )

    weakness = 1.0 - percentile

    weakness_components.append(
        weakness
    )


result["prev_weakness_score"] = (
    pd.concat(
        weakness_components,
        axis=1
    )
    .mean(axis=1)
)


# =============================================================================
# 前日 ◎+○ クラス
# =============================================================================

def star_circle_class(x):

    if pd.isna(x):
        return "判定不能"

    if x == 0:
        return "0台"

    if x == 1:
        return "1台"

    if x == 2:
        return "2台"

    return "3台以上"


result["prev_star_circle_class"] = (
    result["prev_star_circle_count"]
    .apply(star_circle_class)
)


# =============================================================================
# 前日 △以上 クラス
# =============================================================================

def triangle_class(x):

    if pd.isna(x):
        return "判定不能"

    if x == 0:
        return "0台"

    if x == 1:
        return "1台"

    if x == 2:
        return "2台"

    if x == 3:
        return "3台"

    return "4台以上"


result["prev_triangle_class"] = (
    result["prev_triangle_plus_count"]
    .apply(triangle_class)
)


# =============================================================================
# 前日弱さクラス
# =============================================================================

def weakness_class(x):

    if pd.isna(x):
        return "判定不能"

    if x >= 0.75:
        return "非常に弱い"

    if x >= 0.50:
        return "弱い"

    if x >= 0.25:
        return "やや弱い"

    return "強い"


result["weakness_class"] = (
    result["prev_weakness_score"]
    .apply(weakness_class)
)


# =============================================================================
# 前回strong履歴
# =============================================================================

target_dates = sorted(
    pd.to_datetime(
        target["日付"]
    ).dt.normalize().unique()
)


strong_history = {}

for island in result["島"].unique():

    strong_history[island] = {}

    for d in target_dates:

        row = result[
            (result["島"] == island)
            &
            (result["日付"] == d)
        ]

        if len(row) == 0:
            continue

        strong_history[island][
            pd.Timestamp(d)
        ] = int(
            row.iloc[0]["target_strong"]
        )


def get_previous_strong(row):

    island = row["島"]
    current = pd.Timestamp(row["日付"])

    dates = [
        d for d in strong_history.get(
            island, {}
        )
        if d < current
    ]

    if not dates:
        return 0

    latest = max(dates)

    return strong_history[island][latest]


result["previous_strong"] = (
    result.apply(
        get_previous_strong,
        axis=1
    )
)


# =============================================================================
# 直近2回以内にstrongがあったか
# =============================================================================

def get_previous2_strong(row):

    island = row["島"]
    current = pd.Timestamp(row["日付"])

    dates = sorted(
        [
            d for d in strong_history.get(
                island, {}
            )
            if d < current
        ],
        reverse=True
    )

    if len(dates) == 0:
        return 0

    if len(dates) == 1:
        return strong_history[island][dates[0]]

    return max(
        strong_history[island][dates[0]],
        strong_history[island][dates[1]]
    )


result["previous2_strong"] = (
    result.apply(
        get_previous2_strong,
        axis=1
    )
)


# =============================================================================
# 前日から9日へのLIFT
# =============================================================================

result["star_rate_lift"] = (
    result["star_rate"]
    - result["prev_star_rate"]
)

result["circle_plus_rate_lift"] = (
    result["circle_plus_rate"]
    - result["prev_circle_plus_rate"]
)

result["triangle_plus_rate_lift"] = (
    result["triangle_plus_rate"]
    - result["prev_triangle_plus_rate"]
)


result["games_lift"] = (
    result["avg_games"]
    - result["prev_avg_games"]
)


# =============================================================================
# 前日弱さ × strong
# =============================================================================

result["weak_bottom30"] = (
    result["prev_weakness_score"]
    >= 0.70
)

result["weak_bottom20"] = (
    result["prev_weakness_score"]
    >= 0.80
)

result["weak_bottom10"] = (
    result["prev_weakness_score"]
    >= 0.90
)


# =============================================================================
# 前日低出力条件
# =============================================================================

result["prev_star0"] = (
    result["prev_star_count"] == 0
)

result["prev_circle0"] = (
    result["prev_circle_plus_count"] == 0
)

result["prev_triangle_le1"] = (
    result["prev_triangle_plus_count"] <= 1
)

result["prev_triangle_le2"] = (
    result["prev_triangle_plus_count"] <= 2
)

result["prev_star_circle_le1"] = (
    result["prev_star_circle_count"] <= 1
)

result["prev_games_le3000"] = (
    result["prev_avg_games"] <= 3000
)


# =============================================================================
# 結果表示
# =============================================================================

print()
print("=" * 80)
print("RESULT")
print("=" * 80)


total = len(result)

strong_total = int(
    result["target_strong"].sum()
)

print()
print(f"対象島数 : {total}")
print(f"strong  : {strong_total}")


# =============================================================================
# 条件集計関数
# =============================================================================

def print_condition(
    name,
    condition
):

    subset = result[condition].copy()

    n = len(subset)

    s = int(
        subset["target_strong"].sum()
    )

    rate = (
        s / n * 100
        if n > 0
        else 0
    )

    print(
        f"{name:<45}"
        f"{n:>5} "
        f"{s:>5} "
        f"{rate:>7.2f}%"
    )

    return {
        "condition": name,
        "total": n,
        "strong": s,
        "rate": rate,
    }


# =============================================================================
# 弱さスコア
# =============================================================================

print()
print("1. PREVIOUS-DAY WEAKNESS")
print("-" * 80)

summary_rows = []

summary_rows.append(
    print_condition(
        "前日弱さ >= 0.70",
        result["weak_bottom30"]
    )
)

summary_rows.append(
    print_condition(
        "前日弱さ >= 0.80",
        result["weak_bottom20"]
    )
)

summary_rows.append(
    print_condition(
        "前日弱さ >= 0.90",
        result["weak_bottom10"]
    )
)


# =============================================================================
# ◎+○
# =============================================================================

print()
print("2. PREVIOUS ◎+○")
print("-" * 80)

summary_rows.append(
    print_condition(
        "前日 ◎+○ = 0台",
        result["prev_star_circle_count"] == 0
    )
)

summary_rows.append(
    print_condition(
        "前日 ◎+○ <= 1台",
        result["prev_star_circle_count"] <= 1
    )
)

summary_rows.append(
    print_condition(
        "前日 ◎+○ <= 2台",
        result["prev_star_circle_count"] <= 2
    )
)


# =============================================================================
# △以上
# =============================================================================

print()
print("3. PREVIOUS △+")
print("-" * 80)

summary_rows.append(
    print_condition(
        "前日 △以上 = 0台",
        result["prev_triangle_plus_count"] == 0
    )
)

summary_rows.append(
    print_condition(
        "前日 △以上 <= 1台",
        result["prev_triangle_plus_count"] <= 1
    )
)

summary_rows.append(
    print_condition(
        "前日 △以上 <= 2台",
        result["prev_triangle_plus_count"] <= 2
    )
)

summary_rows.append(
    print_condition(
        "前日 △以上 <= 3台",
        result["prev_triangle_plus_count"] <= 3
    )
)


# =============================================================================
# 組み合わせ
# =============================================================================

print()
print("4. COMBINATION")
print("-" * 80)

c1 = (
    (result["prev_star_circle_count"] <= 1)
    &
    (result["prev_triangle_plus_count"] <= 2)
)

summary_rows.append(
    print_condition(
        "◎+○<=1 AND △以上<=2",
        c1
    )
)


c2 = (
    (result["prev_star_circle_count"] <= 1)
    &
    (result["prev_triangle_plus_count"] <= 2)
    &
    (result["previous_strong"] == 0)
)

summary_rows.append(
    print_condition(
        "前回strongなし AND ◎+○<=1 AND △以上<=2",
        c2
    )
)


c3 = (
    (result["prev_weakness_score"] >= 0.70)
    &
    (result["previous_strong"] == 0)
)

summary_rows.append(
    print_condition(
        "前回strongなし AND 前日弱さ>=0.70",
        c3
    )
)


c4 = (
    (result["prev_weakness_score"] >= 0.70)
    &
    (result["prev_star_circle_count"] <= 1)
    &
    (result["prev_triangle_plus_count"] <= 2)
)

summary_rows.append(
    print_condition(
        "弱さ>=0.70 AND ◎+○<=1 AND △以上<=2",
        c4
    )
)


# =============================================================================
# 順位
# =============================================================================

print()
print("5. PREVIOUS-DAY RANK")
print("-" * 80)


rank_conditions = [

    (
        "◎率 下位30%",
        result["prev_star_rate_rank"]
        >= result.groupby("日付")["prev_star_rate_rank"]
        .transform("max") * 0.70
    ),

    (
        "◎+○率 下位30%",
        result["prev_circle_plus_rate_rank"]
        >= result.groupby("日付")["prev_circle_plus_rate_rank"]
        .transform("max") * 0.70
    ),

    (
        "△以上率 下位30%",
        result["prev_triangle_plus_rate_rank"]
        >= result.groupby("日付")["prev_triangle_plus_rate_rank"]
        .transform("max") * 0.70
    ),

    (
        "平均G数 下位30%",
        result["prev_avg_games_rank"]
        >= result.groupby("日付")["prev_avg_games_rank"]
        .transform("max") * 0.70
    ),
]


for name, condition in rank_conditions:

    summary_rows.append(
        print_condition(
            name,
            condition
        )
    )


# =============================================================================
# 強い「持ち上がり」だけを見る
# =============================================================================

print()
print("6. PREVIOUS WEAK → CURRENT STRONG")
print("-" * 80)


lift_conditions = [

    (
        "前日弱さ>=0.70 → 9日strong",
        result["prev_weakness_score"] >= 0.70
    ),

    (
        "前日 ◎+○<=1 → 9日strong",
        result["prev_star_circle_count"] <= 1
    ),

    (
        "前日 △以上<=2 → 9日strong",
        result["prev_triangle_plus_count"] <= 2
    ),

    (
        "前日 ◎+○<=1 & △以上<=2 → strong",
        (
            (result["prev_star_circle_count"] <= 1)
            &
            (result["prev_triangle_plus_count"] <= 2)
        )
    ),

    (
        "前日弱さ>=0.70 & ◎+○<=1 & △以上<=2",
        (
            (result["prev_weakness_score"] >= 0.70)
            &
            (result["prev_star_circle_count"] <= 1)
            &
            (result["prev_triangle_plus_count"] <= 2)
        )
    ),
]


for name, condition in lift_conditions:

    subset = result[condition].copy()

    n = len(subset)

    s = int(
        subset["target_strong"].sum()
    )

    if n > 0:

        lift = (
            subset["triangle_plus_rate"]
            - subset["prev_triangle_plus_rate"]
        )

        mean_lift = lift.mean()

    else:

        mean_lift = np.nan

    rate = (
        s / n * 100
        if n > 0
        else 0
    )

    print(
        f"{name:<55}"
        f"{n:>5} "
        f"{s:>5} "
        f"{rate:>7.2f}% "
        f"平均△以上率LIFT={mean_lift:>8.2f}"
    )


# =============================================================================
# strong島一覧
# =============================================================================

print()
print("7. STRONG ISLANDS WITH PREVIOUS-DAY CONDITION")
print("-" * 80)

strong_columns = [
    "日付",
    "島",
    "target_strong",

    "prev_star_count",
    "prev_circle_plus_count",
    "prev_triangle_plus_count",

    "prev_star_rate",
    "prev_circle_plus_rate",
    "prev_triangle_plus_rate",

    "prev_avg_games",

    "prev_star_rate_rank",
    "prev_circle_plus_rate_rank",
    "prev_triangle_plus_rate_rank",
    "prev_avg_games_rank",

    "prev_rank_mean",
    "prev_weakness_score",
    "weakness_class",

    "previous_strong",

    "star_rate_lift",
    "circle_plus_rate_lift",
    "triangle_plus_rate_lift",
    "games_lift",
]

strong_df = result[
    result["target_strong"] == 1
][strong_columns].copy()

print(
    strong_df.to_string(
        index=False
    )
)


# =============================================================================
# 保存
# =============================================================================

print()
print("=" * 80)
print("SAVE")
print("=" * 80)

result.to_csv(
    DETAIL_PATH,
    index=False,
    encoding="utf-8-sig"
)

summary_df = pd.DataFrame(
    summary_rows
)

summary_df.to_csv(
    SUMMARY_PATH,
    index=False,
    encoding="utf-8-sig"
)

print()
print(f"detail : {DETAIL_PATH}")
print(f"summary: {SUMMARY_PATH}")

print()
print("=" * 80)
print("ANALYSIS END")
print("=" * 80)