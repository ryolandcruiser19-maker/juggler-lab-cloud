"""
ジャグラーラボ
Prediction Engine バックテスト準備

各分析テーブルについて、

・行数
・列名
・日付列の有無
・日付範囲
・最新日
・台数
・過去日を再現できそうか

を確認する。
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
# 安全な数値変換
# ============================================================

def safe_int(value, default=0):
    try:
        if pd.isna(value):
            return default

        return int(value)

    except (ValueError, TypeError):
        return default


# ============================================================
# テーブル存在確認
# ============================================================

def table_exists(conn, table_name):

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
# 日付列検出
# ============================================================

def find_date_columns(df):

    found = []

    for column in DATE_COLUMNS:

        if column in df.columns:
            found.append(column)

    return found


# ============================================================
# 1テーブル診断
# ============================================================

def inspect_table(conn, table_name):

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
        return

    try:

        df = pd.read_sql(
            f"""
            SELECT *
            FROM "{table_name}"
            """,
            conn,
        )

    except Exception as error:

        print(
            "読み込みエラー:",
            error,
        )

        return

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

    date_columns = find_date_columns(df)

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

        return

    for date_column in date_columns:

        print()
        print(
            f"--- {date_column} ---"
        )

        values = pd.to_datetime(
            df[date_column],
            errors="coerce",
        )

        valid = values.dropna()

        if valid.empty:

            print(
                "有効な日付データなし"
            )

            continue

        print(
            "最古日:",
            valid.min().strftime(
                "%Y-%m-%d"
            ),
        )

        print(
            "最新日:",
            valid.max().strftime(
                "%Y-%m-%d"
            ),
        )

        print(
            "日付種類数:",
            valid.dt.date.nunique(),
        )

        # 日付ごとの件数
        date_counts = (
            values
            .dt.strftime("%Y-%m-%d")
            .value_counts()
            .sort_index()
        )

        print()
        print(
            "日付別件数（先頭5日）:"
        )

        print(
            date_counts
            .head(5)
            .to_string()
        )

        print()
        print(
            "日付別件数（末尾5日）:"
        )

        print(
            date_counts
            .tail(5)
            .to_string()
        )


# ============================================================
# 全体診断
# ============================================================

def main():

    print("=" * 80)
    print(
        "Prediction Engine バックテスト準備診断"
    )
    print("=" * 80)

    print()
    print(
        "DB:",
        DB_PATH,
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

    try:

        for table_name in TARGET_TABLES:

            inspect_table(
                conn,
                table_name,
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


# ============================================================
# 実行
# ============================================================

if __name__ == "__main__":
    main()