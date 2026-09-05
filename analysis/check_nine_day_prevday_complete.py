import sqlite3
import pandas as pd
import numpy as np
from pathlib import Path


# ============================================================
# 設定
# ============================================================

BASE_DIR = Path(__file__).resolve().parent.parent
DB_PATH = BASE_DIR / "database" / "juggler.db"
OUTPUT_DIR = BASE_DIR / "analysis" / "backtest_output"

OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

OUTPUT_DETAIL = OUTPUT_DIR / "nine_day_prevday_complete_detail.csv"
OUTPUT_SUMMARY = OUTPUT_DIR / "nine_day_prevday_complete_summary.csv"


# ============================================================
# DB読み込み
# ============================================================

print("=" * 80)
print("9 DAY PREVIOUS-DAY COMPLETE ANALYSIS")
print("=" * 80)

print()
print("DB読み込み")
print("-" * 80)

conn = sqlite3.connect(DB_PATH)

df = pd.read_sql_query(
    """
    SELECT *
    FROM daily_data
    """,
    conn
)

conn.close()

print(f"rows: {len(df):,}")


# ============================================================
# 列確認
# ============================================================

required_columns = [
    "日付",
    "島",
    "評価",
    "G数",
]

missing = [c for c in required_columns if c not in df.columns]

if missing:
    print()
    print("ERROR: 必要な列がありません")
    print(missing)
    raise SystemExit(1)


# ============================================================
# データ整形
# ============================================================

df["日付"] = pd.to_datetime(df["日付"], errors="coerce")

df["G数"] = pd.to_numeric(
    df["G数"],
    errors="coerce"
)

df["評価"] = df["評価"].fillna("").astype(str)

df = df.dropna(subset=["日付", "島"])


# ============================================================
# 2026/03以降に限定
# ============================================================

START_DATE = pd.Timestamp("2026-03-01")

df = df[df["日付"] >= START_DATE].copy()

print()
print("分析期間")
print("-" * 80)

print(
    f"{df['日付'].min().date()} ～ "
    f"{df['日付'].max().date()}"
)


# ============================================================
# 評価判定
# ============================================================

def is_star(x):
    return "◎" in x


def is_circle(x):
    return "○" in x


def is_triangle(x):
    return "△" in x


df["is_star"] = df["評価"].apply(is_star)
df["is_circle"] = df["評価"].apply(is_circle)
df["is_triangle"] = df["評価"].apply(is_triangle)

df["is_circle_plus"] = (
    df["is_star"] |
    df["is_circle"]
)

df["is_triangle_plus"] = (
    df["is_star"] |
    df["is_circle"] |
    df["is_triangle"]
)


# ============================================================
# 日付×島 集計
# ============================================================

print()
print("日付×島集計")
print("-" * 80)

group = (
    df
    .groupby(["日付", "島"], dropna=False)
    .agg(
        island_size=("評価", "size"),

        star_count=("is_star", "sum"),
        circle_plus_count=("is_circle_plus", "sum"),
        triangle_plus_count=("is_triangle_plus", "sum"),

        avg_games=("G数", "mean"),
    )
    .reset_index()
)


group["star_rate"] = (
    group["star_count"]
    / group["island_size"]
    * 100
)

group["circle_plus_rate"] = (
    group["circle_plus_count"]
    / group["island_size"]
    * 100
)

group["triangle_plus_rate"] = (
    group["triangle_plus_count"]
    / group["island_size"]
    * 100
)


print(f"日付×島 rows: {len(group):,}")


# ============================================================
# 9の日
# ============================================================

group["is_nine_day"] = (
    group["日付"].dt.day % 10 == 9
)

nine_days = sorted(
    group.loc[group["is_nine_day"], "日付"]
    .unique()
)

print()
print("9の日")
print("-" * 80)

print(f"nine days: {len(nine_days)}")

for i, d in enumerate(nine_days, 1):
    n = group.loc[
        group["日付"] == d,
        "島"
    ].nunique()

    print(
        f"{i:2d}: {d.date()} islands={n}"
    )


# ============================================================
# strong判定
#
# ここは現在の既存strong判定を再現
#
# ◎率 >= 30
# ○以上率 >= 40
# △以上率 >= 80
#
# ※必要なら既存スクリプトの定義に合わせて変更
# ============================================================

def strong_rule(row):

    return (
        row["star_rate"] >= 30
        and
        row["circle_plus_rate"] >= 40
        and
        row["triangle_plus_rate"] >= 80
    )


group["strong"] = group.apply(
    strong_rule,
    axis=1
)


# ============================================================
# 9の日のstrong島
# ============================================================

target = group[
    group["is_nine_day"]
].copy()

strong_count = int(target["strong"].sum())

print()
print("=" * 80)
print("STRONG")
print("=" * 80)

print(f"strong islands: {strong_count}")


# ============================================================
# 前日のデータを結合
# ============================================================

nine = target[
    [
        "日付",
        "島",
        "strong",
    ]
].copy()

nine["prev_date"] = (
    nine["日付"] -
    pd.Timedelta(days=1)
)


prev = group[
    [
        "日付",
        "島",
        "island_size",
        "star_count",
        "circle_plus_count",
        "triangle_plus_count",
        "star_rate",
        "circle_plus_rate",
        "triangle_plus_rate",
        "avg_games",
    ]
].copy()

prev = prev.rename(
    columns={
        "日付": "prev_date",
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


result = nine.merge(
    prev,
    on=["prev_date", "島"],
    how="left"
)


# ============================================================
# 前日特徴量
# ============================================================

result["prev_star_circle_count"] = (
    result["prev_star_count"].fillna(0)
    +
    (
        result["prev_circle_plus_count"]
        -
        result["prev_star_count"]
    ).fillna(0)
)

# ◎+○台数
result["prev_star_circle_count"] = (
    result["prev_star_count"].fillna(0)
    +
    (
        result["prev_circle_plus_count"].fillna(0)
        -
        result["prev_star_count"].fillna(0)
    )
)

# △以上台数
result["prev_triangle_plus_count"] = (
    result["prev_triangle_plus_count"]
    .fillna(0)
)


# ============================================================
# 前日◎+○台数区分
# ============================================================

def star_circle_class(x):

    if pd.isna(x):
        return "判定不能"

    x = int(x)

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


# ============================================================
# 前日△以上台数区分
# ============================================================

def triangle_class(x):

    if pd.isna(x):
        return "判定不能"

    x = int(x)

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


# ============================================================
# 前日弱さスコア
#
# ◎・○が少なく、
# △以上も少ないほど「弱い」
#
# 0～1に正規化
# ============================================================

result["prev_weakness_score"] = (
    1
    -
    (
        result["prev_star_rate"].fillna(0) * 0.4
        +
        result["prev_circle_plus_rate"].fillna(0) * 0.3
        +
        result["prev_triangle_plus_rate"].fillna(0) * 0.3
    ) / 100
)


# ============================================================
# 島間順位
# ============================================================

rank_cols = [
    "prev_star_rate",
    "prev_circle_plus_rate",
    "prev_triangle_plus_rate",
    "prev_avg_games",
]

rank_names = [
    "prev_star_rate_rank",
    "prev_circle_plus_rate_rank",
    "prev_triangle_plus_rate_rank",
    "prev_avg_games_rank",
]


for col, rank_col in zip(rank_cols, rank_names):

    result[rank_col] = (
        result
        .groupby("日付")[col]
        .rank(
            ascending=True,
            method="average"
        )
    )


result["prev_rank_mean"] = (
    result[
        [
            "prev_star_rate_rank",
            "prev_circle_plus_rate_rank",
            "prev_triangle_plus_rate_rank",
        ]
    ]
    .mean(axis=1)
)


# ============================================================
# 前回strong
# ============================================================

history = target[
    [
        "日付",
        "島",
        "strong",
    ]
].copy()

history = history.rename(
    columns={
        "日付": "history_date",
        "strong": "history_strong",
    }
)


def get_previous_strong(
    row,
    days_back
):

    d = row["日付"]

    candidates = target[
        (target["島"] == row["島"])
        &
        (target["日付"] < d)
    ].sort_values("日付")

    if len(candidates) < days_back:
        return 0

    return int(
        candidates.iloc[-days_back]["strong"]
    )


result["previous_strong"] = result.apply(
    lambda r: get_previous_strong(r, 1),
    axis=1
)

result["previous2_strong"] = result.apply(
    lambda r: get_previous_strong(r, 2),
    axis=1
)


# ============================================================
# 表示用
# ============================================================

print()
print("=" * 80)
print("RESULT")
print("=" * 80)

print()
print("対象島数")
print("-" * 80)

print(f"total islands: {len(result)}")
print(
    f"strong islands: "
    f"{int(result['strong'].sum())}"
)


# ============================================================
# 1. 前日平均
# ============================================================

print()
print("=" * 80)
print("1. PREVIOUS DAY")
print("=" * 80)

for col in [
    "prev_star_rate",
    "prev_circle_plus_rate",
    "prev_triangle_plus_rate",
    "prev_avg_games",
]:

    print()
    print(col)

    for label, flag in [
        ("strong", True),
        ("normal", False),
    ]:

        values = result.loc[
            result["strong"] == flag,
            col
        ].dropna()

        if len(values) == 0:
            print(
                f"  {label}: N/A"
            )
        else:
            print(
                f"  {label}: "
                f"{values.mean():.2f}"
            )


# ============================================================
# 2. ◎+○台数
# ============================================================

print()
print("=" * 80)
print("2. PREVIOUS ◎+○ COUNT")
print("=" * 80)

table = (
    result
    .groupby("prev_star_circle_class")
    .agg(
        total=("strong", "size"),
        strong=("strong", "sum"),
    )
)

table["rate"] = (
    table["strong"]
    /
    table["total"]
    *
    100
)

print(table)


# ============================================================
# 3. △以上台数
# ============================================================

print()
print("=" * 80)
print("3. PREVIOUS △+ COUNT")
print("=" * 80)

table2 = (
    result
    .groupby("prev_triangle_class")
    .agg(
        total=("strong", "size"),
        strong=("strong", "sum"),
    )
)

table2["rate"] = (
    table2["strong"]
    /
    table2["total"]
    *
    100
)

print(table2)


# ============================================================
# 4. 前日弱さスコア
# ============================================================

print()
print("=" * 80)
print("4. PREVIOUS WEAKNESS SCORE")
print("=" * 80)

bins = [
    -np.inf,
    0.25,
    0.40,
    0.55,
    np.inf,
]

labels = [
    "強い",
    "やや強い",
    "やや弱い",
    "弱い",
]

result["weakness_class"] = pd.cut(
    result["prev_weakness_score"],
    bins=bins,
    labels=labels
)

weak_table = (
    result
    .groupby(
        "weakness_class",
        observed=False
    )
    .agg(
        total=("strong", "size"),
        strong=("strong", "sum"),
    )
)

weak_table["rate"] = (
    weak_table["strong"]
    /
    weak_table["total"]
    *
    100
)

print(weak_table)


# ============================================================
# 5. 島間順位
# ============================================================

print()
print("=" * 80)
print("5. PREVIOUS DAY RANK")
print("=" * 80)

for col in rank_names:

    print()
    print(col)

    for label, flag in [
        ("strong", True),
        ("normal", False),
    ]:

        values = result.loc[
            result["strong"] == flag,
            col
        ].dropna()

        if len(values):
            print(
                f"  {label}: "
                f"{values.mean():.2f}"
            )


# ============================================================
# 6. 前回strongとの関係
# ============================================================

print()
print("=" * 80)
print("6. PREVIOUS STRONG")
print("=" * 80)

for col in [
    "previous_strong",
    "previous2_strong",
]:

    table3 = (
        result
        .groupby(col)
        .agg(
            total=("strong", "size"),
            strong=("strong", "sum"),
        )
    )

    table3["rate"] = (
        table3["strong"]
        /
        table3["total"]
        *
        100
    )

    print()
    print(col)
    print(table3)


# ============================================================
# 7. 組み合わせ条件
# ============================================================

print()
print("=" * 80)
print("7. COMBINATION CONDITIONS")
print("=" * 80)


conditions = {

    "◎+○ = 0台":
        result["prev_star_circle_count"] == 0,

    "◎+○ <= 1台":
        result["prev_star_circle_count"] <= 1,

    "△以上 <= 1台":
        result["prev_triangle_plus_count"] <= 1,

    "◎+○ = 0 AND △以上 <= 1":
        (
            (result["prev_star_circle_count"] == 0)
            &
            (result["prev_triangle_plus_count"] <= 1)
        ),

    "◎+○ <= 1 AND △以上 <= 2":
        (
            (result["prev_star_circle_count"] <= 1)
            &
            (result["prev_triangle_plus_count"] <= 2)
        ),

    "前回strongではない":
        result["previous_strong"] == 0,

    "前回strongなし AND ◎+○=0":
        (
            (result["previous_strong"] == 0)
            &
            (result["prev_star_circle_count"] == 0)
        ),

    "前回strongなし AND ◎+○<=1":
        (
            (result["previous_strong"] == 0)
            &
            (result["prev_star_circle_count"] <= 1)
        ),

    "前回strongなし AND ◎+○<=1 AND △以上<=2":
        (
            (result["previous_strong"] == 0)
            &
            (result["prev_star_circle_count"] <= 1)
            &
            (result["prev_triangle_plus_count"] <= 2)
        ),
}


rows = []

for name, condition in conditions.items():

    subset = result[condition]

    total = len(subset)
    strong = int(subset["strong"].sum())

    rate = (
        strong / total * 100
        if total > 0
        else np.nan
    )

    rows.append(
        {
            "condition": name,
            "total": total,
            "strong": strong,
            "rate": rate,
        }
    )

combination_table = pd.DataFrame(rows)

print(combination_table.to_string(index=False))


# ============================================================
# 8. 詳細データ
# ============================================================

detail_columns = [
    "日付",
    "島",
    "strong",

    "prev_date",
    "prev_island_size",

    "prev_star_count",
    "prev_circle_plus_count",
    "prev_triangle_plus_count",

    "prev_star_circle_count",

    "prev_star_rate",
    "prev_circle_plus_rate",
    "prev_triangle_plus_rate",

    "prev_avg_games",

    "prev_star_circle_class",
    "prev_triangle_class",

    "prev_weakness_score",
    "weakness_class",

    "prev_star_rate_rank",
    "prev_circle_plus_rate_rank",
    "prev_triangle_plus_rate_rank",
    "prev_avg_games_rank",
    "prev_rank_mean",

    "previous_strong",
    "previous2_strong",
]

detail = result[detail_columns].copy()

detail.to_csv(
    OUTPUT_DETAIL,
    index=False,
    encoding="utf-8-sig"
)


# ============================================================
# 9. サマリー保存
# ============================================================

summary_rows = []

for _, row in combination_table.iterrows():

    summary_rows.append(row.to_dict())


summary = pd.DataFrame(summary_rows)

summary.to_csv(
    OUTPUT_SUMMARY,
    index=False,
    encoding="utf-8-sig"
)


# ============================================================
# 完了
# ============================================================

print()
print("=" * 80)
print("SAVE")
print("=" * 80)

print(f"detail : {OUTPUT_DETAIL}")
print(f"summary: {OUTPUT_SUMMARY}")

print()
print("=" * 80)
print("ANALYSIS END")
print("=" * 80)