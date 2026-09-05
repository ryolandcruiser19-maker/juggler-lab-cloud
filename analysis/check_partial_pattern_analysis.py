import sqlite3
from pathlib import Path

import pandas as pd


# ============================================================
# ジャグラーラボ
# その他2～3台候補・部分投入パターン分析
#
# 目的
# ------------------------------------------------------------
# 全台系・マイジャグラー3台並びとは別に、
# 「同一島・同一機種の一部だけが高評価になる」
# パターンが実際に存在するかを過去実績から検証する。
#
# 重要
# ------------------------------------------------------------
# ・prediction_scoreは使用しない
# ・予測スコアは作らない
# ・明日の候補台は選ばない
# ・まず過去実績の存在と頻度だけを確認する
#
# 2025/12～2026/02
# ------------------------------------------------------------
# 簡易データ期間。
# 現在の台数を分母にした精密な発生率には使用しない。
#
# 2026/03以降
# ------------------------------------------------------------
# 完全データ期間として別集計する。
# ============================================================


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
# 定数
# ============================================================

HIGH_EVALUATIONS = {
    "◎",
    "○",
}

NINE_DAYS = {
    9,
    19,
    29,
}

COMPLETE_DATA_START = pd.Timestamp(
    "2026-03-01"
)

SIMPLE_DATA_START = pd.Timestamp(
    "2025-12-01"
)

SIMPLE_DATA_END = pd.Timestamp(
    "2026-02-28"
)


# ============================================================
# 共通
# ============================================================

def normalize_island_name(value):
    if pd.isna(value):
        return ""

    return (
        str(value)
        .replace("🔴", "")
        .replace("🔵", "")
        .replace("🟢", "")
        .replace("🟣", "")
        .replace("🟠", "")
        .replace("🟡", "")
        .strip()
    )


def is_nine_day(value):
    try:
        date = pd.to_datetime(value)
        return date.day in NINE_DAYS
    except Exception:
        return False


def get_business_type(value):
    if is_nine_day(value):
        return "9の日"

    return "通常日"


# ============================================================
# テーブル・カラム確認
# ============================================================

def get_tables(conn):
    df = pd.read_sql(
        """
        SELECT
            name
        FROM sqlite_master
        WHERE type = 'table'
        ORDER BY name
        """,
        conn,
    )

    return set(df["name"].tolist())


def get_columns(conn, table_name):
    df = pd.read_sql(
        f"""
        PRAGMA table_info({table_name})
        """,
        conn,
    )

    if df.empty:
        return []

    return df["name"].tolist()


# ============================================================
# 最新営業日
# ============================================================

def get_latest_date(conn):
    df = pd.read_sql(
        """
        SELECT
            MAX(日付) AS 日付
        FROM daily_data
        """,
        conn,
    )

    if df.empty:
        return None

    value = df.iloc[0]["日付"]

    if pd.isna(value):
        return None

    return pd.to_datetime(value)


# ============================================================
# daily_data取得
# ============================================================

def get_daily_data(conn):
    """
    過去のdaily_dataを取得する。
    """

    columns = get_columns(
        conn,
        "daily_data",
    )

    required = [
        "日付",
        "機種",
        "台番号",
        "評価",
    ]

    missing = [
        column
        for column in required
        if column not in columns
    ]

    if missing:
        raise RuntimeError(
            "daily_dataに必要な列がありません: "
            + ", ".join(missing)
        )

    select_columns = [
        "日付",
        "店舗" if "店舗" in columns else None,
        "機種",
        "台番号",
        "BB" if "BB" in columns else None,
        "RB" if "RB" in columns else None,
        "G数" if "G数" in columns else None,
        "合成確率" if "合成確率" in columns else None,
        "評価",
    ]

    select_columns = [
        column
        for column in select_columns
        if column is not None
    ]

    sql = f"""
        SELECT
            {", ".join(select_columns)}
        FROM daily_data
        ORDER BY 日付, 台番号
    """

    df = pd.read_sql(
        sql,
        conn,
    )

    df["日付"] = pd.to_datetime(
        df["日付"],
        errors="coerce",
    )

    df = df.dropna(
        subset=["日付"]
    ).copy()

    return df


# ============================================================
# 島情報取得
# ============================================================

def get_island_map(conn, latest_date):
    """
    現在の台番号→島対応を取得する。

    daily_dataに島列がある場合はそれを使用。

    ない場合はmachines等から探す。
    """

    daily_columns = get_columns(
        conn,
        "daily_data",
    )

    # --------------------------------------------------------
    # daily_dataに島がある場合
    # --------------------------------------------------------

    if "島" in daily_columns:

        df = pd.read_sql(
            """
            SELECT
                台番号,
                島
            FROM daily_data
            WHERE 日付 = ?
            """,
            conn,
            params=[
                latest_date.strftime("%Y-%m-%d")
            ],
        )

        df["台番号"] = pd.to_numeric(
            df["台番号"],
            errors="coerce",
        )

        df["島"] = df["島"].apply(
            normalize_island_name
        )

        return (
            df.dropna(
                subset=["台番号"]
            )
            .drop_duplicates(
                subset=["台番号"]
            )
        )

    # --------------------------------------------------------
    # machinesを確認
    # --------------------------------------------------------

    tables = get_tables(conn)

    if "machines" in tables:

        columns = get_columns(
            conn,
            "machines",
        )

        machine_no_column = None
        island_column = None

        for column in [
            "台番号",
            "machine_no",
            "machine_number",
            "台番",
        ]:
            if column in columns:
                machine_no_column = column
                break

        for column in [
            "島",
            "島名",
            "island",
            "island_name",
        ]:
            if column in columns:
                island_column = column
                break

        if (
            machine_no_column is not None
            and island_column is not None
        ):

            df = pd.read_sql(
                f"""
                SELECT
                    {machine_no_column} AS 台番号,
                    {island_column} AS 島
                FROM machines
                """,
                conn,
            )

            df["台番号"] = pd.to_numeric(
                df["台番号"],
                errors="coerce",
            )

            df["島"] = df["島"].apply(
                normalize_island_name
            )

            return (
                df.dropna(
                    subset=["台番号"]
                )
                .drop_duplicates(
                    subset=["台番号"]
                )
            )

    # --------------------------------------------------------
    # 見つからない場合
    # --------------------------------------------------------

    return pd.DataFrame(
        columns=[
            "台番号",
            "島",
        ]
    )


# ============================================================
# 台番号→島を付与
# ============================================================

def attach_island(df, island_map):
    work = df.copy()

    work["台番号"] = pd.to_numeric(
        work["台番号"],
        errors="coerce",
    )

    if island_map.empty:
        work["島"] = ""
        return work

    work = work.merge(
        island_map,
        on="台番号",
        how="left",
    )

    work["島"] = work["島"].fillna(
        ""
    )

    return work


# ============================================================
# 同一島・同一機種の構成台数
# ============================================================

def build_current_machine_counts(
    conn,
    latest_date,
):
    """
    現在の完全データから、
    島×機種ごとの台数を取得する。

    重要
    --------------------------------------------------------
    これは2026/03以降の完全データの
    「現在の構成」を確認するために使用する。
    過去簡易データの分母には使用しない。
    """

    df = pd.read_sql(
        """
        SELECT
            日付,
            機種,
            台番号
        FROM daily_data
        WHERE 日付 = ?
        """,
        conn,
        params=[
            latest_date.strftime("%Y-%m-%d")
        ],
    )

    if df.empty:
        return pd.DataFrame()

    df["台番号"] = pd.to_numeric(
        df["台番号"],
        errors="coerce",
    )

    island_map = get_island_map(
        conn,
        latest_date,
    )

    df = attach_island(
        df,
        island_map,
    )

    result = (
        df.groupby(
            ["島", "機種"],
            dropna=False,
        )
        .agg(
            現在台数=(
                "台番号",
                "nunique",
            )
        )
        .reset_index()
    )

    return result


# ============================================================
# 高評価台の抽出
# ============================================================

def prepare_high_evaluation_data(
    df,
):
    work = df.copy()

    work["評価"] = (
        work["評価"]
        .fillna("")
        .astype(str)
        .str.strip()
    )

    work["高評価"] = work[
        "評価"
    ].isin(
        HIGH_EVALUATIONS
    )

    return work


# ============================================================
# 連番判定
# ============================================================

def classify_numbers(numbers):
    """
    台番号リストから、
    連番状況を判定する。
    """

    numbers = sorted(
        set(
            int(number)
            for number in numbers
            if pd.notna(number)
        )
    )

    count = len(numbers)

    if count == 0:
        return "なし"

    if count == 1:
        return "単台"

    if count == 2:
        if numbers[1] - numbers[0] == 1:
            return "2台連番"

        return "2台非連番"

    # 3台以上
    max_run = 1
    current_run = 1

    for index in range(
        1,
        len(numbers),
    ):

        if (
            numbers[index]
            - numbers[index - 1]
            == 1
        ):
            current_run += 1
            max_run = max(
                max_run,
                current_run,
            )
        else:
            current_run = 1

    if max_run >= 3:
        return "3台以上連番"

    if max_run == 2:
        return "2台連番を含む"

    return "非連番"


# ============================================================
# 島×機種ごとの日別分析
# ============================================================

def build_daily_pattern_analysis(
    df,
):
    """
    日付×島×機種ごとに
    高評価台数を集計する。
    """

    rows = []

    grouped = df.groupby(
        [
            "日付",
            "島",
            "機種",
        ],
        dropna=False,
    )

    for (
        date,
        island,
        machine,
    ), group in grouped:

        total_count = len(group)

        high_df = group[
            group["高評価"]
        ].copy()

        high_count = len(
            high_df
        )

        high_numbers = sorted(
            pd.to_numeric(
                high_df["台番号"],
                errors="coerce",
            )
            .dropna()
            .astype(int)
            .tolist()
        )

        rows.append(
            {
                "日付": date,
                "営業日タイプ": get_business_type(
                    date
                ),
                "島": normalize_island_name(
                    island
                ),
                "機種": machine,
                "記録台数": total_count,
                "高評価台数": high_count,
                "高評価台番号": ",".join(
                    map(
                        str,
                        high_numbers,
                    )
                ),
                "連番パターン": classify_numbers(
                    high_numbers
                ),
            }
        )

    return pd.DataFrame(
        rows
    )


# ============================================================
# 2～3台パターン抽出
# ============================================================

def get_partial_patterns(
    daily_patterns,
):
    """
    高評価2～3台のケースだけ抽出。
    """

    if daily_patterns.empty:
        return daily_patterns

    result = daily_patterns[
        daily_patterns["高評価台数"].isin(
            [2, 3]
        )
    ].copy()

    return result.sort_values(
        [
            "日付",
            "営業日タイプ",
            "島",
            "機種",
        ]
    )


# ============================================================
# 分布集計
# ============================================================

def print_distribution(
    daily_patterns,
):
    print()
    print("=" * 70)
    print("高評価台数分布")
    print("=" * 70)

    if daily_patterns.empty:
        print("データがありません。")
        return

    distribution = (
        daily_patterns.groupby(
            [
                "営業日タイプ",
                "高評価台数",
            ]
        )
        .size()
        .reset_index(
            name="発生日数"
        )
        .sort_values(
            [
                "営業日タイプ",
                "高評価台数",
            ]
        )
    )

    print(
        distribution.to_string(
            index=False
        )
    )


# ============================================================
# 2～3台パターン集計
# ============================================================

def print_partial_summary(
    partial_df,
):
    print()
    print("=" * 70)
    print("その他2～3台パターン実績")
    print("=" * 70)

    if partial_df.empty:
        print(
            "2～3台の高評価パターンはありません。"
        )
        return

    summary = (
        partial_df.groupby(
            [
                "営業日タイプ",
                "高評価台数",
            ]
        )
        .size()
        .reset_index(
            name="発生日数"
        )
    )

    print(
        summary.to_string(
            index=False
        )
    )

    print()
    print("連番パターン別")

    alignment_summary = (
        partial_df.groupby(
            [
                "営業日タイプ",
                "高評価台数",
                "連番パターン",
            ]
        )
        .size()
        .reset_index(
            name="発生日数"
        )
        .sort_values(
            [
                "営業日タイプ",
                "高評価台数",
                "発生日数",
            ],
            ascending=[
                True,
                True,
                False,
            ],
        )
    )

    print(
        alignment_summary.to_string(
            index=False
        )
    )


# ============================================================
# 機種別
# ============================================================

def print_machine_summary(
    partial_df,
):
    print()
    print("=" * 70)
    print("機種別 2～3台パターン")
    print("=" * 70)

    if partial_df.empty:
        print("データがありません。")
        return

    summary = (
        partial_df.groupby(
            [
                "営業日タイプ",
                "機種",
                "高評価台数",
            ]
        )
        .size()
        .reset_index(
            name="発生日数"
        )
        .sort_values(
            "発生日数",
            ascending=False,
        )
    )

    print(
        summary.to_string(
            index=False
        )
    )


# ============================================================
# 島別
# ============================================================

def print_island_summary(
    partial_df,
):
    print()
    print("=" * 70)
    print("島別 2～3台パターン")
    print("=" * 70)

    if partial_df.empty:
        print("データがありません。")
        return

    summary = (
        partial_df.groupby(
            [
                "営業日タイプ",
                "島",
                "機種",
                "高評価台数",
            ]
        )
        .size()
        .reset_index(
            name="発生日数"
        )
        .sort_values(
            "発生日数",
            ascending=False,
        )
    )

    print(
        summary.to_string(
            index=False
        )
    )


# ============================================================
# 最近の実例
# ============================================================

def print_recent_examples(
    partial_df,
):
    print()
    print("=" * 70)
    print("直近の2～3台パターン実例")
    print("=" * 70)

    if partial_df.empty:
        print("データがありません。")
        return

    output = (
        partial_df.sort_values(
            "日付",
            ascending=False,
        )
        .head(50)
        .copy()
    )

    print(
        output[
            [
                "日付",
                "営業日タイプ",
                "島",
                "機種",
                "記録台数",
                "高評価台数",
                "高評価台番号",
                "連番パターン",
            ]
        ].to_string(
            index=False
        )
    )


# ============================================================
# 期間別
# ============================================================

def print_period_summary(
    partial_df,
):
    print()
    print("=" * 70)
    print("データ期間別")
    print("=" * 70)

    if partial_df.empty:
        print("データがありません。")
        return

    work = partial_df.copy()

    work["データ期間"] = work[
        "日付"
    ].apply(
        lambda x:
        "簡易データ"
        if SIMPLE_DATA_START <= x <= SIMPLE_DATA_END
        else (
            "完全データ"
            if x >= COMPLETE_DATA_START
            else "対象外"
        )
    )

    summary = (
        work.groupby(
            [
                "データ期間",
                "営業日タイプ",
                "高評価台数",
            ]
        )
        .size()
        .reset_index(
            name="発生日数"
        )
    )

    print(
        summary.to_string(
            index=False
        )
    )


# ============================================================
# メイン分析
# ============================================================

def analyze(conn):
    latest_date = get_latest_date(
        conn
    )

    if latest_date is None:
        raise RuntimeError(
            "最新営業日を取得できません。"
        )

    print(
        "最新営業日:",
        latest_date.strftime(
            "%Y-%m-%d"
        ),
    )

    print()
    print(
        "分析対象:",
        "daily_dataの全期間"
    )

    # --------------------------------------------------------
    # データ取得
    # --------------------------------------------------------

    df = get_daily_data(
        conn
    )

    if df.empty:
        raise RuntimeError(
            "daily_dataが空です。"
        )

    # --------------------------------------------------------
    # 島情報
    # --------------------------------------------------------

    island_map = get_island_map(
        conn,
        latest_date,
    )

    if island_map.empty:
        print()
        print(
            "警告: 台番号→島の対応を取得できませんでした。"
        )
        print(
            "島別分析では島名が空欄になる可能性があります。"
        )

    df = attach_island(
        df,
        island_map,
    )

    # --------------------------------------------------------
    # 高評価判定
    # --------------------------------------------------------

    df = prepare_high_evaluation_data(
        df
    )

    # --------------------------------------------------------
    # 日別パターン
    # --------------------------------------------------------

    daily_patterns = (
        build_daily_pattern_analysis(
            df
        )
    )

    # --------------------------------------------------------
    # 分布
    # --------------------------------------------------------

    print_distribution(
        daily_patterns
    )

    # --------------------------------------------------------
    # 2～3台
    # --------------------------------------------------------

    partial_df = get_partial_patterns(
        daily_patterns
    )

    print_partial_summary(
        partial_df
    )

    print_machine_summary(
        partial_df
    )

    print_island_summary(
        partial_df
    )

    print_period_summary(
        partial_df
    )

    print_recent_examples(
        partial_df
    )

    return daily_patterns, partial_df


# ============================================================
# 実行
# ============================================================

def main():

    print("=" * 70)
    print(
        "ジャグラーラボ "
        "その他2～3台候補・部分投入パターン分析"
    )
    print("=" * 70)

    print()
    print(
        "DB:",
        DB_PATH,
    )

    print()
    print(
        "※ prediction_scoreは使用しません。"
    )

    print(
        "※ 予測スコアは作成しません。"
    )

    print(
        "※ 過去実績の存在・頻度だけを検証します。"
    )

    print(
        "※ ◎・○を高評価として扱います。"
    )

    print(
        "※ 2025/12～2026/02と2026/03以降を区別します。"
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

        analyze(
            conn
        )

    finally:

        conn.close()


if __name__ == "__main__":
    main()