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

# 現在の島台数
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

# ============================================================
# 全台系判定
# ============================================================

MIN_MACHINES = 5

STRONG_ALL_RATE = 80.0
NORMAL_ALL_RATE = 70.0
WEAK_ALL_RATE = 60.0


# ============================================================
# DB読み込み
# ============================================================

print("=" * 80)
print("9の日 全台系 再投入・回避分析")
print("=" * 80)

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

print(f"DB rows : {len(df):,}")


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

df = df.dropna(subset=["日付", "島"])


# ============================================================
# 9の日だけ
# ============================================================

nine_df = df[
    df["日付"].dt.day.isin([9, 19, 29])
].copy()

dates = sorted(
    nine_df["日付"].drop_duplicates().tolist()
)

print(f"9の日数 : {len(dates)}")
print(
    f"期間 : {dates[0].date()} ～ {dates[-1].date()}"
)


# ============================================================
# 日付×島 実績を再構築
# 現在島台数固定
# ============================================================

records = []

for date in dates:

    day_df = nine_df[
        nine_df["日付"] == date
    ]

    for island, current_count in CURRENT_ISLAND_COUNTS.items():

        group = day_df[
            day_df["島"] == island
        ].copy()

        # ----------------------------------------
        # 現在の島台数を分母に固定
        # ----------------------------------------

        total_count = current_count

        # DBに存在した評価だけ集計
        star_count = int(
            group["評価"].eq("◎").sum()
        )

        circle_count = int(
            group["評価"].eq("○").sum()
        )

        triangle_count = int(
            group["評価"].eq("△").sum()
        )

        high_count = (
            star_count
            + circle_count
            + triangle_count
        )

        high_rate = (
            high_count
            / total_count
            * 100
        )

        star_rate = (
            star_count
            / total_count
            * 100
        )

        circle_rate = (
            circle_count
            / total_count
            * 100
        )

        # ----------------------------------------
        # 現行strong判定
        # ----------------------------------------

        if high_rate >= STRONG_ALL_RATE:
            strong = 1
        else:
            strong = 0

        # ----------------------------------------
        # candidate
        # ----------------------------------------

        if high_rate >= NORMAL_ALL_RATE:
            candidate = 1
        else:
            candidate = 0

        records.append({
            "日付": date,
            "島": island,
            "台数": total_count,
            "◎率": star_rate,
            "○以上率": star_rate + circle_rate,
            "△以上率": high_rate,
            "strong": strong,
            "candidate": candidate,
        })


actual = pd.DataFrame(records)

actual = actual.sort_values(
    ["島", "日付"]
).reset_index(drop=True)


# ============================================================
# lag生成
# ============================================================

actual["lag1_strong"] = (
    actual.groupby("島")["strong"]
    .shift(1)
)

actual["lag2_strong"] = (
    actual.groupby("島")["strong"]
    .shift(2)
)

actual["lag3_strong"] = (
    actual.groupby("島")["strong"]
    .shift(3)
)


# ============================================================
# 直近連続投入回数
# ============================================================

def consecutive_previous(row):

    values = [
        row["lag1_strong"],
        row["lag2_strong"],
        row["lag3_strong"],
    ]

    count = 0

    for v in values:
        if pd.isna(v):
            break

        if int(v) == 1:
            count += 1
        else:
            break

    return count


actual["previous_consecutive"] = actual.apply(
    consecutive_previous,
    axis=1
)


# ============================================================
# 前回投入から何回空いたか
# ============================================================

def calc_gap(group):

    result = []

    last_strong_index = None

    for i, row in enumerate(group.itertuples()):

        if last_strong_index is None:
            gap = None
        else:
            gap = i - last_strong_index - 1

        result.append(gap)

        if row.strong == 1:
            last_strong_index = i

    group = group.copy()
    group["gap_since_strong"] = result

    return group


actual = (
    actual
    .groupby("島", group_keys=False)
    .apply(calc_gap)
    .reset_index(drop=True)
)


# ============================================================
# 分析① 前回strong
# ============================================================

print()
print("=" * 80)
print("① 前回strong → 今回")
print("=" * 80)

valid = actual.dropna(
    subset=["lag1_strong"]
)

for value in [0, 1]:

    x = valid[
        valid["lag1_strong"] == value
    ]

    total = len(x)
    strong = int(x["strong"].sum())

    rate = (
        strong / total * 100
        if total
        else 0
    )

    print(
        f"前回strong={value} : "
        f"{strong}/{total} = {rate:.2f}%"
    )


# ============================================================
# 分析② 直近2回連続
# ============================================================

print()
print("=" * 80)
print("② 直近2回連続投入 → 今回")
print("=" * 80)

valid = actual.dropna(
    subset=["lag1_strong", "lag2_strong"]
).copy()

valid["previous_2"] = (
    (valid["lag1_strong"] == 1)
    &
    (valid["lag2_strong"] == 1)
)

for value in [False, True]:

    x = valid[
        valid["previous_2"] == value
    ]

    total = len(x)
    strong = int(x["strong"].sum())

    rate = (
        strong / total * 100
        if total
        else 0
    )

    print(
        f"直近2回連続={int(value)} : "
        f"{strong}/{total} = {rate:.2f}%"
    )


# ============================================================
# 分析③ 直近3回連続
# ============================================================

print()
print("=" * 80)
print("③ 直近3回連続投入 → 今回")
print("=" * 80)

valid = actual.dropna(
    subset=[
        "lag1_strong",
        "lag2_strong",
        "lag3_strong"
    ]
).copy()

valid["previous_3"] = (
    (valid["lag1_strong"] == 1)
    &
    (valid["lag2_strong"] == 1)
    &
    (valid["lag3_strong"] == 1)
)

for value in [False, True]:

    x = valid[
        valid["previous_3"] == value
    ]

    total = len(x)
    strong = int(x["strong"].sum())

    rate = (
        strong / total * 100
        if total
        else 0
    )

    print(
        f"直近3回連続={int(value)} : "
        f"{strong}/{total} = {rate:.2f}%"
    )


# ============================================================
# 分析④ 前回投入からの間隔
# ============================================================

print()
print("=" * 80)
print("④ 前回strongからの経過")
print("=" * 80)

valid = actual.dropna(
    subset=["gap_since_strong"]
)

summary = (
    valid
    .groupby("gap_since_strong")
    .agg(
        total=("strong", "count"),
        strong=("strong", "sum")
    )
)

summary["rate"] = (
    summary["strong"]
    / summary["total"]
    * 100
)

print(summary.to_string())


# ============================================================
# 分析⑤ 「前回投入後は避けるのか」
# ============================================================

print()
print("=" * 80)
print("⑤ 前回strong後の回避率")
print("=" * 80)

x = valid[
    valid["gap_since_strong"] == 0
]

if len(x) > 0:

    total = len(x)
    strong = int(x["strong"].sum())
    avoid = total - strong

    print(f"前回strong → 今回:")
    print(f"  件数       : {total}")
    print(f"  再投入     : {strong}")
    print(f"  非投入     : {avoid}")
    print(
        f"  再投入率   : "
        f"{strong / total * 100:.2f}%"
    )
    print(
        f"  回避率     : "
        f"{avoid / total * 100:.2f}%"
    )


# ============================================================
# 分析⑥ 直近3回のstrong回数
# ============================================================

print()
print("=" * 80)
print("⑥ 直近3回のstrong回数 → 今回")
print("=" * 80)

valid = actual.dropna(
    subset=[
        "lag1_strong",
        "lag2_strong",
        "lag3_strong"
    ]
).copy()

valid["recent3_count"] = (
    valid["lag1_strong"]
    + valid["lag2_strong"]
    + valid["lag3_strong"]
)

summary3 = (
    valid
    .groupby("recent3_count")
    .agg(
        total=("strong", "count"),
        strong=("strong", "sum")
    )
)

summary3["rate"] = (
    summary3["strong"]
    / summary3["total"]
    * 100
)

print(summary3.to_string())


# ============================================================
# 保存
# ============================================================

detail_path = (
    OUTPUT_DIR
    / "nine_day_reentry_analysis.csv"
)

summary_path = (
    OUTPUT_DIR
    / "nine_day_reentry_summary.csv"
)

actual.to_csv(
    detail_path,
    index=False,
    encoding="utf-8-sig"
)

summary3.to_csv(
    summary_path,
    encoding="utf-8-sig"
)

print()
print("=" * 80)
print("保存完了")
print("=" * 80)

print(f"detail : {detail_path}")
print(f"summary: {summary_path}")