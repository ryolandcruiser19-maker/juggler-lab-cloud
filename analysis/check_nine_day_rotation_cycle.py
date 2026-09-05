# -*- coding: utf-8 -*-

"""
9の日 全台系島ローテーション・サイクル検証

目的
----
9日 → 19日 → 29日 → 翌月9日
という連続した「9の日シリーズ」において、

1. 9→19
2. 19→29
3. 29→翌月9

の島移動を分離して検証する。

さらに、
- 前回 → 今回
- 2回前 → 今回
- 3回前 → 今回

の再登場率を確認し、
「前回とは違う島にするが、過去に使った島は再利用する」
というローテーション仮説を検証する。

注意
----
このスクリプトは予測ロジックを変更しない。
実績データのみを分析する。
"""

import sqlite3
from pathlib import Path
from collections import defaultdict

import pandas as pd
import numpy as np


# ============================================================
# 設定
# ============================================================

BASE_DIR = Path(
    r"C:\Users\sphs4\OneDrive\デスクトップ\ジャグラーラボ"
)

DB_PATH = BASE_DIR / "database" / "juggler.db"

OUTPUT_DIR = BASE_DIR / "analysis" / "backtest_output"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

START_DATE = "2026-03-01"


# ============================================================
# 共通
# ============================================================

def print_title(text):
    print()
    print("=" * 80)
    print(text)
    print("=" * 80)


def normalize_island(value):
    if pd.isna(value):
        return None

    value = str(value).strip()

    if value == "":
        return None

    return value


# ============================================================
# DB読み込み
# ============================================================

def load_daily_data():
    if not DB_PATH.exists():
        raise FileNotFoundError(f"DBが見つかりません: {DB_PATH}")

    conn = sqlite3.connect(DB_PATH)

    try:
        df = pd.read_sql_query(
            """
            SELECT
                日付,
                島,
                評価
            FROM daily_data
            WHERE 日付 >= ?
            ORDER BY 日付
            """,
            conn,
            params=[START_DATE],
        )
    finally:
        conn.close()

    if df.empty:
        raise ValueError("daily_dataからデータを取得できませんでした。")

    df["日付"] = pd.to_datetime(df["日付"], errors="coerce")
    df["島"] = df["島"].apply(normalize_island)
    df["評価"] = df["評価"].astype(str).str.strip()

    df = df.dropna(subset=["日付", "島"])

    return df


# ============================================================
# 9の日抽出
# ============================================================

def get_nine_days(df):

    dates = sorted(df["日付"].dt.normalize().unique())

    nine_days = []

    for d in dates:
        day = pd.Timestamp(d).day

        if day in (9, 19, 29):
            nine_days.append(pd.Timestamp(d))

    return nine_days


# ============================================================
# 島別実績判定
# ============================================================

def build_island_actual(df, date):

    target = df[df["日付"].dt.normalize() == date].copy()

    if target.empty:
        return {}

    result = {}

    for island, group in target.groupby("島"):

        total = len(group)

        strong = int((group["評価"] == "◎").sum())

        candidate = int(
            group["評価"].isin(["◎", "○"]).sum()
        )

        # 強い全台系
        #
        # ここでは既存のジャグラーラボ分析に合わせ、
        # 島内の全台が◎または高評価であることを
        # 単純な「強い全台系」として判定しない。
        #
        # 既存分析との比較を優先し、
        # ◎率50%以上を強い全台系の目安とする。
        #
        # ※必要なら後で閾値を既存ロジックに完全一致させる。
        strong_rate = strong / total if total > 0 else 0
        candidate_rate = candidate / total if total > 0 else 0

        if strong_rate >= 0.50:
            actual_strong = True
        else:
            actual_strong = False

        if candidate_rate >= 0.50:
            actual_candidate = True
        else:
            actual_candidate = False

        result[island] = {
            "台数": total,
            "◎台数": strong,
            "○以上台数": candidate,
            "◎率": strong_rate * 100,
            "○以上率": candidate_rate * 100,
            "強い全台系": actual_strong,
            "候補以上": actual_candidate,
        }

    return result


# ============================================================
# 9の日シリーズ作成
# ============================================================

def build_nine_day_series(df):

    nine_days = get_nine_days(df)

    records = []

    for i, date in enumerate(nine_days):

        if date.day == 9:
            kind = "9日"
        elif date.day == 19:
            kind = "19日"
        elif date.day == 29:
            kind = "29日"
        else:
            kind = ""

        records.append(
            {
                "index": i,
                "date": date,
                "kind": kind,
            }
        )

    return pd.DataFrame(records)


# ============================================================
# 実績島セット
# ============================================================

def build_actual_sets(df, series):

    actual_sets = {}

    for _, row in series.iterrows():

        date = row["date"]

        actual = build_island_actual(df, date)

        strong_islands = sorted(
            [
                island
                for island, data in actual.items()
                if data["強い全台系"]
            ]
        )

        candidate_islands = sorted(
            [
                island
                for island, data in actual.items()
                if data["候補以上"]
            ]
        )

        actual_sets[date] = {
            "strong": set(strong_islands),
            "candidate": set(candidate_islands),
            "actual": actual,
        }

    return actual_sets


# ============================================================
# 連続9の日比較
# ============================================================

def compare_consecutive(series, actual_sets):

    records = []

    for i in range(1, len(series)):

        prev = series.iloc[i - 1]
        curr = series.iloc[i]

        prev_date = prev["date"]
        curr_date = curr["date"]

        prev_strong = actual_sets[prev_date]["strong"]
        curr_strong = actual_sets[curr_date]["strong"]

        overlap = prev_strong & curr_strong

        union = prev_strong | curr_strong

        if len(union) > 0:
            overlap_rate = len(overlap) / len(union) * 100
        else:
            overlap_rate = 0.0

        if len(curr_strong) > 0:
            current_from_previous_rate = (
                len(overlap) / len(curr_strong) * 100
            )
        else:
            current_from_previous_rate = 0.0

        if len(prev_strong) > 0:
            previous_to_current_rate = (
                len(overlap) / len(prev_strong) * 100
            )
        else:
            previous_to_current_rate = 0.0

        records.append(
            {
                "前回日": prev_date.strftime("%Y-%m-%d"),
                "前回種別": prev["kind"],
                "今回日": curr_date.strftime("%Y-%m-%d"),
                "今回種別": curr["kind"],
                "前回強い全台系島数": len(prev_strong),
                "今回強い全台系島数": len(curr_strong),
                "重複島数": len(overlap),
                "重複島": " / ".join(sorted(overlap)),
                "Jaccard重複率": round(overlap_rate, 2),
                "今回→前回継続率": round(
                    current_from_previous_rate, 2
                ),
                "前回→今回継続率": round(
                    previous_to_current_rate, 2
                ),
                "完全入替": len(overlap) == 0,
            }
        )

    return pd.DataFrame(records)


# ============================================================
# 9→19 / 19→29 / 29→9 分離
# ============================================================

def summarize_transition(df):

    if df.empty:
        return pd.DataFrame()

    rows = []

    transition_map = {
        ("9日", "19日"): "9→19",
        ("19日", "29日"): "19→29",
        ("29日", "9日"): "29→翌月9",
    }

    for (prev_kind, curr_kind), label in transition_map.items():

        subset = df[
            (df["前回種別"] == prev_kind)
            & (df["今回種別"] == curr_kind)
        ]

        if subset.empty:
            rows.append(
                {
                    "移動": label,
                    "比較回数": 0,
                    "重複回数": 0,
                    "重複率": 0.0,
                    "完全入替回数": 0,
                    "完全入替率": 0.0,
                    "平均Jaccard重複率": 0.0,
                }
            )
            continue

        overlap_count = int((subset["重複島数"] > 0).sum())
        complete_count = int(subset["完全入替"].sum())

        rows.append(
            {
                "移動": label,
                "比較回数": len(subset),
                "重複回数": overlap_count,
                "重複率": round(
                    overlap_count / len(subset) * 100,
                    2,
                ),
                "完全入替回数": complete_count,
                "完全入替率": round(
                    complete_count / len(subset) * 100,
                    2,
                ),
                "平均Jaccard重複率": round(
                    subset["Jaccard重複率"].mean(),
                    2,
                ),
            }
        )

    return pd.DataFrame(rows)


# ============================================================
# ラグ分析
# ============================================================

def build_lag_analysis(series, actual_sets):

    records = []

    for lag in [1, 2, 3]:

        for i in range(lag, len(series)):

            prev = series.iloc[i - lag]
            curr = series.iloc[i]

            prev_date = prev["date"]
            curr_date = curr["date"]

            prev_strong = actual_sets[prev_date]["strong"]
            curr_strong = actual_sets[curr_date]["strong"]

            overlap = prev_strong & curr_strong

            records.append(
                {
                    "ラグ": lag,
                    "基準日": prev_date.strftime("%Y-%m-%d"),
                    "今回日": curr_date.strftime("%Y-%m-%d"),
                    "基準種別": prev["kind"],
                    "今回種別": curr["kind"],
                    "基準強い全台系島数": len(prev_strong),
                    "今回強い全台系島数": len(curr_strong),
                    "重複島数": len(overlap),
                    "重複あり": len(overlap) > 0,
                    "重複島": " / ".join(sorted(overlap)),
                }
            )

    return pd.DataFrame(records)


def summarize_lag(lag_df):

    rows = []

    for lag in [1, 2, 3]:

        subset = lag_df[lag_df["ラグ"] == lag]

        if subset.empty:
            continue

        overlap_count = int(subset["重複あり"].sum())

        rows.append(
            {
                "ラグ": lag,
                "比較回数": len(subset),
                "重複回数": overlap_count,
                "重複率": round(
                    overlap_count / len(subset) * 100,
                    2,
                ),
            }
        )

    return pd.DataFrame(rows)


# ============================================================
# 島別ラグ分析
# ============================================================

def build_island_lag_analysis(series, actual_sets):

    islands = set()

    for date_data in actual_sets.values():
        islands.update(date_data["strong"])

    rows = []

    for island in sorted(islands):

        strong_sequence = []

        for _, row in series.iterrows():

            date = row["date"]

            strong = (
                island in actual_sets[date]["strong"]
            )

            strong_sequence.append(
                strong
            )

        total = len(strong_sequence)

        count = sum(strong_sequence)

        lag1 = 0
        lag2 = 0
        lag3 = 0

        for i in range(total):

            if not strong_sequence[i]:
                continue

            if i >= 1 and strong_sequence[i - 1]:
                lag1 += 1

            if i >= 2 and strong_sequence[i - 2]:
                lag2 += 1

            if i >= 3 and strong_sequence[i - 3]:
                lag3 += 1

        rows.append(
            {
                "島": island,
                "9の日数": total,
                "強い全台系回数": count,
                "前回も強い回数": lag1,
                "2回前も強い回数": lag2,
                "3回前も強い回数": lag3,
            }
        )

    return pd.DataFrame(rows)


# ============================================================
# 9→19→29 サイクル
# ============================================================

def build_cycle_analysis(series, actual_sets):

    records = []

    for i in range(2, len(series)):

        first = series.iloc[i - 2]
        second = series.iloc[i - 1]
        third = series.iloc[i]

        if not (
            first["kind"] == "9日"
            and second["kind"] == "19日"
            and third["kind"] == "29日"
        ):
            continue

        a = actual_sets[first["date"]]["strong"]
        b = actual_sets[second["date"]]["strong"]
        c = actual_sets[third["date"]]["strong"]

        records.append(
            {
                "9日": first["date"].strftime("%Y-%m-%d"),
                "19日": second["date"].strftime("%Y-%m-%d"),
                "29日": third["date"].strftime("%Y-%m-%d"),
                "9日→19日重複": len(a & b),
                "19日→29日重複": len(b & c),
                "9日→29日重複": len(a & c),
                "9日島": " / ".join(sorted(a)),
                "19日島": " / ".join(sorted(b)),
                "29日島": " / ".join(sorted(c)),
            }
        )

    return pd.DataFrame(records)


# ============================================================
# メイン
# ============================================================

def main():

    print_title("9の日 全台系島ローテーション・サイクル検証")

    print(f"DB: {DB_PATH}")
    print(f"分析開始日: {START_DATE}")

    df = load_daily_data()

    series = build_nine_day_series(df)

    print()
    print(f"検出9の日数: {len(series)}")

    if series.empty:
        print("9の日がありません。")
        return

    print(
        f"最初: {series.iloc[0]['date'].strftime('%Y-%m-%d')}"
    )
    print(
        f"最後: {series.iloc[-1]['date'].strftime('%Y-%m-%d')}"
    )

    actual_sets = build_actual_sets(
        df,
        series,
    )

    # --------------------------------------------------------
    # 連続比較
    # --------------------------------------------------------

    consecutive_df = compare_consecutive(
        series,
        actual_sets,
    )

    print_title("=== 連続9の日比較 ===")

    if not consecutive_df.empty:

        display_cols = [
            "前回日",
            "前回種別",
            "今回日",
            "今回種別",
            "前回強い全台系島数",
            "今回強い全台系島数",
            "重複島数",
            "重複島",
            "完全入替",
        ]

        print(
            consecutive_df[
                display_cols
            ].to_string(index=False)
        )

    # --------------------------------------------------------
    # 種別別
    # --------------------------------------------------------

    transition_df = summarize_transition(
        consecutive_df
    )

    print_title(
        "=== 9→19 / 19→29 / 29→翌月9 分離 ==="
    )

    if not transition_df.empty:
        print(
            transition_df.to_string(
                index=False
            )
        )

    # --------------------------------------------------------
    # ラグ
    # --------------------------------------------------------

    lag_df = build_lag_analysis(
        series,
        actual_sets,
    )

    lag_summary_df = summarize_lag(
        lag_df
    )

    print_title("=== ラグ別再登場率 ===")

    if not lag_summary_df.empty:
        print(
            lag_summary_df.to_string(
                index=False
            )
        )

    # --------------------------------------------------------
    # 島別
    # --------------------------------------------------------

    island_lag_df = build_island_lag_analysis(
        series,
        actual_sets,
    )

    print_title("=== 島別 ラグ別再登場状況 ===")

    if not island_lag_df.empty:
        print(
            island_lag_df.to_string(
                index=False
            )
        )

    # --------------------------------------------------------
    # 9→19→29
    # --------------------------------------------------------

    cycle_df = build_cycle_analysis(
        series,
        actual_sets,
    )

    print_title("=== 9→19→29 サイクル ===")

    if cycle_df.empty:
        print("9→19→29の完全なサイクルがありません。")
    else:
        print(
            cycle_df.to_string(
                index=False
            )
        )

    # --------------------------------------------------------
    # 総合判定
    # --------------------------------------------------------

    print_title("=== ローテーション仮説の暫定評価 ===")

    if not lag_summary_df.empty:

        lag1 = lag_summary_df[
            lag_summary_df["ラグ"] == 1
        ]

        lag2 = lag_summary_df[
            lag_summary_df["ラグ"] == 2
        ]

        lag1_rate = (
            float(lag1.iloc[0]["重複率"])
            if not lag1.empty
            else np.nan
        )

        lag2_rate = (
            float(lag2.iloc[0]["重複率"])
            if not lag2.empty
            else np.nan
        )

        print(
            f"ラグ1（前回→今回）重複率: "
            f"{lag1_rate:.2f}%"
        )

        print(
            f"ラグ2（2回前→今回）重複率: "
            f"{lag2_rate:.2f}%"
        )

        if (
            not np.isnan(lag1_rate)
            and not np.isnan(lag2_rate)
            and lag2_rate > lag1_rate
        ):
            print()
            print(
                "→ 2回前の島が前回より再登場しやすい傾向があります。"
            )
            print(
                "→ ローテーション仮説と整合します。"
            )
        else:
            print()
            print(
                "→ 現時点では明確なラグ型ローテーションは"
                "確認できません。"
            )

    print()
    print(
        "注意: サンプル数が少ないため、"
        "この結果だけでローテーションを確定しません。"
    )

    # --------------------------------------------------------
    # CSV
    # --------------------------------------------------------

    consecutive_path = (
        OUTPUT_DIR
        / "nine_day_rotation_cycle_detail.csv"
    )

    transition_path = (
        OUTPUT_DIR
        / "nine_day_rotation_cycle_summary.csv"
    )

    lag_path = (
        OUTPUT_DIR
        / "nine_day_rotation_lag_detail.csv"
    )

    lag_summary_path = (
        OUTPUT_DIR
        / "nine_day_rotation_lag_summary.csv"
    )

    island_lag_path = (
        OUTPUT_DIR
        / "nine_day_rotation_island_lag.csv"
    )

    cycle_path = (
        OUTPUT_DIR
        / "nine_day_rotation_cycle_929.csv"
    )

    consecutive_df.to_csv(
        consecutive_path,
        index=False,
        encoding="utf-8-sig",
    )

    transition_df.to_csv(
        transition_path,
        index=False,
        encoding="utf-8-sig",
    )

    lag_df.to_csv(
        lag_path,
        index=False,
        encoding="utf-8-sig",
    )

    lag_summary_df.to_csv(
        lag_summary_path,
        index=False,
        encoding="utf-8-sig",
    )

    island_lag_df.to_csv(
        island_lag_path,
        index=False,
        encoding="utf-8-sig",
    )

    cycle_df.to_csv(
        cycle_path,
        index=False,
        encoding="utf-8-sig",
    )

    print_title("=== CSV保存 ===")

    print(f"詳細: {consecutive_path}")
    print(f"種別別: {transition_path}")
    print(f"ラグ詳細: {lag_path}")
    print(f"ラグ集計: {lag_summary_path}")
    print(f"島別ラグ: {island_lag_path}")
    print(f"9→19→29: {cycle_path}")

    print()
    print("=" * 80)
    print("9の日 全台系島ローテーション・サイクル検証終了")
    print("=" * 80)


if __name__ == "__main__":
    main()