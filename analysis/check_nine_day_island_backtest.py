"""
ジャグラーラボ
9の日 島単位バックテスト

目的
----
9の日を通常日とは分離し、
「9の日にどの島が全台系になりやすいか」
を過去データから検証する。

重要
----
・元データは daily_data のみを使用
・予測基準日より未来のデータは使用しない
・9日 / 19日 / 29日のみを対象
・通常日は対象外
・個別台TOP3ではなく島単位で評価する

今回のバックテストでは、

1. 過去の9の日実績から島ごとの強さを算出
2. その実績を使って次回9の日の島をランキング
3. 実際にその島が強かったか確認
4. TOP1 / TOP2 / TOP3島の的中状況を確認

する。

注意
----
2025/12～2026/02は簡易データ期間のため、
本バックテストでは 2026-03-01 以降を対象とする。
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

# 本検証開始日
START_DATE = "2026-03-01"

# Noneならdaily_dataの最新日の前日まで
END_DATE = None

# 過去最低9の日実績数
MIN_HISTORY_NINE_DAYS = 1

# 予測する島数
TOP_ISLANDS = 3

# 島を「強い島」と判定する基準
#
# 9の日の島全体に対する
# ◎以上台率を使用する。
#
# 例:
#  50%以上 → 強い
#  35%以上 → 候補
#
STRONG_RATE = 50.0
CANDIDATE_RATE = 35.0


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


def is_delta(value):

    return value in ["◎", "○", "△"]


# ============================================================
# 島実績集計
# ============================================================

def calculate_island_result(
    daily_df,
    target_date,
):

    target_date = pd.to_datetime(
        target_date
    )

    day_df = daily_df[
        pd.to_datetime(
            daily_df["日付"]
        )
        == target_date
    ].copy()

    if day_df.empty:

        return pd.DataFrame()

    # 9の日のみ
    if get_business_type(target_date) != "9の日":

        return pd.DataFrame()

    # --------------------------------------------------------
    # 島情報がない行を除外
    # --------------------------------------------------------

    day_df["島"] = (
        day_df["島"]
        .fillna("")
        .astype(str)
    )

    day_df = day_df[
        day_df["島"].str.strip() != ""
    ].copy()

    if day_df.empty:

        return pd.DataFrame()

    # --------------------------------------------------------
    # 数値列
    # --------------------------------------------------------

    day_df["G数_numeric"] = pd.to_numeric(
        day_df["G数"],
        errors="coerce",
    )

    day_df["合成_numeric"] = pd.to_numeric(
        day_df["合成確率"],
        errors="coerce",
    )

    # --------------------------------------------------------
    # フラグ
    # --------------------------------------------------------

    day_df["◎"] = (
        day_df["評価"]
        .apply(is_strong)
        .astype(int)
    )

    day_df["○以上"] = (
        day_df["評価"]
        .apply(is_high)
        .astype(int)
    )

    day_df["△以上"] = (
        day_df["評価"]
        .apply(is_delta)
        .astype(int)
    )

    # --------------------------------------------------------
    # 島単位集計
    #
    # 日本語列名を直接aggのキーワード引数にしない。
    # これが今回のSyntaxError対策。
    # --------------------------------------------------------

    grouped = (
        day_df
        .groupby("島")
        .agg({
            "台番号": "count",
            "G数_numeric": "mean",
            "合成_numeric": "mean",
            "◎": "sum",
            "○以上": "sum",
            "△以上": "sum",
        })
        .reset_index()
    )

    grouped = grouped.rename(
        columns={
            "台番号": "台数",
            "G数_numeric": "平均G数",
            "合成_numeric": "平均合成確率",
            "◎": "◎台数",
            "○以上": "○以上台数",
            "△以上": "△以上台数",
        }
    )

    # --------------------------------------------------------
    # 率
    # --------------------------------------------------------

    grouped["◎率"] = (
        grouped["◎台数"]
        / grouped["台数"]
        * 100
    )

    grouped["○以上率"] = (
        grouped["○以上台数"]
        / grouped["台数"]
        * 100
    )

    grouped["△以上率"] = (
        grouped["△以上台数"]
        / grouped["台数"]
        * 100
    )

    # --------------------------------------------------------
    # 島の実績強度
    #
    # ◎率を中心に、
    # ○以上率・△以上率を補助的に使用
    # --------------------------------------------------------

    grouped["実績スコア"] = (
        grouped["◎率"] * 0.50
        + grouped["○以上率"] * 0.30
        + grouped["△以上率"] * 0.20
    )

    # --------------------------------------------------------
    # 判定
    # --------------------------------------------------------

    def judge(rate):

        if rate >= STRONG_RATE:

            return "強い全台系"

        if rate >= CANDIDATE_RATE:

            return "全台系候補"

        return "通常"

    grouped["判定"] = (
        grouped["◎率"]
        .apply(judge)
    )

    grouped["日付"] = (
        target_date.strftime(
            "%Y-%m-%d"
        )
    )

    grouped["営業日タイプ"] = "9の日"

    # --------------------------------------------------------
    # 列順
    # --------------------------------------------------------

    columns = [
        "日付",
        "営業日タイプ",
        "島",
        "台数",
        "平均G数",
        "平均合成確率",
        "◎台数",
        "○以上台数",
        "△以上台数",
        "◎率",
        "○以上率",
        "△以上率",
        "実績スコア",
        "判定",
    ]

    grouped = grouped[
        columns
    ]

    # --------------------------------------------------------
    # 丸め
    # --------------------------------------------------------

    numeric_columns = [
        "平均G数",
        "平均合成確率",
        "◎率",
        "○以上率",
        "△以上率",
        "実績スコア",
    ]

    grouped[numeric_columns] = (
        grouped[numeric_columns]
        .round(2)
    )

    return grouped


# ============================================================
# 過去9の日 島履歴
# ============================================================

def build_island_history(
    island_results,
):

    if island_results.empty:

        return pd.DataFrame()

    df = island_results.copy()

    grouped = (
        df
        .groupby("島")
        .agg({
            "日付": "count",
            "台数": "mean",
            "◎率": "mean",
            "○以上率": "mean",
            "△以上率": "mean",
            "実績スコア": "mean",
            "強い全台系フラグ": "sum",
            "候補フラグ": "sum",
        })
        .reset_index()
    )

    grouped = grouped.rename(
        columns={
            "日付": "出現回数",
            "台数": "平均台数",
            "◎率": "平均◎率",
            "○以上率": "平均○以上率",
            "△以上率": "平均△以上率",
            "実績スコア": "平均実績スコア",
            "強い全台系フラグ": "強い全台系回数",
            "候補フラグ": "候補回数",
        }
    )

    grouped["強い全台系率"] = (
        grouped["強い全台系回数"]
        / grouped["出現回数"]
        * 100
    )

    grouped["候補率"] = (
        grouped["候補回数"]
        / grouped["出現回数"]
        * 100
    )

    # --------------------------------------------------------
    # 島期待度
    #
    # 出現回数が少ない島が極端に上位に来るのを
    # ある程度抑制する。
    # --------------------------------------------------------

    grouped["期待度スコア"] = (
        grouped["平均実績スコア"] * 0.50
        + grouped["強い全台系率"] * 0.30
        + grouped["候補率"] * 0.20
    )

    numeric_columns = [
        "平均台数",
        "平均◎率",
        "平均○以上率",
        "平均△以上率",
        "平均実績スコア",
        "強い全台系率",
        "候補率",
        "期待度スコア",
    ]

    grouped[numeric_columns] = (
        grouped[numeric_columns]
        .round(2)
    )

    return grouped.sort_values(
        "期待度スコア",
        ascending=False,
    ).reset_index(
        drop=True
    )


# ============================================================
# 1回分の予測
# ============================================================

def predict_islands_for_date(
    history_df,
    target_date,
):

    if history_df.empty:

        return pd.DataFrame()

    target_date = pd.to_datetime(
        target_date
    )

    # --------------------------------------------------------
    # 予測対象日より前の履歴だけ
    # --------------------------------------------------------

    history = history_df[
        pd.to_datetime(
            history_df["日付"]
        )
        < target_date
    ].copy()

    if history.empty:

        return pd.DataFrame()

    # --------------------------------------------------------
    # 島別履歴
    # --------------------------------------------------------

    island_history = (
        build_island_history(
            history
        )
    )

    if island_history.empty:

        return pd.DataFrame()

    # --------------------------------------------------------
    # 最低履歴回数
    # --------------------------------------------------------

    island_history = island_history[
        island_history["出現回数"]
        >= MIN_HISTORY_NINE_DAYS
    ].copy()

    if island_history.empty:

        return pd.DataFrame()

    # --------------------------------------------------------
    # 上位島
    # --------------------------------------------------------

    prediction = (
        island_history
        .sort_values(
            [
                "期待度スコア",
                "強い全台系率",
                "平均◎率",
            ],
            ascending=False,
        )
        .head(TOP_ISLANDS)
        .copy()
    )

    prediction["予測日"] = (
        target_date.strftime(
            "%Y-%m-%d"
        )
    )

    prediction["予測順位"] = range(
        1,
        len(prediction) + 1,
    )

    return prediction


# ============================================================
# 予測と実績を比較
# ============================================================

def compare_prediction_actual(
    prediction_df,
    actual_df,
):

    if prediction_df.empty:

        return pd.DataFrame()

    if actual_df.empty:

        return pd.DataFrame()

    records = []

    for _, row in prediction_df.iterrows():

        island = row["島"]

        actual = actual_df[
            actual_df["島"]
            == island
        ]

        actual_exists = (
            not actual.empty
        )

        if actual_exists:

            actual_row = (
                actual.iloc[0]
            )

            actual_judge = (
                actual_row["判定"]
            )

            actual_rate = safe_float(
                actual_row["◎率"]
            )

            actual_score = safe_float(
                actual_row["実績スコア"]
            )

        else:

            actual_judge = "データなし"
            actual_rate = 0.0
            actual_score = 0.0

        records.append(
            {
                "予測日": row["予測日"],
                "予測順位": row["予測順位"],
                "島": island,
                "過去出現回数": row["出現回数"],
                "過去強い全台系率": row["強い全台系率"],
                "過去候補率": row["候補率"],
                "期待度スコア": row["期待度スコア"],
                "実績判定": actual_judge,
                "実績◎率": actual_rate,
                "実績スコア": actual_score,
                "強い全台系的中": (
                    1
                    if actual_judge
                    == "強い全台系"
                    else 0
                ),
                "全台系候補以上": (
                    1
                    if actual_judge
                    in [
                        "強い全台系",
                        "全台系候補",
                    ]
                    else 0
                ),
            }
        )

    return pd.DataFrame(
        records
    )


# ============================================================
# 日別結果集計
# ============================================================

def summarize_daily_results(
    comparison_df,
):

    if comparison_df.empty:

        return pd.DataFrame()

    records = []

    for date_value, group in (
        comparison_df.groupby(
            "予測日"
        )
    ):

        top1 = group[
            group["予測順位"] == 1
        ]

        top2 = group[
            group["予測順位"] <= 2
        ]

        top3 = group[
            group["予測順位"] <= 3
        ]

        top1_strong = (
            top1["強い全台系的中"]
            .sum()
        )

        top1_candidate = (
            top1["全台系候補以上"]
            .sum()
        )

        top2_strong = (
            top2["強い全台系的中"]
            .sum()
        )

        top2_candidate = (
            top2["全台系候補以上"]
            .sum()
        )

        top3_strong = (
            top3["強い全台系的中"]
            .sum()
        )

        top3_candidate = (
            top3["全台系候補以上"]
            .sum()
        )

        records.append(
            {
                "予測日": date_value,

                "TOP1強い全台系的中": int(
                    top1_strong
                ),

                "TOP1候補以上": int(
                    top1_candidate
                ),

                "TOP2内強い全台系": int(
                    top2_strong
                ),

                "TOP2内候補以上": int(
                    top2_candidate
                ),

                "TOP3内強い全台系": int(
                    top3_strong
                ),

                "TOP3内候補以上": int(
                    top3_candidate
                ),
            }
        )

    return pd.DataFrame(
        records
    )


# ============================================================
# 結果表示
# ============================================================

def print_summary(
    daily_summary,
    comparison_df,
):

    print()
    print("=" * 80)
    print("=== 9の日 島単位バックテスト結果 ===")
    print("=" * 80)

    if daily_summary.empty:

        print()
        print("結果なし")
        return

    days = len(
        daily_summary
    )

    top1_strong = (
        daily_summary[
            "TOP1強い全台系的中"
        ]
        .sum()
    )

    top1_candidate = (
        daily_summary[
            "TOP1候補以上"
        ]
        .sum()
    )

    top2_strong = (
        daily_summary[
            "TOP2内強い全台系"
        ]
        .sum()
    )

    top2_candidate = (
        daily_summary[
            "TOP2内候補以上"
        ]
        .sum()
    )

    top3_strong = (
        daily_summary[
            "TOP3内強い全台系"
        ]
        .sum()
    )

    top3_candidate = (
        daily_summary[
            "TOP3内候補以上"
        ]
        .sum()
    )

    print()
    print(
        "バックテスト9の日数:",
        days,
    )

    print()
    print("--- TOP1 ---")

    print(
        "強い全台系的中:",
        top1_strong,
        "/",
        days,
        f"({top1_strong / days * 100:.2f}%)",
    )

    print(
        "候補以上:",
        top1_candidate,
        "/",
        days,
        f"({top1_candidate / days * 100:.2f}%)",
    )

    print()
    print("--- TOP2 ---")

    print(
        "強い全台系:",
        top2_strong,
        "/",
        days,
        f"({top2_strong / days * 100:.2f}%)",
    )

    print(
        "候補以上:",
        top2_candidate,
        "/",
        days,
        f"({top2_candidate / days * 100:.2f}%)",
    )

    print()
    print("--- TOP3 ---")

    print(
        "強い全台系:",
        top3_strong,
        "/",
        days,
        f"({top3_strong / days * 100:.2f}%)",
    )

    print(
        "候補以上:",
        top3_candidate,
        "/",
        days,
        f"({top3_candidate / days * 100:.2f}%)",
    )

    # --------------------------------------------------------
    # 島別
    # --------------------------------------------------------

    print()
    print("--- 予測島別 集計 ---")

    island_summary = (
        comparison_df
        .groupby("島")
        .agg({
            "予測日": "count",
            "強い全台系的中": "sum",
            "全台系候補以上": "sum",
            "実績◎率": "mean",
            "実績スコア": "mean",
        })
        .reset_index()
    )

    island_summary = (
        island_summary.rename(
            columns={
                "予測日": "予測回数",
                "強い全台系的中": "強い全台系回数",
                "全台系候補以上": "候補以上回数",
                "実績◎率": "平均実績◎率",
                "実績スコア": "平均実績スコア",
            }
        )
    )

    island_summary["強い全台系的中率"] = (
        island_summary["強い全台系回数"]
        / island_summary["予測回数"]
        * 100
    )

    island_summary["候補以上率"] = (
        island_summary["候補以上回数"]
        / island_summary["予測回数"]
        * 100
    )

    island_summary = (
        island_summary
        .sort_values(
            "予測回数",
            ascending=False,
        )
    )

    numeric_columns = [
        "平均実績◎率",
        "平均実績スコア",
        "強い全台系的中率",
        "候補以上率",
    ]

    island_summary[
        numeric_columns
    ] = (
        island_summary[
            numeric_columns
        ].round(2)
    )

    print(
        island_summary.to_string(
            index=False
        )
    )


# ============================================================
# CSV保存
# ============================================================

def save_results(
    island_results,
    comparison_df,
    daily_summary,
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

    island_path = (
        output_dir
        / "nine_day_island_actual.csv"
    )

    prediction_path = (
        output_dir
        / "nine_day_island_prediction.csv"
    )

    daily_path = (
        output_dir
        / "nine_day_island_daily.csv"
    )

    island_results.to_csv(
        island_path,
        index=False,
        encoding="utf-8-sig",
    )

    comparison_df.to_csv(
        prediction_path,
        index=False,
        encoding="utf-8-sig",
    )

    daily_summary.to_csv(
        daily_path,
        index=False,
        encoding="utf-8-sig",
    )

    print()
    print("=== CSV保存 ===")

    print(
        "島実績:",
        island_path,
    )

    print(
        "予測比較:",
        prediction_path,
    )

    print(
        "日別結果:",
        daily_path,
    )


# ============================================================
# main
# ============================================================

def main():

    print("=" * 80)
    print("9の日 島単位バックテスト")
    print("=" * 80)

    print()
    print(
        "DB:",
        DB_PATH,
    )

    print(
        "検証開始日:",
        START_DATE,
    )

    if not DB_PATH.exists():

        print()
        print(
            "DBがありません。"
        )

        return

    # ========================================================
    # DB読み込み
    # ========================================================

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

    df["島"] = (
        df["島"]
        .fillna("")
        .astype(str)
    )

    df = df.sort_values(
        [
            "日付",
            "台番号",
        ]
    )

    # ========================================================
    # 検証期間
    # ========================================================

    start_date = pd.to_datetime(
        START_DATE
    )

    if END_DATE is not None:

        end_date = pd.to_datetime(
            END_DATE
        )

    else:

        end_date = (
            df["日付"]
            .max()
        )

    # ========================================================
    # 9の日一覧
    # ========================================================

    dates = sorted(
        df["日付"]
        .dt.normalize()
        .unique()
    )

    nine_dates = [
        pd.Timestamp(d)
        for d in dates
        if (
            pd.Timestamp(d) >= start_date
            and pd.Timestamp(d) <= end_date
            and get_business_type(d)
            == "9の日"
        )
    ]

    print()
    print(
        "検証対象9の日数:",
        len(nine_dates),
    )

    if not nine_dates:

        print()
        print(
            "対象となる9の日がありません。"
        )

        return

    # ========================================================
    # 各9日の実績を構築
    # ========================================================

    all_actual = []

    print()
    print("9の日実績を再構築中...")

    for target_date in nine_dates:

        actual = calculate_island_result(
            df,
            target_date,
        )

        if actual.empty:

            continue

        # ----------------------------------------------------
        # フラグ
        # ----------------------------------------------------

        actual["強い全台系フラグ"] = (
            actual["判定"]
            == "強い全台系"
        ).astype(int)

        actual["候補フラグ"] = (
            actual["判定"]
            .isin(
                [
                    "強い全台系",
                    "全台系候補",
                ]
            )
        ).astype(int)

        all_actual.append(
            actual
        )

    if not all_actual:

        print()
        print(
            "島実績を作成できませんでした。"
        )

        return

    island_results = pd.concat(
        all_actual,
        ignore_index=True,
    )

    # ========================================================
    # 予測バックテスト
    #
    # 各9の日について、
    # その日より前の9の日だけで予測。
    # ========================================================

    all_comparisons = []

    print()
    print("島予測バックテスト中...")

    for target_date in nine_dates:

        target_date_string = (
            target_date.strftime(
                "%Y-%m-%d"
            )
        )

        history = island_results[
            pd.to_datetime(
                island_results["日付"]
            )
            < target_date
        ].copy()

        # ----------------------------------------------------
        # 過去実績が足りない場合
        # ----------------------------------------------------

        if history.empty:

            continue

        prediction = (
            predict_islands_for_date(
                island_results,
                target_date,
            )
        )

        if prediction.empty:

            continue

        actual = island_results[
            island_results["日付"]
            == target_date_string
        ].copy()

        comparison = (
            compare_prediction_actual(
                prediction,
                actual,
            )
        )

        if comparison.empty:

            continue

        all_comparisons.append(
            comparison
        )

    if not all_comparisons:

        print()
        print(
            "予測比較結果がありません。"
        )

        # 実績CSVだけは保存
        save_results(
            island_results,
            pd.DataFrame(),
            pd.DataFrame(),
        )

        return

    comparison_df = pd.concat(
        all_comparisons,
        ignore_index=True,
    )

    # ========================================================
    # 日別結果
    # ========================================================

    daily_summary = (
        summarize_daily_results(
            comparison_df
        )
    )

    # ========================================================
    # 結果表示
    # ========================================================

    print_summary(
        daily_summary,
        comparison_df,
    )

    # ========================================================
    # CSV
    # ========================================================

    save_results(
        island_results,
        comparison_df,
        daily_summary,
    )

    print()
    print("=" * 80)
    print("9の日 島単位バックテスト終了")
    print("=" * 80)


# ============================================================
# 実行
# ============================================================

if __name__ == "__main__":
    main()