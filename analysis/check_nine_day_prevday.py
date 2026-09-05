import sqlite3
from pathlib import Path
import pandas as pd

# ============================================================
# 設定
# ============================================================

BASE_DIR = Path(__file__).resolve().parents[1]
DB_PATH = BASE_DIR / "database" / "juggler.db"
OUTPUT_DIR = BASE_DIR / "analysis" / "backtest_output"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

CURRENT_ISLAND_COUNTS = {
    "ガール島": 10,
    "ゴー島①": 10,
    "ゴー島②": 10,
    "ネオアイム島①": 8,
    "ネオアイム島②": 8,
    "ネオアイム島③": 12,
    "ネオアイム島④": 12,
    "ネオアイム島⑤": 8,
    "ハッピ島": 8,
    "ファン島①": 10,
    "ファン島②": 10,
    "マイジャグ島A": 15,
    "マイジャグ島B": 10,
    "マイジャグ島C": 10,
    "マイジャグ島D": 15,
    "ミスタ島": 10,
    "ミラクル島": 10,
}

MIN_MACHINES = 5
STRONG_ALL_RATE = 80.0


# ============================================================
# DB
# ============================================================

conn = sqlite3.connect(DB_PATH)

df = pd.read_sql_query(
    """
    SELECT
        日付,
        島,
        G数,
        評価
    FROM daily_data
    WHERE 島 IS NOT NULL
    """,
    conn
)

conn.close()

df["日付"] = pd.to_datetime(
    df["日付"],
    errors="coerce"
)

df["G数"] = pd.to_numeric(
    df["G数"],
    errors="coerce"
)

df = df.dropna(
    subset=["日付", "島"]
)


# ============================================================
# 9の日
# ============================================================

nine_dates = sorted(
    df.loc[
        df["日付"].dt.day.isin([9, 19, 29]),
        "日付"
    ].drop_duplicates()
)

print("=" * 80)
print("9 DAY PREVIOUS-DAY ANALYSIS")
print("=" * 80)

print("nine days:", len(nine_dates))
print(
    "range:",
    nine_dates[0].date(),
    "~",
    nine_dates[-1].date()
)


# ============================================================
# 9日前日の島データを作成
# ============================================================

records = []

for target_date in nine_dates:

    prev_date = target_date - pd.Timedelta(days=1)

    prev_df = df[
        df["日付"] == prev_date
    ]

    target_df = df[
        df["日付"] == target_date
    ]

    for island, current_count in CURRENT_ISLAND_COUNTS.items():

        # --------------------------------------------
        # 前日
        # --------------------------------------------

        group = prev_df[
            prev_df["島"] == island
        ]

        total = current_count

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
        circle_rate = (
            star + circle
        ) / total * 100
        triangle_rate = (
            high
        ) / total * 100

        if not group.empty:
            avg_games = group["G数"].mean()
        else:
            avg_games = 0.0

        # --------------------------------------------
        # 翌9日
        # --------------------------------------------

        target_group = target_df[
            target_df["島"] == island
        ]

        t_star = int(
            target_group["評価"].eq("◎").sum()
        )

        t_circle = int(
            target_group["評価"].eq("○").sum()
        )

        t_triangle = int(
            target_group["評価"].eq("△").sum()
        )

        target_high = (
            t_star
            + t_circle
            + t_triangle
        )

        target_high_rate = (
            target_high
            / total
            * 100
        )

        target_strong = int(
            target_high_rate >= STRONG_ALL_RATE
        )

        records.append({
            "target_date": target_date,
            "prev_date": prev_date,
            "island": island,

            "prev_star_rate": star_rate,
            "prev_circle_plus_rate": circle_rate,
            "prev_triangle_plus_rate": triangle_rate,
            "prev_avg_games": avg_games,

            "target_strong": target_strong,
        })


result = pd.DataFrame(records)


# ============================================================
# 9の日ごとの相対順位
# ============================================================

for col in [
    "prev_star_rate",
    "prev_circle_plus_rate",
    "prev_triangle_plus_rate",
    "prev_avg_games",
]:

    result[col + "_rank"] = (
        result
        .groupby("target_date")[col]
        .rank(
            method="min",
            ascending=True
        )
    )


# ============================================================
# 前日データの基本比較
# ============================================================

print()
print("=" * 80)
print("1. PREVIOUS DAY")
print("=" * 80)

strong = result[
    result["target_strong"] == 1
]

normal = result[
    result["target_strong"] == 0
]

print("strong count :", len(strong))
print("normal count :", len(normal))

for col in [
    "prev_star_rate",
    "prev_circle_plus_rate",
    "prev_triangle_plus_rate",
    "prev_avg_games",
]:

    print()
    print(col)

    print(
        " strong mean:",
        round(strong[col].mean(), 2)
    )

    print(
        " normal mean:",
        round(normal[col].mean(), 2)
    )


# ============================================================
# 相対順位
# ============================================================

print()
print("=" * 80)
print("2. PREVIOUS DAY RANK")
print("=" * 80)

for col in [
    "prev_star_rate_rank",
    "prev_circle_plus_rate_rank",
    "prev_triangle_plus_rate_rank",
    "prev_avg_games_rank",
]:

    print()
    print(col)

    print(
        " strong mean:",
        round(strong[col].mean(), 2)
    )

    print(
        " normal mean:",
        round(normal[col].mean(), 2)
    )


# ============================================================
# 下位グループのstrong率
# ============================================================

print()
print("=" * 80)
print("3. WEAK PREVIOUS DAY -> STRONG")
print("=" * 80)

metrics = [
    (
        "prev_star_rate_rank",
        "star"
    ),
    (
        "prev_circle_plus_rate_rank",
        "circle_plus"
    ),
    (
        "prev_triangle_plus_rate_rank",
        "triangle_plus"
    ),
    (
        "prev_avg_games_rank",
        "games"
    ),
]

for col, name in metrics:

    print()
    print(name)

    # 下位30%
    result["group30"] = (
        result
        .groupby("target_date")[col]
        .transform(
            lambda x: x <= max(1, round(len(x) * 0.3))
        )
    )

    x = result[
        result["group30"]
    ]

    if len(x) > 0:

        print(
            " bottom30 strong:",
            f"{int(x['target_strong'].sum())}/"
            f"{len(x)} = "
            f"{x['target_strong'].mean()*100:.2f}%"
        )

    # 下位50%
    result["group50"] = (
        result
        .groupby("target_date")[col]
        .transform(
            lambda x: x <= max(1, round(len(x) * 0.5))
        )
    )

    x = result[
        result["group50"]
    ]

    if len(x) > 0:

        print(
            " bottom50 strong:",
            f"{int(x['target_strong'].sum())}/"
            f"{len(x)} = "
            f"{x['target_strong'].mean()*100:.2f}%"
        )


# ============================================================
# 4項目すべてが下位50%
# ============================================================

print()
print("=" * 80)
print("4. ALL WEAK")
print("=" * 80)

rank_cols = [
    "prev_star_rate_rank",
    "prev_circle_plus_rate_rank",
    "prev_triangle_plus_rate_rank",
    "prev_avg_games_rank",
]

for col in rank_cols:

    result[col + "_bottom50"] = (
        result
        .groupby("target_date")[col]
        .transform(
            lambda x: x <= max(1, round(len(x) * 0.5))
        )
    )

result["all_bottom50"] = result[
    [c + "_bottom50" for c in rank_cols]
].all(axis=1)

x = result[
    result["all_bottom50"]
]

print(
    "all bottom50:",
    f"{int(x['target_strong'].sum())}/"
    f"{len(x)} = "
    f"{x['target_strong'].mean()*100:.2f}%"
)


# ============================================================
# 5. 前日「◎0・○0・△少数」
# ============================================================

print()
print("=" * 80)
print("5. PREVIOUS DAY LOW OUTPUT")
print("=" * 80)

conditions = {
    "star0": result["prev_star_rate"] == 0,
    "circle0": result["prev_circle_plus_rate"] == 0,
    "triangle_le20": result["prev_triangle_plus_rate"] <= 20,
    "games_le3000": result["prev_avg_games"] <= 3000,
}

for name, cond in conditions.items():

    x = result[cond]

    print(
        name,
        ":",
        f"{int(x['target_strong'].sum())}/"
        f"{len(x)} = "
        f"{x['target_strong'].mean()*100:.2f}%"
        if len(x) > 0
        else "no data"
    )


# ============================================================
# CSV
# ============================================================

detail_path = (
    OUTPUT_DIR
    / "nine_day_prevday_analysis.csv"
)

result.to_csv(
    detail_path,
    index=False,
    encoding="utf-8-sig"
)

print()
print("=" * 80)
print("SAVED")
print("=" * 80)
print(detail_path)