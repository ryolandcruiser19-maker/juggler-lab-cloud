"""
ジャグラーラボ
alignment_day_analysis 作成

・1日に発生した並び箇所数を分析
・通常日 / 9のつく日を分離
・直近傾向を分析
・島別の並び発生率を分析

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
# 9のつく日判定
# ============================================================

def is_nine_day(date_value):
    """
    9のつく日か判定する。

    例:
        2026-08-09 → True
        2026-08-19 → True
        2026-08-29 → True
        2026-08-08 → False
    """

    try:

        date = pd.to_datetime(date_value)

        return date.day % 10 == 9

    except Exception:

        return False


# ============================================================
# メイン処理
# ============================================================

def main():

    print("=" * 60)
    print("alignment_day_analysis 作成開始")
    print("=" * 60)

    print()
    print("DB:")
    print(DB_PATH)

    # --------------------------------------------------------
    # DB接続
    # --------------------------------------------------------

    conn = sqlite3.connect(DB_PATH)

    try:

        # ====================================================
        # alignment_history 読み込み
        # ====================================================

        print()
        print("alignment_history 読み込み開始")

        query = """
        SELECT
            日付,
            島,
            開始台番号,
            終了台番号,
            台数,
            ◎台数,
            ○台数,
            平均G数,
            平均合成確率,
            並びスコア,
            判定
        FROM alignment_history
        """

        df = pd.read_sql_query(
            query,
            conn
        )

        print(
            f"alignment_history件数: {len(df)}"
        )

        if df.empty:

            print(
                "alignment_historyにデータがありません。"
            )

            return

        # ====================================================
        # 日付変換
        # ====================================================

        df["日付_dt"] = pd.to_datetime(
            df["日付"],
            errors="coerce"
        )

        df = df.dropna(
            subset=["日付_dt"]
        ).copy()

        # ====================================================
        # 9のつく日判定
        # ====================================================

        df["9のつく日"] = (
            df["日付_dt"]
            .dt.day
            .mod(10)
            .eq(9)
        )

        df["日種別"] = df["9のつく日"].map(
            {
                True: "9のつく日",
                False: "通常日",
            }
        )

        # ====================================================
        # 1日の並び発生箇所数
        #
        # 同じ日に同じ島・開始・終了の重複がある場合は
        # 1箇所として扱う。
        # ====================================================

        daily_alignment = (
            df[
                [
                    "日付",
                    "日付_dt",
                    "島",
                    "開始台番号",
                    "終了台番号",
                    "日種別",
                ]
            ]
            .drop_duplicates(
                subset=[
                    "日付",
                    "島",
                    "開始台番号",
                    "終了台番号",
                ]
            )
            .groupby(
                [
                    "日付",
                    "日付_dt",
                    "日種別",
                ],
                as_index=False
            )
            .agg(
                並び発生箇所数=(
                    "島",
                    "count"
                )
            )
        )

        # ====================================================
        # 生データ件数
        # ====================================================

        raw_daily = (
            df.groupby(
                [
                    "日付",
                    "日付_dt",
                    "日種別",
                ],
                as_index=False
            )
            .size()
            .rename(
                columns={
                    "size": "生データ件数"
                }
            )
        )

        # ====================================================
        # 日別データ統合
        # ====================================================

        daily = pd.merge(
            daily_alignment,
            raw_daily,
            on=[
                "日付",
                "日付_dt",
                "日種別",
            ],
            how="left"
        )

        daily = daily.sort_values(
            "日付_dt"
        ).reset_index(drop=True)

        print()
        print("===== 日別並び発生状況 =====")

        print(
            daily[
                [
                    "日付",
                    "日種別",
                    "並び発生箇所数",
                    "生データ件数",
                ]
            ].tail(20).to_string(
                index=False
            )
        )

        # ====================================================
        # 通常日 / 9のつく日 集計
        # ====================================================

        day_type_summary = (
            daily.groupby(
                "日種別",
                as_index=False
            )
            .agg(
                日数=("日付", "count"),
                平均並び発生箇所数=(
                    "並び発生箇所数",
                    "mean"
                ),
                中央値並び発生箇所数=(
                    "並び発生箇所数",
                    "median"
                ),
                最小並び発生箇所数=(
                    "並び発生箇所数",
                    "min"
                ),
                最大並び発生箇所数=(
                    "並び発生箇所数",
                    "max"
                ),
            )
        )

        day_type_summary[
            "平均並び発生箇所数"
        ] = (
            day_type_summary[
                "平均並び発生箇所数"
            ].round(2)
        )

        day_type_summary[
            "中央値並び発生箇所数"
        ] = (
            day_type_summary[
                "中央値並び発生箇所数"
            ].round(2)
        )

        print()
        print("===== 通常日 / 9のつく日 =====")

        print(
            day_type_summary.to_string(
                index=False
            )
        )

        # ====================================================
        # 直近平均
        # ====================================================

        latest_date = daily["日付_dt"].max()

        print()
        print(
            "最新並び分析日:",
            latest_date.strftime("%Y-%m-%d")
        )

        recent_results = []

        for days in [7, 14, 30]:

            start_date = (
                latest_date
                - pd.Timedelta(
                    days=days - 1
                )
            )

            recent = daily[
                daily["日付_dt"]
                >= start_date
            ]

            if recent.empty:

                average = 0

            else:

                average = (
                    recent[
                        "並び発生箇所数"
                    ].mean()
                )

            recent_results.append(
                {
                    "期間": f"直近{days}日",
                    "開始日": start_date.strftime(
                        "%Y-%m-%d"
                    ),
                    "終了日": latest_date.strftime(
                        "%Y-%m-%d"
                    ),
                    "対象日数": len(recent),
                    "平均並び発生箇所数": round(
                        average,
                        2
                    ),
                }
            )

        recent_summary = pd.DataFrame(
            recent_results
        )

        print()
        print("===== 直近並び発生状況 =====")

        print(
            recent_summary.to_string(
                index=False
            )
        )

        # ====================================================
        # 通常日 / 9のつく日ごとの直近傾向
        # ====================================================

        recent_type_results = []

        for days in [30, 60, 90]:

            start_date = (
                latest_date
                - pd.Timedelta(
                    days=days - 1
                )
            )

            recent = daily[
                daily["日付_dt"]
                >= start_date
            ]

            for day_type in [
                "通常日",
                "9のつく日",
            ]:

                target = recent[
                    recent["日種別"]
                    == day_type
                ]

                if target.empty:

                    continue

                recent_type_results.append(
                    {
                        "期間": f"直近{days}日",
                        "日種別": day_type,
                        "対象日数": len(target),
                        "平均並び発生箇所数": round(
                            target[
                                "並び発生箇所数"
                            ].mean(),
                            2
                        ),
                        "中央値": round(
                            target[
                                "並び発生箇所数"
                            ].median(),
                            2
                        ),
                    }
                )

        recent_type_summary = pd.DataFrame(
            recent_type_results
        )

        print()
        print(
            "===== 日種別 × 直近期間 ====="
        )

        if not recent_type_summary.empty:

            print(
                recent_type_summary.to_string(
                    index=False
                )
            )

        # ====================================================
        # 島別集計
        #
        # 全期間
        # ====================================================

        island_total = (
            df[
                [
                    "日付",
                    "島",
                    "開始台番号",
                    "終了台番号",
                ]
            ]
            .drop_duplicates(
                subset=[
                    "日付",
                    "島",
                    "開始台番号",
                    "終了台番号",
                ]
            )
        )

        island_daily = (
            island_total.groupby(
                [
                    "日付",
                    "島",
                ],
                as_index=False
            )
            .size()
            .rename(
                columns={
                    "size": "並び発生箇所数"
                }
            )
        )

        island_summary = (
            island_daily.groupby(
                "島",
                as_index=False
            )
            .agg(
                並び発生日数=(
                    "日付",
                    "count"
                ),
                総並び発生箇所数=(
                    "並び発生箇所数",
                    "sum"
                ),
                平均並び発生箇所数=(
                    "並び発生箇所数",
                    "mean"
                ),
            )
        )

        # 観測期間の日数
        observation_days = (
            daily["日付"]
            .nunique()
        )

        island_summary[
            "並び発生日率"
        ] = (
            island_summary[
                "並び発生日数"
            ]
            / observation_days
        )

        island_summary[
            "平均並び発生箇所数"
        ] = (
            island_summary[
                "平均並び発生箇所数"
            ].round(2)
        )

        island_summary[
            "並び発生日率"
        ] = (
            island_summary[
                "並び発生日率"
            ].round(4)
        )

        # ====================================================
        # 島別 9のつく日 / 通常日
        # ====================================================

        island_total = pd.merge(
            island_total,
            df[
                [
                    "日付",
                    "日種別",
                ]
            ].drop_duplicates(
                subset=["日付"]
            ),
            on="日付",
            how="left"
        )

        island_type_daily = (
            island_total.groupby(
                [
                    "日付",
                    "島",
                    "日種別",
                ],
                as_index=False
            )
            .size()
            .rename(
                columns={
                    "size": "並び発生箇所数"
                }
            )
        )

        island_type_summary = (
            island_type_daily.groupby(
                [
                    "島",
                    "日種別",
                ],
                as_index=False
            )
            .agg(
                発生日数=(
                    "日付",
                    "count"
                ),
                総発生箇所数=(
                    "並び発生箇所数",
                    "sum"
                ),
                平均発生箇所数=(
                    "並び発生箇所数",
                    "mean"
                ),
            )
        )

        island_type_summary[
            "平均発生箇所数"
        ] = (
            island_type_summary[
                "平均発生箇所数"
            ].round(2)
        )

        # ====================================================
        # 直近30日の島別傾向
        # ====================================================

        recent_30_start = (
            latest_date
            - pd.Timedelta(days=29)
        )

        recent_30 = island_type_daily[
            island_type_daily["日付"].apply(
                lambda x:
                pd.to_datetime(x)
                >= recent_30_start
            )
        ]

        recent_30_summary = (
            recent_30.groupby(
                [
                    "島",
                    "日種別",
                ],
                as_index=False
            )
            .agg(
                発生日数=(
                    "日付",
                    "count"
                ),
                平均発生箇所数=(
                    "並び発生箇所数",
                    "mean"
                ),
            )
        )

        recent_30_summary[
            "平均発生箇所数"
        ] = (
            recent_30_summary[
                "平均発生箇所数"
            ].round(2)
        )

        # ====================================================
        # 既存テーブル確認
        # ====================================================

        table_exists = conn.execute(
            """
            SELECT COUNT(*)
            FROM sqlite_master
            WHERE type = 'table'
            AND name = 'alignment_day_analysis'
            """
        ).fetchone()[0]

        # ====================================================
        # テーブル作成
        #
        # 日別データを保存
        # ====================================================

        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS
            alignment_day_analysis (

                日付 TEXT PRIMARY KEY,

                日種別 TEXT,

                並び発生箇所数 INTEGER,

                生データ件数 INTEGER

            )
            """
        )

        conn.commit()

        # ====================================================
        # 全削除
        # ====================================================

        conn.execute(
            """
            DELETE FROM alignment_day_analysis
            """
        )

        conn.commit()

        # ====================================================
        # 日別データ登録
        # ====================================================

        daily_save = daily[
            [
                "日付",
                "日種別",
                "並び発生箇所数",
                "生データ件数",
            ]
        ].copy()

        daily_save.to_sql(
            "alignment_day_analysis",
            conn,
            if_exists="append",
            index=False
        )

        conn.commit()

        # ====================================================
        # 分析結果表示
        # ====================================================

        print()
        print("=" * 60)
        print("alignment_day_analysis 更新完了")
        print("=" * 60)

        print(
            f"登録日数: {len(daily_save)}"
        )

        print()
        print("===== 最新10日 =====")

        latest10 = (
            daily_save
            .sort_values(
                "日付",
                ascending=False
            )
            .head(10)
        )

        print(
            latest10.to_string(
                index=False
            )
        )

        print()
        print("===== 通常日 / 9のつく日 =====")

        print(
            day_type_summary.to_string(
                index=False
            )
        )

        print()
        print("===== 島別 総合発生状況 =====")

        print(
            island_summary
            .sort_values(
                "総並び発生箇所数",
                ascending=False
            )
            .head(20)
            .to_string(
                index=False
            )
        )

        print()
        print(
            "===== 島別 × 日種別 ====="
        )

        print(
            island_type_summary
            .sort_values(
                [
                    "日種別",
                    "総発生箇所数",
                ],
                ascending=[
                    True,
                    False,
                ]
            )
            .to_string(
                index=False
            )
        )

        print()
        print(
            "===== 直近30日 島別 × 日種別 ====="
        )

        if not recent_30_summary.empty:

            print(
                recent_30_summary
                .sort_values(
                    [
                        "日種別",
                        "平均発生箇所数",
                    ],
                    ascending=[
                        True,
                        False,
                    ]
                )
                .to_string(
                    index=False
                )
            )

    finally:

        conn.close()


# ============================================================
# 実行
# ============================================================

if __name__ == "__main__":

    main()