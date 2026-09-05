"""
ジャグラーラボ
9の日 全台系シンプル確率予測

方針:
- 9の日専用モデル
- 島単位で予測
- 複雑なローテーション補正は使用しない
- 過去の9の日実績から島ごとの確率を算出
- 「強い全台系」と「候補以上」を分けて表示
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

# 最低サンプル数
MIN_SAMPLE_COUNT = 3

# TOP表示数
TOP_N = 5


# ============================================================
# 島名正規化
# ============================================================

def normalize_island_name(name):
    """島名から装飾用絵文字を除去する。"""

    return (
        str(name)
        .replace("🔴", "")
        .replace("🔵", "")
        .replace("🟢", "")
        .replace("🟣", "")
        .replace("🟠", "")
        .replace("🟡", "")
        .strip()
    )


# ============================================================
# 9の日判定
# ============================================================

def is_nine_day(date_value):
    """
    9の日判定。

    9日・19日・29日を対象とする。
    """

    try:
        day = pd.to_datetime(date_value).day
        return day in (9, 19, 29)

    except Exception:
        return False


# ============================================================
# データ取得
# ============================================================

def load_nine_day_data(conn):

    print()
    print("=" * 70)
    print("9の日実績データ読み込み")
    print("=" * 70)

    # --------------------------------------------------------
    # 全台系分析テーブルを確認
    # --------------------------------------------------------

    tables = pd.read_sql(
        """
        SELECT name
        FROM sqlite_master
        WHERE type = 'table'
        ORDER BY name
        """,
        conn,
    )

    table_names = set(tables["name"].tolist())

    print()
    print("DB:", DB_PATH)

    # --------------------------------------------------------
    # island_all_setting_analysis
    # --------------------------------------------------------

    if "island_all_setting_analysis" not in table_names:
        raise RuntimeError(
            "island_all_setting_analysis がDBに存在しません。"
        )

    df = pd.read_sql(
        """
        SELECT *
        FROM island_all_setting_analysis
        """,
        conn,
    )

    if df.empty:
        raise RuntimeError(
            "island_all_setting_analysis にデータがありません。"
        )

    print()
    print("読み込み行数:", len(df))
    print("列:", list(df.columns))

    return df


# ============================================================
# データ構造確認
# ============================================================

def find_column(df, candidates):
    """
    候補列名から実在する列を探す。
    """

    for column in candidates:
        if column in df.columns:
            return column

    return None


# ============================================================
# 9の日確率作成
# ============================================================

def calculate_probability(df, analysis_date):

    data = df.copy()

    # --------------------------------------------------------
    # 日付列
    # --------------------------------------------------------

    date_column = find_column(
        data,
        [
            "日付",
            "営業日",
            "対象日",
        ],
    )

    if date_column is None:
        raise RuntimeError(
            "9の日判定に使用できる日付列がありません。"
        )

    data[date_column] = pd.to_datetime(
        data[date_column],
        errors="coerce",
    )

    data = data[
        data[date_column].notna()
    ].copy()

    # --------------------------------------------------------
    # 9の日だけ
    # --------------------------------------------------------

    data = data[
        data[date_column].apply(is_nine_day)
    ].copy()

    if data.empty:
        raise RuntimeError(
            "9の日データがありません。"
        )

    # --------------------------------------------------------
    # 分析基準日より前だけ使用
    # --------------------------------------------------------

    target_date = pd.to_datetime(
        analysis_date
    )

    data = data[
        data[date_column] < target_date
    ].copy()

    if data.empty:
        raise RuntimeError(
            "分析基準日より前の9の日データがありません。"
        )

    # --------------------------------------------------------
    # 島
    # --------------------------------------------------------

    island_column = find_column(
        data,
        [
            "島",
            "島名",
        ],
    )

    if island_column is None:
        raise RuntimeError(
            "島列がありません。"
        )

    data["島"] = data[island_column].apply(
        normalize_island_name
    )

    # --------------------------------------------------------
    # 強い全台系判定
    # --------------------------------------------------------

    strong_column = find_column(
        data,
        [
            "強い全台系",
            "強い全台系判定",
            "強い全台系フラグ",
        ],
    )

    candidate_column = find_column(
        data,
        [
            "全台系候補",
            "全台系候補判定",
            "全台系候補フラグ",
        ],
    )

    if strong_column is None:
        raise RuntimeError(
            "強い全台系判定列がありません。"
        )

    if candidate_column is None:
        raise RuntimeError(
            "全台系候補判定列がありません。"
        )

    # --------------------------------------------------------
    # 0/1へ変換
    # --------------------------------------------------------

    def to_flag(value):

        if pd.isna(value):
            return 0

        if value in [1, True, "1", "True", "TRUE", "○", "◎"]:
            return 1

        try:
            return 1 if float(value) > 0 else 0
        except Exception:
            return 0

    data["強い全台系フラグ"] = data[
        strong_column
    ].apply(to_flag)

    data["全台系候補フラグ"] = data[
        candidate_column
    ].apply(to_flag)

    # --------------------------------------------------------
    # 同一島・同一日の重複を排除
    # --------------------------------------------------------

    data = data.drop_duplicates(
        subset=[
            date_column,
            "島",
        ]
    ).copy()

    # --------------------------------------------------------
    # 島ごとの集計
    # --------------------------------------------------------

    result = (
        data.groupby("島")
        .agg(
            検証日数=(
                date_column,
                "nunique",
            ),
            強い全台系回数=(
                "強い全台系フラグ",
                "sum",
            ),
            全台系候補回数=(
                "全台系候補フラグ",
                "sum",
            ),
        )
        .reset_index()
    )

    # --------------------------------------------------------
    # 確率
    # --------------------------------------------------------

    result["強い全台系確率"] = (
        result["強い全台系回数"]
        / result["検証日数"]
        * 100
    )

    result["候補以上確率"] = (
        result["全台系候補回数"]
        / result["検証日数"]
        * 100
    )

    # --------------------------------------------------------
    # サンプル数による最低条件
    # --------------------------------------------------------

    result["予測対象"] = (
        result["検証日数"]
        >= MIN_SAMPLE_COUNT
    )

    # --------------------------------------------------------
    # 強い全台系確率順
    # --------------------------------------------------------

    result = result.sort_values(
        [
            "予測対象",
            "強い全台系確率",
            "候補以上確率",
            "検証日数",
        ],
        ascending=[
            False,
            False,
            False,
            False,
        ],
    ).reset_index(drop=True)

    return result


# ============================================================
# 出力
# ============================================================

def print_prediction(result, analysis_date, prediction_date):

    print()
    print("=" * 70)
    print("9の日 全台系シンプル確率予測")
    print("=" * 70)

    print()
    print("分析基準日:", analysis_date)
    print("予測対象日:", prediction_date)

    print()
    print(
        "モデル:"
        " 過去の9の日実績による島別単純確率"
    )

    print()
    print(
        "※複雑なローテーション補正・時系列重みは使用しません。"
    )

    print()
    print("=== 全島 ===")

    display_columns = [
        "島",
        "検証日数",
        "強い全台系回数",
        "全台系候補回数",
        "強い全台系確率",
        "候補以上確率",
        "予測対象",
    ]

    print(
        result[display_columns]
        .to_string(
            index=False,
            formatters={
                "強い全台系確率": "{:.1f}%".format,
                "候補以上確率": "{:.1f}%".format,
            },
        )
    )

    # --------------------------------------------------------
    # 予測対象だけ
    # --------------------------------------------------------

    target = result[
        result["予測対象"]
    ].copy()

    # --------------------------------------------------------
    # TOP
    # --------------------------------------------------------

    print()
    print("=" * 70)
    print("=== 9の日 TOP予測 ===")
    print("=" * 70)

    if target.empty:

        print()
        print("十分なサンプル数を持つ島がありません。")
        return

    top = target.head(TOP_N).copy()

    top.insert(
        0,
        "順位",
        range(1, len(top) + 1),
    )

    print()

    print(
        top[
            [
                "順位",
                "島",
                "強い全台系確率",
                "候補以上確率",
                "検証日数",
            ]
        ].to_string(
            index=False,
            formatters={
                "強い全台系確率": "{:.1f}%".format,
                "候補以上確率": "{:.1f}%".format,
            },
        )
    )

    # --------------------------------------------------------
    # TOP3
    # --------------------------------------------------------

    top3 = target.head(3)

    print()
    print("=== TOP3 ===")
    print()

    for i, (_, row) in enumerate(
        top3.iterrows(),
        start=1,
    ):

        print(
            f"{i}位 "
            f"{row['島']} "
            f"(強い全台系 {row['強い全台系確率']:.1f}% / "
            f"候補以上 {row['候補以上確率']:.1f}%)"
        )


# ============================================================
# CSV保存
# ============================================================

def save_result(result, analysis_date):

    output_dir = (
        BASE_DIR
        / "analysis"
        / "backtest_output"
    )

    output_dir.mkdir(
        parents=True,
        exist_ok=True,
    )

    output_file = (
        output_dir
        / "nine_day_probability_prediction.csv"
    )

    output = result.copy()

    output.insert(
        0,
        "分析基準日",
        analysis_date,
    )

    output.to_csv(
        output_file,
        index=False,
        encoding="utf-8-sig",
    )

    print()
    print("出力ファイル:")
    print(output_file)


# ============================================================
# メイン
# ============================================================

def main():

    print("=" * 70)
    print("ジャグラーラボ")
    print("9の日 Simple Probability Prediction")
    print("=" * 70)

    print()
    print("DB:", DB_PATH)

    if not DB_PATH.exists():
        raise FileNotFoundError(
            f"DBがありません: {DB_PATH}"
        )

    conn = sqlite3.connect(DB_PATH)

    try:

        # ----------------------------------------------------
        # 最新営業日
        # ----------------------------------------------------

        latest = pd.read_sql(
            """
            SELECT MAX(日付) AS 日付
            FROM daily_data
            """,
            conn,
        ).iloc[0]["日付"]

        if pd.isna(latest):
            raise RuntimeError(
                "daily_data にデータがありません。"
            )

        analysis_date = pd.to_datetime(
            latest
        ).strftime("%Y-%m-%d")

        prediction_date = (
            pd.to_datetime(analysis_date)
            + pd.Timedelta(days=1)
        ).strftime("%Y-%m-%d")

        print()
        print("最新営業日:", analysis_date)
        print("予測対象日:", prediction_date)

        # ----------------------------------------------------
        # 9の日の場合だけ予測
        # ----------------------------------------------------

        if not is_nine_day(prediction_date):

            print()
            print(
                "予測対象日は9の日ではありません。"
            )

            print(
                "このスクリプトは9の日専用です。"
            )

            return

        # ----------------------------------------------------
        # データ取得
        # ----------------------------------------------------

        df = load_nine_day_data(
            conn
        )

        # ----------------------------------------------------
        # 確率計算
        # ----------------------------------------------------

        result = calculate_probability(
            df,
            analysis_date,
        )

        # ----------------------------------------------------
        # 表示
        # ----------------------------------------------------

        print_prediction(
            result,
            analysis_date,
            prediction_date,
        )

        # ----------------------------------------------------
        # 保存
        # ----------------------------------------------------

        save_result(
            result,
            analysis_date,
        )

        print()
        print("=" * 70)
        print("完了")
        print("=" * 70)

    finally:

        conn.close()


# ============================================================
# 実行
# ============================================================

if __name__ == "__main__":
    main()