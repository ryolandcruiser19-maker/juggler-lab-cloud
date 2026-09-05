"""
ジャグラーラボ
Prediction Engine バックテスト準備診断 v2

目的
----
Prediction Engine の全期間バックテストに向けて、
各分析テーブルが過去日を再現できる状態か診断する。

確認内容
--------
・テーブル存在
・行数
・列
・日付列
・最古日 / 最新日
・日付種類数
・2026-03-01以降の日付種類数
・9の日の日数
・通常日の日数
・1日あたり平均行数
・daily_dataから再構築可能性
・バックテスト利用判定

重要
----
2025-12～2026-02は簡易データ期間として扱い、
本診断では2026-03-01以降を主要判定対象とする。
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
# 本検証開始日
# ============================================================

VALID_START_DATE = pd.Timestamp(
    "2026-03-01"
)


# ============================================================
# 確認対象テーブル
# ============================================================

TARGET_TABLES = [
    "daily_data",
    "machine_history_analysis",
    "machine_pattern_analysis",
    "island_analysis",
    "machine_holdover_analysis",
    "weekday_analysis",
    "number_tail_analysis",
    "store_condition_analysis",
    "alignment_analysis",
    "alignment_history_analysis",
    "alignment_history",
]


# ============================================================
# 日付候補列
# ============================================================

DATE_COLUMNS = [
    "日付",
    "分析日",
    "基準日",
    "予測日",
]


# ============================================================
# 9の日判定
# ============================================================

def is_nine_day(value):

    try:

        date = pd.to_datetime(value)

        return date.day in (
            9,
            19,
            29,
        )

    except Exception:

        return False


# ============================================================
# テーブル存在確認
# ============================================================

def table_exists(
    conn,
    table_name,
):

    result = pd.read_sql(
        """
        SELECT name
        FROM sqlite_master
        WHERE type = 'table'
        AND name = ?
        """,
        conn,
        params=[table_name],
    )

    return not result.empty


# ============================================================
# テーブル情報取得
# ============================================================

def load_table(
    conn,
    table_name,
):

    try:

        return pd.read_sql(
            f'''
            SELECT *
            FROM "{table_name}"
            ''',
            conn,
        )

    except Exception as error:

        print(
            "読み込みエラー:",
            error,
        )

        return pd.DataFrame()


# ============================================================
# 日付列検出
# ============================================================

def find_date_columns(df):

    found = []

    for column in DATE_COLUMNS:

        if column in df.columns:

            found.append(column)

    return found


# ============================================================
# 日付情報
# ============================================================

def analyze_date_column(
    df,
    date_column,
):

    values = pd.to_datetime(
        df[date_column],
        errors="coerce",
    )

    valid = values.dropna()

    if valid.empty:

        return None

    normalized = (
        valid
        .dt.normalize()
    )

    valid_period = normalized[
        normalized >= VALID_START_DATE
    ]

    nine_days = sum(
        is_nine_day(value)
        for value in valid_period
    )

    unique_dates = (
        normalized
        .drop_duplicates()
        .sort_values()
    )

    valid_unique_dates = (
        valid_period
        .drop_duplicates()
        .sort_values()
    )

    if len(valid_unique_dates) > 0:

        nine_unique_dates = sum(
            is_nine_day(value)
            for value in valid_unique_dates
        )

        normal_unique_dates = (
            len(valid_unique_dates)
            - nine_unique_dates
        )

    else:

        nine_unique_dates = 0
        normal_unique_dates = 0

    return {
        "最古日": normalized.min(),
        "最新日": normalized.max(),
        "日付種類数": normalized.nunique(),
        "2026-03-01以降日数": len(
            valid_unique_dates
        ),
        "2026-03-01以降9の日数": (
            nine_unique_dates
        ),
        "2026-03-01以降通常日日数": (
            normal_unique_dates
        ),
        "2026-03-01以降行数": len(
            valid_period
        ),
    }


# ============================================================
# 再構築可能性判定
# ============================================================

def judge_rebuildability(
    table_name,
    df,
    date_columns,
):

    # --------------------------------------------------------
    # daily_data
    # --------------------------------------------------------

    if table_name == "daily_data":

        if "日付" in df.columns:

            return (
                "◎",
                "元データ。過去日の再構築基盤として使用可能",
            )

        return (
            "×",
            "日付列なし",
        )

    # --------------------------------------------------------
    # 日付なし
    # --------------------------------------------------------

    if not date_columns:

        return (
            "△",
            "日付列なし。別テーブルから再生成する必要あり",
        )

    # --------------------------------------------------------
    # 基本的な再構築可能性
    # --------------------------------------------------------

    required_columns = [
        "日付",
    ]

    has_date = (
        "日付" in df.columns
    )

    # --------------------------------------------------------
    # 島分析
    # --------------------------------------------------------

    if table_name == "island_analysis":

        if (
            has_date
            and "島" in df.columns
        ):

            return (
                "◎",
                "daily_dataから島単位集計を再構築可能",
            )

        return (
            "△",
            "島列または日付列が不足",
        )

    # --------------------------------------------------------
    # 機種履歴
    # --------------------------------------------------------

    if table_name == "machine_history_analysis":

        if has_date:

            return (
                "◎",
                "daily_dataから台別履歴を再構築可能",
            )

        return (
            "△",
            "日付情報不足",
        )

    # --------------------------------------------------------
    # 機種パターン
    # --------------------------------------------------------

    if table_name == "machine_pattern_analysis":

        if has_date:

            return (
                "◎",
                "daily_dataから台別パターンを再構築可能性あり",
            )

        return (
            "△",
            "日付情報不足",
        )

    # --------------------------------------------------------
    # 並び分析
    # --------------------------------------------------------

    if table_name == "alignment_analysis":

        if has_date:

            return (
                "◎",
                "daily_dataから並び候補を再構築可能性あり",
            )

        return (
            "△",
            "日付情報不足",
        )

    # --------------------------------------------------------
    # 並び履歴
    # --------------------------------------------------------

    if table_name in (
        "alignment_history_analysis",
        "alignment_history",
    ):

        if has_date:

            return (
                "○",
                "過去データから再計算可能性あり。ただし履歴ロジック確認が必要",
            )

        return (
            "△",
            "日付情報不足",
        )

    # --------------------------------------------------------
    # その他
    # --------------------------------------------------------

    if has_date:

        return (
            "○",
            "日付あり。再構築ロジック確認が必要",
        )

    return (
        "△",
        "日付情報不足",
    )


# ============================================================
# 1テーブル診断
# ============================================================

def inspect_table(
    conn,
    table_name,
):

    print()
    print("=" * 80)
    print(
        f"=== {table_name} ==="
    )
    print("=" * 80)

    if not table_exists(
        conn,
        table_name,
    ):

        print("テーブルなし")

        return {
            "テーブル": table_name,
            "存在": "×",
            "行数": 0,
            "最古日": "",
            "最新日": "",
            "日付種類数": 0,
            "本検証日数": 0,
            "9の日": 0,
            "通常日": 0,
            "判定": "×",
            "備考": "テーブルなし",
        }

    df = load_table(
        conn,
        table_name,
    )

    print()
    print(
        "行数:",
        len(df),
    )

    print()
    print("列:")

    for column in df.columns:

        print(
            " ",
            column,
        )

    date_columns = find_date_columns(
        df
    )

    print()
    print(
        "日付候補列:",
        date_columns,
    )

    if not date_columns:

        print()
        print(
            "判定: 日付列なし"
        )

        return {
            "テーブル": table_name,
            "存在": "○",
            "行数": len(df),
            "最古日": "",
            "最新日": "",
            "日付種類数": 0,
            "本検証日数": 0,
            "9の日": 0,
            "通常日": 0,
            "判定": "△",
            "備考": "日付列なし",
        }

    # 基本的には「日付」を優先
    if "日付" in date_columns:

        date_column = "日付"

    else:

        date_column = date_columns[0]

    info = analyze_date_column(
        df,
        date_column,
    )

    if info is None:

        print(
            "有効な日付データなし"
        )

        return {
            "テーブル": table_name,
            "存在": "○",
            "行数": len(df),
            "最古日": "",
            "最新日": "",
            "日付種類数": 0,
            "本検証日数": 0,
            "9の日": 0,
            "通常日": 0,
            "判定": "×",
            "備考": "有効な日付なし",
        }

    print()
    print(
        "使用日付列:",
        date_column,
    )

    print(
        "最古日:",
        info["最古日"].strftime(
            "%Y-%m-%d"
        ),
    )

    print(
        "最新日:",
        info["最新日"].strftime(
            "%Y-%m-%d"
        ),
    )

    print(
        "日付種類数:",
        info["日付種類数"],
    )

    print(
        "2026-03-01以降日数:",
        info["2026-03-01以降日数"],
    )

    print(
        "2026-03-01以降9の日数:",
        info["2026-03-01以降9の日数"],
    )

    print(
        "2026-03-01以降通常日日数:",
        info["2026-03-01以降通常日日数"],
    )

    print(
        "2026-03-01以降行数:",
        info["2026-03-01以降行数"],
    )

    judge, comment = judge_rebuildability(
        table_name,
        df,
        date_columns,
    )

    print()
    print(
        "再構築可能性:",
        judge,
    )

    print(
        "判定:",
        comment,
    )

    return {
        "テーブル": table_name,
        "存在": "○",
        "行数": len(df),
        "最古日": info["最古日"].strftime(
            "%Y-%m-%d"
        ),
        "最新日": info["最新日"].strftime(
            "%Y-%m-%d"
        ),
        "日付種類数": info["日付種類数"],
        "本検証日数": info[
            "2026-03-01以降日数"
        ],
        "9の日": info[
            "2026-03-01以降9の日数"
        ],
        "通常日": info[
            "2026-03-01以降通常日日数"
        ],
        "判定": judge,
        "備考": comment,
    }


# ============================================================
# 全体診断
# ============================================================

def main():

    print("=" * 80)
    print(
        "Prediction Engine バックテスト準備診断 v2"
    )
    print("=" * 80)

    print()
    print(
        "DB:",
        DB_PATH,
    )

    print()
    print(
        "本検証開始日:",
        VALID_START_DATE.strftime(
            "%Y-%m-%d"
        ),
    )

    if not DB_PATH.exists():

        print()
        print(
            "DBが見つかりません。"
        )

        return

    conn = sqlite3.connect(
        DB_PATH
    )

    results = []

    try:

        for table_name in TARGET_TABLES:

            result = inspect_table(
                conn,
                table_name,
            )

            results.append(
                result
            )

    finally:

        conn.close()

    # ========================================================
    # 総合一覧
    # ========================================================

    summary = pd.DataFrame(
        results
    )

    print()
    print()
    print("=" * 80)
    print(
        "=== 総合診断一覧 ==="
    )
    print("=" * 80)

    print()

    display_columns = [
        "テーブル",
        "存在",
        "行数",
        "最古日",
        "最新日",
        "日付種類数",
        "本検証日数",
        "9の日",
        "通常日",
        "判定",
    ]

    print(
        summary[
            display_columns
        ].to_string(
            index=False
        )
    )

    # ========================================================
    # 判定別
    # ========================================================

    print()
    print(
        "=== 判定別 ==="
    )

    for judge in [
        "◎",
        "○",
        "△",
        "×",
    ]:

        target = summary[
            summary["判定"] == judge
        ]

        print()
        print(
            f"{judge}: {len(target)} テーブル"
        )

        if not target.empty:

            for table_name in target[
                "テーブル"
            ]:

                print(
                    "  ",
                    table_name,
                )

    # ========================================================
    # 9の日確認
    # ========================================================

    print()
    print(
        "=== 9の日データ保持状況 ==="
    )

    nine_summary = summary[
        [
            "テーブル",
            "9の日",
            "本検証日数",
            "判定",
        ]
    ].copy()

    print(
        nine_summary.to_string(
            index=False
        )
    )

    # ========================================================
    # CSV保存
    # ========================================================

    output_dir = (
        BASE_DIR
        / "analysis"
        / "backtest_output"
    )

    output_dir.mkdir(
        parents=True,
        exist_ok=True,
    )

    output_path = (
        output_dir
        / "backtest_table_diagnosis.csv"
    )

    summary.to_csv(
        output_path,
        index=False,
        encoding="utf-8-sig",
    )

    print()
    print(
        "診断結果CSV:",
        output_path,
    )

    print()
    print("=" * 80)
    print(
        "診断終了"
    )
    print("=" * 80)


# ============================================================
# 実行
# ============================================================

if __name__ == "__main__":
    main()