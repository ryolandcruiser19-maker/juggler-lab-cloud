import sqlite3
from pathlib import Path

import pandas as pd


# ============================================================
# 設定
# ============================================================

BASE_DIR = Path(__file__).resolve().parent.parent
DB_PATH = BASE_DIR / "database" / "juggler.db"

LATEST_DATE = "2026-08-09"

# 2026年3月以降を完全データ期間として主分析
FULL_DATA_START = "2026-03-01"

# 高評価の定義
HIGH_EVALUATIONS = ["◎", "○"]

# 連番判定の対象
TARGET_COUNTS = [2, 3]


# ============================================================
# DB接続
# ============================================================

def get_connection():
    return sqlite3.connect(DB_PATH)


# ============================================================
# 9の日判定
# ============================================================

def is_nine_day(date_value):
    """
    9 / 19 / 29 を9の日として扱う。
    """
    try:
        day = pd.to_datetime(date_value).day
        return day in (9, 19, 29)
    except Exception:
        return False


# ============================================================
# パーセント
# ============================================================

def pct(numerator, denominator):
    if denominator == 0:
        return 0.0

    return numerator / denominator * 100


# ============================================================
# 島名正規化
# ============================================================

def normalize_island_name(value):
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


# ============================================================
# 9の日データ取得
# ============================================================

def get_daily_data(conn):
    """
    daily_dataから完全データ期間の9の日を取得する。

    島列が存在する場合は利用する。
    島列がない場合は後段でmachines等から補完する。
    """

    columns = pd.read_sql(
        """
        PRAGMA table_info(daily_data)
        """,
        conn,
    )

    column_names = set(columns["name"].tolist())

    select_columns = [
        "日付",
        "店舗",
        "機種",
        "台番号",
        "BB",
        "RB",
        "G数",
        "合成確率",
        "評価",
    ]

    if "信頼度補正" in column_names:
        select_columns.append("信頼度補正")

    if "島" in column_names:
        select_columns.append("島")

    sql = f"""
        SELECT
            {", ".join(select_columns)}
        FROM daily_data
        WHERE 日付 >= ?
          AND 日付 <= ?
        ORDER BY 日付, 機種, 台番号
    """

    df = pd.read_sql(
        sql,
        conn,
        params=[
            FULL_DATA_START,
            LATEST_DATE,
        ],
    )

    if df.empty:
        return df

    df["日付"] = pd.to_datetime(
        df["日付"],
        errors="coerce",
    )

    df = df.dropna(
        subset=["日付"]
    ).copy()

    df = df[
        df["日付"].apply(is_nine_day)
    ].copy()

    return df


# ============================================================
# 台番号 → 島マップ
# ============================================================

def get_machine_island_map(conn):
    """
    台番号→島の対応を取得する。

    優先順位：
    1. daily_data
    2. machines

    同じ台番号が複数存在する場合は重複除去する。
    """

    # --------------------------------------------------------
    # 1. daily_data
    # --------------------------------------------------------

    columns = pd.read_sql(
        """
        PRAGMA table_info(daily_data)
        """,
        conn,
    )

    daily_columns = set(
        columns["name"].tolist()
    )

    if "島" in daily_columns:

        df = pd.read_sql(
            """
            SELECT
                台番号,
                島
            FROM daily_data
            WHERE 島 IS NOT NULL
              AND TRIM(CAST(島 AS TEXT)) <> ''
            """,
            conn,
        )

        if not df.empty:

            df["台番号"] = pd.to_numeric(
                df["台番号"],
                errors="coerce",
            )

            df["島"] = df["島"].apply(
                normalize_island_name
            )

            df = df.dropna(
                subset=["台番号"]
            )

            df = df[
                df["島"] != ""
            ]

            df = df.drop_duplicates(
                subset=["台番号"]
            )

            if not df.empty:
                return df[
                    [
                        "台番号",
                        "島",
                    ]
                ]

    # --------------------------------------------------------
    # 2. machines
    # --------------------------------------------------------

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

    if "machines" not in table_names:
        return pd.DataFrame(
            columns=[
                "台番号",
                "島",
            ]
        )

    columns = pd.read_sql(
        """
        PRAGMA table_info(machines)
        """,
        conn,
    )

    machine_columns = set(
        columns["name"].tolist()
    )

    if (
        "台番号" not in machine_columns
        or "島" not in machine_columns
    ):
        return pd.DataFrame(
            columns=[
                "台番号",
                "島",
            ]
        )

    df = pd.read_sql(
        """
        SELECT
            台番号,
            島
        FROM machines
        WHERE 島 IS NOT NULL
          AND TRIM(CAST(島 AS TEXT)) <> ''
        """,
        conn,
    )

    if df.empty:
        return pd.DataFrame(
            columns=[
                "台番号",
                "島",
            ]
        )

    df["台番号"] = pd.to_numeric(
        df["台番号"],
        errors="coerce",
    )

    df["島"] = df["島"].apply(
        normalize_island_name
    )

    df = df.dropna(
        subset=["台番号"]
    )

    df = df[
        df["島"] != ""
    ]

    df = df.drop_duplicates(
        subset=["台番号"]
    )

    return df[
        [
            "台番号",
            "島",
        ]
    ]


# ============================================================
# 全台系候補島取得
# ============================================================

def get_all_setting_candidates(conn):
    """
    island_all_setting_analysisから、

    ・9の日
    ・2026年3月以降

    の全台系候補島を取得する。

    check_nine_day_all_setting.pyと
    同じ判定ラベルを使用する。
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

    if "island_all_setting_analysis" not in table_names:
        print(
            "island_all_setting_analysisが見つかりません。"
        )
        return pd.DataFrame(
            columns=[
                "日付",
                "島",
                "判定",
            ]
        )

    df = pd.read_sql(
        """
        SELECT
            日付,
            島,
            判定
        FROM island_all_setting_analysis
        WHERE 日付 >= ?
          AND 日付 <= ?
        """,
        conn,
        params=[
            FULL_DATA_START,
            LATEST_DATE,
        ],
    )

    if df.empty:
        return df

    df["日付"] = pd.to_datetime(
        df["日付"],
        errors="coerce",
    )

    df = df.dropna(
        subset=["日付"]
    )

    df = df[
        df["日付"].apply(is_nine_day)
    ].copy()

    df["島"] = df["島"].apply(
        normalize_island_name
    )

    candidate_labels = [
        "強い全台系候補",
        "全台系候補",
        "弱い全台系候補",
    ]

    df["全台系候補"] = df["判定"].isin(
        candidate_labels
    )

    return df


# ============================================================
# 全台系候補島を除外したデータ作成
# ============================================================

def prepare_non_all_setting_data(
    daily_df,
    candidate_df,
    island_map,
):
    """
    全台系候補島を除外し、
    全台系以外の高評価台だけを分析できる形にする。
    """

    work = daily_df.copy()

    # --------------------------------------------------------
    # 島情報
    # --------------------------------------------------------

    if "島" not in work.columns:
        work = work.merge(
            island_map,
            on="台番号",
            how="left",
        )

    else:
        work["島"] = work["島"].apply(
            normalize_island_name
        )

        missing_island = (
            work["島"].isna()
            | (work["島"] == "")
        )

        if missing_island.any():

            work = work.drop(
                columns=["島"]
            ).merge(
                island_map,
                on="台番号",
                how="left",
            )

    work["島"] = work["島"].fillna(
        ""
    )

    # --------------------------------------------------------
    # 台番号の数値化
    # --------------------------------------------------------

    work["台番号"] = pd.to_numeric(
        work["台番号"],
        errors="coerce",
    )

    work = work.dropna(
        subset=["台番号"]
    ).copy()

    work["台番号"] = (
        work["台番号"]
        .astype(int)
    )

    # --------------------------------------------------------
    # 全台系候補島フラグ
    # --------------------------------------------------------

    candidate_keys = set()

    for _, row in candidate_df.iterrows():

        if not row["全台系候補"]:
            continue

        date_value = row["日付"]
        island = normalize_island_name(
            row["島"]
        )

        candidate_keys.add(
            (
                date_value.strftime("%Y-%m-%d"),
                island,
            )
        )

    work["日付キー"] = (
        work["日付"]
        .dt.strftime("%Y-%m-%d")
    )

    work["島"] = work["島"].apply(
        normalize_island_name
    )

    work["全台系候補島"] = work.apply(
        lambda row:
        (
            row["日付キー"],
            row["島"],
        ) in candidate_keys,
        axis=1,
    )

    return work


# ============================================================
# 高評価台の基本集計
# ============================================================

def analyze_basic_distribution(df):
    """
    全台系候補島を除外した後の、
    9の日の高評価台分布を分析する。
    """

    work = df[
        ~df["全台系候補島"]
    ].copy()

    work["高評価"] = work["評価"].isin(
        HIGH_EVALUATIONS
    )

    # --------------------------------------------------------
    # 全台系以外の台数
    # --------------------------------------------------------

    total_machines = len(work)

    high_machines = int(
        work["高評価"].sum()
    )

    print()
    print(
        "=== 1. 全台系候補島を除いた基本集計 ==="
    )
    print()

    print(
        f"分析対象台数: {total_machines}"
    )

    print(
        f"高評価台数(◎+○): {high_machines}"
    )

    print(
        "高評価率: "
        f"{pct(high_machines, total_machines):.2f}%"
    )

    # --------------------------------------------------------
    # 日別
    # --------------------------------------------------------

    daily = (
        work.groupby("日付")
        .agg(
            対象台数=("台番号", "count"),
            高評価台数=("高評価", "sum"),
        )
        .reset_index()
    )

    daily["高評価率"] = (
        daily["高評価台数"]
        / daily["対象台数"]
        * 100
    )

    print()
    print(
        "=== 2. 9の日ごとの全台系以外 高評価分布 ==="
    )
    print()

    print(
        daily[
            [
                "日付",
                "対象台数",
                "高評価台数",
                "高評価率",
            ]
        ]
        .to_string(
            index=False,
            formatters={
                "高評価率": "{:.2f}".format,
            },
        )
    )

    return work


# ============================================================
# 機種別分布
# ============================================================

def analyze_machine_distribution(df):
    """
    全台系候補島を除外した後、
    機種ごとの高評価分布を見る。
    """

    work = df[
        ~df["全台系候補島"]
    ].copy()

    work["高評価"] = work["評価"].isin(
        HIGH_EVALUATIONS
    )

    result = (
        work.groupby("機種")
        .agg(
            分析日数=("日付", "nunique"),
            対象台数=("台番号", "count"),
            高評価台数=("高評価", "sum"),
        )
        .reset_index()
    )

    result["高評価率"] = (
        result["高評価台数"]
        / result["対象台数"]
        * 100
    )

    result = result.sort_values(
        "高評価率",
        ascending=False,
    )

    print()
    print(
        "=== 3. 全台系以外 機種別高評価分布 ==="
    )
    print()

    print(
        result.to_string(
            index=False,
            formatters={
                "高評価率": "{:.2f}".format,
            },
        )
    )

    return result


# ============================================================
# 島×機種単位の高評価台数
# ============================================================

def analyze_island_machine_distribution(df):
    """
    全台系候補島を除外した後、

    日付 × 島 × 機種

    の単位で◎+○が何台発生したかを見る。
    """

    work = df[
        ~df["全台系候補島"]
    ].copy()

    work["高評価"] = work["評価"].isin(
        HIGH_EVALUATIONS
    )

    result = (
        work.groupby(
            [
                "日付",
                "島",
                "機種",
            ]
        )
        .agg(
            対象台数=("台番号", "count"),
            高評価台数=("高評価", "sum"),
        )
        .reset_index()
    )

    result = result[
        result["高評価台数"] > 0
    ].copy()

    print()
    print(
        "=== 4. 全台系以外 日付×島×機種 高評価台数 ==="
    )
    print()

    distribution = (
        result.groupby("高評価台数")
        .size()
        .reset_index(
            name="発生回数"
        )
        .sort_values(
            "高評価台数"
        )
    )

    distribution["割合"] = (
        distribution["発生回数"]
        / distribution["発生回数"].sum()
        * 100
    )

    print(
        distribution.to_string(
            index=False,
            formatters={
                "割合": "{:.2f}".format,
            },
        )
    )

    print()
    print(
        "※ これは「2～3台セット投入」の証明ではありません。"
    )
    print(
        "※ 同一機種内で高評価台が何台発生したかを示します。"
    )

    return result


# ============================================================
# 2～3台高評価の連番分析
# ============================================================

def analyze_alignment_distribution(df):
    """
    全台系候補島を除外した後、

    同一日 × 同一島 × 同一機種

    における高評価台について、
    2台・3台の連番がどの程度あるかを確認する。

    「連番が存在した」ことと
    「店が並び投入した」ことは同義ではない。
    """

    work = df[
        ~df["全台系候補島"]
    ].copy()

    work["高評価"] = work["評価"].isin(
        HIGH_EVALUATIONS
    )

    high_df = work[
        work["高評価"]
    ].copy()

    records = []

    for (
        date_value,
        island,
        machine,
    ), group in high_df.groupby(
        [
            "日付",
            "島",
            "機種",
        ]
    ):

        numbers = sorted(
            pd.to_numeric(
                group["台番号"],
                errors="coerce",
            )
            .dropna()
            .astype(int)
            .unique()
            .tolist()
        )

        if len(numbers) < 2:
            continue

        number_set = set(numbers)

        consecutive_pairs = 0
        consecutive_triples = 0

        for number in numbers:

            if number + 1 in number_set:
                consecutive_pairs += 1

            if (
                number + 1 in number_set
                and number + 2 in number_set
            ):
                consecutive_triples += 1

        records.append(
            {
                "日付": date_value,
                "島": island,
                "機種": machine,
                "高評価台数": len(numbers),
                "連番2台": consecutive_pairs,
                "連番3台": consecutive_triples,
            }
        )

    result = pd.DataFrame(
        records
    )

    print()
    print(
        "=== 5. 全台系以外 2～3台高評価の連番状況 ==="
    )
    print()

    if result.empty:

        print(
            "対象となる2台以上の高評価ケースがありません。"
        )

        return result

    # --------------------------------------------------------
    # 2台高評価
    # --------------------------------------------------------

    two = result[
        result["高評価台数"] == 2
    ].copy()

    if not two.empty:

        two_consecutive = (
            two["連番2台"] > 0
        ).sum()

        print(
            f"高評価2台ケース: {len(two)}回"
        )

        print(
            f"連番2台: {two_consecutive}回 "
            f"({pct(two_consecutive, len(two)):.2f}%)"
        )

        print(
            f"非連番: "
            f"{len(two) - two_consecutive}回 "
            f"({pct(len(two) - two_consecutive, len(two)):.2f}%)"
        )

    # --------------------------------------------------------
    # 3台高評価
    # --------------------------------------------------------

    three = result[
        result["高評価台数"] == 3
    ].copy()

    if not three.empty:

        three_consecutive = (
            three["連番3台"] > 0
        ).sum()

        print()
        print(
            f"高評価3台ケース: {len(three)}回"
        )

        print(
            f"3台連番: {three_consecutive}回 "
            f"({pct(three_consecutive, len(three)):.2f}%)"
        )

        print(
            f"3台完全連番ではない: "
            f"{len(three) - three_consecutive}回 "
            f"({pct(len(three) - three_consecutive, len(three)):.2f}%)"
        )

    return result


# ============================================================
# 日単位の「広がり」分析
# ============================================================

def analyze_daily_spread(df):
    """
    全台系候補島を除いた後、

    1日の中で何機種・何島に
    高評価台が発生したかを見る。

    これにより、

    「特定の2～3台だけ」

    なのか、

    「複数機種・複数島に広く散る」

    のかを確認する。
    """

    work = df[
        ~df["全台系候補島"]
    ].copy()

    work["高評価"] = work["評価"].isin(
        HIGH_EVALUATIONS
    )

    high = work[
        work["高評価"]
    ].copy()

    if high.empty:
        print(
            "高評価台がありません。"
        )
        return pd.DataFrame()

    daily = (
        high.groupby("日付")
        .agg(
            高評価台数=("台番号", "count"),
            高評価機種数=("機種", "nunique"),
            高評価島数=("島", "nunique"),
        )
        .reset_index()
    )

    print()
    print(
        "=== 6. 9の日ごとの高評価台の広がり ==="
    )
    print()

    print(
        daily.to_string(
            index=False
        )
    )

    print()
    print(
        "平均高評価台数: "
        f"{daily['高評価台数'].mean():.2f}"
    )

    print(
        "平均高評価機種数: "
        f"{daily['高評価機種数'].mean():.2f}"
    )

    print(
        "平均高評価島数: "
        f"{daily['高評価島数'].mean():.2f}"
    )

    return daily


# ============================================================
# 全台系と非全台系の高評価構成
# ============================================================

def analyze_all_setting_vs_other(
    daily_df,
    candidate_df,
):
    """
    9の日全体の高評価台について、

    ・全台系候補島
    ・それ以外

    にどれだけ分かれているかを見る。
    """

    work = daily_df.copy()

    # 島情報
    if "島" not in work.columns:
        print(
            "島情報がないため、全台系/非全台系比較を"
            "実行できません。"
        )
        return

    work["島"] = work["島"].apply(
        normalize_island_name
    )

    work["高評価"] = work["評価"].isin(
        HIGH_EVALUATIONS
    )

    candidate_keys = set()

    for _, row in candidate_df.iterrows():

        if not row["全台系候補"]:
            continue

        candidate_keys.add(
            (
                row["日付"].strftime("%Y-%m-%d"),
                normalize_island_name(
                    row["島"]
                ),
            )
        )

    work["日付キー"] = (
        work["日付"]
        .dt.strftime("%Y-%m-%d")
    )

    work["全台系候補島"] = work.apply(
        lambda row:
        (
            row["日付キー"],
            row["島"],
        ) in candidate_keys,
        axis=1,
    )

    high = work[
        work["高評価"]
    ].copy()

    summary = (
        high.groupby("全台系候補島")
        .agg(
            高評価台数=("台番号", "count"),
        )
        .reset_index()
    )

    total = summary[
        "高評価台数"
    ].sum()

    summary["高評価台構成比"] = (
        summary["高評価台数"]
        / total
        * 100
    )

    summary["区分"] = summary[
        "全台系候補島"
    ].map(
        {
            True: "全台系候補島",
            False: "全台系以外",
        }
    )

    summary = summary[
        [
            "区分",
            "高評価台数",
            "高評価台構成比",
        ]
    ]

    print()
    print(
        "=== 7. 高評価台の全台系 / 非全台系構成 ==="
    )
    print()

    print(
        summary.to_string(
            index=False,
            formatters={
                "高評価台構成比": "{:.2f}".format,
            },
        )
    )


# ============================================================
# メイン
# ============================================================

def main():

    print("=" * 80)
    print(
        "ジャグラーラボ"
    )
    print(
        "9の日 全台系以外の高評価台 分散分析"
    )
    print("=" * 80)

    print()
    print(
        f"DB: {DB_PATH}"
    )

    print(
        f"完全データ期間: "
        f"{FULL_DATA_START} ～ {LATEST_DATE}"
    )

    print()

    if not DB_PATH.exists():

        print(
            "DBが見つかりません。"
        )

        return

    conn = get_connection()

    try:

        # ----------------------------------------------------
        # daily_data
        # ----------------------------------------------------

        daily_df = get_daily_data(
            conn
        )

        if daily_df.empty:

            print(
                "9の日のdaily_dataがありません。"
            )

            return

        # ----------------------------------------------------
        # 島マップ
        # ----------------------------------------------------

        island_map = get_machine_island_map(
            conn
        )

        if island_map.empty:

            print()
            print(
                "台番号→島の対応を取得できませんでした。"
            )

            print(
                "daily_dataまたはmachinesに"
                "島情報が必要です。"
            )

            return

        # ----------------------------------------------------
        # 全台系候補
        # ----------------------------------------------------

        candidate_df = get_all_setting_candidates(
            conn
        )

        if candidate_df.empty:

            print()
            print(
                "全台系候補データを取得できませんでした。"
            )

            return

        # ----------------------------------------------------
        # データ準備
        # ----------------------------------------------------

        work = prepare_non_all_setting_data(
            daily_df,
            candidate_df,
            island_map,
        )

        # ----------------------------------------------------
        # 基本分布
        # ----------------------------------------------------

        work = analyze_basic_distribution(
            work
        )

        # ----------------------------------------------------
        # 機種別
        # ----------------------------------------------------

        analyze_machine_distribution(
            work
        )

        # ----------------------------------------------------
        # 島×機種
        # ----------------------------------------------------

        analyze_island_machine_distribution(
            work
        )

        # ----------------------------------------------------
        # 連番
        # ----------------------------------------------------

        analyze_alignment_distribution(
            work
        )

        # ----------------------------------------------------
        # 日別の広がり
        # ----------------------------------------------------

        analyze_daily_spread(
            work
        )

        # ----------------------------------------------------
        # 全台系 vs その他
        # ----------------------------------------------------

        analyze_all_setting_vs_other(
            daily_df,
            candidate_df,
        )

        print()
        print("=" * 80)
        print(
            "分析終了"
        )
        print("=" * 80)

    finally:

        conn.close()


# ============================================================
# 実行
# ============================================================

if __name__ == "__main__":
    main()