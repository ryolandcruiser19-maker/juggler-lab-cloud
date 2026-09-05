# ============================================================
# check_nine_day_prevday_rank.py
#
# 9の日 全台系 前日状態分析
#
# 目的:
#   9の日に全台系になった島について、
#   前日（8の日）の状態を分析する。
#
# 特に、
#   「前日に◎○が少ない」
#   「△が少ない」
#   「稼働が低い」
#   「他の島と比較して弱い」
#
# という条件が、翌9日のstrongと関係するかを検証する。
# ============================================================

import sqlite3
from pathlib import Path

import pandas as pd


# ============================================================
# パス
# ============================================================

BASE_DIR = Path(__file__).resolve().parents[1]

DB_PATH = BASE_DIR / "database" / "juggler.db"

OUTPUT_DIR = BASE_DIR / "analysis" / "backtest_output"

OUTPUT_FILE = (
    OUTPUT_DIR / "nine_day_prevday_rank.csv"
)


# ============================================================
# 設定
# ============================================================

# 9の日
# 日付の「日」が 9 / 19 / 29 のもの
NINE_DAYS = {9, 19, 29}


# ============================================================
# DB読み込み
# ============================================================

print("=" * 80)
print("9 DAY PREVIOUS-DAY ANALYSIS")
print("=" * 80)

print()
print("DB読み込み")
print("-" * 80)

conn = sqlite3.connect(DB_PATH)

df = pd.read_sql_query(
    """
    SELECT
        日付,
        島,
        G数,
        合成確率,
        評価,
        信頼度補正
    FROM daily_data
    WHERE 島 IS NOT NULL
    """,
    conn
)

conn.close()

print("rows:", len(df))


# ============================================================
# 型変換
# ============================================================

df["日付"] = pd.to_datetime(
    df["日付"],
    errors="coerce"
)

df["G数"] = pd.to_numeric(
    df["G数"],
    errors="coerce"
)

df["合成確率"] = pd.to_numeric(
    df["合成確率"],
    errors="coerce"
)


# ============================================================
# 評価集計
# ============================================================

def summarize_island(group):

    total = len(group)

    if total == 0:
        return None

    star = int(
        group["評価"].eq("◎").sum()
    )

    circle = int(
        group["評価"].eq("○").sum()
    )

    triangle = int(
        group["評価"].eq("△").sum()
    )

    high = star + circle + triangle

    star_rate = star / total * 100
    circle_plus_rate = (
        (star + circle) / total * 100
    )
    triangle_plus_rate = (
        high / total * 100
    )

    avg_games = group["G数"].mean()

    return {
        "machines": total,
        "star_count": star,
        "circle_count": circle,
        "triangle_count": triangle,
        "star_rate": star_rate,
        "circle_plus_rate": circle_plus_rate,
        "triangle_plus_rate": triangle_plus_rate,
        "avg_games": avg_games,
    }


# ============================================================
# 日付×島集計
# ============================================================

print()
print("日付×島集計")
print("-" * 80)

records = []

for (date, island), group in df.groupby(
    ["日付", "島"]
):

    result = summarize_island(group)

    if result is None:
        continue

    row = {
        "date": date,
        "island": island,
    }

    row.update(result)

    records.append(row)


island_daily = pd.DataFrame(records)

print(
    "日付×島 rows:",
    len(island_daily)
)


# ============================================================
# 9の日一覧
# ============================================================

nine_dates = sorted(
    d for d in island_daily["date"].dropna().unique()
    if d.day in NINE_DAYS
)

print()
print("9の日")
print("-" * 80)

print("nine days:", len(nine_dates))

for i, d in enumerate(nine_dates, 1):
    count = (
        island_daily["date"].eq(d).sum()
    )

    print(
        f"{i:2d}: "
        f"{d.strftime('%Y-%m-%d')} "
        f"islands={count}"
    )


# ============================================================
# 9の日 strong判定
#
# ここでは既存の
# 「強い全台系フラグ」
# を再計算するのではなく、
# 現在の判定基準を使用する。
#
# 現行strong:
#   △以上率 >= 80%
#
# candidate:
#   △以上率 >= 70%
# ============================================================

island_daily["strong"] = (
    island_daily["triangle_plus_rate"] >= 80
).astype(int)

island_daily["candidate"] = (
    island_daily["triangle_plus_rate"] >= 70
).astype(int)


# ============================================================
# 前日データを作成
# ============================================================

prev = island_daily.copy()

prev["date"] = (
    prev["date"] +
    pd.Timedelta(days=1)
)

prev = prev.rename(
    columns={
        "date": "nine_date",

        "machines": "prev_machines",

        "star_rate":
            "prev_star_rate",

        "circle_plus_rate":
            "prev_circle_plus_rate",

        "triangle_plus_rate":
            "prev_triangle_plus_rate",

        "avg_games":
            "prev_avg_games",

        "strong":
            "prev_strong",

        "candidate":
            "prev_candidate",
    }
)


# ============================================================
# 9の日の当日データ
# ============================================================

target = island_daily[
    island_daily["date"].isin(nine_dates)
].copy()

target = target.rename(
    columns={
        "date": "nine_date",

        "machines": "current_machines",

        "star_rate":
            "current_star_rate",

        "circle_plus_rate":
            "current_circle_plus_rate",

        "triangle_plus_rate":
            "current_triangle_plus_rate",

        "avg_games":
            "current_avg_games",

        "strong":
            "target_strong",

        "candidate":
            "target_candidate",
    }
)


# ============================================================
# 前日×9日 JOIN
# ============================================================

result = target.merge(
    prev[
        [
            "nine_date",
            "island",
            "prev_machines",
            "prev_star_rate",
            "prev_circle_plus_rate",
            "prev_triangle_plus_rate",
            "prev_avg_games",
            "prev_strong",
            "prev_candidate",
        ]
    ],
    on=[
        "nine_date",
        "island",
    ],
    how="left"
)


# ============================================================
# 日付ごとの「前日順位」
# ============================================================

print()
print("前日順位計算")
print("-" * 80)


def rank_desc(series):
    """
    大きいほど1位。
    NaNはNaNのまま。
    """
    return series.rank(
        ascending=False,
        method="min",
        na_option="keep"
    )


# ◎率
result["prev_star_rate_rank"] = (
    result.groupby("nine_date")[
        "prev_star_rate"
    ].transform(rank_desc)
)

# ○以上率
result["prev_circle_plus_rate_rank"] = (
    result.groupby("nine_date")[
        "prev_circle_plus_rate"
    ].transform(rank_desc)
)

# △以上率
result["prev_triangle_plus_rate_rank"] = (
    result.groupby("nine_date")[
        "prev_triangle_plus_rate"
    ].transform(rank_desc)
)

# 平均G数
result["prev_avg_games_rank"] = (
    result.groupby("nine_date")[
        "prev_avg_games"
    ].transform(rank_desc)
)


# ============================================================
# 総合順位
#
# 4項目の順位平均。
#
# 数字が小さいほど
# 「前日に強かった」
#
# 数字が大きいほど
# 「前日に弱かった」
# ============================================================

rank_columns = [
    "prev_star_rate_rank",
    "prev_circle_plus_rate_rank",
    "prev_triangle_plus_rate_rank",
    "prev_avg_games_rank",
]

result["prev_rank_mean"] = (
    result[rank_columns]
    .mean(axis=1)
)


# ============================================================
# 前日弱さスコア
#
# 順位を反転。
#
# 1 = 前日強い
# 17 = 前日弱い
#
# したがって、
# 値が大きいほど「前日弱い」
#
# ※島数が変わるため絶対順位ではなく
#   0～1の相対スコアも作る。
# ============================================================

result["prev_weakness_score"] = (
    result[rank_columns]
    .mean(axis=1)
)

result["prev_weakness_rate"] = (
    result["prev_weakness_score"]
    / result.groupby("nine_date")[
        "island"
    ].transform("count")
)


# ============================================================
# 前日状態カテゴリー
# ============================================================

def classify_weakness(x):

    if pd.isna(x):
        return "判定不能"

    if x <= 0.25:
        return "強い"

    if x <= 0.50:
        return "やや強い"

    if x <= 0.75:
        return "やや弱い"

    return "弱い"


result["prev_weakness_class"] = (
    result["prev_weakness_rate"]
    .apply(classify_weakness)
)


# ============================================================
# NaN安全な整数化
# ============================================================

def safe_int(x):

    if pd.isna(x):
        return None

    return int(x)


for col in [
    "prev_star_rate_rank",
    "prev_circle_plus_rate_rank",
    "prev_triangle_plus_rate_rank",
    "prev_avg_games_rank",
]:

    result[col] = (
        result[col]
        .apply(safe_int)
    )


# ============================================================
# 結果表示
# ============================================================

print()
print("=" * 80)
print("RESULT")
print("=" * 80)


strong = result[
    result["target_strong"] == 1
]

normal = result[
    result["target_strong"] == 0
]


print()
print("strong islands:", len(strong))
print("normal islands:", len(normal))


# ============================================================
# strong / normal 比較
# ============================================================

print()
print("=" * 80)
print("1. PREVIOUS DAY")
print("=" * 80)


compare_columns = [
    "prev_star_rate",
    "prev_circle_plus_rate",
    "prev_triangle_plus_rate",
    "prev_avg_games",
    "prev_rank_mean",
]


for col in compare_columns:

    print()
    print(col)

    print(
        "  strong:",
        round(
            strong[col].mean(),
            2
        )
    )

    print(
        "  normal:",
        round(
            normal[col].mean(),
            2
        )
    )


# ============================================================
# 前日順位
# ============================================================

print()
print("=" * 80)
print("2. PREVIOUS DAY RANK")
print("=" * 80)


rank_compare = [
    "prev_star_rate_rank",
    "prev_circle_plus_rate_rank",
    "prev_triangle_plus_rate_rank",
    "prev_avg_games_rank",
    "prev_rank_mean",
]


for col in rank_compare:

    print()
    print(col)

    print(
        "  strong:",
        round(
            strong[col].mean(),
            2
        )
    )

    print(
        "  normal:",
        round(
            normal[col].mean(),
            2
        )
    )


# ============================================================
# 前日弱い島 → strong
# ============================================================

print()
print("=" * 80)
print("3. PREVIOUS DAY WEAKNESS")
print("=" * 80)


for threshold in [
    0.30,
    0.50,
    0.70,
]:

    subset = result[
        result["prev_weakness_rate"] >= threshold
    ]

    hit = int(
        subset["target_strong"].sum()
    )

    total = len(subset)

    rate = (
        hit / total * 100
        if total > 0
        else 0
    )

    print(
        f"weakness >= {threshold:.2f}: "
        f"{hit}/{total} = {rate:.2f}%"
    )


# ============================================================
# 前日4条件すべて弱い
# ============================================================

print()
print("=" * 80)
print("4. ALL WEAK")
print("=" * 80)


# 各指標について日内下位50%

weak_conditions = []

for date, group in result.groupby(
    "nine_date"
):

    temp = group.copy()

    conditions = pd.DataFrame(
        index=temp.index
    )

    for col in [
        "prev_star_rate",
        "prev_circle_plus_rate",
        "prev_triangle_plus_rate",
        "prev_avg_games",
    ]:

        median = temp[col].median()

        conditions[col] = (
            temp[col] <= median
        )

    weak = conditions.all(
        axis=1
    )

    weak_conditions.append(
        temp.loc[weak].index
    )


if weak_conditions:

    weak_indices = (
        pd.Index([])
        .union_many(weak_conditions)
        if hasattr(
            pd.Index([]),
            "union_many"
        )
        else pd.Index(
            sum(
                [list(x) for x in weak_conditions],
                []
            )
        )
    )

    all_weak = result.loc[
        weak_indices
    ]

    hit = int(
        all_weak["target_strong"].sum()
    )

    total = len(all_weak)

    rate = (
        hit / total * 100
        if total > 0
        else 0
    )

    print(
        "all weak:",
        f"{hit}/{total} = {rate:.2f}%"
    )

else:

    print("該当データなし")


# ============================================================
# 前日◎・○が少なく、△が少ない条件
# ============================================================

print()
print("=" * 80)
print("5. LOW OUTPUT PREVIOUS DAY")
print("=" * 80)


conditions = {

    "star0":
        result["prev_star_rate"] == 0,

    "circle0":
        result["prev_circle_plus_rate"] == 0,

    "triangle_le20":
        result["prev_triangle_plus_rate"] <= 20,

    "games_le3000":
        result["prev_avg_games"] <= 3000,

    "star_le10":
        result["prev_star_rate"] <= 10,

    "circle_le20":
        result["prev_circle_plus_rate"] <= 20,

    "triangle_le30":
        result["prev_triangle_plus_rate"] <= 30,

}


for name, condition in conditions.items():

    subset = result[
        condition
    ]

    hit = int(
        subset["target_strong"].sum()
    )

    total = len(subset)

    rate = (
        hit / total * 100
        if total > 0
        else 0
    )

    print(
        f"{name:15s}: "
        f"{hit}/{total} = {rate:.2f}%"
    )


# ============================================================
# 前日弱さカテゴリー別
# ============================================================

print()
print("=" * 80)
print("6. WEAKNESS CLASS")
print("=" * 80)


class_summary = (
    result
    .groupby(
        "prev_weakness_class",
        dropna=False
    )
    .agg(
        total=(
            "target_strong",
            "count"
        ),
        strong=(
            "target_strong",
            "sum"
        )
    )
)

class_summary["rate"] = (
    class_summary["strong"]
    /
    class_summary["total"]
    * 100
)

print(
    class_summary
)


# ============================================================
# strong島一覧
# ============================================================

print()
print("=" * 80)
print("7. STRONG ISLANDS")
print("=" * 80)


show_columns = [
    "nine_date",
    "island",

    "prev_star_rate",
    "prev_circle_plus_rate",
    "prev_triangle_plus_rate",
    "prev_avg_games",

    "prev_star_rate_rank",
    "prev_circle_plus_rate_rank",
    "prev_triangle_plus_rate_rank",
    "prev_avg_games_rank",

    "prev_rank_mean",
    "prev_weakness_class",

    "target_strong",
]


print(
    strong[
        show_columns
    ]
    .sort_values(
        [
            "nine_date",
            "prev_rank_mean",
        ]
    )
    .to_string(
        index=False
    )
)


# ============================================================
# CSV保存
# ============================================================

print()
print("=" * 80)
print("SAVE")
print("=" * 80)

OUTPUT_DIR.mkdir(
    parents=True,
    exist_ok=True
)

result.to_csv(
    OUTPUT_FILE,
    index=False,
    encoding="utf-8-sig"
)

print(
    "saved:",
    OUTPUT_FILE
)

print()
print("=" * 80)
print("ANALYSIS END")
print("=" * 80)