"""
ジャグラーラボ
単体候補バックテスト

============================================================
目的
============================================================

過去の営業日について、

「その日の prediction_score 上位台を
 単体候補として選んだ場合、
 実際に◎・○をどれだけ拾えていたか」

を検証する。

============================================================
重要
============================================================

・9の日と通常日を分離
・prediction_scoreの総合スコアを基本材料とする
・当日のdaily_dataは答え合わせ専用
・未来情報を予測スコアに混ぜない
・全台系候補島を除外
・マイジャグラー3台並び候補を除外
・TOP3を単体候補とする

============================================================
未来情報リーク対策
============================================================

全台系候補島：
    target_date より前の分析結果だけを使用

並び候補：
    target_date より前の分析結果だけを使用

当日のdaily_data：
    実績評価専用

============================================================
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
# 設定
# ============================================================

TOP_N = 3

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


def normalize_island_name(value):
    """
    島名の装飾文字を除去する。
    """

    if value is None:
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


def safe_float(value, default=0.0):
    """
    安全なfloat変換。
    """

    try:

        if pd.isna(value):
            return default

        return float(value)

    except (
        ValueError,
        TypeError,
    ):

        return default


# ============================================================
# テーブル確認
# ============================================================

def get_table_names(conn):

    df = pd.read_sql(
        """
        SELECT name
        FROM sqlite_master
        WHERE type = 'table'
        ORDER BY name
        """,
        conn,
    )

    return set(
        df["name"].tolist()
    )


# ============================================================
# テーブルのカラム取得
# ============================================================

def get_column_names(conn, table_name):
    """
    指定テーブルのカラム名を取得する。
    """

    try:

        df = pd.read_sql(
            f"""
            PRAGMA table_info({table_name})
            """,
            conn,
        )

    except Exception:

        return set()

    if df.empty:
        return set()

    return set(
        df["name"].tolist()
    )


# ============================================================
# prediction_score取得
# ============================================================

def get_prediction_scores(
    conn,
    start_date,
    end_date,
):
    """
    prediction_scoreを取得する。

    prediction_scoreの日付を
    「予測対象日」として扱う。

    つまり、

        prediction_scoreの日付
            ↓
        予測対象日

        daily_dataの日付
            ↓
        答え合わせ対象日

    とする。
    """

    df = pd.read_sql(
        """
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
        ORDER BY 日付, 総合スコア DESC
        """,
        conn,
        params=[
            start_date,
            end_date,
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

    df["総合スコア"] = pd.to_numeric(
        df["総合スコア"],
        errors="coerce",
    )

    return df


# ============================================================
# daily_data取得
# ============================================================

def get_daily_data(
    conn,
    start_date,
    end_date,
):
    """
    答え合わせ用の実績データ。

    このデータは予測順位の作成には使用しない。
    """

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
            信頼度補正
        FROM daily_data
        WHERE 日付 >= ?
          AND 日付 <= ?
        ORDER BY 日付, 台番号
        """,
        conn,
        params=[
            start_date,
            end_date,
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

    df["G数"] = pd.to_numeric(
        df["G数"],
        errors="coerce",
    )

    return df


# ============================================================
# 島対応
# ============================================================

def get_machine_island_map(
    conn,
    dates,
):
    """
    daily_dataに存在する島情報を取得する。

    島構成情報として使用する。
    実績評価値はここでは使用しない。
    """

    if not dates:
        return pd.DataFrame(
            columns=[
                "日付",
                "台番号",
                "島",
            ]
        )

    columns = pd.read_sql(
        """
        PRAGMA table_info(daily_data)
        """,
        conn,
    )

    column_names = set(
        columns["name"].tolist()
    )

    if "島" not in column_names:

        return pd.DataFrame(
            columns=[
                "日付",
                "台番号",
                "島",
            ]
        )

    placeholders = ",".join(
        ["?"] * len(dates)
    )

    sql = f"""
        SELECT
            日付,
            台番号,
            島
        FROM daily_data
        WHERE 日付 IN ({placeholders})
    """

    df = pd.read_sql(
        sql,
        conn,
        params=list(dates),
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

    df["島"] = df["島"].apply(
        normalize_island_name
    )

    return (
        df.drop_duplicates(
            subset=[
                "日付",
                "台番号",
            ]
        )
    )


# ============================================================
# 過去の全台系候補島取得
# ============================================================

def get_all_setting_islands(
    conn,
    target_date,
):
    """
    target_dateより前に、
    全台系候補として判定された島を取得する。

    ========================================================
    重要
    ========================================================

    target_date当日の分析結果は使用しない。

    これにより、

        当日の結果
            ↓
        全台系候補島判定
            ↓
        単体候補から除外

    という未来情報リークを防ぐ。

    ========================================================

    なお、これは「過去に全台系になった島」を
    単体候補から除外するという保守的な扱いである。
    """

    tables = get_table_names(conn)

    target_table = None

    candidates = [
        "island_all_setting_analysis",
        "island_analysis",
        "island_trend_analysis",
    ]

    for table in candidates:

        if table in tables:

            target_table = table
            break

    if target_table is None:
        return set()

    columns = get_column_names(
        conn,
        target_table,
    )

    if "日付" not in columns:
        return set()

    island_column = None

    for column in [
        "島",
        "島名",
    ]:

        if column in columns:

            island_column = column
            break

    if island_column is None:
        return set()

    judgment_column = None

    for column in [
        "判定",
        "全台系判定",
        "評価",
    ]:

        if column in columns:

            judgment_column = column
            break

    if judgment_column is None:
        return set()

    try:

        df = pd.read_sql(
            f"""
            SELECT
                日付,
                "{island_column}" AS 島,
                "{judgment_column}" AS 判定
            FROM "{target_table}"
            """,
            conn,
        )

    except Exception:

        return set()

    if df.empty:
        return set()

    df["日付"] = pd.to_datetime(
        df["日付"],
        errors="coerce",
    )

    target = pd.to_datetime(
        target_date
    )

    # ========================================================
    # 重要：対象日より前だけ
    # ========================================================

    df = df[
        df["日付"] < target
    ].copy()

    if df.empty:
        return set()

    result = set()

    for _, row in df.iterrows():

        judgment = str(
            row.get(
                "判定",
                "",
            )
        )

        if (
            "全台系候補" in judgment
            or "強い全台系" in judgment
        ):

            island = normalize_island_name(
                row["島"]
            )

            if island:
                result.add(island)

    return result


# ============================================================
# 過去の並び候補取得
# ============================================================

def get_alignment_candidates(
    conn,
    target_date,
):
    """
    target_dateより前に分析された
    並び候補台を取得する。

    未来の並び情報を除外するため、
    日付列が存在する場合は

        日付 < target_date

    のみを使用する。

    日付列が存在しない場合は、
    未来情報判定ができないため
    「除外しない」安全側の処理とする。
    """

    tables = get_table_names(conn)

    target_table = None

    candidates = [
        "alignment_analysis",
        "alignment_history_analysis",
        "alignment_history",
    ]

    for table in candidates:

        if table in tables:

            target_table = table
            break

    if target_table is None:
        return set()

    columns = get_column_names(
        conn,
        target_table,
    )

    if "日付" not in columns:

        print(
            "  ※ 並び分析テーブルに日付列がないため、"
            "未来情報リーク防止のため除外処理を無効化"
        )

        return set()

    try:

        df = pd.read_sql(
            f"""
            SELECT *
            FROM "{target_table}"
            """,
            conn,
        )

    except Exception:

        return set()

    if df.empty:
        return set()

    df["日付"] = pd.to_datetime(
        df["日付"],
        errors="coerce",
    )

    target = pd.to_datetime(
        target_date
    )

    # ========================================================
    # 対象日より前のみ
    # ========================================================

    df = df[
        df["日付"] < target
    ].copy()

    if df.empty:
        return set()

    result = set()

    # ========================================================
    # 台番号形式
    # ========================================================

    if "台番号" in df.columns:

        values = pd.to_numeric(
            df["台番号"],
            errors="coerce",
        )

        for value in values.dropna():

            result.add(
                int(value)
            )

    # ========================================================
    # 開始～終了形式
    # ========================================================

    if (
        "開始台番号" in df.columns
        and "終了台番号" in df.columns
    ):

        for _, row in df.iterrows():

            try:

                start = int(
                    row["開始台番号"]
                )

                end = int(
                    row["終了台番号"]
                )

                for number in range(
                    start,
                    end + 1,
                ):

                    result.add(number)

            except (
                ValueError,
                TypeError,
            ):

                continue

    return result


# ============================================================
# マイジャグラー3台並び除外
# ============================================================

def exclude_three_alignment(
    df,
    island_map,
):
    """
    マイジャグラーの同一島内3連番を除外する。

    これは予測ではなく、
    単体候補と3台並びモデルの役割重複を避けるための
    除外処理。

    注意：
    これは「当日の結果」から3台並びを判定しているわけではない。
    台番号と島構成だけを使用する。
    """

    if df.empty:
        return df

    work = df.copy()

    work["台番号_num"] = pd.to_numeric(
        work["台番号"],
        errors="coerce",
    )

    if (
        not island_map.empty
        and "島" in island_map.columns
    ):

        map_df = island_map.copy()

        map_df["台番号"] = pd.to_numeric(
            map_df["台番号"],
            errors="coerce",
        )

        map_df["日付"] = pd.to_datetime(
            map_df["日付"],
            errors="coerce",
        )

        work["日付"] = pd.to_datetime(
            work["日付"],
            errors="coerce",
        )

        work = work.merge(
            map_df[
                [
                    "日付",
                    "台番号",
                    "島",
                ]
            ],
            on=[
                "日付",
                "台番号",
            ],
            how="left",
            suffixes=(
                "",
                "_map",
            ),
        )

        if "島_map" in work.columns:

            if "島" not in work.columns:

                work["島"] = work[
                    "島_map"
                ]

            else:

                work["島"] = (
                    work["島"]
                    .fillna(
                        work["島_map"]
                    )
                )

            work = work.drop(
                columns=[
                    "島_map"
                ]
            )

    if "島" not in work.columns:
        return work

    myjuggler = work[
        work["機種"]
        .astype(str)
        .str.contains(
            "マイジャグラー",
            na=False,
        )
    ].copy()

    if myjuggler.empty:
        return work

    exclude_numbers = set()

    for _, group in myjuggler.groupby(
        [
            "日付",
            "島",
        ],
        dropna=False,
    ):

        numbers = sorted(
            group[
                "台番号_num"
            ]
            .dropna()
            .astype(int)
            .unique()
            .tolist()
        )

        number_set = set(
            numbers
        )

        for number in numbers:

            if (
                number + 1 in number_set
                and number + 2 in number_set
            ):

                exclude_numbers.update(
                    [
                        number,
                        number + 1,
                        number + 2,
                    ]
                )

    return work[
        ~work[
            "台番号_num"
        ].isin(
            exclude_numbers
        )
    ].copy()


# ============================================================
# 1営業日を検証
# ============================================================

def backtest_one_day(
    prediction_df,
    actual_df,
    island_map,
    all_setting_islands,
    alignment_candidates,
    target_date,
):
    """
    1営業日の単体候補TOP3を作成し、
    当日の実績で答え合わせする。
    """

    if prediction_df.empty:
        return None

    if actual_df.empty:
        return None

    pred = prediction_df.copy()
    actual = actual_df.copy()

    pred["日付"] = pd.to_datetime(
        pred["日付"],
        errors="coerce",
    )

    actual["日付"] = pd.to_datetime(
        actual["日付"],
        errors="coerce",
    )

    target = pd.to_datetime(
        target_date
    )

    pred = pred[
        pred["日付"] == target
    ].copy()

    actual = actual[
        actual["日付"] == target
    ].copy()

    if pred.empty or actual.empty:
        return None

    # --------------------------------------------------------
    # prediction_score重複除外
    # --------------------------------------------------------

    pred = (
        pred
        .sort_values(
            "総合スコア",
            ascending=False,
        )
        .drop_duplicates(
            subset=[
                "台番号"
            ],
            keep="first",
        )
    )

    # --------------------------------------------------------
    # 実績結合
    #
    # ここで初めて当日のdaily_dataを使用する。
    # ただし予測順位決定後の答え合わせ専用。
    # --------------------------------------------------------

    result = pred.merge(
        actual[
            [
                "台番号",
                "BB",
                "RB",
                "G数",
                "合成確率",
                "評価",
            ]
        ],
        on="台番号",
        how="inner",
        suffixes=(
            "_予測",
            "_実績",
        ),
    )

    if result.empty:
        return None

    # --------------------------------------------------------
    # 島を付与
    # --------------------------------------------------------

    if (
        not island_map.empty
        and "島" in island_map.columns
    ):

        map_day = island_map[
            island_map["日付"] == target
        ][
            [
                "台番号",
                "島",
            ]
        ].drop_duplicates(
            subset=[
                "台番号"
            ]
        )

        result = result.merge(
            map_day,
            on="台番号",
            how="left",
        )

    if "島" not in result.columns:
        result["島"] = ""

    result["島"] = result[
        "島"
    ].apply(
        normalize_island_name
    )

    # --------------------------------------------------------
    # 全台系候補島除外
    #
    # all_setting_islandsはtarget_dateより前の情報のみ。
    # --------------------------------------------------------

    if all_setting_islands:

        result = result[
            ~result["島"].isin(
                all_setting_islands
            )
        ].copy()

    if result.empty:
        return None

    # --------------------------------------------------------
    # マイジャグラー3台並び除外
    # --------------------------------------------------------

    if not island_map.empty:

        target_island_map = island_map[
            island_map["日付"] == target
        ].copy()

    else:

        target_island_map = island_map

    result = exclude_three_alignment(
        result,
        target_island_map,
    )

    if result.empty:
        return None

    # --------------------------------------------------------
    # 過去の既存並び候補除外
    # --------------------------------------------------------

    if alignment_candidates:

        result = result[
            ~result[
                "台番号"
            ].isin(
                alignment_candidates
            )
        ].copy()

    if result.empty:
        return None

    # --------------------------------------------------------
    # prediction_score順
    # --------------------------------------------------------

    result = result.sort_values(
        [
            "総合スコア",
            "台番号",
        ],
        ascending=[
            False,
            True,
        ],
    ).reset_index(
        drop=True
    )

    result["予測順位"] = (
        result.index + 1
    )

    # --------------------------------------------------------
    # TOP3
    # --------------------------------------------------------

    top = result.head(
        TOP_N
    ).copy()

    # --------------------------------------------------------
    # 答え合わせ
    # --------------------------------------------------------

    top["高評価"] = top[
        "評価"
    ].isin(
        [
            "◎",
            "○",
        ]
    )

    top["◎"] = (
        top["評価"] == "◎"
    )

    top["○"] = (
        top["評価"] == "○"
    )

    top["△以上"] = top[
        "評価"
    ].isin(
        [
            "◎",
            "○",
            "△",
        ]
    )

    return top


# ============================================================
# バックテスト実行
# ============================================================

def run_backtest(conn):

    print()
    print("=" * 80)
    print("単体候補バックテスト")
    print("=" * 80)

    print()
    print(
        f"期間: {START_DATE} ～ {END_DATE}"
    )

    # --------------------------------------------------------
    # データ取得
    # --------------------------------------------------------

    prediction_df = get_prediction_scores(
        conn,
        START_DATE,
        END_DATE,
    )

    actual_df = get_daily_data(
        conn,
        START_DATE,
        END_DATE,
    )

    # ========================================================
    # prediction_score 日付診断
    # ========================================================

    print()
    print("=" * 80)
    print("=== prediction_score 日付診断 ===")
    print("=" * 80)

    date_summary = (
        prediction_df
        .groupby("日付")
        .agg(
            台数=("台番号", "count"),
            機種数=("機種", "nunique"),
            最小スコア=("総合スコア", "min"),
            最大スコア=("総合スコア", "max"),
        )
        .reset_index()
    )

    date_summary["日付"] = (
        date_summary["日付"]
        .dt.strftime("%Y-%m-%d")
    )

    print()

    print(
        date_summary.to_string(
            index=False
        )
    )

    # ========================================================
    # daily_data と prediction_score の日付対応
    # ========================================================

    print()
    print("=" * 80)
    print("=== daily_data と prediction_score の日付対応 ===")
    print("=" * 80)

    prediction_dates_set = set(
        prediction_df["日付"]
        .dropna()
    )

    actual_dates_set = set(
        actual_df["日付"]
        .dropna()
    )

    print()

    print(
        "prediction_score日数:",
        len(prediction_dates_set)
    )

    print(
        "daily_data日数:",
        len(actual_dates_set)
    )

    print(
        "prediction_score最古:",
        min(prediction_dates_set)
        if prediction_dates_set
        else None
    )

    print(
        "prediction_score最新:",
        max(prediction_dates_set)
        if prediction_dates_set
        else None
    )

    print(
        "daily_data最古:",
        min(actual_dates_set)
        if actual_dates_set
        else None
    )

    print(
        "daily_data最新:",
        max(actual_dates_set)
        if actual_dates_set
        else None
    )


    if prediction_df.empty:

        print()
        print(
            "prediction_scoreに対象データがありません。"
        )

        return

    if actual_df.empty:

        print()
        print(
            "daily_dataに対象データがありません。"
        )

        return

    print()
    print(
        f"prediction_score: "
        f"{len(prediction_df):,}件"
    )

    print(
        f"daily_data: "
        f"{len(actual_df):,}件"
    )

    # --------------------------------------------------------
    # 対象日
    # --------------------------------------------------------

    prediction_dates = sorted(
        prediction_df[
            "日付"
        ]
        .dropna()
        .dt.strftime(
            "%Y-%m-%d"
        )
        .unique()
        .tolist()
    )

    # --------------------------------------------------------
    # 島対応
    # --------------------------------------------------------

    island_map = get_machine_island_map(
        conn,
        prediction_dates,
    )

    # --------------------------------------------------------
    # 日別バックテスト
    # --------------------------------------------------------

    daily_results = []
    candidate_results = []

    for target_date in prediction_dates:

        target_prediction = prediction_df[
            prediction_df["日付"]
            == pd.to_datetime(
                target_date
            )
        ].copy()

        target_actual = actual_df[
            actual_df["日付"]
            == pd.to_datetime(
                target_date
            )
        ].copy()

        if (
            target_prediction.empty
            or target_actual.empty
        ):
            continue

        # ----------------------------------------------------
        # 過去の全台系候補島
        # ----------------------------------------------------

        all_setting_islands = (
            get_all_setting_islands(
                conn,
                target_date,
            )
        )

        # ----------------------------------------------------
        # 過去の並び候補
        # ----------------------------------------------------

        alignment_candidates = (
            get_alignment_candidates(
                conn,
                target_date,
            )
        )

        # ----------------------------------------------------
        # 予測
        # ----------------------------------------------------

        result = backtest_one_day(
            target_prediction,
            target_actual,
            island_map,
            all_setting_islands,
            alignment_candidates,
            target_date,
        )

        if result is None:
            continue

        target_type = (
            "9の日"
            if is_nine_day(
                target_date
            )
            else "通常日"
        )

        high_count = int(
            result[
                "高評価"
            ].sum()
        )

        strong_count = int(
            result[
                "◎"
            ].sum()
        )

        medium_count = int(
            result[
                "○"
            ].sum()
        )

        triangle_count = int(
            result[
                "△以上"
            ].sum()
        )

        daily_results.append(
            {
                "日付": target_date,
                "営業日タイプ": target_type,
                "候補数": len(result),
                "高評価台数": high_count,
                "◎台数": strong_count,
                "○台数": medium_count,
                "△以上台数": triangle_count,
                "1台以上高評価":
                    high_count >= 1,
            }
        )

        for _, row in result.iterrows():

            candidate_results.append(
                {
                    "日付": target_date,
                    "営業日タイプ": target_type,
                    "予測順位": row[
                        "予測順位"
                    ],
                    "台番号": row[
                        "台番号"
                    ],
                    "機種": row[
                        "機種"
                    ],
                    "島": row[
                        "島"
                    ],
                    "総合スコア": row[
                        "総合スコア"
                    ],
                    "実績評価": row[
                        "評価"
                    ],
                    "高評価": row[
                        "高評価"
                    ],
                    "◎": row[
                        "◎"
                    ],
                    "○": row[
                        "○"
                    ],
                    "△以上": row[
                        "△以上"
                    ],
                    "G数": row[
                        "G数"
                    ],
                    "合成確率": row[
                        "合成確率"
                    ],
                }
            )

    if not daily_results:

        print()
        print(
            "バックテスト対象日がありません。"
        )

        return

    daily_result_df = pd.DataFrame(
        daily_results
    )

    candidate_result_df = pd.DataFrame(
        candidate_results
    )

    # ========================================================
    # 日別結果
    # ========================================================

    print()
    print("=" * 80)
    print("=== 1. 日別バックテスト結果 ===")
    print("=" * 80)

    print()

    print(
        daily_result_df.to_string(
            index=False
        )
    )

    # ========================================================
    # 全体評価
    # ========================================================

    print()
    print()
    print("=" * 80)
    print("=== 2. 全体評価 ===")
    print("=" * 80)

    total_days = len(
        daily_result_df
    )

    high_days = int(
        daily_result_df[
            "1台以上高評価"
        ].sum()
    )

    total_candidates = len(
        candidate_result_df
    )

    high_candidates = int(
        candidate_result_df[
            "高評価"
        ].sum()
    )

    strong_candidates = int(
        candidate_result_df[
            "◎"
        ].sum()
    )

    medium_candidates = int(
        candidate_result_df[
            "○"
        ].sum()
    )

    print()

    print(
        f"検証営業日数: "
        f"{total_days}"
    )

    print(
        f"TOP{TOP_N}候補総数: "
        f"{total_candidates}"
    )

    print(
        f"高評価台数: "
        f"{high_candidates}"
    )

    print(
        f"◎台数: "
        f"{strong_candidates}"
    )

    print(
        f"○台数: "
        f"{medium_candidates}"
    )

    if total_candidates > 0:

        print(
            f"TOP{TOP_N}高評価率: "
            f"{high_candidates / total_candidates * 100:.2f}%"
        )

    if total_days > 0:

        print(
            f"TOP{TOP_N}から1台以上高評価率: "
            f"{high_days / total_days * 100:.2f}%"
        )

    # ========================================================
    # 9の日 / 通常日
    # ========================================================

    print()
    print()
    print("=" * 80)
    print("=== 3. 9の日 vs 通常日 ===")
    print("=" * 80)

    type_summary = (
        daily_result_df
        .groupby(
            "営業日タイプ"
        )
        .agg(
            営業日数=(
                "日付",
                "count",
            ),
            高評価日数=(
                "1台以上高評価",
                "sum",
            ),
            平均高評価台数=(
                "高評価台数",
                "mean",
            ),
            **{
                "平均◎台数": (
                    "◎台数",
                    "mean",
                ),
                "平均○台数": (
                    "○台数",
                    "mean",
                ),
            },
        )
        .reset_index()
    )

    type_summary[
        "TOP3_1台以上高評価率"
    ] = (
        type_summary[
            "高評価日数"
        ]
        / type_summary[
            "営業日数"
        ]
        * 100
    )

    print()

    print(
        type_summary.to_string(
            index=False,
            formatters={
                "TOP3_1台以上高評価率":
                    "{:.2f}".format,
                "平均高評価台数":
                    "{:.2f}".format,
                "平均◎台数":
                    "{:.2f}".format,
                "平均○台数":
                    "{:.2f}".format,
            }
        )
    )

    # ========================================================
    # 予測順位別
    # ========================================================

    print()
    print()
    print("=" * 80)
    print("=== 4. 予測順位別 成績 ===")
    print("=" * 80)

    rank_summary = (
        candidate_result_df
        .groupby(
            [
                "営業日タイプ",
                "予測順位",
            ]
        )
        .agg(
            件数=(
                "台番号",
                "count",
            ),
            高評価数=(
                "高評価",
                "sum",
            ),
            **{
                "◎数": (
                    "◎",
                    "sum",
                ),
                "○数": (
                    "○",
                    "sum",
                ),
            },
        )
        .reset_index()
    )

    rank_summary[
        "高評価率"
    ] = (
        rank_summary[
            "高評価数"
        ]
        / rank_summary[
            "件数"
        ]
        * 100
    )

    print()

    print(
        rank_summary.to_string(
            index=False,
            formatters={
                "高評価率":
                    "{:.2f}".format,
            }
        )
    )

    # ========================================================
    # 実績一覧
    # ========================================================

    print()
    print()
    print("=" * 80)
    print("=== 5. 候補台 実績一覧 ===")
    print("=" * 80)

    print()

    print(
        candidate_result_df.to_string(
            index=False
        )
    )

    print()
    print("=" * 80)
    print("バックテスト終了")
    print("=" * 80)


# ============================================================
# メイン
# ============================================================

def main():

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

        run_backtest(
            conn
        )

    finally:

        conn.close()


# ============================================================
# 実行
# ============================================================

if __name__ == "__main__":
    main()