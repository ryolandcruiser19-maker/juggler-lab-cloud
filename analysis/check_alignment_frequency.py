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
# 3台並びの重複をまとめる
# ============================================================

def merge_alignment_records(group):
    """
    同一島・同一日の重複した3台並びをまとめる。

    例:

        1027-1029
        1028-1030
        1029-1031

    は、1つの連続した並びとして扱う。

    戻り値:
        実質的な並び箇所数
    """

    if group.empty:
        return 0

    # 開始台番号順
    group = group.sort_values(
        "開始台番号"
    ).reset_index(drop=True)

    clusters = []

    current_start = None
    current_end = None

    for _, row in group.iterrows():

        start = int(row["開始台番号"])
        end = int(row["終了台番号"])

        # 最初
        if current_start is None:

            current_start = start
            current_end = end

            continue

        # ----------------------------------------------------
        # 現在の並びと重なっている場合
        #
        # 例:
        # 現在 1027-1029
        # 次   1028-1030
        #
        # → 同じ並びグループ
        # ----------------------------------------------------

        if start <= current_end + 1:

            current_end = max(
                current_end,
                end
            )

        else:

            clusters.append(
                (
                    current_start,
                    current_end
                )
            )

            current_start = start
            current_end = end

    # 最後のグループ
    if current_start is not None:

        clusters.append(
            (
                current_start,
                current_end
            )
        )

    return len(clusters)


# ============================================================
# 日別・島別の実質並び数
# ============================================================

def calculate_alignment_frequency(df):

    results = []

    for (
        date,
        island
    ), group in df.groupby(
        [
            "日付",
            "島"
        ],
        sort=True
    ):

        count = merge_alignment_records(
            group
        )

        results.append(
            {
                "日付": date,
                "島": island,
                "並び発生箇所数": count
            }
        )

    return pd.DataFrame(
        results
    )


# ============================================================
# メイン
# ============================================================

def main():

    print("=" * 60)
    print("並び発生頻度分析")
    print("=" * 60)

    print()
    print("DB:")
    print(DB_PATH)

    conn = sqlite3.connect(
        DB_PATH
    )

    try:

        # ----------------------------------------------------
        # alignment_history 読み込み
        # ----------------------------------------------------

        df = pd.read_sql_query(
            """
            SELECT
                日付,
                島,
                開始台番号,
                終了台番号,
                台数,
                ◎台数,
                ○台数,
                判定
            FROM alignment_history
            WHERE 日付 IS NOT NULL
            ORDER BY
                日付,
                島,
                開始台番号
            """,
            conn
        )

        print()
        print(
            "alignment_history件数:",
            len(df)
        )

        if df.empty:

            print(
                "alignment_historyにデータがありません。"
            )

            return

        # ----------------------------------------------------
        # 数値化
        # ----------------------------------------------------

        for column in [
            "開始台番号",
            "終了台番号",
            "台数",
            "◎台数",
            "○台数"
        ]:

            df[column] = pd.to_numeric(
                df[column],
                errors="coerce"
            )

        df = df.dropna(
            subset=[
                "日付",
                "島",
                "開始台番号",
                "終了台番号"
            ]
        ).copy()

        # ====================================================
        # ① 生データの日別件数
        # ====================================================

        raw_daily = (
            df.groupby(
                "日付"
            )
            .size()
            .reset_index(
                name="生データ件数"
            )
        )

        # ====================================================
        # ② 重複をまとめた実質並び箇所数
        # ====================================================

        frequency = calculate_alignment_frequency(
            df
        )

        daily = (
            frequency.groupby(
                "日付"
            )["並び発生箇所数"]
            .sum()
            .reset_index()
        )

        daily = daily.merge(
            raw_daily,
            on="日付",
            how="left"
        )

        daily = daily.sort_values(
            "日付"
        )

        # ====================================================
        # 日別結果
        # ====================================================

        print()
        print("=" * 60)
        print("=== 日別の並び発生状況 ===")
        print("=" * 60)

        print(
            daily.to_string(
                index=False
            )
        )

        # ====================================================
        # 統計
        # ====================================================

        print()
        print("=" * 60)
        print("=== 店舗全体の並び発生数 統計 ===")
        print("=" * 60)

        stats = daily[
            "並び発生箇所数"
        ].describe()

        print(
            stats.to_string()
        )

        print()
        print(
            "平均:",
            round(
                daily["並び発生箇所数"].mean(),
                2
            )
        )

        print(
            "中央値:",
            round(
                daily["並び発生箇所数"].median(),
                2
            )
        )

        print(
            "最小:",
            int(
                daily["並び発生箇所数"].min()
            )
        )

        print(
            "最大:",
            int(
                daily["並び発生箇所数"].max()
            )
        )

        # ====================================================
        # 直近7日
        # ====================================================

        recent_7 = daily.tail(
            7
        )

        print()
        print("=" * 60)
        print("=== 直近7日 ===")
        print("=" * 60)

        print(
            recent_7.to_string(
                index=False
            )
        )

        print()
        print(
            "直近7日平均:",
            round(
                recent_7["並び発生箇所数"].mean(),
                2
            )
        )

        # ====================================================
        # 直近14日
        # ====================================================

        recent_14 = daily.tail(
            14
        )

        print()
        print("=" * 60)
        print("=== 直近14日 ===")
        print("=" * 60)

        print(
            "直近14日平均:",
            round(
                recent_14["並び発生箇所数"].mean(),
                2
            )
        )

        # ====================================================
        # 直近30日
        # ====================================================

        recent_30 = daily.tail(
            30
        )

        print()
        print("=" * 60)
        print("=== 直近30日 ===")
        print("=" * 60)

        print(
            "直近30日平均:",
            round(
                recent_30["並び発生箇所数"].mean(),
                2
            )
        )

        # ====================================================
        # 島別分析
        # ====================================================

        print()
        print("=" * 60)
        print("=== 島別・累計並び発生数 ===")
        print("=" * 60)

        island_total = (
            frequency.groupby(
                "島"
            )["並び発生箇所数"]
            .sum()
            .reset_index()
            .sort_values(
                "並び発生箇所数",
                ascending=False
            )
        )

        print(
            island_total.to_string(
                index=False
            )
        )

        # ====================================================
        # 島別・直近7日
        # ====================================================

        latest_date = (
            pd.to_datetime(
                frequency["日付"]
            ).max()
        )

        recent_start = (
            latest_date
            - pd.Timedelta(days=6)
        )

        frequency["日付_dt"] = pd.to_datetime(
            frequency["日付"]
        )

        recent_island = frequency[
            frequency["日付_dt"]
            >=
            recent_start
        ]

        island_recent = (
            recent_island.groupby(
                "島"
            )["並び発生箇所数"]
            .sum()
            .reset_index()
            .sort_values(
                "並び発生箇所数",
                ascending=False
            )
        )

        print()
        print("=" * 60)
        print("=== 島別・直近7日並び発生数 ===")
        print("=" * 60)

        print(
            island_recent.to_string(
                index=False
            )
        )

        # ====================================================
        # 直近日の詳細
        # ====================================================

        latest_date_str = (
            latest_date.strftime(
                "%Y-%m-%d"
            )
        )

        latest = frequency[
            frequency["日付"]
            ==
            latest_date_str
        ].copy()

        latest = latest.sort_values(
            [
                "並び発生箇所数",
                "島"
            ],
            ascending=[
                False,
                True
            ]
        )

        print()
        print("=" * 60)
        print(
            f"=== 最新日 {latest_date_str} の島別並び ==="
        )
        print("=" * 60)

        print(
            latest.to_string(
                index=False
            )
        )

        # ====================================================
        # 最終確認
        # ====================================================

        print()
        print("=" * 60)
        print("分析完了")
        print("=" * 60)

    finally:

        conn.close()


# ============================================================
# 実行
# ============================================================

if __name__ == "__main__":
    main()