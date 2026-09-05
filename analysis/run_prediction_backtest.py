"""
ジャグラーラボ
Prediction Engine バックテスト v2

目的
------------------------------------------------------------
・通常日 / 9の日を完全分離してバックテスト
・予測対象日の営業日タイプと同じ過去営業日だけを履歴として使用
・TOP1 / TOP3 の実績確認
・TOP3スコア差と実績の関係確認

重要
------------------------------------------------------------
通常日を予測
    → 過去の通常日のみ使用

9の日を予測
    → 過去の9日のみ使用

9の日はデータ数が少ないため、
通常日30営業日とは別に最低3回の9の日履歴を使用する。

この版では daily_data のみを使用する。
既存の prediction_score や分析テーブルは使用しない。
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


# ============================================================
# バックテスト設定
# ============================================================

TOP_N = 3

# 通常日の最低履歴営業日数
MIN_NORMAL_HISTORY = 30

# 9日の最低履歴営業日数
MIN_NINE_HISTORY = 3

# 最近傾向として使用する営業日数
RECENT_DAYS_NORMAL = 7
RECENT_DAYS_NINE = 3

# バックテスト開始日
START_DATE = None

# バックテスト終了日
END_DATE = None


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

def get_business_type(date_value):

    date = pd.to_datetime(date_value)

    if date.day in (9, 19, 29):
        return "9の日"

    return "通常日"


# ============================================================
# 評価判定
# ============================================================

def is_strong(value):

    return value == "◎"


def is_high(value):

    return value in ["◎", "○"]


def is_delta_or_higher(value):

    return value in ["◎", "○", "△"]


# ============================================================
# 予測対象タイプに応じた最低履歴日数
# ============================================================

def get_min_history_days(business_type):

    if business_type == "9の日":
        return MIN_NINE_HISTORY

    return MIN_NORMAL_HISTORY


# ============================================================
# 最近使用する日数
# ============================================================

def get_recent_days(business_type):

    if business_type == "9の日":
        return RECENT_DAYS_NINE

    return RECENT_DAYS_NORMAL


# ============================================================
# 過去履歴取得
# ============================================================

def get_history(
    daily_df,
    machine_no,
    analysis_date,
    target_business_type,
):

    temp = daily_df.copy()

    temp["日付"] = pd.to_datetime(
        temp["日付"]
    )

    # 対象台
    target = temp[
        temp["台番号"] == machine_no
    ].copy()

    # 基準日以前
    target = target[
        target["日付"] <= pd.to_datetime(
            analysis_date
        )
    ].copy()

    if target.empty:
        return target

    # 営業日タイプを付与
    target["営業日タイプ"] = (
        target["日付"]
        .apply(get_business_type)
    )

    # 予測対象と同じタイプだけ残す
    target = target[
        target["営業日タイプ"]
        == target_business_type
    ].copy()

    target = target.sort_values(
        "日付"
    )

    return target


# ============================================================
# 履歴スコア
# ============================================================

def calculate_history_score(
    history_df,
):

    if history_df.empty:
        return 0.0

    high_count = (
        history_df["評価"]
        .apply(is_high)
        .sum()
    )

    total_days = len(history_df)

    if total_days == 0:
        return 0.0

    rate = (
        high_count
        / total_days
        * 100
    )

    return round(rate, 2)


# ============================================================
# 最近傾向スコア
# ============================================================

def calculate_recent_score(
    history_df,
    business_type,
):

    if history_df.empty:
        return 0.0

    recent_days = get_recent_days(
        business_type
    )

    recent = (
        history_df
        .sort_values("日付")
        .tail(recent_days)
    )

    if recent.empty:
        return 0.0

    high_count = (
        recent["評価"]
        .apply(is_high)
        .sum()
    )

    rate = (
        high_count
        / len(recent)
        * 100
    )

    return round(rate, 2)


# ============================================================
# ◎スコア
# ============================================================

def calculate_strong_score(
    history_df,
    business_type,
):

    if history_df.empty:
        return 0.0

    recent_days = get_recent_days(
        business_type
    )

    recent = (
        history_df
        .sort_values("日付")
        .tail(recent_days)
    )

    if recent.empty:
        return 0.0

    strong_count = (
        recent["評価"]
        .apply(is_strong)
        .sum()
    )

    rate = (
        strong_count
        / len(recent)
        * 100
    )

    return round(rate, 2)


# ============================================================
# G数スコア
# ============================================================

def calculate_game_score(
    history_df,
    business_type,
):

    if history_df.empty:
        return 0.0

    recent_days = get_recent_days(
        business_type
    )

    recent = (
        history_df
        .sort_values("日付")
        .tail(recent_days)
    )

    if recent.empty:
        return 0.0

    avg_games = pd.to_numeric(
        recent["G数"],
        errors="coerce",
    ).mean()

    if pd.isna(avg_games):
        return 0.0

    score = (
        avg_games
        / 5000
        * 10
    )

    return round(
        min(score, 10.0),
        2,
    )


# ============================================================
# 前回評価スコア
# ============================================================

def calculate_before_score(
    history_df,
):

    if history_df.empty:
        return 0.0

    last = (
        history_df
        .sort_values("日付")
        .iloc[-1]
    )

    evaluation = last["評価"]

    if evaluation == "◎":
        return 5.0

    if evaluation == "○":
        return 3.0

    return 0.0


# ============================================================
# 総合スコア
# ============================================================

def calculate_prediction_score(
    history_df,
    business_type,
):

    history_score = (
        calculate_history_score(
            history_df
        )
    )

    recent_score = (
        calculate_recent_score(
            history_df,
            business_type
        )
    )

    strong_score = (
        calculate_strong_score(
            history_df,
            business_type
        )
    )

    game_score = (
        calculate_game_score(
            history_df,
            business_type
        )
    )

    before_score = (
        calculate_before_score(
            history_df
        )
    )

    score = (
        history_score
        + recent_score
        + strong_score
        + game_score
        + before_score
    )

    return round(
        score,
        2,
    )


# ============================================================
# 1日分バックテスト
# ============================================================

def backtest_one_day(
    daily_df,
    analysis_date,
    result_date,
):

    analysis_date = pd.to_datetime(
        analysis_date
    )

    result_date = pd.to_datetime(
        result_date
    )

    # 予測対象日の営業日タイプ
    business_type = get_business_type(
        result_date
    )

    machines = daily_df[
        pd.to_datetime(
            daily_df["日付"]
        ) == analysis_date
    ].copy()

    if machines.empty:
        return pd.DataFrame()

    results = []

    min_history = get_min_history_days(
        business_type
    )

    for _, machine_row in machines.iterrows():

        machine_no = machine_row[
            "台番号"
        ]

        machine_name = machine_row[
            "機種"
        ]

        island_name = machine_row.get(
            "島",
            "",
        )

        # ----------------------------------------------------
        # 同じ営業日タイプだけで履歴を作る
        # ----------------------------------------------------

        history = get_history(
            daily_df,
            machine_no,
            analysis_date,
            business_type,
        )

        # 最低履歴日数
        if len(history) < min_history:
            continue

        score = calculate_prediction_score(
            history,
            business_type,
        )

        # ----------------------------------------------------
        # 翌日実績
        # ----------------------------------------------------

        actual = daily_df[
            (
                pd.to_datetime(
                    daily_df["日付"]
                )
                == result_date
            )
            &
            (
                daily_df["台番号"]
                == machine_no
            )
        ]

        actual_evaluation = ""
        actual_games = 0.0
        actual_combined = 0.0

        if not actual.empty:

            actual_row = actual.iloc[0]

            actual_evaluation = (
                actual_row["評価"]
            )

            actual_games = safe_float(
                actual_row["G数"]
            )

            actual_combined = safe_float(
                actual_row["合成確率"]
            )

        results.append(
            {
                "基準日": analysis_date.strftime(
                    "%Y-%m-%d"
                ),

                "予測日": result_date.strftime(
                    "%Y-%m-%d"
                ),

                "営業日タイプ": business_type,

                "台番号": machine_no,

                "機種": machine_name,

                "島": island_name,

                "使用履歴日数": len(history),

                "総合スコア": score,

                "翌日評価": actual_evaluation,

                "翌日G数": actual_games,

                "翌日合成": actual_combined,

                "翌日◎": (
                    1
                    if actual_evaluation == "◎"
                    else 0
                ),

                "翌日○以上": (
                    1
                    if is_high(
                        actual_evaluation
                    )
                    else 0
                ),

                "翌日△以上": (
                    1
                    if is_delta_or_higher(
                        actual_evaluation
                    )
                    else 0
                ),
            }
        )

    return pd.DataFrame(
        results
    )


# ============================================================
# TOP3作成
# ============================================================

def create_daily_top3(
    df,
):

    if df.empty:
        return pd.DataFrame()

    records = []

    for date_value, group in df.groupby(
        "基準日"
    ):

        group = group.sort_values(
            [
                "総合スコア",
                "台番号",
            ],
            ascending=[
                False,
                True,
            ],
        ).head(TOP_N)

        if len(group) < TOP_N:
            continue

        rows = list(
            group.itertuples(
                index=False
            )
        )

        first = rows[0]
        second = rows[1]
        third = rows[2]

        scores = [
            safe_float(
                first.総合スコア
            ),
            safe_float(
                second.総合スコア
            ),
            safe_float(
                third.総合スコア
            ),
        ]

        score_gap_12 = (
            scores[0]
            - scores[1]
        )

        score_gap_23 = (
            scores[1]
            - scores[2]
        )

        score_gap_13 = (
            scores[0]
            - scores[2]
        )

        top3_strong_count = sum(
            1
            for row in rows
            if row.翌日評価 == "◎"
        )

        top3_high_count = sum(
            1
            for row in rows
            if row.翌日評価
            in ["◎", "○"]
        )

        top3_delta_count = sum(
            1
            for row in rows
            if row.翌日評価
            in ["◎", "○", "△"]
        )

        records.append(
            {
                "基準日": date_value,

                "予測日": first.予測日,

                "営業日タイプ":
                    first.営業日タイプ,

                "1位台番号":
                    first.台番号,

                "1位機種":
                    first.機種,

                "1位スコア":
                    scores[0],

                "1位評価":
                    first.翌日評価,

                "2位台番号":
                    second.台番号,

                "2位機種":
                    second.機種,

                "2位スコア":
                    scores[1],

                "2位評価":
                    second.翌日評価,

                "3位台番号":
                    third.台番号,

                "3位機種":
                    third.機種,

                "3位スコア":
                    scores[2],

                "3位評価":
                    third.翌日評価,

                "1位-2位":
                    round(
                        score_gap_12,
                        2,
                    ),

                "2位-3位":
                    round(
                        score_gap_23,
                        2,
                    ),

                "1位-3位":
                    round(
                        score_gap_13,
                        2,
                    ),

                "TOP3◎台数":
                    top3_strong_count,

                "TOP3○以上台数":
                    top3_high_count,

                "TOP3△以上台数":
                    top3_delta_count,
            }
        )

    return pd.DataFrame(
        records
    )


# ============================================================
# スコア差区分
# ============================================================

def classify_score_gap(
    value,
):

    value = safe_float(
        value
    )

    if value < 5:
        return "0～5"

    if value < 10:
        return "5～10"

    if value < 20:
        return "10～20"

    return "20以上"


# ============================================================
# TOP3実績
# ============================================================

def print_top3_performance(
    top3_df,
):

    print()
    print("=" * 80)
    print("=== TOP3 バックテスト実績 ===")
    print("=" * 80)

    if top3_df.empty:

        print("データなし")
        return

    # --------------------------------------------------------
    # 日付別
    # --------------------------------------------------------

    print()
    print("--- 日付別 ---")

    display_columns = [
        "基準日",
        "営業日タイプ",
        "1位スコア",
        "2位スコア",
        "3位スコア",
        "1位-3位",
        "TOP3◎台数",
        "TOP3○以上台数",
        "TOP3△以上台数",
    ]

    print(
        top3_df[
            display_columns
        ].to_string(
            index=False
        )
    )

    # --------------------------------------------------------
    # 営業日タイプ別
    # --------------------------------------------------------

    print()
    print("--- 営業日タイプ別 ---")

    grouped = (
        top3_df
        .groupby("営業日タイプ")
        .agg(
            {
                "基準日": "count",
                "1位-3位": "mean",
                "TOP3◎台数": "mean",
                "TOP3○以上台数": "mean",
                "TOP3△以上台数": "mean",
            }
        )
        .reset_index()
    )

    grouped = grouped.rename(
        columns={
            "基準日":
                "営業日数",

            "1位-3位":
                "平均1位3位差",

            "TOP3◎台数":
                "平均TOP3◎台数",

            "TOP3○以上台数":
                "平均TOP3○以上台数",

            "TOP3△以上台数":
                "平均TOP3△以上台数",
        }
    )

    numeric_columns = [
        "平均1位3位差",
        "平均TOP3◎台数",
        "平均TOP3○以上台数",
        "平均TOP3△以上台数",
    ]

    grouped[numeric_columns] = (
        grouped[numeric_columns]
        .round(2)
    )

    print(
        grouped.to_string(
            index=False
        )
    )


# ============================================================
# スコア差実績
# ============================================================

def print_score_gap_performance(
    top3_df,
):

    print()
    print("=" * 80)
    print("=== TOP3 スコア差 × 実績 ===")
    print("=" * 80)

    if top3_df.empty:

        print("データなし")
        return

    df = top3_df.copy()

    df["スコア差区分"] = (
        df["1位-3位"]
        .apply(
            classify_score_gap
        )
    )

    # --------------------------------------------------------
    # 営業日タイプ別・スコア差区分別
    # --------------------------------------------------------

    print()
    print("--- スコア差区分別 実績 ---")

    grouped = (
        df
        .groupby(
            [
                "営業日タイプ",
                "スコア差区分",
            ]
        )
        .agg(
            {
                "基準日": "count",

                "TOP3◎台数":
                    "mean",

                "TOP3○以上台数":
                    "mean",

                "TOP3△以上台数":
                    "mean",
            }
        )
        .reset_index()
    )

    grouped = grouped.rename(
        columns={
            "基準日":
                "営業日数",

            "TOP3◎台数":
                "平均TOP3◎台数",

            "TOP3○以上台数":
                "平均TOP3○以上台数",

            "TOP3△以上台数":
                "平均TOP3△以上台数",
        }
    )

    numeric_columns = [
        "平均TOP3◎台数",
        "平均TOP3○以上台数",
        "平均TOP3△以上台数",
    ]

    grouped[numeric_columns] = (
        grouped[numeric_columns]
        .round(2)
    )

    print(
        grouped.to_string(
            index=False
        )
    )


# ============================================================
# TOP1 / TOP3 的中率
# ============================================================

def print_hit_rate(
    top3_df,
):

    print()
    print("=" * 80)
    print("=== TOP1 / TOP3 的中率 ===")
    print("=" * 80)

    if top3_df.empty:

        print("データなし")
        return

    records = []

    for business_type, group in (
        top3_df.groupby(
            "営業日タイプ"
        )
    ):

        days = len(group)

        if days == 0:
            continue

        top1_strong = (
            group["1位評価"]
            == "◎"
        ).sum()

        top1_high = (
            group["1位評価"]
            .isin(
                ["◎", "○"]
            )
            .sum()
        )

        top3_strong = (
            group["TOP3◎台数"]
            > 0
        ).sum()

        top3_high = (
            group["TOP3○以上台数"]
            > 0
        ).sum()

        top3_delta = (
            group["TOP3△以上台数"]
            > 0
        ).sum()

        records.append(
            {
                "営業日タイプ":
                    business_type,

                "営業日数":
                    days,

                "TOP1◎日数":
                    top1_strong,

                "TOP1◎率":
                    round(
                        top1_strong
                        / days
                        * 100,
                        2,
                    ),

                "TOP1○以上日数":
                    top1_high,

                "TOP1○以上率":
                    round(
                        top1_high
                        / days
                        * 100,
                        2,
                    ),

                "TOP3内◎あり日数":
                    top3_strong,

                "TOP3内◎あり率":
                    round(
                        top3_strong
                        / days
                        * 100,
                        2,
                    ),

                "TOP3内○以上あり日数":
                    top3_high,

                "TOP3内○以上率":
                    round(
                        top3_high
                        / days
                        * 100,
                        2,
                    ),

                "TOP3内△以上あり日数":
                    top3_delta,

                "TOP3内△以上率":
                    round(
                        top3_delta
                        / days
                        * 100,
                        2,
                    ),
            }
        )

    result = pd.DataFrame(
        records
    )

    print(
        result.to_string(
            index=False
        )
    )


# ============================================================
# 履歴分離状況
# ============================================================

def print_history_diagnostic(
    result_df,
):

    print()
    print("=" * 80)
    print("=== 営業日タイプ別 履歴使用状況 ===")
    print("=" * 80)

    if result_df.empty:

        print("データなし")
        return

    grouped = (
        result_df
        .groupby("営業日タイプ")
        .agg(
            {
                "基準日": "nunique",
                "使用履歴日数": [
                    "min",
                    "mean",
                    "max",
                ],
            }
        )
    )

    grouped.columns = [
        "営業日数",
        "最小履歴日数",
        "平均履歴日数",
        "最大履歴日数",
    ]

    grouped = grouped.reset_index()

    grouped[
        [
            "最小履歴日数",
            "平均履歴日数",
            "最大履歴日数",
        ]
    ] = grouped[
        [
            "最小履歴日数",
            "平均履歴日数",
            "最大履歴日数",
        ]
    ].round(2)

    print(
        grouped.to_string(
            index=False
        )
    )


# ============================================================
# 全体実績
# ============================================================

def print_overall_performance(
    result_df,
):

    print()
    print("=" * 80)
    print("=== 全体バックテスト結果 ===")
    print("=" * 80)

    if result_df.empty:

        print("データなし")
        return

    grouped = []

    for business_type, group in (
        result_df.groupby(
            "営業日タイプ"
        )
    ):

        total = len(group)

        strong = group[
            "翌日◎"
        ].sum()

        high = group[
            "翌日○以上"
        ].sum()

        delta = group[
            "翌日△以上"
        ].sum()

        grouped.append(
            {
                "営業日タイプ":
                    business_type,

                "対象台数":
                    total,

                "◎率":
                    round(
                        strong
                        / total
                        * 100,
                        2,
                    ),

                "○以上率":
                    round(
                        high
                        / total
                        * 100,
                        2,
                    ),

                "△以上率":
                    round(
                        delta
                        / total
                        * 100,
                        2,
                    ),
            }
        )

    result = pd.DataFrame(
        grouped
    )

    print(
        result.to_string(
            index=False
        )
    )


# ============================================================
# CSV保存
# ============================================================

def save_results(
    result_df,
    top3_df,
):

    output_dir = (
        BASE_DIR
        / "analysis"
        / "backtest_output"
    )

    output_dir.mkdir(
        parents=True,
        exist_ok=True,
    )

    result_path = (
        output_dir
        / "prediction_backtest_detail.csv"
    )

    top3_path = (
        output_dir
        / "prediction_backtest_top3.csv"
    )

    result_df.to_csv(
        result_path,
        index=False,
        encoding="utf-8-sig",
    )

    top3_df.to_csv(
        top3_path,
        index=False,
        encoding="utf-8-sig",
    )

    print()
    print("=== CSV保存 ===")

    print(
        "詳細:",
        result_path,
    )

    print(
        "TOP3:",
        top3_path,
    )


# ============================================================
# main
# ============================================================

def main():

    print("=" * 80)
    print(
        "Prediction Engine "
        "営業日タイプ分離バックテスト"
    )
    print("=" * 80)

    print()
    print(
        "DB:",
        DB_PATH,
    )

    if not DB_PATH.exists():

        print()
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
            conn,
        )

    finally:

        conn.close()

    if df.empty:

        print()
        print(
            "daily_data が空です。"
        )
        return

    # ========================================================
    # 前処理
    # ========================================================

    df["日付"] = pd.to_datetime(
        df["日付"],
        errors="coerce",
    )

    df = df[
        df["日付"].notna()
    ].copy()

    df["台番号"] = pd.to_numeric(
        df["台番号"],
        errors="coerce",
    )

    df = df[
        df["台番号"].notna()
    ].copy()

    df["台番号"] = (
        df["台番号"]
        .astype(int)
    )

    df = df.sort_values(
        [
            "日付",
            "台番号",
        ]
    )

    dates = sorted(
        df["日付"]
        .dt.normalize()
        .unique()
    )

    if len(dates) < 2:

        print()
        print(
            "バックテスト可能な日数が不足しています。"
        )
        return

    latest_date = pd.Timestamp(
        dates[-1]
    )

    # ========================================================
    # 対象期間
    # ========================================================

    if END_DATE is not None:

        end_date = pd.to_datetime(
            END_DATE
        )

    else:

        # 最新日は翌日実績がないため除外
        end_date = latest_date

    if START_DATE is not None:

        start_date = pd.to_datetime(
            START_DATE
        )

    else:

        start_date = pd.Timestamp(
            dates[0]
        )

    print()
    print(
        "バックテスト開始日:",
        start_date.strftime(
            "%Y-%m-%d"
        ),
    )

    print(
        "バックテスト終了日:",
        end_date.strftime(
            "%Y-%m-%d"
        ),
    )

    print()
    print(
        "通常日 最低履歴:",
        MIN_NORMAL_HISTORY,
        "営業日",
    )

    print(
        "9の日 最低履歴:",
        MIN_NINE_HISTORY,
        "営業日",
    )

    # ========================================================
    # 各基準日
    # ========================================================

    all_results = []

    valid_days = 0
    skipped_days = 0

    normal_days = 0
    nine_days = 0

    normal_valid_days = 0
    nine_valid_days = 0

    for i in range(
        len(dates) - 1
    ):

        analysis_date = pd.Timestamp(
            dates[i]
        )

        result_date = pd.Timestamp(
            dates[i + 1]
        )

        if analysis_date < start_date:
            continue

        if analysis_date > end_date:
            continue

        result_business_type = (
            get_business_type(
                result_date
            )
        )

        if result_business_type == "9の日":
            nine_days += 1
        else:
            normal_days += 1

        # ----------------------------------------------------
        # 基準日以前の同タイプ営業日数
        # ----------------------------------------------------

        previous_same_type_dates = [
            d
            for d in dates
            if d <= analysis_date
            and get_business_type(d)
            == result_business_type
        ]

        min_history = (
            get_min_history_days(
                result_business_type
            )
        )

        if len(
            previous_same_type_dates
        ) < min_history:

            skipped_days += 1
            continue

        print(
            f"\r処理中: "
            f"{analysis_date.strftime('%Y-%m-%d')}"
            f" → "
            f"{result_date.strftime('%Y-%m-%d')}"
            f" [{result_business_type}]",
            end="",
            flush=True,
        )

        result = backtest_one_day(
            df,
            analysis_date,
            result_date,
        )

        if result.empty:

            skipped_days += 1
            continue

        all_results.append(
            result
        )

        valid_days += 1

        if result_business_type == "9の日":
            nine_valid_days += 1
        else:
            normal_valid_days += 1

    print()

    # ========================================================
    # 結果なし
    # ========================================================

    if not all_results:

        print()
        print(
            "バックテスト結果がありません。"
        )
        return

    # ========================================================
    # 結合
    # ========================================================

    result_df = pd.concat(
        all_results,
        ignore_index=True,
    )

    # ========================================================
    # TOP3
    # ========================================================

    top3_df = create_daily_top3(
        result_df
    )

    print()
    print(
        "有効バックテスト日数:",
        valid_days,
    )

    print(
        "除外日数:",
        skipped_days,
    )

    print(
        "通常日候補日数:",
        normal_days,
    )

    print(
        "通常日有効日数:",
        normal_valid_days,
    )

    print(
        "9の日候補日数:",
        nine_days,
    )

    print(
        "9の日有効日数:",
        nine_valid_days,
    )

    print(
        "対象台数:",
        len(result_df),
    )

    print(
        "TOP3日数:",
        len(top3_df),
    )

    # ========================================================
    # 結果表示
    # ========================================================

    print_history_diagnostic(
        result_df
    )

    print_overall_performance(
        result_df
    )

    print_top3_performance(
        top3_df
    )

    print_score_gap_performance(
        top3_df
    )

    print_hit_rate(
        top3_df
    )

    # ========================================================
    # CSV
    # ========================================================

    save_results(
        result_df,
        top3_df,
    )

    print()
    print("=" * 80)
    print("バックテスト終了")
    print("=" * 80)


# ============================================================
# 実行
# ============================================================

if __name__ == "__main__":
    main()