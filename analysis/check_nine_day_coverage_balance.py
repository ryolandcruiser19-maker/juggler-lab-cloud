"""
9の日 全台系判定バランス検証

目的:
    「9の日には最低1島は全台系がある」という前提に対して、
    各判定基準がどの程度その島を拾えるかを検証する。

重要:
    ・現在の島台数を分母として固定
    ・記録がない台は × 扱い
    ・日付×島×台番号は1台1レコードに正規化
    ・簡易データ期間も含める
"""

import sqlite3
from pathlib import Path
import pandas as pd


# ============================================================
# PATH
# ============================================================

ROOT = Path(__file__).resolve().parents[1]
DB_PATH = ROOT / "database" / "juggler.db"
OUT_DIR = ROOT / "analysis" / "backtest_output"
OUT_DIR.mkdir(parents=True, exist_ok=True)


# ============================================================
# 現在の島台数
# ============================================================

ISLAND_SIZES = {
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


# ============================================================
# 判定基準
# ============================================================

RULES = {
    "R1_現行strong": {
        "star": 0,
        "circle_plus": 0,
        "triangle_plus": 80,
    },

    "R2_○重視": {
        "star": 0,
        "circle_plus": 60,
        "triangle_plus": 80,
    },

    "R3_○＋◎": {
        "star": 30,
        "circle_plus": 60,
        "triangle_plus": 80,
    },

    "R4_強め": {
        "star": 40,
        "circle_plus": 60,
        "triangle_plus": 80,
    },

    "R5_かなり強め": {
        "star": 30,
        "circle_plus": 70,
        "triangle_plus": 80,
    },

    "R6_◎重視": {
        "star": 40,
        "circle_plus": 70,
        "triangle_plus": 80,
    },
}


# ============================================================
# DB読み込み
# ============================================================

print("=" * 80)
print("9の日 全台系判定バランス検証")
print("=" * 80)

print()
print("DB読み込み")
print("-" * 80)

conn = sqlite3.connect(DB_PATH)

df = pd.read_sql_query(
    """
    SELECT
        日付,
        台番号,
        島,
        評価
    FROM daily_data
    WHERE 日付 IS NOT NULL
      AND 島 IS NOT NULL
      AND 台番号 IS NOT NULL
    """,
    conn,
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

df["評価"] = df["評価"].fillna("×")

df["評価"] = df["評価"].replace(
    {
        "－": "×",
        "-": "×",
        "": "×",
    }
)


# ============================================================
# 9の日抽出
# ============================================================

df = df[df["日付"].dt.day.isin([9, 19, 29])].copy()

df = df[
    df["島"].isin(ISLAND_SIZES)
].copy()

nine_dates = sorted(
    df["日付"].dropna().unique()
)

print()
print("9の日")
print("-" * 80)
print("対象日数:", len(nine_dates))

for i, date in enumerate(nine_dates, 1):
    print(
        f"{i:2d}: "
        f"{date.strftime('%Y-%m-%d')}"
    )


# ============================================================
# 日付×島×台番号を1レコード化
#
# 同一台に複数レコードがある場合は、
# より高い評価を採用
# ============================================================

rank = {
    "×": 0,
    "△": 1,
    "○": 2,
    "◎": 3,
}

df["_rank"] = df["評価"].map(rank).fillna(0)

df = (
    df.sort_values(
        ["日付", "島", "台番号", "_rank"]
    )
    .drop_duplicates(
        ["日付", "島", "台番号"],
        keep="last"
    )
)


# ============================================================
# 現在島台数固定で集計
# ============================================================

results = []

for date in nine_dates:

    day = df[df["日付"] == date]

    for island, total in ISLAND_SIZES.items():

        island_df = day[
            day["島"] == island
        ]

        # 現在島台数を分母固定
        evaluations = (
            island_df["評価"]
            .tolist()
        )

        # 足りない台は ×
        evaluations += [
            "×"
        ] * max(
            0,
            total - len(evaluations)
        )

        # 万一現在台数を超えていたら切る
        evaluations = evaluations[:total]

        star = evaluations.count("◎")
        circle = evaluations.count("○")
        triangle = evaluations.count("△")

        circle_plus = star + circle
        triangle_plus = (
            star
            + circle
            + triangle
        )

        star_rate = star / total * 100
        circle_plus_rate = (
            circle_plus / total * 100
        )
        triangle_plus_rate = (
            triangle_plus / total * 100
        )

        results.append({
            "日付": date.strftime("%Y-%m-%d"),
            "島": island,
            "台数": total,
            "◎率": star_rate,
            "○以上率": circle_plus_rate,
            "△以上率": triangle_plus_rate,
        })


result_df = pd.DataFrame(results)


# ============================================================
# 判定
# ============================================================

def judge(row, rule):

    if (
        row["◎率"] >= rule["star"]
        and row["○以上率"] >= rule["circle_plus"]
        and row["△以上率"] >= rule["triangle_plus"]
    ):
        return 1

    return 0


for name, rule in RULES.items():

    result_df[name] = result_df.apply(
        lambda r: judge(r, rule),
        axis=1
    )


# ============================================================
# 基準別分析
# ============================================================

print()
print("=" * 80)
print("判定基準別バランス")
print("=" * 80)

summary = []

for name in RULES:

    picked = result_df[
        result_df[name] == 1
    ]

    # 日ごとに最低1島拾えたか
    daily = (
        result_df
        .groupby("日付")[name]
        .sum()
    )

    covered = int(
        (daily >= 1).sum()
    )

    total_days = len(daily)

    coverage = (
        covered / total_days * 100
        if total_days
        else 0
    )

    avg_islands = (
        daily.mean()
        if len(daily)
        else 0
    )

    max_islands = (
        daily.max()
        if len(daily)
        else 0
    )

    zero_days = int(
        (daily == 0).sum()
    )

    summary.append({
        "判定基準": name,
        "該当島数": len(picked),
        "最低1島捕捉日数": covered,
        "9の日数": total_days,
        "最低1島捕捉率": coverage,
        "平均該当島数": avg_islands,
        "最大該当島数": max_islands,
        "0島の日数": zero_days,
    })

    print()
    print(name)
    print(
        f"  該当島数       : {len(picked)}"
    )
    print(
        f"  最低1島捕捉     : "
        f"{covered}/{total_days} "
        f"({coverage:.2f}%)"
    )
    print(
        f"  平均該当島数    : "
        f"{avg_islands:.2f}"
    )
    print(
        f"  最大該当島数    : "
        f"{max_islands}"
    )
    print(
        f"  0島の日数      : "
        f"{zero_days}"
    )


summary_df = pd.DataFrame(summary)


# ============================================================
# 日別比較
# ============================================================

print()
print("=" * 80)
print("日別：各判定で何島拾ったか")
print("=" * 80)

daily_summary = (
    result_df
    .groupby("日付")
    [list(RULES.keys())]
    .sum()
)

print(daily_summary.to_string())


# ============================================================
# 実績の◎・○以上・△以上分布
# ============================================================

print()
print("=" * 80)
print("9の日 島実績分布")
print("=" * 80)

print()
print("◎率")
print(
    result_df["◎率"]
    .describe()
    .to_string()
)

print()
print("○以上率")
print(
    result_df["○以上率"]
    .describe()
    .to_string()
)

print()
print("△以上率")
print(
    result_df["△以上率"]
    .describe()
    .to_string()
)


# ============================================================
# CSV保存
# ============================================================

detail_path = (
    OUT_DIR
    / "nine_day_coverage_balance_detail.csv"
)

summary_path = (
    OUT_DIR
    / "nine_day_coverage_balance_summary.csv"
)

result_df.to_csv(
    detail_path,
    index=False,
    encoding="utf-8-sig"
)

summary_df.to_csv(
    summary_path,
    index=False,
    encoding="utf-8-sig"
)


print()
print("=" * 80)
print("保存完了")
print("=" * 80)

print("detail :", detail_path)
print("summary:", summary_path)