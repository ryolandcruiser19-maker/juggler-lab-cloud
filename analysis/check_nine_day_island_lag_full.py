from pathlib import Path
import sqlite3
import pandas as pd


# ============================================================
# 設定
# ============================================================

DB_PATH = Path("database/juggler.db")
OUT_DIR = Path("analysis/backtest_output")

START_DATE = "2025-12-01"
CURRENT_DATE = "2026-08-15"

STRONG_RATE = 80.0
CANDIDATE_RATE = 70.0


# ============================================================
# DB読み込み
# ============================================================

print("=" * 80)
print("9の日 島ラグ分析（簡易データ含む・現在島台数固定）")
print("=" * 80)

conn = sqlite3.connect(DB_PATH)

df = pd.read_sql_query(
    """
    SELECT
        日付,
        島,
        評価
    FROM daily_data
    WHERE 日付 >= ?
      AND 島 IS NOT NULL
    """,
    conn,
    params=[START_DATE],
)

conn.close()

df["日付"] = pd.to_datetime(df["日付"], errors="coerce")

print()
print("DB読み込み")
print("-" * 80)
print("rows :", len(df))
print("date :", df["日付"].min().date(), "～", df["日付"].max().date())


# ============================================================
# 9の日抽出
# ============================================================

df9 = df[df["日付"].dt.day.isin([9, 19, 29])].copy()

dates = sorted(df9["日付"].dropna().unique())

print()
print("9の日")
print("-" * 80)
print("対象9の日数:", len(dates))

for i, d in enumerate(dates, 1):
    n = df9[df9["日付"] == d]["島"].nunique()
    print(f"{i:2d}: {pd.Timestamp(d).date()}  島数={n}")


# ============================================================
# 現在の島台数
# ============================================================

current = df[df["日付"] == pd.Timestamp(CURRENT_DATE)].copy()

if current.empty:
    raise RuntimeError(
        f"{CURRENT_DATE} のデータがありません。"
    )

current_island_counts = (
    current.groupby("島")
    .size()
    .rename("current_machines")
)

print()
print("現在島台数")
print("-" * 80)

for island, count in current_island_counts.items():
    print(f"{island:15s} {count:3d}台")


# ============================================================
# 島一覧
# ============================================================

islands = sorted(current_island_counts.index.tolist())


# ============================================================
# 各9の日 × 島を再構築
#
# ◎ ○ △ = △以上
# × － = 低設定
#
# 「未記録台」は現在島台数との差分として×扱い
# ============================================================

records = []

positive = {"◎", "○", "△"}

for date in dates:

    day = df9[df9["日付"] == date]

    for island in islands:

        current_count = int(current_island_counts[island])

        group = day[day["島"] == island]

        # 実際に記録されていた評価
        observed_count = len(group)

        high_count = int(
            group["評価"].isin(positive).sum()
        )

        # 現在島台数を分母固定
        high_rate = (
            high_count / current_count * 100
            if current_count > 0
            else 0.0
        )

        # 判定
        if high_rate >= STRONG_RATE:
            strong = 1
            candidate = 1
        elif high_rate >= CANDIDATE_RATE:
            strong = 0
            candidate = 1
        else:
            strong = 0
            candidate = 0

        records.append({
            "日付": date,
            "島": island,
            "current_machines": current_count,
            "observed_count": observed_count,
            "unrecorded_count": max(
                current_count - observed_count,
                0
            ),
            "high_count": high_count,
            "high_rate": high_rate,
            "strong": strong,
            "candidate": candidate,
        })


actual = pd.DataFrame(records)

actual["日付"] = pd.to_datetime(actual["日付"])

actual = actual.sort_values(
    ["日付", "島"]
).reset_index(drop=True)


# ============================================================
# 診断
# ============================================================

print()
print("=" * 80)
print("再構築結果")
print("=" * 80)

print("行数:", len(actual))
print("strong:", actual["strong"].sum())
print("candidate:", actual["candidate"].sum())

print()
print("9の日別 strong")
print(
    actual.groupby("日付")["strong"]
    .sum()
    .to_string()
)

print()
print("9の日別 candidate")
print(
    actual.groupby("日付")["candidate"]
    .sum()
    .to_string()
)


# ============================================================
# lag1～lag3
# ============================================================

lag_records = []

for island in islands:

    island_df = (
        actual[actual["島"] == island]
        .sort_values("日付")
        .reset_index(drop=True)
    )

    for i in range(3, len(island_df)):

        row = island_df.iloc[i]

        lag1 = island_df.iloc[i - 1]
        lag2 = island_df.iloc[i - 2]
        lag3 = island_df.iloc[i - 3]

        lag_records.append({
            "日付": row["日付"],
            "島": island,

            "strong": int(row["strong"]),
            "candidate": int(row["candidate"]),

            "lag1_strong": int(lag1["strong"]),
            "lag1_candidate": int(lag1["candidate"]),

            "lag2_strong": int(lag2["strong"]),
            "lag2_candidate": int(lag2["candidate"]),

            "lag3_strong": int(lag3["strong"]),
            "lag3_candidate": int(lag3["candidate"]),

            "strong_last3":
                int(
                    lag1["strong"]
                    + lag2["strong"]
                    + lag3["strong"]
                ),
        })


lag = pd.DataFrame(lag_records)


# ============================================================
# A～E
# ============================================================

print()
print("=" * 80)
print("A～E lag単独分析")
print("=" * 80)


def show_lag(df, col):

    print()
    print(f"[{col}]")

    for value in [0, 1]:

        x = df[df[col] == value]

        if len(x) == 0:
            print(f"  {col}={value} : データなし")
            continue

        hit = int(x["strong"].sum())
        total = len(x)
        rate = hit / total * 100

        print(
            f"  {col}={value} : "
            f"{hit}/{total} = {rate:.2f}%"
        )


show_lag(lag, "lag1_strong")
show_lag(lag, "lag2_strong")
show_lag(lag, "lag3_strong")

print()
print("candidate履歴 → 今回strong")

show_lag(lag, "lag1_candidate")
show_lag(lag, "lag2_candidate")
show_lag(lag, "lag3_candidate")


# ============================================================
# F strong組み合わせ
# ============================================================

print()
print("=" * 80)
print("F. lag1 × lag2 × lag3")
print("=" * 80)

for a in [0, 1]:
    for b in [0, 1]:
        for c in [0, 1]:

            x = lag[
                (lag["lag1_strong"] == a)
                & (lag["lag2_strong"] == b)
                & (lag["lag3_strong"] == c)
            ]

            if len(x) == 0:
                print(f"  {a},{b},{c} : データなし")
                continue

            hit = int(x["strong"].sum())
            total = len(x)

            print(
                f"  {a},{b},{c} : "
                f"{hit}/{total} = "
                f"{hit / total * 100:.2f}%"
            )


# ============================================================
# 直近3回のstrong回数
# ============================================================

print()
print("=" * 80)
print("直近3回 strong回数")
print("=" * 80)

for n in [0, 1, 2, 3]:

    x = lag[lag["strong_last3"] == n]

    if len(x) == 0:
        print(f"  {n}回 : データなし")
        continue

    hit = int(x["strong"].sum())
    total = len(x)

    print(
        f"  {n}回 : "
        f"{hit}/{total} = "
        f"{hit / total * 100:.2f}%"
    )


# ============================================================
# 投入間隔
# ============================================================

print()
print("=" * 80)
print("投入間隔")
print("=" * 80)

interval_records = []

for island in islands:

    x = actual[
        actual["島"] == island
    ].sort_values("日付").reset_index(drop=True)

    last_strong_index = None

    for i in range(len(x)):

        if x.iloc[i]["strong"] == 1:

            if last_strong_index is not None:

                empty = (
                    i
                    - last_strong_index
                    - 1
                )

                interval_records.append({
                    "島": island,
                    "empty_nine_days": empty,
                })

            last_strong_index = i


interval = pd.DataFrame(interval_records)

if not interval.empty:

    print(
        interval["empty_nine_days"]
        .value_counts()
        .sort_index()
        .to_string()
    )

else:

    print("データなし")


# ============================================================
# 島別集計
# ============================================================

summary = (
    actual.groupby("島")
    .agg(
        days=("日付", "count"),
        strong=("strong", "sum"),
        candidate=("candidate", "sum"),
        avg_high_rate=("high_rate", "mean"),
    )
    .reset_index()
)

summary["strong_rate"] = (
    summary["strong"]
    / summary["days"]
    * 100
)

summary["candidate_rate"] = (
    summary["candidate"]
    / summary["days"]
    * 100
)

summary = summary.sort_values(
    "strong_rate",
    ascending=False
)


# ============================================================
# 保存
# ============================================================

OUT_DIR.mkdir(
    parents=True,
    exist_ok=True
)

actual_path = (
    OUT_DIR /
    "nine_day_island_actual_full_period.csv"
)

lag_path = (
    OUT_DIR /
    "nine_day_island_lag_full_period.csv"
)

summary_path = (
    OUT_DIR /
    "nine_day_island_lag_full_summary.csv"
)

actual.to_csv(
    actual_path,
    index=False,
    encoding="utf-8-sig"
)

lag.to_csv(
    lag_path,
    index=False,
    encoding="utf-8-sig"
)

summary.to_csv(
    summary_path,
    index=False,
    encoding="utf-8-sig"
)


print()
print("=" * 80)
print("保存完了")
print("=" * 80)

print("actual :", actual_path)
print("lag    :", lag_path)
print("summary:", summary_path)