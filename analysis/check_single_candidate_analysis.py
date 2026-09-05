"""
ジャグラーラボ
単体候補分析

目的
------------------------------------------------------------
全台系・マイジャグラー3台並びとは別に、

「それ以外で単体として狙う価値がありそうな台」

を抽出する。

重要な考え方
------------------------------------------------------------
1. 9の日と通常日を完全に分離する
2. 全台系候補島の中から「強い台」を選ばない
   → 全台系なら設定5・6の可能性が高く、
      台ごとの出玉差はヒキの影響が大きいため
3. マイジャグラー3台並びは別モデルとして扱う
4. 単体候補は「全台系・3台並び以外」から選ぶ
5. 候補は2～3台に絞る
6. prediction_score の既存スコアを基本材料として使う
7. 過去実績は補助情報として使う
8. 現在の営業日の台数を分母として扱う

DB:
C:\\Users\\sphs4\\OneDrive\\デスクトップ\\ジャグラーラボ\\database\\juggler.db
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
# 定数
# ============================================================

TOP_N = 3

# 単体候補として最低限必要とするG数
MIN_GAMES = 1000

# 9の日の判定
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
    日付が9のつく日か判定する。
    """

    try:
        date = pd.to_datetime(date_value)
        return date.day in NINE_DAYS

    except Exception:
        return False


def safe_float(value, default=0.0):
    """
    安全なfloat変換。
    """

    try:
        if pd.isna(value):
            return default

        return float(value)

    except (ValueError, TypeError):
        return default


def normalize_island_name(name):
    """
    島名の装飾文字を除去する。
    """

    if name is None:
        return ""

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
# 最新営業日取得
# ============================================================

def get_latest_date(conn):
    """
    daily_dataの最新営業日を取得する。
    """

    row = pd.read_sql(
        """
        SELECT
            MAX(日付) AS 日付
        FROM daily_data
        """,
        conn,
    )

    if row.empty:
        return None

    value = row.iloc[0]["日付"]

    if pd.isna(value):
        return None

    return pd.to_datetime(value).strftime(
        "%Y-%m-%d"
    )


# ============================================================
# 最新営業日の実績取得
# ============================================================

def get_latest_daily_data(conn, latest_date):
    """
    最新営業日の全台データを取得する。
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
        WHERE 日付 = ?
        """,
        conn,
        params=[latest_date],
    )

    return df


# ============================================================
# prediction_score取得
# ============================================================

def get_prediction_score(conn, latest_date):
    """
    最新営業日のprediction_scoreを取得する。

    通常は予測対象日が翌日なので、
    latest_dateそのものにprediction_scoreがない場合は
    最新のprediction_scoreを取得する。
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
        WHERE 日付 = (
            SELECT MAX(日付)
            FROM prediction_score
        )
        """,
        conn,
    )

    return df


# ============================================================
# 島情報
# ============================================================

def build_island_info(df):
    """
    最新営業日の島別情報を作る。

    重要
    --------------------------------------------------------
    ここで現在の各島の台数を取得する。

    過去の簡易データ期間についても、
    「当時の記録台数」を分母として推測しない。
    現在の島構成を基準として扱う。
    """

    if df.empty:
        return pd.DataFrame()

    work = df.copy()

    work["島"] = work["島"] if "島" in work.columns else ""

    # 島列がdaily_dataにない場合は後段で補完する
    if "島" not in work.columns:
        work["島"] = ""

    return work


# ============================================================
# 直近データから島を取得
# ============================================================

def get_machine_island_map(conn, latest_date):
    """
    最新営業日の台番号→島対応を取得する。

    daily_dataに島列が存在しないDBにも対応する。
    """

    columns = pd.read_sql(
        """
        PRAGMA table_info(daily_data)
        """,
        conn,
    )

    column_names = set(
        columns["name"].tolist()
    )

    if "島" in column_names:

        df = pd.read_sql(
            """
            SELECT
                台番号,
                島
            FROM daily_data
            WHERE 日付 = ?
            """,
            conn,
            params=[latest_date],
        )

        return df

    return pd.DataFrame(
        columns=[
            "台番号",
            "島",
        ]
    )


# ============================================================
# 評価文字列を数値化
# ============================================================

def evaluation_rank(value):
    """
    評価を数値化。

    ◎ = 3
    ○ = 2
    △ = 1
    その他 = 0
    """

    if value == "◎":
        return 3

    if value == "○":
        return 2

    if value == "△":
        return 1

    return 0


# ============================================================
# 単体候補スコア
# ============================================================

def calculate_single_score(row):
    """
    単体候補用の補助スコアを計算する。

    全台系や3台並びのような「まとまり」を評価する
    スコアではなく、単体としての注目度を評価する。

    重要
    --------------------------------------------------------
    prediction_scoreの総合スコアをそのまま採用するのではなく、
    全台系候補・3台並び候補を除外した後に使用する。
    """

    score = 0.0

    # --------------------------------------------------------
    # prediction_score
    # --------------------------------------------------------

    prediction_score = safe_float(
        row.get("総合スコア")
    )

    # prediction_scoreは既存モデルの中心値
    score += min(
        prediction_score,
        50.0,
    )

    # --------------------------------------------------------
    # 台単体の現在評価
    # --------------------------------------------------------

    evaluation = row.get("評価")

    if evaluation == "◎":
        score += 12.0

    elif evaluation == "○":
        score += 8.0

    elif evaluation == "△":
        score += 4.0

    # --------------------------------------------------------
    # G数
    # --------------------------------------------------------

    games = safe_float(
        row.get("G数")
    )

    if games >= 6000:
        score += 8.0

    elif games >= 5000:
        score += 6.0

    elif games >= 3000:
        score += 3.0

    # --------------------------------------------------------
    # 合成確率
    # --------------------------------------------------------

    combine = safe_float(
        row.get("合成確率")
    )

    if combine > 0:

        if combine <= 120:
            score += 10.0

        elif combine <= 130:
            score += 8.0

        elif combine <= 140:
            score += 6.0

        elif combine <= 150:
            score += 4.0

        elif combine <= 160:
            score += 2.0

    # --------------------------------------------------------
    # 信頼度
    # --------------------------------------------------------

    confidence = safe_float(
        row.get("信頼度補正")
    )

    score += min(
        confidence,
        5.0,
    )

    return round(
        score,
        2,
    )


# ============================================================
# 全台系候補島取得
# ============================================================

def get_all_setting_islands(conn, latest_date):
    """
    最新営業日の全台系候補島を取得する。

    既存の全台系分析テーブルを利用する。
    """

    # テーブル一覧
    tables = pd.read_sql(
        """
        SELECT name
        FROM sqlite_master
        WHERE type = 'table'
        """,
        conn,
    )

    table_names = set(
        tables["name"].tolist()
    )

    target_table = None

    candidates = [
        "island_analysis",
        "island_trend_analysis",
        "analysis_summary",
    ]

    for table in candidates:

        if table in table_names:
            target_table = table
            break

    if target_table is None:
        return set()

    try:

        df = pd.read_sql(
            f"""
            SELECT *
            FROM {target_table}
            """,
            conn,
        )

    except Exception:
        return set()

    if df.empty:
        return set()

    # 日付列がある場合は最新日だけ
    if "日付" in df.columns:

        df["日付"] = pd.to_datetime(
            df["日付"],
            errors="coerce",
        )

        target_date = pd.to_datetime(
            latest_date
        )

        df = df[
            df["日付"] == target_date
        ].copy()

    if df.empty:
        return set()

    # 島列
    island_column = None

    for column in [
        "島",
        "島名",
    ]:

        if column in df.columns:
            island_column = column
            break

    if island_column is None:
        return set()

    # 判定列
    judgment_column = None

    for column in [
        "判定",
        "全台系判定",
        "評価",
    ]:

        if column in df.columns:
            judgment_column = column
            break

    if judgment_column is None:
        return set()

    result = set()

    for _, row in df.iterrows():

        judgment = str(
            row.get(
                judgment_column,
                "",
            )
        )

        if (
            "全台系候補" in judgment
            or "強い全台系" in judgment
        ):

            result.add(
                normalize_island_name(
                    row[island_column]
                )
            )

    return result


# ============================================================
# 3台並び候補台取得
# ============================================================

def get_alignment_candidates(conn, latest_date):
    """
    既存の並び分析から、
    マイジャグラー3台並び候補を取得する。

    この関数は「単体候補から除外するため」に使用する。
    """

    tables = pd.read_sql(
        """
        SELECT name
        FROM sqlite_master
        WHERE type = 'table'
        """,
        conn,
    )

    table_names = set(
        tables["name"].tolist()
    )

    target_table = None

    candidates = [
        "alignment_analysis",
        "alignment_history_analysis",
        "alignment_history",
    ]

    for table in candidates:

        if table in table_names:
            target_table = table
            break

    if target_table is None:
        return set()

    try:

        df = pd.read_sql(
            f"""
            SELECT *
            FROM {target_table}
            """,
            conn,
        )

    except Exception:
        return set()

    if df.empty:
        return set()

    result = set()

    # --------------------------------------------------------
    # 台番号単位の分析テーブル
    # --------------------------------------------------------

    if "台番号" in df.columns:

        for _, row in df.iterrows():

            machine_no = row.get(
                "台番号"
            )

            if pd.isna(machine_no):
                continue

            try:
                result.add(
                    int(machine_no)
                )
            except (
                ValueError,
                TypeError,
            ):
                pass

    # --------------------------------------------------------
    # 開始～終了形式の場合
    # --------------------------------------------------------

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

                for no in range(
                    start,
                    end + 1,
                ):

                    result.add(no)

            except (
                ValueError,
                TypeError,
            ):
                continue

    return result


# ============================================================
# 島内の3台並び除外
# ============================================================

def exclude_three_machine_alignment(
    df,
    machine_island_map,
):
    """
    マイジャグラーの連番3台を候補から除外する。

    ただし「3台並びを実際に予測する」機能ではなく、
    単体候補と役割が重ならないように除外するための処理。
    """

    if df.empty:
        return df

    work = df.copy()

    if "台番号" not in work.columns:
        return work

    # 台番号を整数化
    work["台番号_num"] = pd.to_numeric(
        work["台番号"],
        errors="coerce",
    )

    # 島を付与
    if (
        not machine_island_map.empty
        and "台番号" in machine_island_map.columns
        and "島" in machine_island_map.columns
    ):

        island_map = machine_island_map.copy()

        island_map["台番号_num"] = pd.to_numeric(
            island_map["台番号"],
            errors="coerce",
        )

        island_map = island_map[
            [
                "台番号_num",
                "島",
            ]
        ].drop_duplicates(
            subset=["台番号_num"]
        )

        work = work.merge(
            island_map,
            on="台番号_num",
            how="left",
            suffixes=(
                "",
                "_map",
            ),
        )

        if "島_map" in work.columns:

            if "島" not in work.columns:
                work["島"] = work["島_map"]

            else:
                work["島"] = work["島"].fillna(
                    work["島_map"]
                )

            work = work.drop(
                columns=["島_map"]
            )

    # 島不明ならそのまま
    if "島" not in work.columns:
        return work

    # --------------------------------------------------------
    # マイジャグラーだけ対象
    # --------------------------------------------------------

    myjuggler = work[
        work["機種"].astype(str).str.contains(
            "マイジャグラー",
            na=False,
        )
    ].copy()

    if myjuggler.empty:
        return work

    exclude_numbers = set()

    for island_name, group in myjuggler.groupby(
        "島",
        dropna=False,
    ):

        numbers = sorted(
            pd.to_numeric(
                group["台番号_num"],
                errors="coerce",
            )
            .dropna()
            .astype(int)
            .tolist()
        )

        number_set = set(numbers)

        for no in numbers:

            if (
                no + 1 in number_set
                and no + 2 in number_set
            ):

                exclude_numbers.update(
                    [
                        no,
                        no + 1,
                        no + 2,
                    ]
                )

    return work[
        ~work["台番号_num"].isin(
            exclude_numbers
        )
    ].copy()


# ============================================================
# 単体候補分析
# ============================================================

def analyze_single_candidates(
    conn,
    latest_date,
):
    """
    単体候補を分析する。
    """

    daily_df = get_latest_daily_data(
        conn,
        latest_date,
    )

    if daily_df.empty:
        print("最新営業日のデータがありません。")
        return pd.DataFrame()

    # --------------------------------------------------------
    # 島対応
    # --------------------------------------------------------

    machine_island_map = (
        get_machine_island_map(
            conn,
            latest_date,
        )
    )

    if (
        not machine_island_map.empty
        and "島" in machine_island_map.columns
    ):

        daily_df = daily_df.merge(
            machine_island_map,
            on="台番号",
            how="left",
        )

    elif "島" not in daily_df.columns:

        daily_df["島"] = ""

    # --------------------------------------------------------
    # prediction_score
    # --------------------------------------------------------

    prediction_df = get_prediction_score(
        conn,
        latest_date,
    )

    if not prediction_df.empty:

        # 同一台番号が複数ある場合は最新日だけ
        prediction_df = (
            prediction_df
            .sort_values("日付")
            .drop_duplicates(
                subset=["台番号"],
                keep="last",
            )
        )

        merge_columns = [
            "台番号",
            "総合スコア",
            "判定",
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

        merge_columns = [
            column
            for column in merge_columns
            if column in prediction_df.columns
        ]

        daily_df = daily_df.merge(
            prediction_df[
                merge_columns
            ],
            on="台番号",
            how="left",
        )

    # --------------------------------------------------------
    # 数値化
    # --------------------------------------------------------

    for column in [
        "G数",
        "合成確率",
        "BB",
        "RB",
        "信頼度補正",
        "総合スコア",
    ]:

        if column in daily_df.columns:

            daily_df[column] = pd.to_numeric(
                daily_df[column],
                errors="coerce",
            )

    # --------------------------------------------------------
    # 低G除外
    # --------------------------------------------------------

    if "G数" in daily_df.columns:

        candidate_df = daily_df[
            daily_df["G数"].fillna(0)
            >= MIN_GAMES
        ].copy()

    else:

        candidate_df = daily_df.copy()

    if candidate_df.empty:
        return pd.DataFrame()

    # --------------------------------------------------------
    # 全台系候補島
    # --------------------------------------------------------

    all_setting_islands = (
        get_all_setting_islands(
            conn,
            latest_date,
        )
    )

    candidate_df[
        "全台系候補島"
    ] = candidate_df["島"].apply(
        lambda x:
        normalize_island_name(x)
        in all_setting_islands
    )

    # --------------------------------------------------------
    # マイジャグラー3台並び除外
    # --------------------------------------------------------

    candidate_df = (
        exclude_three_machine_alignment(
            candidate_df,
            machine_island_map,
        )
    )

    if candidate_df.empty:
        return pd.DataFrame()

    # --------------------------------------------------------
    # 単体候補スコア
    # --------------------------------------------------------

    candidate_df[
        "単体候補スコア"
    ] = candidate_df.apply(
        calculate_single_score,
        axis=1,
    )

    # --------------------------------------------------------
    # 全台系候補島は単体候補から除外
    # --------------------------------------------------------

    candidate_df = candidate_df[
        ~candidate_df["全台系候補島"]
    ].copy()

    if candidate_df.empty:
        return pd.DataFrame()

    # --------------------------------------------------------
    # 既存の判定
    # --------------------------------------------------------

    # ◎・○の台は単体候補として残す。
    # ただし全台系島を除外しているので、
    # 「全台系の中で一番強い台」を選ぶことにはならない。

    candidate_df = candidate_df.sort_values(
        [
            "単体候補スコア",
            "総合スコア",
            "G数",
        ],
        ascending=False,
    ).copy()

    # --------------------------------------------------------
    # 上位3台
    # --------------------------------------------------------

    result = candidate_df.head(
        TOP_N
    ).copy()

    return result


# ============================================================
# 結果表示
# ============================================================

def print_results(
    result,
    latest_date,
):
    """
    分析結果を表示する。
    """

    print()
    print("=" * 70)
    print("単体候補分析")
    print("=" * 70)

    print()
    print("分析日:", latest_date)

    if is_nine_day(latest_date):

        print(
            "営業日タイプ: 9の日"
        )

    else:

        print(
            "営業日タイプ: 通常日"
        )

    print()
    print(
        "※ 全台系候補島は除外しています。"
    )

    print(
        "※ マイジャグラー3台並び候補も除外しています。"
    )

    print(
        "※ 全台系の中で「どの台が強いか」は予想していません。"
    )

    print()

    if result.empty:

        print(
            "単体候補を抽出できませんでした。"
        )

        return

    display_columns = [
        "台番号",
        "機種",
        "島",
        "BB",
        "RB",
        "G数",
        "合成確率",
        "評価",
        "総合スコア",
        "単体候補スコア",
        "基礎台評価",
        "最近傾向評価",
        "島評価",
        "イベント補正",
        "店舗状態補正",
        "曜日補正",
        "末尾補正",
        "据置期待補正",
        "リセット傾向補正",
        "並び期待補正",
    ]

    display_columns = [
        column
        for column in display_columns
        if column in result.columns
    ]

    output = result[
        display_columns
    ].copy()

    print(
        output.to_string(
            index=False
        )
    )

    print()
    print(
        "=" * 70
    )
    print(
        f"単体候補: 上位{len(result)}台"
    )
    print(
        "=" * 70
    )


# ============================================================
# メイン
# ============================================================

def main():

    print("=" * 70)
    print("ジャグラーラボ 単体候補分析")
    print("=" * 70)

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

        # ----------------------------------------------------
        # 最新営業日
        # ----------------------------------------------------

        latest_date = get_latest_date(
            conn
        )

        if latest_date is None:

            print(
                "最新営業日を取得できません。"
            )

            return

        print(
            "最新分析日:",
            latest_date,
        )

        # ----------------------------------------------------
        # 分析
        # ----------------------------------------------------

        result = analyze_single_candidates(
            conn,
            latest_date,
        )

        # ----------------------------------------------------
        # 表示
        # ----------------------------------------------------

        print_results(
            result,
            latest_date,
        )

    finally:

        conn.close()


# ============================================================
# 実行
# ============================================================

if __name__ == "__main__":
    main()