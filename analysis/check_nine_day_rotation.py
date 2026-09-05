"""
ジャグラーラボ
9の日 全台系島ローテーション検証

目的:
・9日 / 19日 / 29日の全台系島を時系列で比較
・前回9の日と今回9の日で全台系島が重複する割合を確認
・前回全台系ではなかった島へ移動する傾向を確認
・同一島の連続発生率を確認
・島ごとの発生間隔を確認
・9の日の全台系島にローテーション傾向があるか検証

注意:
・予測モデルは使用しない
・prediction_scoreは使用しない
・daily_dataから9の日の島実績を再構築する
・絶対ルールではなく確率的傾向として評価する
"""

import sqlite3
from pathlib import Path

import pandas as pd


# ============================================================
# DB設定
# ============================================================

BASE_DIR = Path(__file__).resolve().parent.parent

DB_PATH = (
    BASE_DIR
    / "database"
    / "juggler.db"
)

OUTPUT_DIR = (
    BASE_DIR
    / "analysis"
    / "backtest_output"
)


# ============================================================
# 検証設定
# ============================================================

START_DATE = pd.Timestamp("2026-03-01")

# 全台系判定
#
# 強い全台系:
#   島内の◎率が基準以上
#
# 候補以上:
#   島内の◎○率が基準以上
#
# ここは既存の9の日島分析と整合させるため、
# 後から調整可能にしておく。
STRONG_RATE = 50.0
CANDIDATE_RATE = 30.0


# ============================================================
# 安全な数値変換
# ============================================================

def safe_float(value, default=0.0):

    try:

        if pd.isna(value):
            return default

        return float(value)

    except (ValueError, TypeError):

        return default


# ============================================================
# 営業日タイプ
# ============================================================

def is_nine_day(date_value):

    date = pd.to_datetime(date_value)

    return date.day in (9, 19, 29)


# ============================================================
# 日付を9の日として取得
# ============================================================

def get_nine_days(df):

    dates = sorted(
        pd.to_datetime(
            df["日付"]
        )
        .dropna()
        .dt.normalize()
        .unique()
    )

    result = [
        pd.Timestamp(d)
        for d in dates
        if d.day in (9, 19, 29)
        and pd.Timestamp(d) >= START_DATE
    ]

    return result


# ============================================================
# 島実績を再構築
# ============================================================

def build_island_actual(df, nine_days):

    records = []

    for date_value in nine_days:

        day_df = df[
            pd.to_datetime(
                df["日付"]
            ).dt.normalize()
            == date_value
        ].copy()

        if day_df.empty:
            continue

        for island, group in day_df.groupby(
            "島",
            dropna=False
        ):

            if pd.isna(island):
                continue

            island = str(island).strip()

            if not island:
                continue

            total = len(group)

            if total == 0:
                continue

            strong_count = (
                group["評価"] == "◎"
            ).sum()

            high_count = (
                group["評価"]
                .isin(["◎", "○"])
                .sum()
            )

            delta_count = (
                group["評価"]
                .isin(["◎", "○", "△"])
                .sum()
            )

            strong_rate = (
                strong_count
                / total
                * 100
            )

            high_rate = (
                high_count
                / total
                * 100
            )

            delta_rate = (
                delta_count
                / total
                * 100
            )

            avg_games = pd.to_numeric(
                group["G数"],
                errors="coerce"
            ).mean()

            avg_combined = pd.to_numeric(
                group["合成確率"],
                errors="coerce"
            ).mean()

            if pd.isna(avg_games):
                avg_games = 0.0

            if pd.isna(avg_combined):
                avg_combined = 0.0

            # ------------------------------------------------
            # 判定
            # ------------------------------------------------

            if strong_rate >= STRONG_RATE:

                judgment = "強い全台系"

            elif high_rate >= CANDIDATE_RATE:

                judgment = "全台系候補"

            else:

                judgment = "対象外"

            records.append(
                {
                    "日付": date_value.strftime(
                        "%Y-%m-%d"
                    ),
                    "島": island,
                    "台数": total,
                    "◎台数": int(strong_count),
                    "○以上台数": int(high_count),
                    "△以上台数": int(delta_count),
                    "◎率": round(
                        strong_rate,
                        2
                    ),
                    "○以上率": round(
                        high_rate,
                        2
                    ),
                    "△以上率": round(
                        delta_rate,
                        2
                    ),
                    "平均G数": round(
                        safe_float(avg_games),
                        2
                    ),
                    "平均合成確率": round(
                        safe_float(avg_combined),
                        2
                    ),
                    "判定": judgment,
                }
            )

    return pd.DataFrame(records)


# ============================================================
# 全台系島一覧を取得
# ============================================================

def get_selected_islands(
    actual_df,
    date_value,
    judgment_list
):

    target = actual_df[
        (
            actual_df["日付"]
            == date_value
        )
        &
        (
            actual_df["判定"]
            .isin(judgment_list)
        )
    ]

    return sorted(
        target["島"]
        .dropna()
        .unique()
        .tolist()
    )


# ============================================================
# 日別ローテーション分析
# ============================================================

def analyze_daily_rotation(
    actual_df,
    nine_days
):

    records = []

    for i in range(1, len(nine_days)):

        previous_date = nine_days[i - 1]
        current_date = nine_days[i]

        previous_date_str = (
            previous_date.strftime(
                "%Y-%m-%d"
            )
        )

        current_date_str = (
            current_date.strftime(
                "%Y-%m-%d"
            )
        )

        previous_strong = get_selected_islands(
            actual_df,
            previous_date_str,
            ["強い全台系"]
        )

        current_strong = get_selected_islands(
            actual_df,
            current_date_str,
            ["強い全台系"]
        )

        previous_candidate = get_selected_islands(
            actual_df,
            previous_date_str,
            ["強い全台系", "全台系候補"]
        )

        current_candidate = get_selected_islands(
            actual_df,
            current_date_str,
            ["強い全台系", "全台系候補"]
        )

        strong_overlap = sorted(
            set(previous_strong)
            & set(current_strong)
        )

        candidate_overlap = sorted(
            set(previous_candidate)
            & set(current_candidate)
        )

        # 前回強かった島が今回も強い
        if previous_strong:

            repeat_rate = (
                len(
                    set(previous_strong)
                    & set(current_strong)
                )
                /
                len(previous_strong)
                * 100
            )

        else:

            repeat_rate = 0.0

        # 今回の強い島のうち、
        # 前回も強かった島の割合
        if current_strong:

            current_from_previous_rate = (
                len(strong_overlap)
                /
                len(current_strong)
                * 100
            )

        else:

            current_from_previous_rate = 0.0

        # 全台系候補以上についても同様
        if previous_candidate:

            candidate_repeat_rate = (
                len(candidate_overlap)
                /
                len(previous_candidate)
                * 100
            )

        else:

            candidate_repeat_rate = 0.0

        if current_candidate:

            candidate_from_previous_rate = (
                len(candidate_overlap)
                /
                len(current_candidate)
                * 100
            )

        else:

            candidate_from_previous_rate = 0.0

        records.append(
            {
                "前回9の日": previous_date_str,
                "今回9の日": current_date_str,

                "前回強い全台系島数":
                    len(previous_strong),

                "今回強い全台系島数":
                    len(current_strong),

                "前回強い全台系島":
                    " / ".join(
                        previous_strong
                    ),

                "今回強い全台系島":
                    " / ".join(
                        current_strong
                    ),

                "強い全台系重複島":
                    " / ".join(
                        strong_overlap
                    ),

                "強い全台系重複島数":
                    len(strong_overlap),

                "前回→今回強い全台系継続率":
                    round(
                        repeat_rate,
                        2
                    ),

                "今回強い全台系の前回重複率":
                    round(
                        current_from_previous_rate,
                        2
                    ),

                "前回候補以上島数":
                    len(previous_candidate),

                "今回候補以上島数":
                    len(current_candidate),

                "候補以上重複島":
                    " / ".join(
                        candidate_overlap
                    ),

                "候補以上重複島数":
                    len(candidate_overlap),

                "前回→今回候補以上継続率":
                    round(
                        candidate_repeat_rate,
                        2
                    ),

                "今回候補以上の前回重複率":
                    round(
                        candidate_from_previous_rate,
                        2
                    ),
            }
        )

    return pd.DataFrame(records)


# ============================================================
# 同一島連続発生分析
# ============================================================

def analyze_consecutive_islands(
    actual_df,
    nine_days
):

    island_records = []

    islands = sorted(
        actual_df["島"]
        .dropna()
        .unique()
    )

    date_strings = [
        d.strftime("%Y-%m-%d")
        for d in nine_days
    ]

    for island in islands:

        strong_flags = []

        candidate_flags = []

        for date_value in date_strings:

            target = actual_df[
                (
                    actual_df["日付"]
                    == date_value
                )
                &
                (
                    actual_df["島"]
                    == island
                )
            ]

            if target.empty:

                strong_flags.append(False)
                candidate_flags.append(False)

                continue

            judgment = target.iloc[0]["判定"]

            strong_flags.append(
                judgment == "強い全台系"
            )

            candidate_flags.append(
                judgment
                in [
                    "強い全台系",
                    "全台系候補"
                ]
            )

        strong_occurrences = sum(
            strong_flags
        )

        candidate_occurrences = sum(
            candidate_flags
        )

        strong_consecutive = 0
        candidate_consecutive = 0

        strong_max_consecutive = 0
        candidate_max_consecutive = 0

        current_strong = 0
        current_candidate = 0

        for flag in strong_flags:

            if flag:

                current_strong += 1

                strong_max_consecutive = max(
                    strong_max_consecutive,
                    current_strong
                )

            else:

                current_strong = 0

        for flag in candidate_flags:

            if flag:

                current_candidate += 1

                candidate_max_consecutive = max(
                    candidate_max_consecutive,
                    current_candidate
                )

            else:

                current_candidate = 0

        for i in range(
            1,
            len(strong_flags)
        ):

            if (
                strong_flags[i - 1]
                and strong_flags[i]
            ):

                strong_consecutive += 1

        for i in range(
            1,
            len(candidate_flags)
        ):

            if (
                candidate_flags[i - 1]
                and candidate_flags[i]
            ):

                candidate_consecutive += 1

        island_records.append(
            {
                "島": island,
                "9の日数": len(date_strings),
                "強い全台系回数":
                    strong_occurrences,
                "候補以上回数":
                    candidate_occurrences,
                "強い全台系連続回数":
                    strong_consecutive,
                "強い全台系最大連続":
                    strong_max_consecutive,
                "候補以上連続回数":
                    candidate_consecutive,
                "候補以上最大連続":
                    candidate_max_consecutive,
            }
        )

    return pd.DataFrame(
        island_records
    )


# ============================================================
# 9日→19日→29日の移動分析
# ============================================================

def analyze_day_cycle(
    daily_df,
    actual_df
):

    records = []

    dates = sorted(
        pd.to_datetime(
            daily_df["日付"]
        )
        .dropna()
        .dt.normalize()
        .unique()
    )

    nine_days = [
        pd.Timestamp(d)
        for d in dates
        if (
            pd.Timestamp(d).day
            in (9, 19, 29)
        )
        and pd.Timestamp(d) >= START_DATE
    ]

    for i in range(
        len(nine_days) - 1
    ):

        current = nine_days[i]
        next_date = nine_days[i + 1]

        current_day = current.day
        next_day = next_date.day

        current_str = current.strftime(
            "%Y-%m-%d"
        )

        next_str = next_date.strftime(
            "%Y-%m-%d"
        )

        current_islands = get_selected_islands(
            actual_df,
            current_str,
            ["強い全台系"]
        )

        next_islands = get_selected_islands(
            actual_df,
            next_str,
            ["強い全台系"]
        )

        overlap = sorted(
            set(current_islands)
            & set(next_islands)
        )

        moved = sorted(
            set(next_islands)
            - set(current_islands)
        )

        records.append(
            {
                "前回日": current_str,
                "前回種別": f"{current_day}の日",
                "今回日": next_str,
                "今回種別": f"{next_day}の日",
                "前回全台系島":
                    " / ".join(
                        current_islands
                    ),
                "今回全台系島":
                    " / ".join(
                        next_islands
                    ),
                "重複島":
                    " / ".join(
                        overlap
                    ),
                "新規島":
                    " / ".join(
                        moved
                    ),
                "島移動あり":
                    1 if moved else 0,
                "完全入替":
                    (
                        1
                        if (
                            current_islands
                            and next_islands
                            and not overlap
                        )
                        else 0
                    ),
            }
        )

    return pd.DataFrame(records)


# ============================================================
# 結果表示
# ============================================================

def print_results(
    actual_df,
    daily_rotation_df,
    consecutive_df,
    cycle_df
):

    print()
    print("=" * 80)
    print("=== 9の日 全台系島ローテーション検証 ===")
    print("=" * 80)

    print()
    print(
        "分析開始日:",
        START_DATE.strftime("%Y-%m-%d")
    )

    nine_dates = sorted(
        actual_df["日付"]
        .unique()
    )

    print(
        "9の日数:",
        len(nine_dates)
    )

    # --------------------------------------------------------
    # 日別実績
    # --------------------------------------------------------

    print()
    print("--- 9の日別 全台系島 ---")

    for date_value in nine_dates:

        strong = get_selected_islands(
            actual_df,
            date_value,
            ["強い全台系"]
        )

        candidate = get_selected_islands(
            actual_df,
            date_value,
            ["全台系候補"]
        )

        print(
            f"{date_value} "
            f"強い全台系: "
            f"{' / '.join(strong) if strong else '-'}"
        )

        print(
            f"{'':12}"
            f"候補: "
            f"{' / '.join(candidate) if candidate else '-'}"
        )

    # --------------------------------------------------------
    # 前回との重複
    # --------------------------------------------------------

    print()
    print("--- 前回9の日との重複 ---")

    if daily_rotation_df.empty:

        print("比較データなし")

    else:

        display_columns = [
            "前回9の日",
            "今回9の日",
            "前回強い全台系島",
            "今回強い全台系島",
            "強い全台系重複島",
            "強い全台系重複島数",
            "前回→今回強い全台系継続率",
        ]

        print(
            daily_rotation_df[
                display_columns
            ].to_string(
                index=False
            )
        )

    # --------------------------------------------------------
    # サマリー
    # --------------------------------------------------------

    print()
    print("--- ローテーション指標 ---")

    if not daily_rotation_df.empty:

        comparisons = len(
            daily_rotation_df
        )

        overlap_cases = (
            daily_rotation_df[
                "強い全台系重複島数"
            ]
            > 0
        ).sum()

        no_overlap_cases = (
            daily_rotation_df[
                "強い全台系重複島数"
            ]
            == 0
        ).sum()

        complete_change = (
            daily_rotation_df[
                "強い全台系重複島数"
            ]
            == 0
        ).sum()

        avg_repeat = (
            daily_rotation_df[
                "今回強い全台系の前回重複率"
            ]
            .mean()
        )

        print(
            "比較回数:",
            comparisons
        )

        print(
            "前回と重複あり:",
            overlap_cases,
            "/",
            comparisons,
            f"({overlap_cases / comparisons * 100:.2f}%)"
        )

        print(
            "前回と重複なし:",
            no_overlap_cases,
            "/",
            comparisons,
            f"({no_overlap_cases / comparisons * 100:.2f}%)"
        )

        print(
            "平均「今回の全台系が前回も全台系」率:",
            f"{avg_repeat:.2f}%"
        )

        print()
        print(
            "※ 重複率が低いほど、"
            "前回とは違う島へ移る傾向を示します。"
        )

    # --------------------------------------------------------
    # 連続発生
    # --------------------------------------------------------

    print()
    print("--- 島別 連続発生状況 ---")

    if not consecutive_df.empty:

        print(
            consecutive_df.sort_values(
                [
                    "強い全台系回数",
                    "強い全台系最大連続"
                ],
                ascending=False
            ).to_string(
                index=False
            )
        )

    # --------------------------------------------------------
    # 9→19→29サイクル
    # --------------------------------------------------------

    print()
    print("--- 9日→19日→29日の島移動 ---")

    if cycle_df.empty:

        print("データなし")

    else:

        print(
            cycle_df.to_string(
                index=False
            )
        )

        total = len(cycle_df)

        move_count = (
            cycle_df["島移動あり"]
            .sum()
        )

        complete_count = (
            cycle_df["完全入替"]
            .sum()
        )

        print()
        print(
            "島移動あり:",
            move_count,
            "/",
            total,
            f"({move_count / total * 100:.2f}%)"
        )

        print(
            "完全入替:",
            complete_count,
            "/",
            total,
            f"({complete_count / total * 100:.2f}%)"
        )


# ============================================================
# CSV保存
# ============================================================

def save_results(
    actual_df,
    daily_rotation_df,
    consecutive_df,
    cycle_df
):

    OUTPUT_DIR.mkdir(
        parents=True,
        exist_ok=True
    )

    actual_path = (
        OUTPUT_DIR
        / "nine_day_rotation_actual.csv"
    )

    rotation_path = (
        OUTPUT_DIR
        / "nine_day_rotation_daily.csv"
    )

    consecutive_path = (
        OUTPUT_DIR
        / "nine_day_rotation_consecutive.csv"
    )

    cycle_path = (
        OUTPUT_DIR
        / "nine_day_rotation_cycle.csv"
    )

    actual_df.to_csv(
        actual_path,
        index=False,
        encoding="utf-8-sig"
    )

    daily_rotation_df.to_csv(
        rotation_path,
        index=False,
        encoding="utf-8-sig"
    )

    consecutive_df.to_csv(
        consecutive_path,
        index=False,
        encoding="utf-8-sig"
    )

    cycle_df.to_csv(
        cycle_path,
        index=False,
        encoding="utf-8-sig"
    )

    print()
    print("=" * 80)
    print("=== CSV保存 ===")
    print("=" * 80)

    print()
    print("島実績:")
    print(actual_path)

    print("日別ローテーション:")
    print(rotation_path)

    print("島別連続発生:")
    print(consecutive_path)

    print("9→19→29サイクル:")
    print(cycle_path)


# ============================================================
# main
# ============================================================

def main():

    print("=" * 80)
    print("9の日 全台系島ローテーション検証")
    print("=" * 80)

    print()
    print("DB:", DB_PATH)

    if not DB_PATH.exists():

        print("DBがありません。")
        return

    conn = sqlite3.connect(
        DB_PATH
    )

    try:

        df = pd.read_sql(
            """
            SELECT
                日付,
                店舗,
                機種,
                台番号,
                BB,
                RB,
                G数,
                合成確率,
                評価,
                信頼度補正,
                イベント種別,
                備考,
                島
            FROM daily_data
            """,
            conn
        )

    finally:

        conn.close()

    if df.empty:

        print("daily_dataが空です。")
        return

    # --------------------------------------------------------
    # 前処理
    # --------------------------------------------------------

    df["日付"] = pd.to_datetime(
        df["日付"],
        errors="coerce"
    )

    df = df[
        df["日付"].notna()
    ].copy()

    df["日付"] = (
        df["日付"]
        .dt.normalize()
    )

    df["評価"] = (
        df["評価"]
        .fillna("")
        .astype(str)
        .str.strip()
    )

    # --------------------------------------------------------
    # 9の日取得
    # --------------------------------------------------------

    nine_days = get_nine_days(
        df
    )

    print()
    print(
        "検出9の日数:",
        len(nine_days)
    )

    if not nine_days:

        print("9の日がありません。")
        return

    print()
    print(
        "最初:",
        nine_days[0].strftime(
            "%Y-%m-%d"
        )
    )

    print(
        "最後:",
        nine_days[-1].strftime(
            "%Y-%m-%d"
        )
    )

    # --------------------------------------------------------
    # 島実績
    # --------------------------------------------------------

    actual_df = build_island_actual(
        df,
        nine_days
    )

    if actual_df.empty:

        print("島実績を作成できませんでした。")
        return

    # --------------------------------------------------------
    # ローテーション
    # --------------------------------------------------------

    daily_rotation_df = (
        analyze_daily_rotation(
            actual_df,
            nine_days
        )
    )

    # --------------------------------------------------------
    # 連続発生
    # --------------------------------------------------------

    consecutive_df = (
        analyze_consecutive_islands(
            actual_df,
            nine_days
        )
    )

    # --------------------------------------------------------
    # 9→19→29
    # --------------------------------------------------------

    cycle_df = analyze_day_cycle(
        df,
        actual_df
    )

    # --------------------------------------------------------
    # 結果
    # --------------------------------------------------------

    print_results(
        actual_df,
        daily_rotation_df,
        consecutive_df,
        cycle_df
    )

    # --------------------------------------------------------
    # 保存
    # --------------------------------------------------------

    save_results(
        actual_df,
        daily_rotation_df,
        consecutive_df,
        cycle_df
    )

    print()
    print("=" * 80)
    print("9の日 全台系島ローテーション検証終了")
    print("=" * 80)


# ============================================================
# 実行
# ============================================================

if __name__ == "__main__":
    main()