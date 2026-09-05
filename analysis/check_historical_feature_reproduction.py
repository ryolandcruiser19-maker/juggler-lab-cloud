"""
ジャグラーラボ
過去時点Prediction Feature再現診断

対象：
・基礎台評価
・最近傾向評価

目的：
現在のPrediction Engineが利用している
machine_history_analysis
machine_pattern_analysis
を、

daily_dataだけから過去基準日で再現できるか確認する。
"""

import sqlite3
from pathlib import Path

import pandas as pd


# ============================================================
# DB
# ============================================================

BASE_DIR = Path(__file__).resolve().parent.parent

DB_PATH = (
    BASE_DIR
    / "database"
    / "juggler.db"
)


# ============================================================
# 対象期間
# ============================================================

BACKTEST_START = "2026-03-01"
BACKTEST_END = "2026-08-09"


# ============================================================
# 対象台
# ============================================================

TARGET_MACHINES = [
    ("マイジャグラーV", 979),
    ("マイジャグラーV", 1020),
    ("マイジャグラーV", 1035),
]


# ============================================================
# daily_data読み込み
# ============================================================

def load_daily_data(conn):

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
        WHERE 日付 >= ?
          AND 日付 <= ?
        ORDER BY 日付, 台番号
        """,
        conn,
        params=[
            BACKTEST_START,
            BACKTEST_END,
        ],
    )

    df["日付"] = pd.to_datetime(
        df["日付"],
        errors="coerce",
    )

    df["台番号"] = pd.to_numeric(
        df["台番号"],
        errors="coerce",
    )

    df["G数"] = pd.to_numeric(
        df["G数"],
        errors="coerce",
    )

    df["合成確率"] = pd.to_numeric(
        df["合成確率"],
        errors="coerce",
    )

    return df


# ============================================================
# 現在のmachine_history_analysis確認
# ============================================================

def inspect_current_history(conn):

    print()
    print("=" * 80)
    print("=== 現在の machine_history_analysis ===")
    print("=" * 80)

    df = pd.read_sql(
        """
        SELECT *
        FROM machine_history_analysis
        """,
        conn,
    )

    print()

    print(
        df[
            [
                "機種",
                "台番号",
                "稼働日数",
                "累計G数",
                "平均G数",
                "平均合成確率",
                "◎回数",
                "○回数",
                "高評価率",
                "最終日",
                "最終評価",
            ]
        ]
        .loc[
            df["台番号"].isin(
                [
                    number
                    for _, number in TARGET_MACHINES
                ]
            )
        ]
        .to_string(
            index=False
        )
    )


# ============================================================
# 現在のmachine_pattern_analysis確認
# ============================================================

def inspect_current_pattern(conn):

    print()
    print("=" * 80)
    print("=== 現在の machine_pattern_analysis ===")
    print("=" * 80)

    df = pd.read_sql(
        """
        SELECT *
        FROM machine_pattern_analysis
        """,
        conn,
    )

    df["分析日"] = pd.to_datetime(
        df["分析日"],
        errors="coerce",
    )

    df["台番号"] = pd.to_numeric(
        df["台番号"],
        errors="coerce",
    )

    target_numbers = [
        number
        for _, number in TARGET_MACHINES
    ]

    result = (
        df[
            df["台番号"].isin(
                target_numbers
            )
        ]
        .sort_values(
            [
                "台番号",
                "分析日",
            ]
        )
    )

    print()

    print(
        result[
            [
                "分析日",
                "台番号",
                "機種",
                "分析期間",
                "対象日数",
                "◎回数",
                "○回数",
                "◎率",
                "平均G数",
                "平均合成確率",
                "傾向スコア",
            ]
        ]
        .to_string(
            index=False
        )
    )


# ============================================================
# 過去基準日の履歴をdaily_dataから再計算
# ============================================================

def calculate_historical_machine_history(
    daily_data,
    target_date,
    machine_name,
    machine_number,
):

    work = daily_data[
        (
            daily_data["日付"]
            < target_date
        )
        &
        (
            daily_data["機種"]
            == machine_name
        )
        &
        (
            daily_data["台番号"]
            == machine_number
        )
    ].copy()

    if work.empty:
        return None

    return {
        "基準日": target_date,
        "機種": machine_name,
        "台番号": machine_number,
        "稼働日数": len(work),
        "累計G数": work["G数"].sum(),
        "平均G数": work["G数"].mean(),
        "平均合成確率": work["合成確率"].mean(),
        "◎回数": (
            work["評価"]
            .eq("◎")
            .sum()
        ),
        "○回数": (
            work["評価"]
            .eq("○")
            .sum()
        ),
        "高評価回数": (
            work["評価"]
            .isin(
                [
                    "◎",
                    "○",
                ]
            )
            .sum()
        ),
    }


# ============================================================
# 最近傾向
# ============================================================

def calculate_historical_pattern(
    daily_data,
    target_date,
    machine_name,
    machine_number,
    lookback_days=7,
):

    work = daily_data[
        (
            daily_data["日付"]
            < target_date
        )
        &
        (
            daily_data["機種"]
            == machine_name
        )
        &
        (
            daily_data["台番号"]
            == machine_number
        )
    ].copy()

    if work.empty:
        return None

    unique_dates = (
        work["日付"]
        .drop_duplicates()
        .sort_values(
            ascending=False
        )
        .head(
            lookback_days
        )
    )

    work = work[
        work["日付"].isin(
            unique_dates
        )
    ]

    if work.empty:
        return None

    return {
        "基準日": target_date,
        "機種": machine_name,
        "台番号": machine_number,
        "対象日数": len(
            unique_dates
        ),
        "◎回数": (
            work["評価"]
            .eq("◎")
            .sum()
        ),
        "○回数": (
            work["評価"]
            .eq("○")
            .sum()
        ),
        "◎率": (
            work["評価"]
            .eq("◎")
            .mean()
            * 100
        ),
        "平均G数": work[
            "G数"
        ].mean(),
        "平均合成確率": work[
            "合成確率"
        ].mean(),
    }


# ============================================================
# 過去再現結果
# ============================================================

def run_historical_test(
    daily_data,
):

    print()
    print("=" * 80)
    print("=== daily_dataからの過去時点再計算 ===")
    print("=" * 80)

    target_dates = pd.to_datetime(
        [
            "2026-08-01",
            "2026-08-03",
            "2026-08-05",
            "2026-08-09",
        ]
    )

    for target_date in target_dates:

        print()
        print(
            "-" * 80
        )

        print(
            "予測基準日:",
            target_date.strftime(
                "%Y-%m-%d"
            )
        )

        print(
            "予測対象日:",
            (
                target_date
                + pd.Timedelta(days=1)
            ).strftime(
                "%Y-%m-%d"
            )
        )

        print()

        history_rows = []

        pattern_rows = []

        for machine_name, machine_number in TARGET_MACHINES:

            history = (
                calculate_historical_machine_history(
                    daily_data,
                    target_date,
                    machine_name,
                    machine_number,
                )
            )

            pattern = (
                calculate_historical_pattern(
                    daily_data,
                    target_date,
                    machine_name,
                    machine_number,
                )
            )

            if history is not None:
                history_rows.append(
                    history
                )

            if pattern is not None:
                pattern_rows.append(
                    pattern
                )

        print(
            "--- 基礎台評価用 履歴 ---"
        )

        if history_rows:

            history_df = pd.DataFrame(
                history_rows
            )

            print(
                history_df.to_string(
                    index=False
                )
            )

        else:

            print(
                "データなし"
            )

        print()

        print(
            "--- 最近傾向用 直近7営業日 ---"
        )

        if pattern_rows:

            pattern_df = pd.DataFrame(
                pattern_rows
            )

            print(
                pattern_df.to_string(
                    index=False
                )
            )

        else:

            print(
                "データなし"
            )


# ============================================================
# main
# ============================================================

def main():

    print("=" * 80)
    print(
        "過去時点 Feature 再現診断"
    )
    print("=" * 80)

    print()
    print(
        "DB:",
        DB_PATH,
    )

    conn = sqlite3.connect(
        DB_PATH
    )

    try:

        daily_data = load_daily_data(
            conn
        )

        print()
        print(
            "daily_data:",
            len(daily_data),
            "行"
        )

        inspect_current_history(
            conn
        )

        inspect_current_pattern(
            conn
        )

        run_historical_test(
            daily_data
        )

        print()
        print()
        print("=" * 80)
        print(
            "診断終了"
        )
        print("=" * 80)

    finally:

        conn.close()


if __name__ == "__main__":
    main()