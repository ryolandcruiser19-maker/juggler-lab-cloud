"""
ジャグラーラボ
prediction_score 分布診断

## 目的

prediction_score が、

・特定機種に偏っていないか
・特定台番号に偏っていないか
・9の日 / 通常日で構造が違うか
・総合スコアをどの項目が押し上げているか

を確認する。

## 重要

・DBは読み取り専用
・daily_dataは答え合わせには使用しない
・prediction_scoreのみを分析する
・未来情報を追加しない
"""

import sqlite3
from pathlib import Path

import pandas as pd

# ============================================================
# 安全な数値変換
# ============================================================

def safe_float(value, default=0.0):
    """
    None / NaN / 数値文字列などを安全にfloatへ変換する。
    """

    try:
        if pd.isna(value):
            return default

        return float(value)

    except (ValueError, TypeError):
        return default

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
# 設定
# ============================================================

START_DATE = "2026-03-01"
END_DATE = "2026-08-09"

NINE_DAYS = {
    9,
    19,
    29,
}


# ============================================================
# 共通関数
# ============================================================

def is_nine_day(date_value):
    """
    9 / 19 / 29 を9の日として扱う。
    """

    try:
        date = pd.to_datetime(date_value)

        return date.day in NINE_DAYS

    except Exception:
        return False


def safe_numeric(df, columns):
    """
    指定列を数値化する。
    """

    for column in columns:

        if column in df.columns:

            df[column] = pd.to_numeric(
                df[column],
                errors="coerce",
            )

    return df


# ============================================================
# prediction_score取得
# ============================================================

def get_prediction_scores(conn):

    sql = """
        SELECT
            日付,
            台番号,
            機種,
            島,
            基礎台評価,
            最近傾向評価,
            島評価,
            並び評価,
            イベント補正,
            店舗状態補正,
            曜日補正,
            末尾補正,
            前日高評価補正,
            据置期待補正,
            リセット傾向補正,
            並び期待補正,
            総合スコア,
            判定
        FROM prediction_score
        WHERE 日付 >= ?
          AND 日付 <= ?
        ORDER BY
            日付,
            総合スコア DESC
    """

    df = pd.read_sql(
        sql,
        conn,
        params=[
            START_DATE,
            END_DATE,
        ],
    )

    if df.empty:
        return df

    df["日付"] = pd.to_datetime(
        df["日付"],
        errors="coerce",
    )

    df["台番号"] = pd.to_numeric(
        df["台番号"],
        errors="coerce",
    )

    numeric_columns = [
        "基礎台評価",
        "最近傾向評価",
        "島評価",
        "並び評価",
        "イベント補正",
        "店舗状態補正",
        "曜日補正",
        "末尾補正",
        "前日高評価補正",
        "据置期待補正",
        "リセット傾向補正",
        "並び期待補正",
        "総合スコア",
    ]

    df = safe_numeric(
        df,
        numeric_columns,
    )

    df["営業日タイプ"] = df[
        "日付"
    ].apply(
        lambda x:
            "9の日"
            if is_nine_day(x)
            else "通常日"
    )

    return df


# ============================================================
# 1. 基本情報
# ============================================================

def print_basic_info(df):

    print()
    print("=" * 80)
    print("=== 1. prediction_score 基本情報 ===")
    print("=" * 80)

    print()

    if df.empty:

        print(
            "prediction_scoreに対象データがありません。"
        )

        return

    print(
        f"期間: {START_DATE} ～ {END_DATE}"
    )

    print(
        f"件数: {len(df):,}"
    )

    print(
        f"日数: {df['日付'].nunique()}"
    )

    print(
        f"機種数: {df['機種'].nunique()}"
    )

    print(
        f"台番号数: {df['台番号'].nunique()}"
    )

    print()

    daily = (
        df.groupby("日付")
        .agg(
            台数=("台番号", "count"),
            機種数=("機種", "nunique"),
            最小スコア=("総合スコア", "min"),
            最大スコア=("総合スコア", "max"),
            平均スコア=("総合スコア", "mean"),
        )
        .reset_index()
    )

    daily["日付"] = (
        daily["日付"]
        .dt.strftime("%Y-%m-%d")
    )

    print(
        daily.to_string(
            index=False,
            formatters={
                "最小スコア":
                    "{:.2f}".format,
                "最大スコア":
                    "{:.2f}".format,
                "平均スコア":
                    "{:.2f}".format,
            },
        )
    )


# ============================================================
# 2. 日別TOP10
# ============================================================

def print_daily_top10(df):

    print()
    print("=" * 80)
    print("=== 2. 日別 TOP10 ===")
    print("=" * 80)

    if df.empty:
        return

    for target_date, group in df.groupby(
        "日付",
        sort=True,
    ):

        target_type = (
            "9の日"
            if is_nine_day(target_date)
            else "通常日"
        )

        top = (
            group
            .sort_values(
                [
                    "総合スコア",
                    "台番号",
                ],
                ascending=[
                    False,
                    True,
                ],
            )
            .head(10)
            .copy()
        )

        top["順位"] = range(
            1,
            len(top) + 1,
        )

        print()
        print(
            f"--- {target_date:%Y-%m-%d} "
            f"({target_type}) ---"
        )

        output = top[
            [
                "順位",
                "台番号",
                "機種",
                "島",
                "総合スコア",
                "基礎台評価",
                "最近傾向評価",
                "島評価",
                "並び評価",
                "イベント補正",
                "店舗状態補正",
                "曜日補正",
                "末尾補正",
                "前日高評価補正",
                "据置期待補正",
                "リセット傾向補正",
                "並び期待補正",
            ]
        ]

        print(
            output.to_string(
                index=False,
            )
        )


# ============================================================
# 3. 機種別スコア
# ============================================================

def print_machine_summary(df):

    print()
    print("=" * 80)
    print("=== 3. 機種別 スコア分布 ===")
    print("=" * 80)

    if df.empty:
        return

    summary = (
        df.groupby(
            [
                "営業日タイプ",
                "機種",
            ]
        )
        .agg(
            件数=("台番号", "count"),
            平均スコア=(
                "総合スコア",
                "mean",
            ),
            最大スコア=(
                "総合スコア",
                "max",
            ),
            最小スコア=(
                "総合スコア",
                "min",
            ),
        )
        .reset_index()
    )

    summary = summary.sort_values(
        [
            "営業日タイプ",
            "平均スコア",
        ],
        ascending=[
            True,
            False,
        ],
    )

    print()

    print(
        summary.to_string(
            index=False,
            formatters={
                "平均スコア":
                    "{:.2f}".format,
                "最大スコア":
                    "{:.2f}".format,
                "最小スコア":
                    "{:.2f}".format,
            },
        )
    )


# ============================================================
# 4. 台番号別スコア
# ============================================================

def print_machine_number_summary(df):

    print()
    print("=" * 80)
    print("=== 4. 台番号別 スコア分布 ===")
    print("=" * 80)

    if df.empty:
        return

    summary = (
        df.groupby(
            [
                "機種",
                "台番号",
            ]
        )
        .agg(
            件数=("日付", "count"),
            平均スコア=(
                "総合スコア",
                "mean",
            ),
            最大スコア=(
                "総合スコア",
                "max",
            ),
            最小スコア=(
                "総合スコア",
                "min",
            ),
        )
        .reset_index()
    )

    summary = summary.sort_values(
        "平均スコア",
        ascending=False,
    )

    print()

    print(
        "=== 平均スコア 上位30台 ==="
    )

    print()

    print(
        summary.head(30).to_string(
            index=False,
            formatters={
                "平均スコア":
                    "{:.2f}".format,
                "最大スコア":
                    "{:.2f}".format,
                "最小スコア":
                    "{:.2f}".format,
            },
        )
    )


# ============================================================
# 5. TOP3への登場回数
# ============================================================

def print_top3_frequency(df):

    print()
    print("=" * 80)
    print("=== 5. TOP3 登場回数 ===")
    print("=" * 80)

    if df.empty:
        return

    work = df.copy()

    work["日別順位"] = (
        work.groupby("日付")[
            "総合スコア"
        ]
        .rank(
            method="first",
            ascending=False,
        )
    )

    top3 = work[
        work["日別順位"] <= 3
    ].copy()

    print()
    print("=== 機種別 ===")

    machine = (
        top3.groupby(
            [
                "営業日タイプ",
                "機種",
            ]
        )
        .agg(
            TOP3登場回数=(
                "日付",
                "count",
            ),
            登場日数=(
                "日付",
                "nunique",
            ),
        )
        .reset_index()
        .sort_values(
            "TOP3登場回数",
            ascending=False,
        )
    )

    print(
        machine.to_string(
            index=False,
        )
    )

    print()
    print("=== 台番号別 ===")

    number = (
        top3.groupby(
            [
                "機種",
                "台番号",
            ]
        )
        .agg(
            TOP3登場回数=(
                "日付",
                "count",
            ),
            登場日数=(
                "日付",
                "nunique",
            ),
        )
        .reset_index()
        .sort_values(
            "TOP3登場回数",
            ascending=False,
        )
        .head(30)
    )

    print(
        number.to_string(
            index=False,
        )
    )


# ============================================================
# 6. TOP3の機種集中度
# ============================================================

def print_top3_concentration(df):

    print()
    print("=" * 80)
    print("=== 6. TOP3 機種集中度 ===")
    print("=" * 80)

    if df.empty:
        return

    work = df.copy()

    work["日別順位"] = (
        work.groupby("日付")[
            "総合スコア"
        ]
        .rank(
            method="first",
            ascending=False,
        )
    )

    top3 = work[
        work["日別順位"] <= 3
    ].copy()

    rows = []

    for target_date, group in top3.groupby(
        "日付",
        sort=True,
    ):

        counts = (
            group["機種"]
            .value_counts()
        )

        max_count = (
            counts.iloc[0]
            if not counts.empty
            else 0
        )

        unique_machine = (
            group["機種"]
            .nunique()
        )

        rows.append(
            {
                "日付":
                    target_date,
                "営業日タイプ":
                    (
                        "9の日"
                        if is_nine_day(
                            target_date
                        )
                        else "通常日"
                    ),
                "TOP3機種数":
                    unique_machine,
                "最多機種台数":
                    max_count,
                "同一機種3台":
                    max_count == 3,
                "同一機種2台以上":
                    max_count >= 2,
            }
        )

    result = pd.DataFrame(rows)

    result["日付"] = (
        result["日付"]
        .dt.strftime("%Y-%m-%d")
    )

    print()

    print(
        result.to_string(
            index=False,
        )
    )

    print()

    summary = (
        result.groupby(
            "営業日タイプ"
        )
        .agg(
            営業日数=(
                "日付",
                "count",
            ),
            同一機種3台日数=(
                "同一機種3台",
                "sum",
            ),
            同一機種2台以上日数=(
                "同一機種2台以上",
                "sum",
            ),
        )
        .reset_index()
    )

    summary["同一機種3台率"] = (
        summary["同一機種3台日数"]
        / summary["営業日数"]
        * 100
    )

    summary["同一機種2台以上率"] = (
        summary["同一機種2台以上日数"]
        / summary["営業日数"]
        * 100
    )

    print(
        summary.to_string(
            index=False,
            formatters={
                "同一機種3台率":
                    "{:.2f}".format,
                "同一機種2台以上率":
                    "{:.2f}".format,
            },
        )
    )


# ============================================================
# 7. TOP3スコア差と実績
# ============================================================

def print_top3_score_gap(df):
    """
    TOP3のスコア差と、実際の高評価との関係を確認する。
    """

    print()
    print("=" * 80)
    print("=== 7. TOP3 スコア差と実績 ===")
    print("=" * 80)

    work = df.copy()

    work["日付"] = pd.to_datetime(
        work["日付"],
        errors="coerce",
    )

    work["総合スコア"] = pd.to_numeric(
        work["総合スコア"],
        errors="coerce",
    )

    work = work.dropna(
        subset=[
            "日付",
            "総合スコア",
        ]
    )

    rows = []

    for target_date, group in work.groupby("日付"):

        group = group.sort_values(
            "総合スコア",
            ascending=False,
        ).head(3)

        if len(group) < 3:
            continue

        scores = group[
            "総合スコア"
        ].tolist()

        rows.append(
            {
                "日付": target_date,
                "営業日タイプ": (
                    "9の日"
                    if is_nine_day(target_date)
                    else "通常日"
                ),
                "1位": scores[0],
                "2位": scores[1],
                "3位": scores[2],
                "1位-2位": scores[0] - scores[1],
                "2位-3位": scores[1] - scores[2],
                "1位-3位": scores[0] - scores[2],
            }
        )

    if not rows:
        print()
        print("TOP3スコア差を計算できる日がありません。")
        return

    summary = pd.DataFrame(rows)

    print()
    print(
        summary.to_string(
            index=False,
            formatters={
                "1位": "{:.2f}".format,
                "2位": "{:.2f}".format,
                "3位": "{:.2f}".format,
                "1位-2位": "{:.2f}".format,
                "2位-3位": "{:.2f}".format,
                "1位-3位": "{:.2f}".format,
            }
        )
    )

    print()
    print("--- スコア差の統計 ---")

    stat = (
        summary
        .groupby("営業日タイプ")
        .agg(
            営業日数=("日付", "count"),
            平均1位2位差=("1位-2位", "mean"),
            平均2位3位差=("2位-3位", "mean"),
            平均1位3位差=("1位-3位", "mean"),
            中央値1位3位差=("1位-3位", "median"),
            最大1位3位差=("1位-3位", "max"),
        )
        .reset_index()
    )

    print()

    print(
        stat.to_string(
            index=False,
            formatters={
                "平均1位2位差": "{:.2f}".format,
                "平均2位3位差": "{:.2f}".format,
                "平均1位3位差": "{:.2f}".format,
                "中央値1位3位差": "{:.2f}".format,
                "最大1位3位差": "{:.2f}".format,
            }
        )
    )

    # --------------------------------------------------------
    # スコア差の大小で分類
    # --------------------------------------------------------

    print()
    print("--- スコア差による分類 ---")

    summary["スコア差区分"] = pd.cut(
        summary["1位-3位"],
        bins=[
            -0.000001,
            5,
            10,
            20,
            float("inf"),
        ],
        labels=[
            "0～5",
            "5～10",
            "10～20",
            "20以上",
        ],
    )

    print()

    print(
        summary[
            [
                "日付",
                "営業日タイプ",
                "1位-3位",
                "スコア差区分",
            ]
        ].to_string(
            index=False,
            formatters={
                "1位-3位": "{:.2f}".format,
            }
        )
    )


# ============================================================
# 8. TOP3機種集中度と実績
# ============================================================

def print_top3_machine_concentration(df):
    """
    TOP3の機種集中度と、実際の高評価との関係を確認する。
    """

    print()
    print("=" * 80)
    print("=== 8. TOP3 機種集中度と実績 ===")
    print("=" * 80)

    work = df.copy()

    work["日付"] = pd.to_datetime(
        work["日付"],
        errors="coerce",
    )

    work["総合スコア"] = pd.to_numeric(
        work["総合スコア"],
        errors="coerce",
    )

    work = work.dropna(
        subset=[
            "日付",
            "総合スコア",
        ]
    )

    rows = []

    for target_date, group in work.groupby("日付"):

        top = (
            group
            .sort_values(
                "総合スコア",
                ascending=False,
            )
            .head(3)
            .copy()
        )

        if len(top) < 3:
            continue

        machine_counts = (
            top["機種"]
            .astype(str)
            .value_counts()
        )

        max_count = int(
            machine_counts.iloc[0]
        )

        machine_count = int(
            machine_counts.shape[0]
        )

        if max_count >= 3:
            concentration = "同一機種3台"
        elif max_count == 2:
            concentration = "同一機種2台"
        else:
            concentration = "3機種分散"

        rows.append(
            {
                "日付": target_date,
                "営業日タイプ": (
                    "9の日"
                    if is_nine_day(target_date)
                    else "通常日"
                ),
                "TOP3機種数": machine_count,
                "最多機種台数": max_count,
                "集中区分": concentration,
            }
        )

    if not rows:
        print()
        print("TOP3機種集中度を計算できる日がありません。")
        return

    summary = pd.DataFrame(rows)

    print()

    print(
        summary.to_string(
            index=False
        )
    )

    # --------------------------------------------------------
    # 日数集計
    # --------------------------------------------------------

    type_summary = (
        summary
        .groupby("営業日タイプ")
        .agg(
            営業日数=("日付", "count"),
            同一機種3台日数=(
                "最多機種台数",
                lambda x: int((x >= 3).sum()),
            ),
            同一機種2台以上日数=(
                "最多機種台数",
                lambda x: int((x >= 2).sum()),
            ),
        )
        .reset_index()
    )

    type_summary[
        "同一機種3台率"
    ] = (
        type_summary["同一機種3台日数"]
        / type_summary["営業日数"]
        * 100
    )

    type_summary[
        "同一機種2台以上率"
    ] = (
        type_summary["同一機種2台以上日数"]
        / type_summary["営業日数"]
        * 100
    )

    print()
    print("--- 機種集中度の日数集計 ---")
    print()

    print(
        type_summary.to_string(
            index=False,
            formatters={
                "同一機種3台率":
                    "{:.2f}".format,
                "同一機種2台以上率":
                    "{:.2f}".format,
            }
        )
    )


# ============================================================
# 9. TOP3機種別の実績
# ============================================================

def print_top3_machine_performance(df):
    """
    TOP3に登場した機種・台番号の偏りを確認する。
    """

    print()
    print("=" * 80)
    print("=== 9. TOP3 機種・台番号集中 ===")
    print("=" * 80)

    work = df.copy()

    work["日付"] = pd.to_datetime(
        work["日付"],
        errors="coerce",
    )

    work["総合スコア"] = pd.to_numeric(
        work["総合スコア"],
        errors="coerce",
    )

    work = work.dropna(
        subset=[
            "日付",
            "総合スコア",
        ]
    )

    top_list = []

    for target_date, group in work.groupby("日付"):

        top = (
            group
            .sort_values(
                "総合スコア",
                ascending=False,
            )
            .head(3)
            .copy()
        )

        if len(top) < 3:
            continue

        top["営業日タイプ"] = (
            "9の日"
            if is_nine_day(target_date)
            else "通常日"
        )

        top_list.append(top)

    if not top_list:
        print()
        print("TOP3データがありません。")
        return

    top_df = pd.concat(
        top_list,
        ignore_index=True,
    )

    # --------------------------------------------------------
    # 機種別
    # --------------------------------------------------------

    machine_summary = (
        top_df
        .groupby(
            [
                "営業日タイプ",
                "機種",
            ]
        )
        .agg(
            TOP3登場回数=(
                "台番号",
                "count",
            ),
            登場日数=(
                "日付",
                "nunique",
            ),
        )
        .reset_index()
        .sort_values(
            [
                "営業日タイプ",
                "TOP3登場回数",
            ],
            ascending=[
                True,
                False,
            ],
        )
    )

    print()
    print("=== 機種別 ===")

    print(
        machine_summary.to_string(
            index=False
        )
    )

    # --------------------------------------------------------
    # 台番号別
    # --------------------------------------------------------

    machine_number_summary = (
        top_df
        .groupby(
            [
                "機種",
                "台番号",
            ]
        )
        .agg(
            TOP3登場回数=(
                "日付",
                "count",
            ),
            登場日数=(
                "日付",
                "nunique",
            ),
        )
        .reset_index()
        .sort_values(
            "TOP3登場回数",
            ascending=False,
        )
    )

    print()
    print("=== 台番号別 ===")

    print(
        machine_number_summary.to_string(
            index=False
        )
    )

# ============================================================
# 10. TOP3 機種集中 × 実績
# ============================================================

def print_top3_machine_concentration_performance(df):
    """
    TOP3の機種集中と、実際の高評価との関係を確認する。
    """

    print()
    print("=" * 80)
    print("=== 10. TOP3 機種集中 × 実績 ===")
    print("=" * 80)

    work = df.copy()

    work["日付"] = pd.to_datetime(
        work["日付"],
        errors="coerce",
    )

    work["総合スコア"] = pd.to_numeric(
        work["総合スコア"],
        errors="coerce",
    )

    work = work.dropna(
        subset=[
            "日付",
            "総合スコア",
        ]
    )

    rows = []

    for target_date, group in work.groupby("日付"):

        top = (
            group
            .sort_values(
                "総合スコア",
                ascending=False,
            )
            .head(3)
            .copy()
        )

        if len(top) < 3:
            continue

        top["営業日タイプ"] = (
            "9の日"
            if is_nine_day(target_date)
            else "通常日"
        )

        machine_counts = (
            top["機種"]
            .astype(str)
            .value_counts()
        )

        if machine_counts.empty:
            continue

        top_machine = machine_counts.index[0]

        top_machine_count = int(
            machine_counts.iloc[0]
        )

        top_machine_rows = top[
            top["機種"].astype(str) == str(top_machine)
        ]

        row = {
            "日付": target_date,
            "営業日タイプ": (
                "9の日"
                if is_nine_day(target_date)
                else "通常日"
            ),
            "最多機種": top_machine,
            "最多機種台数": top_machine_count,
        }

        # ----------------------------------------------------
        # 実績列が存在する場合のみ集計
        # ----------------------------------------------------

        if "高評価" in top.columns:
            row["最多機種高評価台数"] = int(
                pd.to_numeric(
                    top_machine_rows["高評価"],
                    errors="coerce",
                )
                .fillna(0)
                .sum()
            )

            row["最多機種高評価率"] = (
                pd.to_numeric(
                    top_machine_rows["高評価"],
                    errors="coerce",
                )
                .mean()
                * 100
            )

        if "◎" in top.columns:
            row["最多機種◎台数"] = int(
                pd.to_numeric(
                    top_machine_rows["◎"],
                    errors="coerce",
                )
                .fillna(0)
                .sum()
            )

        if "○" in top.columns:
            row["最多機種○台数"] = int(
                pd.to_numeric(
                    top_machine_rows["○"],
                    errors="coerce",
                )
                .fillna(0)
                .sum()
            )

        rows.append(row)

    if not rows:
        print()
        print("TOP3機種集中 × 実績を計算できる日がありません。")
        return

    summary = pd.DataFrame(rows)

    print()
    print("--- 日付別 ---")
    print()

    print(
        summary.to_string(
            index=False
        )
    )

    # --------------------------------------------------------
    # 営業日タイプ別集計
    # --------------------------------------------------------

    print()
    print("--- 営業日タイプ別 ---")
    print()

    agg_dict = {
        "営業日数": pd.NamedAgg(
            column="日付",
            aggfunc="count",
        ),
        "平均最多機種台数": pd.NamedAgg(
            column="最多機種台数",
            aggfunc="mean",
        ),
    }

    if "最多機種高評価台数" in summary.columns:
        agg_dict[
            "平均最多機種高評価台数"
        ] = pd.NamedAgg(
            column="最多機種高評価台数",
            aggfunc="mean",
        )

    if "最多機種◎台数" in summary.columns:
        agg_dict[
            "平均最多機種◎台数"
        ] = pd.NamedAgg(
            column="最多機種◎台数",
            aggfunc="mean",
        )

    if "最多機種○台数" in summary.columns:
        agg_dict[
            "平均最多機種○台数"
        ] = pd.NamedAgg(
            column="最多機種○台数",
            aggfunc="mean",
        )

    if "最多機種高評価率" in summary.columns:
        agg_dict[
            "平均最多機種高評価率"
        ] = pd.NamedAgg(
            column="最多機種高評価率",
            aggfunc="mean",
        )

    type_summary = (
        summary
        .groupby("営業日タイプ")
        .agg(**agg_dict)
        .reset_index()
    )

    print(
        type_summary.to_string(
            index=False
        )
    )

# ============================================================
# 11. TOP3 スコア差 × 実績
# ============================================================

def print_top3_score_gap_performance(df):

    print()
    print("=" * 80)
    print("=== 11. TOP3 スコア差 × 実績 ===")
    print("=" * 80)

    # --------------------------------------------------------
    # 必要列確認
    # --------------------------------------------------------

    required_columns = [
        "日付",
        "営業日タイプ",
        "総合スコア",
        "台番号",
    ]

    missing_columns = [
        column
        for column in required_columns
        if column not in df.columns
    ]

    if missing_columns:

        print()
        print("必要列がありません:")

        for column in missing_columns:
            print("  -", column)

        return

    # --------------------------------------------------------
    # 日付・スコアを正規化
    # --------------------------------------------------------

    work_df = df.copy()

    work_df["日付"] = pd.to_datetime(
        work_df["日付"],
        errors="coerce",
    )

    work_df["総合スコア"] = pd.to_numeric(
        work_df["総合スコア"],
        errors="coerce",
    )

    work_df = work_df[
        work_df["日付"].notna()
        & work_df["総合スコア"].notna()
    ].copy()

    if work_df.empty:

        print()
        print("有効なデータがありません。")

        return

    # --------------------------------------------------------
    # 日付別 TOP3
    # --------------------------------------------------------

    top3_rows = []

    for date, day_df in work_df.groupby(
        "日付",
        sort=True,
    ):

        day_df = day_df.sort_values(
            "総合スコア",
            ascending=False,
        ).head(3)

        if len(day_df) < 3:
            continue

        scores = day_df["総合スコア"].tolist()

        first_score = safe_float(
            scores[0]
        )

        second_score = safe_float(
            scores[1]
        )

        third_score = safe_float(
            scores[2]
        )

        gap_1_2 = (
            first_score
            - second_score
        )

        gap_2_3 = (
            second_score
            - third_score
        )

        gap_1_3 = (
            first_score
            - third_score
        )

        # ----------------------------------------------------
        # 営業日タイプ
        # ----------------------------------------------------

        business_type = ""

        if "営業日タイプ" in day_df.columns:

            business_type = str(
                day_df.iloc[0]["営業日タイプ"]
            )

        # ----------------------------------------------------
        # スコア差区分
        # ----------------------------------------------------

        if gap_1_3 < 5:
            gap_category = "0～5"

        elif gap_1_3 < 10:
            gap_category = "5～10"

        elif gap_1_3 < 20:
            gap_category = "10～20"

        else:
            gap_category = "20以上"

        top3_rows.append(
            {
                "日付": date,
                "営業日タイプ": business_type,
                "1位": first_score,
                "2位": second_score,
                "3位": third_score,
                "1位-2位": gap_1_2,
                "2位-3位": gap_2_3,
                "1位-3位": gap_1_3,
                "スコア差区分": gap_category,
            }
        )

    # --------------------------------------------------------
    # 日付別結果
    # --------------------------------------------------------

    if not top3_rows:

        print()
        print("TOP3を作成できる営業日がありません。")

        return

    top3_df = pd.DataFrame(
        top3_rows
    )

    print()
    print("--- 日付別 ---")

    display_columns = [
        "日付",
        "営業日タイプ",
        "1位",
        "2位",
        "3位",
        "1位-2位",
        "2位-3位",
        "1位-3位",
    ]

    print(
        top3_df[
            display_columns
        ].to_string(
            index=False,
            formatters={
                "1位": lambda x: f"{x:.2f}",
                "2位": lambda x: f"{x:.2f}",
                "3位": lambda x: f"{x:.2f}",
                "1位-2位": lambda x: f"{x:.2f}",
                "2位-3位": lambda x: f"{x:.2f}",
                "1位-3位": lambda x: f"{x:.2f}",
            },
        )
    )

    # --------------------------------------------------------
    # 営業日タイプ別 スコア差統計
    # --------------------------------------------------------

    print()
    print("--- スコア差の統計 ---")

    stats_df = (
        top3_df
        .groupby(
            "営業日タイプ",
            dropna=False,
        )
        .agg(
            日付数=("日付", "nunique"),
            平均1位2位差=("1位-2位", "mean"),
            平均2位3位差=("2位-3位", "mean"),
            平均1位3位差=("1位-3位", "mean"),
            中央値1位3位差=("1位-3位", "median"),
            最大1位3位差=("1位-3位", "max"),
        )
        .reset_index()
        .rename(
            columns={
                "日付数": "営業日数",
            }
        )
    )

    print(
        stats_df.to_string(
            index=False,
            formatters={
                "平均1位2位差": lambda x: f"{x:.2f}",
                "平均2位3位差": lambda x: f"{x:.2f}",
                "平均1位3位差": lambda x: f"{x:.2f}",
                "中央値1位3位差": lambda x: f"{x:.2f}",
                "最大1位3位差": lambda x: f"{x:.2f}",
            },
        )
    )

    # --------------------------------------------------------
    # スコア差区分
    # --------------------------------------------------------

    print()
    print("--- スコア差による分類 ---")

    category_columns = [
        "日付",
        "営業日タイプ",
        "1位-3位",
        "スコア差区分",
    ]

    print(
        top3_df[
            category_columns
        ].to_string(
            index=False,
            formatters={
                "1位-3位": lambda x: f"{x:.2f}",
            },
        )
    )

    # --------------------------------------------------------
    # スコア差区分別 営業日数
    # --------------------------------------------------------

    print()
    print("--- スコア差区分別 実績 ---")

    category_stats = (
        top3_df
        .groupby(
            [
                "営業日タイプ",
                "スコア差区分",
            ],
            dropna=False,
        )
        .agg(
            日付数=("日付", "nunique"),
        )
        .reset_index()
        .rename(
            columns={
                "日付数": "営業日数",
            }
        )
    )

    # --------------------------------------------------------
    # 区分の表示順
    # --------------------------------------------------------

    category_order = {
        "0～5": 1,
        "5～10": 2,
        "10～20": 3,
        "20以上": 4,
    }

    category_stats["_sort"] = (
        category_stats["スコア差区分"]
        .map(category_order)
        .fillna(99)
    )

    category_stats = (
        category_stats
        .sort_values(
            [
                "営業日タイプ",
                "_sort",
            ]
        )
        .drop(
            columns=["_sort"]
        )
    )

    print(
        category_stats.to_string(
            index=False
        )
    )

# ============================================================
# メイン
# ============================================================

def main():

    print()
    print("=" * 80)
    print("ジャグラーラボ prediction_score 分布診断")
    print("=" * 80)

    print()
    print("DB:", DB_PATH)

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

        df = get_prediction_scores(
            conn
        )

        if df.empty:

            print()
            print(
                "prediction_scoreに対象データがありません。"
            )

            return

        print_basic_info(df)

        print_daily_top10(df)

        print_machine_summary(df)

        print_machine_number_summary(df)

        print_top3_frequency(df)

        print_top3_concentration(df)

        print_top3_score_gap(df)

        print_top3_machine_concentration(df)

        print_top3_machine_performance(df)

        print_top3_machine_concentration_performance(df)

        print_top3_score_gap_performance(df)

        print()
        print("=" * 80)
        print("診断終了")
        print("=" * 80)

    finally:

        conn.close()


if __name__ == "__main__":
    main()