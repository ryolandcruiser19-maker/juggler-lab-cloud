import pandas as pd
from pathlib import Path
from itertools import product

# ============================================================
# 9の日 島ラグ分析
#
# 目的:
#   各島について、前回・前々回・3回前の9の日の状態が
#   今回の「強い全台系」発生率に影響するかを検証する。
#
# 重要:
#   欠損データは「非候補=0」と扱わない。
#   判定不能として除外する。
#
#   prediction engine には接続しない独立分析。
# ============================================================

BASE_DIR = Path("analysis/backtest_output")

ACTUAL_PATH = BASE_DIR / "nine_day_island_actual.csv"

OUTPUT_LAG = BASE_DIR / "nine_day_island_lag_analysis.csv"
OUTPUT_SUMMARY = BASE_DIR / "nine_day_island_lag_summary.csv"
OUTPUT_ROTATION = BASE_DIR / "nine_day_island_rotation_analysis.csv"


# ============================================================
# CSV読み込み
# ============================================================

print("=" * 80)
print("9の日 島ラグ分析")
print("=" * 80)

print()
print("DB / CSV読み込み")
print("-" * 80)

actual = pd.read_csv(ACTUAL_PATH)

print(f"actual rows : {len(actual):,}")
print(f"actual cols : {len(actual.columns)}")

# 列名を自動検出
columns = list(actual.columns)


def find_col(candidates):
    for candidate in candidates:
        if candidate in columns:
            return candidate
    return None


date_col = find_col(["日付", "date"])
island_col = find_col(["島", "island"])
strong_col = find_col(["強い全台系フラグ", "strong_flag"])
candidate_col = find_col(["候補フラグ", "candidate_flag"])

if date_col is None:
    raise ValueError("日付列が見つかりません。")

if island_col is None:
    raise ValueError("島列が見つかりません。")

if strong_col is None:
    raise ValueError("強い全台系フラグ列が見つかりません。")

if candidate_col is None:
    raise ValueError("候補フラグ列が見つかりません。")

print()
print("使用列")
print(f"  date      = {date_col}")
print(f"  island    = {island_col}")
print(f"  strong    = {strong_col}")
print(f"  candidate = {candidate_col}")


# ============================================================
# 前処理
# ============================================================

df = actual.copy()

df[date_col] = pd.to_datetime(
    df[date_col],
    format="%Y-%m-%d",
    errors="coerce"
)

df[strong_col] = pd.to_numeric(
    df[strong_col],
    errors="coerce"
)

df[candidate_col] = pd.to_numeric(
    df[candidate_col],
    errors="coerce"
)

df = df.dropna(subset=[date_col, island_col])

df = df.sort_values([date_col, island_col]).reset_index(drop=True)

dates = sorted(df[date_col].unique())
islands = sorted(df[island_col].dropna().unique())

print()
print("=" * 80)
print("データ診断")
print("=" * 80)

print(f"対象9の日数 : {len(dates)}")
print(f"対象島数     : {len(islands)}")
print(f"日付範囲     : {dates[0].date()} ～ {dates[-1].date()}")

print()
print("9の日一覧")
for i, d in enumerate(dates, start=1):
    count = int((df[date_col] == d).sum())
    print(f"  {i:2d}: {d.date()}  島データ={count}")


# ============================================================
# 日付×島の重複チェック
# ============================================================

dup = (
    df.groupby([date_col, island_col])
      .size()
      .reset_index(name="count")
)

dup = dup[dup["count"] > 1]

print()
print("日付×島の重複")
if len(dup) == 0:
    print("  なし")
else:
    print(f"  {len(dup)}件")
    print(dup.to_string(index=False))
    raise ValueError("日付×島の重複があります。lag分析を中止します。")


# ============================================================
# lookup作成
# ============================================================

lookup = {}

for _, row in df.iterrows():
    d = row[date_col]
    island = row[island_col]

    lookup[(d, island)] = {
        "strong": row[strong_col],
        "candidate": row[candidate_col],
    }


# ============================================================
# lagデータ生成
# ============================================================

print()
print("=" * 80)
print("lag1～lag3生成")
print("=" * 80)

records = []

for current_idx in range(3, len(dates)):

    current_date = dates[current_idx]

    lag_dates = {
        1: dates[current_idx - 1],
        2: dates[current_idx - 2],
        3: dates[current_idx - 3],
    }

    for island in islands:

        current_key = (current_date, island)

        if current_key not in lookup:
            continue

        current = lookup[current_key]

        # 今回の実績が判定不能なら対象外
        if pd.isna(current["strong"]) or pd.isna(current["candidate"]):
            continue

        record = {
            "current_date": current_date.strftime("%Y-%m-%d"),
            "island": island,
            "target_strong": int(current["strong"]),
            "target_candidate": int(current["candidate"]),
        }

        valid_history = True

        for lag in [1, 2, 3]:

            hist_key = (lag_dates[lag], island)

            if hist_key not in lookup:
                record[f"lag{lag}_strong"] = pd.NA
                record[f"lag{lag}_candidate"] = pd.NA
                valid_history = False
                continue

            hist = lookup[hist_key]

            record[f"lag{lag}_strong"] = (
                int(hist["strong"])
                if not pd.isna(hist["strong"])
                else pd.NA
            )

            record[f"lag{lag}_candidate"] = (
                int(hist["candidate"])
                if not pd.isna(hist["candidate"])
                else pd.NA
            )

        # lag3まで全部判定可能か
        record["lag3_complete"] = int(valid_history)

        records.append(record)


lag_df = pd.DataFrame(records)

for col in [
    "lag1_strong",
    "lag2_strong",
    "lag3_strong",
    "lag1_candidate",
    "lag2_candidate",
    "lag3_candidate",
]:
    lag_df[col] = pd.to_numeric(lag_df[col], errors="coerce").astype("Int64")


print(f"lag分析対象レコード : {len(lag_df):,}")

print()
print("lag3完全判定可能")
print(
    lag_df["lag3_complete"]
    .value_counts()
    .sort_index()
    .to_string()
)


# ============================================================
# lag分析用関数
# ============================================================

def calc_rate_table(
    data,
    condition_col,
    target_col,
    label
):
    rows = []

    for state in [0, 1]:

        subset = data[
            data[condition_col].notna() &
            (data[condition_col] == state) &
            data[target_col].notna()
        ]

        n = len(subset)
        hits = int(subset[target_col].sum()) if n else 0
        rate = hits / n * 100 if n else None

        rows.append({
            "analysis": label,
            "condition": condition_col,
            "state": state,
            "n": n,
            "target_hits": hits,
            "target_rate_pct": rate,
        })

    return rows


# ============================================================
# A～E
# ============================================================

print()
print("=" * 80)
print("A～E lag単独分析")
print("=" * 80)

summary_rows = []

for lag in [1, 2, 3]:

    condition = f"lag{lag}_strong"

    rows = calc_rate_table(
        lag_df,
        condition,
        "target_strong",
        f"lag{lag} strong → 今回strong"
    )

    summary_rows.extend(rows)

    print()
    print(f"[lag{lag}]")

    for row in rows:
        print(
            f"  {condition}={row['state']} : "
            f"{row['target_hits']}/{row['n']} "
            f"= {row['target_rate_pct']:.2f}%"
            if row["target_rate_pct"] is not None
            else
            f"  {condition}={row['state']} : データなし"
        )


# ============================================================
# candidate履歴
# ============================================================

print()
print("=" * 80)
print("candidate履歴 → 今回strong")
print("=" * 80)

for lag in [1, 2, 3]:

    condition = f"lag{lag}_candidate"

    rows = calc_rate_table(
        lag_df,
        condition,
        "target_strong",
        f"lag{lag} candidate → 今回strong"
    )

    summary_rows.extend(rows)

    print()
    print(f"[lag{lag}_candidate]")

    for row in rows:
        print(
            f"  {condition}={row['state']} : "
            f"{row['target_hits']}/{row['n']} "
            f"= {row['target_rate_pct']:.2f}%"
            if row["target_rate_pct"] is not None
            else
            f"  {condition}={row['state']} : データなし"
        )


# ============================================================
# F: 8パターン
# ============================================================

print()
print("=" * 80)
print("F. lag1 × lag2 × lag3 組み合わせ")
print("=" * 80)

pattern_rows = []

complete = lag_df[
    lag_df[
        [
            "lag1_strong",
            "lag2_strong",
            "lag3_strong",
            "target_strong",
        ]
    ].notna().all(axis=1)
].copy()

for pattern in product([0, 1], repeat=3):

    l1, l2, l3 = pattern

    subset = complete[
        (complete["lag1_strong"] == l1) &
        (complete["lag2_strong"] == l2) &
        (complete["lag3_strong"] == l3)
    ]

    n = len(subset)
    hits = int(subset["target_strong"].sum()) if n else 0
    rate = hits / n * 100 if n else None

    pattern_text = f"{l1},{l2},{l3}"

    pattern_rows.append({
        "analysis": "lag_pattern",
        "pattern": pattern_text,
        "n": n,
        "target_strong_hits": hits,
        "target_strong_rate_pct": rate,
    })

    if rate is None:
        print(
            f"  {pattern_text} : データなし"
        )
    else:
        print(
            f"  {pattern_text} : "
            f"{hits}/{n} = {rate:.2f}%"
        )


# ============================================================
# candidate組み合わせ
# ============================================================

print()
print("=" * 80)
print("F2. candidate履歴 組み合わせ")
print("=" * 80)

candidate_pattern_rows = []

complete_candidate = lag_df[
    lag_df[
        [
            "lag1_candidate",
            "lag2_candidate",
            "lag3_candidate",
            "target_strong",
        ]
    ].notna().all(axis=1)
].copy()

for pattern in product([0, 1], repeat=3):

    l1, l2, l3 = pattern

    subset = complete_candidate[
        (complete_candidate["lag1_candidate"] == l1) &
        (complete_candidate["lag2_candidate"] == l2) &
        (complete_candidate["lag3_candidate"] == l3)
    ]

    n = len(subset)
    hits = int(subset["target_strong"].sum()) if n else 0
    rate = hits / n * 100 if n else None

    pattern_text = f"{l1},{l2},{l3}"

    candidate_pattern_rows.append({
        "analysis": "candidate_pattern",
        "pattern": pattern_text,
        "n": n,
        "target_strong_hits": hits,
        "target_strong_rate_pct": rate,
    })

    if rate is None:
        print(
            f"  {pattern_text} : データなし"
        )
    else:
        print(
            f"  {pattern_text} : "
            f"{hits}/{n} = {rate:.2f}%"
        )


# ============================================================
# 継続・回避・復活・空け回数
# ============================================================

print()
print("=" * 80)
print("ローテーション分析")
print("=" * 80)

rotation_rows = []

# 全時系列を島ごとに確認
for island in islands:

    island_df = df[
        df[island_col] == island
    ].sort_values(date_col)

    state_by_date = {}

    for _, row in island_df.iterrows():

        value = row[strong_col]

        if pd.isna(value):
            state_by_date[row[date_col]] = None
        else:
            state_by_date[row[date_col]] = int(value)

    for i in range(1, len(dates)):

        prev_date = dates[i - 1]
        current_date = dates[i]

        prev_state = state_by_date.get(prev_date)
        current_state = state_by_date.get(current_date)

        if prev_state is None or current_state is None:
            continue

        if prev_state == 1 and current_state == 1:
            transition = "継続"
        elif prev_state == 1 and current_state == 0:
            transition = "回避"
        elif prev_state == 0 and current_state == 1:
            transition = "復活"
        else:
            transition = "非投入継続"

        rotation_rows.append({
            "island": island,
            "previous_date": prev_date.strftime("%Y-%m-%d"),
            "current_date": current_date.strftime("%Y-%m-%d"),
            "previous_strong": prev_state,
            "current_strong": current_state,
            "transition": transition,
        })


rotation_df = pd.DataFrame(rotation_rows)

print()
print("遷移タイプ別")

if len(rotation_df):

    transition_summary = (
        rotation_df
        .groupby("transition")
        .size()
        .reset_index(name="count")
        .sort_values("count", ascending=False)
    )

    print(
        transition_summary.to_string(index=False)
    )

    print()
    print("投入後の復活間隔")

    # 各島のstrong日を時系列で取得
    gap_rows = []

    for island in islands:

        island_df = df[
            (df[island_col] == island) &
            (df[strong_col] == 1)
        ].copy()

        island_dates = sorted(
            island_df[date_col].dropna().unique()
        )

        for j in range(1, len(island_dates)):

            previous = island_dates[j - 1]
            current = island_dates[j]

            # 9の日何回空いているか
            try:
                previous_idx = dates.index(previous)
                current_idx = dates.index(current)
                gap = current_idx - previous_idx - 1
            except ValueError:
                continue

            gap_rows.append({
                "island": island,
                "previous_strong_date": previous.strftime("%Y-%m-%d"),
                "current_strong_date": current.strftime("%Y-%m-%d"),
                "empty_nine_days": gap,
            })

    gap_df = pd.DataFrame(gap_rows)

    if len(gap_df):
        gap_summary = (
            gap_df
            .groupby("empty_nine_days")
            .size()
            .reset_index(name="count")
            .sort_values("empty_nine_days")
        )

        print(
            gap_summary.to_string(index=False)
        )
    else:
        gap_df = pd.DataFrame(
            columns=[
                "island",
                "previous_strong_date",
                "current_strong_date",
                "empty_nine_days",
            ]
        )

else:
    transition_summary = pd.DataFrame()
    gap_df = pd.DataFrame()


# ============================================================
# CSV保存
# ============================================================

print()
print("=" * 80)
print("CSV保存")
print("=" * 80)

lag_df.to_csv(
    OUTPUT_LAG,
    index=False,
    encoding="utf-8-sig"
)

summary_df = pd.DataFrame(summary_rows)

if len(pattern_rows):
    pattern_df = pd.DataFrame(pattern_rows)
    summary_df = pd.concat(
        [summary_df, pattern_df],
        ignore_index=True,
        sort=False
    )

if len(candidate_pattern_rows):
    candidate_pattern_df = pd.DataFrame(candidate_pattern_rows)
    summary_df = pd.concat(
        [summary_df, candidate_pattern_df],
        ignore_index=True,
        sort=False
    )

summary_df.to_csv(
    OUTPUT_SUMMARY,
    index=False,
    encoding="utf-8-sig"
)

rotation_df.to_csv(
    OUTPUT_ROTATION,
    index=False,
    encoding="utf-8-sig"
)

print(f"lag詳細     : {OUTPUT_LAG}")
print(f"lag集計     : {OUTPUT_SUMMARY}")
print(f"rotation    : {OUTPUT_ROTATION}")

print()
print("=" * 80)
print("分析終了")
print("=" * 80)
