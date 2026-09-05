"""
ジャグラーラボ
9の日 島予測 偏り検証

目的
・9の日島予測が特定の島に偏っていないか確認
・過去実績の多い島が毎回予測される問題を検証
・TOP1～TOP3の予測頻度を集計
・各島の過去実績と予測頻度を比較
・予測回数が多い島ほど的中しているだけではないか確認

入力:
nine_day_island_prediction.csv

出力:
nine_day_island_prediction_bias.csv
"""

import pandas as pd
from pathlib import Path


# ============================================================
# 設定
# ============================================================

BASE_DIR = Path(__file__).resolve().parent.parent

INPUT_PATH = (
    BASE_DIR
    / "analysis"
    / "backtest_output"
    / "nine_day_island_prediction.csv"
)

OUTPUT_PATH = (
    BASE_DIR
    / "analysis"
    / "backtest_output"
    / "nine_day_island_prediction_bias.csv"
)


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
# 列名確認
# ============================================================

def find_column(df, candidates):

    for column in candidates:

        if column in df.columns:
            return column

    return None


# ============================================================
# CSV読み込み
# ============================================================

def load_data():

    print("=" * 80)
    print("9の日 島予測 偏り検証")
    print("=" * 80)

    print()
    print("入力:")
    print(INPUT_PATH)

    if not INPUT_PATH.exists():

        print()
        print("入力CSVがありません。")
        return None

    df = pd.read_csv(
        INPUT_PATH,
        encoding="utf-8-sig",
    )

    print()
    print("=" * 80)
    print("=== CSV確認 ===")
    print("=" * 80)

    print()
    print("行数:")
    print(len(df))

    print()
    print("列:")

    for column in df.columns:

        print(f"  {column}")

    return df


# ============================================================
# 列判定
# ============================================================

def detect_columns(df):

    print()
    print("=" * 80)
    print("=== 列判定 ===")
    print("=" * 80)

    prediction_date_col = find_column(
        df,
        [
            "予測日",
            "基準日",
            "日付",
        ],
    )

    rank_col = find_column(
        df,
        [
            "予測順位",
            "順位",
            "ランキング",
        ],
    )

    island_col = find_column(
        df,
        [
            "島",
            "予測島",
        ],
    )

    historical_count_col = find_column(
        df,
        [
            "過去出現回数",
            "過去登場回数",
            "発生回数",
        ],
    )

    historical_strong_rate_col = find_column(
        df,
        [
            "過去強い全台系率",
            "強い全台系率",
        ],
    )

    historical_candidate_rate_col = find_column(
        df,
        [
            "過去候補率",
            "全台系候補率",
        ],
    )

    score_col = find_column(
        df,
        [
            "期待度スコア",
            "予測スコア",
            "スコア",
        ],
    )

    actual_strong_col = find_column(
        df,
        [
            "強い全台系的中",
            "実績強い全台系",
            "強い全台系",
        ],
    )

    actual_candidate_col = find_column(
        df,
        [
            "全台系候補以上",
            "候補以上",
        ],
    )

    actual_rate_col = find_column(
        df,
        [
            "実績◎率",
            "◎率",
        ],
    )

    actual_score_col = find_column(
        df,
        [
            "実績スコア",
            "評価スコア",
        ],
    )

    print()
    print("予測日:", prediction_date_col)
    print("予測順位:", rank_col)
    print("島:", island_col)
    print("過去出現回数:", historical_count_col)
    print("過去強い全台系率:", historical_strong_rate_col)
    print("過去候補率:", historical_candidate_rate_col)
    print("期待度スコア:", score_col)
    print("強い全台系的中:", actual_strong_col)
    print("全台系候補以上:", actual_candidate_col)
    print("実績◎率:", actual_rate_col)
    print("実績スコア:", actual_score_col)

    return {
        "date": prediction_date_col,
        "rank": rank_col,
        "island": island_col,
        "history_count": historical_count_col,
        "history_strong_rate": historical_strong_rate_col,
        "history_candidate_rate": historical_candidate_rate_col,
        "score": score_col,
        "actual_strong": actual_strong_col,
        "actual_candidate": actual_candidate_col,
        "actual_rate": actual_rate_col,
        "actual_score": actual_score_col,
    }


# ============================================================
# データ前処理
# ============================================================

def prepare_data(df, columns):

    df = df.copy()

    date_col = columns["date"]
    rank_col = columns["rank"]
    island_col = columns["island"]

    if date_col is not None:

        df[date_col] = pd.to_datetime(
            df[date_col],
            errors="coerce",
        )

    if rank_col is not None:

        df[rank_col] = pd.to_numeric(
            df[rank_col],
            errors="coerce",
        )

    if columns["history_count"] is not None:

        df[columns["history_count"]] = pd.to_numeric(
            df[columns["history_count"]],
            errors="coerce",
        ).fillna(0)

    for key in [
        "history_strong_rate",
        "history_candidate_rate",
        "score",
        "actual_rate",
        "actual_score",
    ]:

        column = columns[key]

        if column is not None:

            df[column] = pd.to_numeric(
                df[column],
                errors="coerce",
            ).fillna(0)

    for key in [
        "actual_strong",
        "actual_candidate",
    ]:

        column = columns[key]

        if column is not None:

            df[column] = pd.to_numeric(
                df[column],
                errors="coerce",
            ).fillna(0)

    if island_col is not None:

        df[island_col] = (
            df[island_col]
            .astype(str)
            .str.strip()
        )

    return df


# ============================================================
# TOP1～TOP3予測確認
# ============================================================

def print_daily_prediction(df, columns):

    print()
    print("=" * 80)
    print("=== 9の日別 TOP1～TOP3予測 ===")
    print("=" * 80)

    date_col = columns["date"]
    rank_col = columns["rank"]
    island_col = columns["island"]

    if (
        date_col is None
        or rank_col is None
        or island_col is None
    ):

        print()
        print("予測順位・予測日・島の列が不足しています。")
        return

    records = []

    for date_value, group in df.groupby(
        date_col
    ):

        group = group.sort_values(
            rank_col
        )

        top3 = group[
            group[rank_col].isin([1, 2, 3])
        ]

        if top3.empty:
            continue

        row = {
            "予測日": date_value.strftime("%Y-%m-%d")
            if pd.notna(date_value)
            else "",
        }

        for rank in [1, 2, 3]:

            target = top3[
                top3[rank_col] == rank
            ]

            if target.empty:

                row[f"TOP{rank}"] = ""

            else:

                row[f"TOP{rank}"] = (
                    target.iloc[0][island_col]
                )

        records.append(row)

    result = pd.DataFrame(records)

    if result.empty:

        print()
        print("日別予測データがありません。")
        return

    print()

    print(
        result.to_string(
            index=False
        )
    )


# ============================================================
# 島別予測頻度
# ============================================================

def calculate_prediction_frequency(
    df,
    columns,
):

    rank_col = columns["rank"]
    island_col = columns["island"]

    if (
        rank_col is None
        or island_col is None
    ):

        return pd.DataFrame()

    working = df.copy()

    working["予測順位"] = pd.to_numeric(
        working[rank_col],
        errors="coerce",
    )

    working = working[
        working["予測順位"].isin(
            [1, 2, 3]
        )
    ].copy()

    if working.empty:

        return pd.DataFrame()

    total_prediction_days = (
        working[columns["date"]]
        .nunique()
        if columns["date"] is not None
        else 0
    )

    grouped = (
        working
        .groupby(island_col)
        .agg(
            予測回数=("予測順位", "count"),
            TOP1回数=(
                "予測順位",
                lambda x: (x == 1).sum(),
            ),
            TOP2回数=(
                "予測順位",
                lambda x: (x == 2).sum(),
            ),
            TOP3回数=(
                "予測順位",
                lambda x: (x == 3).sum(),
            ),
        )
        .reset_index()
    )

    grouped = grouped.rename(
        columns={
            island_col: "島",
        }
    )

    if total_prediction_days > 0:

        grouped["予測日占有率"] = (
            grouped["予測回数"]
            / total_prediction_days
            * 100
        )

    else:

        grouped["予測日占有率"] = 0.0

    return grouped


# ============================================================
# 島別実績・予測偏り集計
# ============================================================

def calculate_island_bias(
    df,
    columns,
):

    island_col = columns["island"]

    if island_col is None:

        return pd.DataFrame()

    frequency = calculate_prediction_frequency(
        df,
        columns,
    )

    if frequency.empty:

        return pd.DataFrame()

    agg_dict = {}

    if columns["history_count"] is not None:

        agg_dict[
            columns["history_count"]
        ] = "mean"

    if columns["history_strong_rate"] is not None:

        agg_dict[
            columns["history_strong_rate"]
        ] = "mean"

    if columns["history_candidate_rate"] is not None:

        agg_dict[
            columns["history_candidate_rate"]
        ] = "mean"

    if columns["score"] is not None:

        agg_dict[
            columns["score"]
        ] = "mean"

    if columns["actual_strong"] is not None:

        agg_dict[
            columns["actual_strong"]
        ] = "sum"

    if columns["actual_candidate"] is not None:

        agg_dict[
            columns["actual_candidate"]
        ] = "sum"

    if columns["actual_rate"] is not None:

        agg_dict[
            columns["actual_rate"]
        ] = "mean"

    if columns["actual_score"] is not None:

        agg_dict[
            columns["actual_score"]
        ] = "mean"

    if agg_dict:

        actual = (
            df
            .groupby(island_col)
            .agg(agg_dict)
            .reset_index()
        )

        actual = actual.rename(
            columns={
                island_col: "島",
            }
        )

        result = frequency.merge(
            actual,
            on="島",
            how="left",
        )

    else:

        result = frequency.copy()

    # --------------------------------------------------------
    # 的中率
    # --------------------------------------------------------

    if (
        columns["actual_strong"] is not None
    ):

        result["強い全台系的中率"] = (
            result[
                columns["actual_strong"]
            ]
            / result["予測回数"]
            * 100
        )

    if (
        columns["actual_candidate"] is not None
    ):

        result["候補以上率"] = (
            result[
                columns["actual_candidate"]
            ]
            / result["予測回数"]
            * 100
        )

    # --------------------------------------------------------
    # 数値列丸め
    # --------------------------------------------------------

    for column in result.columns:

        if column in [
            "島",
            "予測回数",
            "TOP1回数",
            "TOP2回数",
            "TOP3回数",
        ]:

            continue

        if pd.api.types.is_numeric_dtype(
            result[column]
        ):

            result[column] = (
                result[column]
                .round(2)
            )

    return result


# ============================================================
# 偏り検証表示
# ============================================================

def print_bias_analysis(
    df,
    columns,
):

    print()
    print("=" * 80)
    print("=== 島別 予測偏り分析 ===")
    print("=" * 80)

    result = calculate_island_bias(
        df,
        columns,
    )

    if result.empty:

        print()
        print("分析可能なデータがありません。")
        return result

    # --------------------------------------------------------
    # 予測回数順
    # --------------------------------------------------------

    print()
    print("--- 予測回数順 ---")

    display_columns = [
        "島",
        "予測回数",
        "TOP1回数",
        "TOP2回数",
        "TOP3回数",
        "予測日占有率",
    ]

    print(
        result
        .sort_values(
            "予測回数",
            ascending=False,
        )[
            display_columns
        ]
        .to_string(
            index=False
        )
    )

    # --------------------------------------------------------
    # 過去実績との比較
    # --------------------------------------------------------

    print()
    print("--- 過去実績 × 予測頻度 ---")

    display_columns = [
        "島",
        "予測回数",
        "予測日占有率",
    ]

    if columns["history_count"] is not None:

        display_columns.append(
            columns["history_count"]
        )

    if columns["history_strong_rate"] is not None:

        display_columns.append(
            columns["history_strong_rate"]
        )

    if columns["history_candidate_rate"] is not None:

        display_columns.append(
            columns["history_candidate_rate"]
        )

    if columns["actual_strong"] is not None:

        display_columns.append(
            columns["actual_strong"]
        )

    if columns["actual_candidate"] is not None:

        display_columns.append(
            columns["actual_candidate"]
        )

    if "強い全台系的中率" in result.columns:

        display_columns.append(
            "強い全台系的中率"
        )

    if "候補以上率" in result.columns:

        display_columns.append(
            "候補以上率"
        )

    print(
        result
        .sort_values(
            "予測回数",
            ascending=False,
        )[
            display_columns
        ]
        .to_string(
            index=False
        )
    )

    # --------------------------------------------------------
    # 最頻予測島
    # --------------------------------------------------------

    most_predicted = (
        result
        .sort_values(
            "予測回数",
            ascending=False,
        )
        .iloc[0]
    )

    print()
    print("--- 最頻予測島 ---")

    print(
        "島:",
        most_predicted["島"],
    )

    print(
        "予測回数:",
        most_predicted["予測回数"],
    )

    print(
        "予測日占有率:",
        most_predicted["予測日占有率"],
        "%",
    )

    # --------------------------------------------------------
    # TOP1集中度
    # --------------------------------------------------------

    total_top1 = (
        result["TOP1回数"]
        .sum()
    )

    print()
    print("--- TOP1集中度 ---")

    if total_top1 > 0:

        top1_result = (
            result
            .copy()
        )

        top1_result["TOP1占有率"] = (
            top1_result["TOP1回数"]
            / total_top1
            * 100
        )

        print(
            top1_result
            .sort_values(
                "TOP1回数",
                ascending=False,
            )[
                [
                    "島",
                    "TOP1回数",
                    "TOP1占有率",
                ]
            ]
            .to_string(
                index=False
            )
        )

    else:

        print("TOP1データなし")

    return result


# ============================================================
# ガール島集中チェック
# ============================================================

def check_girl_island_bias(
    result,
):

    print()
    print("=" * 80)
    print("=== ガール島集中チェック ===")
    print("=" * 80)

    if result.empty:

        print("データなし")
        return

    target = result[
        result["島"].astype(str).str.contains(
            "ガール",
            na=False,
        )
    ]

    if target.empty:

        print()
        print("ガール島は検出されませんでした。")
        return

    row = target.iloc[0]

    print()
    print(
        "ガール島 予測回数:",
        row["予測回数"],
    )

    print(
        "ガール島 予測日占有率:",
        row["予測日占有率"],
        "%",
    )

    print(
        "ガール島 TOP1回数:",
        row["TOP1回数"],
    )

    print(
        "ガール島 TOP2回数:",
        row["TOP2回数"],
    )

    print(
        "ガール島 TOP3回数:",
        row["TOP3回数"],
    )

    if "強い全台系的中率" in row.index:

        print(
            "ガール島 強い全台系的中率:",
            row["強い全台系的中率"],
            "%",
        )

    if "候補以上率" in row.index:

        print(
            "ガール島 候補以上率:",
            row["候補以上率"],
            "%",
        )

    print()
    print(
        "※ ここでは「ガール島が強いか」と"
        "「ガール島ばかり予測しているか」を分離して確認します。"
    )


# ============================================================
# CSV保存
# ============================================================

def save_result(result):

    if result.empty:

        return

    result.to_csv(
        OUTPUT_PATH,
        index=False,
        encoding="utf-8-sig",
    )

    print()
    print("=" * 80)
    print("=== CSV保存 ===")
    print("=" * 80)

    print()
    print("出力:")
    print(OUTPUT_PATH)


# ============================================================
# main
# ============================================================

def main():

    df = load_data()

    if df is None:

        return

    columns = detect_columns(
        df
    )

    df = prepare_data(
        df,
        columns,
    )

    print_daily_prediction(
        df,
        columns,
    )

    result = print_bias_analysis(
        df,
        columns,
    )

    check_girl_island_bias(
        result,
    )

    save_result(
        result
    )

    print()
    print("=" * 80)
    print("9の日 島予測 偏り検証終了")
    print("=" * 80)


# ============================================================
# 実行
# ============================================================

if __name__ == "__main__":
    main()