"""
9の日 島ラグ履歴バックテスト

目的
----
2026/03以降の9の日について、

1. 固定的な島期待度
2. 直近3回の投入履歴
3. 固定期待度 + 直近履歴

の3モデルを比較する。

重要
----
・未来情報を使用しない
・Prediction Engineは変更しない
・lag分析CSVを入力として使用
・target_strongを実績値として使用
・TOP1 / TOP2 / TOP3のstrong的中率を比較
"""

from pathlib import Path
import pandas as pd


# ============================================================
# PATH
# ============================================================

BASE_DIR = Path(__file__).resolve().parent.parent

INPUT = (
    BASE_DIR
    / "analysis"
    / "backtest_output"
    / "nine_day_island_lag_analysis.csv"
)

OUTPUT_DIR = (
    BASE_DIR
    / "analysis"
    / "backtest_output"
)

DETAIL_OUTPUT = (
    OUTPUT_DIR
    / "nine_day_lag_backtest_detail.csv"
)

SUMMARY_OUTPUT = (
    OUTPUT_DIR
    / "nine_day_lag_backtest_summary.csv"
)


# ============================================================
# BACKTEST START
# ============================================================

START_DATE = pd.Timestamp("2026-03-09")


# ============================================================
# Utility
# ============================================================

def safe_float(value):
    try:
        return float(value)
    except Exception:
        return 0.0


# ============================================================
# Main
# ============================================================

def main():

    print("=" * 80)
    print("9 DAY ISLAND LAG BACKTEST")
    print("=" * 80)

    # ========================================================
    # Input check
    # ========================================================

    if not INPUT.exists():

        print()
        print("INPUT FILE NOT FOUND")
        print(INPUT)
        return

    # ========================================================
    # Load CSV
    # ========================================================

    df = pd.read_csv(
        INPUT,
        encoding="utf-8-sig"
    )

    print()
    print("INPUT")
    print("-" * 80)
    print("rows:", len(df))
    print("cols:", len(df.columns))

    print()
    print("columns:")

    for i, col in enumerate(df.columns):
        print(i, repr(col))

    # ========================================================
    # Required columns
    # ========================================================

    required_columns = [
        "current_date",
        "island",
        "target_strong",
        "target_candidate",

        "lag1_strong",
        "lag1_candidate",

        "lag2_strong",
        "lag2_candidate",

        "lag3_strong",
        "lag3_candidate",

        "lag3_complete",
    ]

    missing = [
        col
        for col in required_columns
        if col not in df.columns
    ]

    if missing:

        print()
        print("MISSING COLUMNS")

        for col in missing:
            print(col)

        return

    # ========================================================
    # Date conversion
    # ========================================================

    df["current_date"] = pd.to_datetime(
        df["current_date"],
        format="%Y-%m-%d",
        errors="coerce"
    )

    df = df[
        df["current_date"].notna()
    ].copy()

    # ========================================================
    # 2026/03以降のみ
    # ========================================================

    df = df[
        df["current_date"] >= START_DATE
    ].copy()

    # ========================================================
    # Numeric conversion
    # ========================================================

    numeric_columns = [
        "target_strong",
        "target_candidate",

        "lag1_strong",
        "lag1_candidate",

        "lag2_strong",
        "lag2_candidate",

        "lag3_strong",
        "lag3_candidate",

        "lag3_complete",
    ]

    for col in numeric_columns:

        df[col] = pd.to_numeric(
            df[col],
            errors="coerce"
        ).fillna(0).astype(int)

    # ========================================================
    # Actual result
    # ========================================================

    df["actual_strong"] = (
        df["target_strong"]
    )

    df["actual_candidate"] = (
        df["target_candidate"]
    )

    # ========================================================
    # Recent history count
    # ========================================================

    df["recent_strong_count"] = (
        df["lag1_strong"]
        + df["lag2_strong"]
        + df["lag3_strong"]
    )

    df["recent_candidate_count"] = (
        df["lag1_candidate"]
        + df["lag2_candidate"]
        + df["lag3_candidate"]
    )

    # ========================================================
    # Basic diagnostic
    # ========================================================

    print()
    print("BACKTEST DATA")
    print("-" * 80)

    print(
        "dates:",
        df["current_date"].nunique()
    )

    print(
        "islands:",
        df["island"].nunique()
    )

    print(
        "rows:",
        len(df)
    )

    print(
        "date range:",
        df["current_date"].min().strftime("%Y-%m-%d"),
        "~",
        df["current_date"].max().strftime("%Y-%m-%d")
    )

    # ========================================================
    # Backtest dates
    # ========================================================

    dates = sorted(
        df["current_date"]
        .drop_duplicates()
        .tolist()
    )

    # ========================================================
    # Detail result
    # ========================================================

    detail_rows = []

    # ========================================================
    # Date loop
    # ========================================================

    for target_date in dates:

        # ----------------------------------------------------
        # Target day
        # ----------------------------------------------------

        day = df[
            df["current_date"] == target_date
        ].copy()

        if day.empty:
            continue

        # ----------------------------------------------------
        # Historical data
        #
        # IMPORTANT:
        # target_dateより前だけ使用
        # ----------------------------------------------------

        previous = df[
            df["current_date"] < target_date
        ].copy()

        if previous.empty:
            continue

        # ----------------------------------------------------
        # Historical fixed expectation
        # ----------------------------------------------------

        island_history = (
            previous
            .groupby("island")
            .agg(
                historical_strong_count=(
                    "actual_strong",
                    "sum"
                ),

                historical_count=(
                    "actual_strong",
                    "count"
                )
            )
            .reset_index()
        )

        island_history[
            "historical_strong_rate"
        ] = (
            island_history[
                "historical_strong_count"
            ]
            /
            island_history[
                "historical_count"
            ]
            * 100
        )

        # ----------------------------------------------------
        # Target scoring dataframe
        # ----------------------------------------------------

        scores = day[
            [
                "island",

                "actual_strong",
                "actual_candidate",

                "lag1_strong",
                "lag1_candidate",

                "lag2_strong",
                "lag2_candidate",

                "lag3_strong",
                "lag3_candidate",

                "recent_strong_count",
                "recent_candidate_count",
            ]
        ].copy()

        # ====================================================
        # MODEL A
        # Lag only
        # ====================================================

        scores["lag_score"] = (

            scores["lag1_strong"] * 3.0

            + scores["lag2_strong"] * 2.0

            + scores["lag3_strong"] * 1.0

            + scores["lag1_candidate"] * 0.75

            + scores["lag2_candidate"] * 0.50

            + scores["lag3_candidate"] * 0.25
        )

        # ====================================================
        # MODEL B
        # Fixed expectation
        # ====================================================

        scores = scores.merge(
            island_history[
                [
                    "island",
                    "historical_strong_count",
                    "historical_count",
                    "historical_strong_rate",
                ]
            ],
            on="island",
            how="left"
        )

        scores[
            "historical_strong_count"
        ] = scores[
            "historical_strong_count"
        ].fillna(0)

        scores[
            "historical_count"
        ] = scores[
            "historical_count"
        ].fillna(0)

        scores[
            "historical_strong_rate"
        ] = scores[
            "historical_strong_rate"
        ].fillna(0)

        scores["fixed_score"] = (
            scores[
                "historical_strong_rate"
            ]
        )

        # ====================================================
        # MODEL C
        # Fixed + Lag
        # ====================================================

        scores["combined_score"] = (

            scores["fixed_score"]

            + (
                scores["lag_score"]
                * 5.0
            )
        )

        # ====================================================
        # Ranking
        # ====================================================

        models = {

            "lag":
                "lag_score",

            "fixed":
                "fixed_score",

            "combined":
                "combined_score",
        }

        for model_name, score_column in models.items():

            ranked = scores.sort_values(
                by=[
                    score_column,
                    "historical_strong_count",
                ],
                ascending=False
            ).reset_index(drop=True)

            ranked["rank"] = (
                ranked.index + 1
            )

            # ------------------------------------------------
            # Save each island
            # ------------------------------------------------

            for _, row in ranked.iterrows():

                detail_rows.append(
                    {
                        "date":
                            target_date.strftime(
                                "%Y-%m-%d"
                            ),

                        "model":
                            model_name,

                        "island":
                            row["island"],

                        "rank":
                            int(row["rank"]),

                        "score":
                            safe_float(
                                row[
                                    score_column
                                ]
                            ),

                        "actual_strong":
                            int(
                                row[
                                    "actual_strong"
                                ]
                            ),

                        "actual_candidate":
                            int(
                                row[
                                    "actual_candidate"
                                ]
                            ),

                        "lag1_strong":
                            int(
                                row[
                                    "lag1_strong"
                                ]
                            ),

                        "lag2_strong":
                            int(
                                row[
                                    "lag2_strong"
                                ]
                            ),

                        "lag3_strong":
                            int(
                                row[
                                    "lag3_strong"
                                ]
                            ),

                        "lag1_candidate":
                            int(
                                row[
                                    "lag1_candidate"
                                ]
                            ),

                        "lag2_candidate":
                            int(
                                row[
                                    "lag2_candidate"
                                ]
                            ),

                        "lag3_candidate":
                            int(
                                row[
                                    "lag3_candidate"
                                ]
                            ),

                        "recent_strong_count":
                            int(
                                row[
                                    "recent_strong_count"
                                ]
                            ),

                        "recent_candidate_count":
                            int(
                                row[
                                    "recent_candidate_count"
                                ]
                            ),

                        "historical_strong_count":
                            int(
                                row[
                                    "historical_strong_count"
                                ]
                            ),

                        "historical_count":
                            int(
                                row[
                                    "historical_count"
                                ]
                            ),

                        "historical_strong_rate":
                            safe_float(
                                row[
                                    "historical_strong_rate"
                                ]
                            ),
                    }
                )

    # ========================================================
    # Detail DataFrame
    # ========================================================

    detail_df = pd.DataFrame(
        detail_rows
    )

    if detail_df.empty:

        print()
        print("NO BACKTEST RESULT")
        return

    # ========================================================
    # Save detail
    # ========================================================

    detail_df.to_csv(
        DETAIL_OUTPUT,
        index=False,
        encoding="utf-8-sig"
    )

    # ========================================================
    # Summary
    # ========================================================

    summary_rows = []

    for model_name in [
        "lag",
        "fixed",
        "combined",
    ]:

        model_df = detail_df[
            detail_df["model"]
            == model_name
        ].copy()

        target_dates = sorted(
            model_df["date"].unique()
        )

        # ----------------------------------------------------
        # TOP1 / TOP2 / TOP3
        # ----------------------------------------------------

        for top_n in [1, 2, 3]:

            hit_count = 0

            candidate_hit_count = 0

            for date in target_dates:

                day = model_df[
                    model_df["date"]
                    == date
                ].sort_values(
                    "rank"
                )

                top = day.head(top_n)

                # Strong hit
                if (
                    top[
                        "actual_strong"
                    ].max()
                    == 1
                ):
                    hit_count += 1

                # Candidate hit
                if (
                    top[
                        "actual_candidate"
                    ].max()
                    == 1
                ):
                    candidate_hit_count += 1

            total = len(
                target_dates
            )

            strong_rate = (
                hit_count
                / total
                * 100
                if total
                else 0
            )

            candidate_rate = (
                candidate_hit_count
                / total
                * 100
                if total
                else 0
            )

            summary_rows.append(
                {
                    "model":
                        model_name,

                    "metric":
                        f"TOP{top_n}_strong_hit",

                    "hit":
                        hit_count,

                    "total":
                        total,

                    "rate":
                        strong_rate,
                }
            )

            summary_rows.append(
                {
                    "model":
                        model_name,

                    "metric":
                        f"TOP{top_n}_candidate_hit",

                    "hit":
                        candidate_hit_count,

                    "total":
                        total,

                    "rate":
                        candidate_rate,
                }
            )

        # ----------------------------------------------------
        # Actual strong average rank
        # ----------------------------------------------------

        strong_ranks = model_df[
            model_df[
                "actual_strong"
            ] == 1
        ]["rank"]

        summary_rows.append(
            {
                "model":
                    model_name,

                "metric":
                    "actual_strong_average_rank",

                "hit":
                    None,

                "total":
                    len(strong_ranks),

                "rate":
                    (
                        strong_ranks.mean()
                        if len(strong_ranks)
                        else None
                    ),
            }
        )

        # ----------------------------------------------------
        # Actual strong median rank
        # ----------------------------------------------------

        summary_rows.append(
            {
                "model":
                    model_name,

                "metric":
                    "actual_strong_median_rank",

                "hit":
                    None,

                "total":
                    len(strong_ranks),

                "rate":
                    (
                        strong_ranks.median()
                        if len(strong_ranks)
                        else None
                    ),
            }
        )

    # ========================================================
    # Summary DataFrame
    # ========================================================

    summary_df = pd.DataFrame(
        summary_rows
    )

    summary_df.to_csv(
        SUMMARY_OUTPUT,
        index=False,
        encoding="utf-8-sig"
    )

    # ========================================================
    # Console output
    # ========================================================

    print()
    print("=" * 80)
    print("BACKTEST RESULT")
    print("=" * 80)

    print()

    for model_name in [
        "lag",
        "fixed",
        "combined",
    ]:

        print(
            "[" + model_name + "]"
        )

        model_summary = summary_df[
            summary_df["model"]
            == model_name
        ]

        for _, row in model_summary.iterrows():

            metric = row["metric"]

            hit = row["hit"]

            total = row["total"]

            rate = row["rate"]

            if (
                metric.endswith(
                    "_hit"
                )
                and hit is not None
            ):

                print(
                    f"  {metric}: "
                    f"{int(hit)}/{int(total)} "
                    f"({float(rate):.2f}%)"
                )

            else:

                if rate is None:

                    print(
                        f"  {metric}: N/A"
                    )

                else:

                    print(
                        f"  {metric}: "
                        f"{float(rate):.2f}"
                    )

        print()

    # ========================================================
    # Output
    # ========================================================

    print("=" * 80)
    print("OUTPUT")
    print("=" * 80)

    print(
        "detail :",
        DETAIL_OUTPUT
    )

    print(
        "summary:",
        SUMMARY_OUTPUT
    )

    print()
    print("=" * 80)
    print("BACKTEST END")
    print("=" * 80)


# ============================================================
# Entry
# ============================================================

if __name__ == "__main__":
    main()