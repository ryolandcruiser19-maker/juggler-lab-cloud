"""
ジャグラーラボ
島全台系分析

目的:
    島単位で「全台系」の可能性を分析する。

設計方針:
    ・島の台数そのものでは有利不利をつけない
    ・割合を中心に判定する
    ・全台系判定と結果強度を分離する
    ・並び分析とは独立した分析軸とする
"""

import sqlite3
from pathlib import Path
from datetime import datetime

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
# 全台系判定設定
# ============================================================

# 最低分析台数
MIN_MACHINES = 5


# △以上率
STRONG_ALL_RATE = 80.0
NORMAL_ALL_RATE = 70.0
WEAK_ALL_RATE = 60.0


# ============================================================
# 全台系分析
# ============================================================

def create_island_all_setting_analysis():

    conn = sqlite3.connect(DB_PATH)

    print("=" * 70)
    print("島全台系分析")
    print("=" * 70)

    print("DB:", DB_PATH)


    # ========================================================
    # daily_data取得
    # ========================================================

    df = pd.read_sql(
        """
        SELECT

            日付,
            島,
            G数,
            合成確率,
            評価,
            信頼度補正

        FROM daily_data

        WHERE 島 IS NOT NULL

        """,
        conn
    )


    print("daily_data件数:", len(df))


    if df.empty:

        print("分析対象データなし")

        conn.close()

        return


    # ========================================================
    # 数値列を安全に数値化
    # ========================================================

    df["G数"] = pd.to_numeric(
        df["G数"],
        errors="coerce"
    )

    df["合成確率"] = pd.to_numeric(
        df["合成確率"],
        errors="coerce"
    )


    # ========================================================
    # 日付一覧
    # ========================================================

    dates = (
        df["日付"]
        .dropna()
        .drop_duplicates()
        .sort_values()
        .tolist()
    )


    results = []


    update_date = datetime.now().strftime(
        "%Y-%m-%d"
    )


    # ========================================================
    # 日付 × 島
    # ========================================================

    for date in dates:

        day_df = df[
            df["日付"] == date
        ]


        islands = (
            day_df["島"]
            .dropna()
            .drop_duplicates()
            .tolist()
        )


        for island in islands:

            group = day_df[
                day_df["島"] == island
            ].copy()


            if group.empty:
                continue


            # =================================================
            # 対象台数
            # =================================================

            total_count = len(group)


            # 少数台島は判定対象外
            if total_count < MIN_MACHINES:
                continue


            # =================================================
            # 評価集計
            # =================================================

            star_count = int(
                group["評価"]
                .eq("◎")
                .sum()
            )


            circle_count = int(
                group["評価"]
                .eq("○")
                .sum()
            )


            triangle_count = int(
                group["評価"]
                .eq("△")
                .sum()
            )


            cross_count = int(
                group["評価"]
                .eq("×")
                .sum()
            )


            # =================================================
            # △以上
            # =================================================

            high_count = (
                star_count
                + circle_count
                + triangle_count
            )


            high_rate = (
                high_count
                / total_count
                * 100
            )


            # =================================================
            # 各評価率
            # =================================================

            star_rate = (
                star_count
                / total_count
                * 100
            )


            circle_rate = (
                circle_count
                / total_count
                * 100
            )


            triangle_rate = (
                triangle_count
                / total_count
                * 100
            )


            cross_rate = (
                cross_count
                / total_count
                * 100
            )


            # =================================================
            # 平均G数
            # =================================================

            avg_games = (
                group["G数"]
                .mean()
            )


            # =================================================
            # 平均合成確率
            # =================================================

            valid_prob = (
                group["合成確率"]
                .dropna()
            )


            if not valid_prob.empty:

                avg_probability = (
                    valid_prob.mean()
                )

            else:

                avg_probability = None


            # =================================================
            # 信頼度補正台数
            # =================================================

            confidence_count = int(
                group["信頼度補正"]
                .notna()
                .sum()
            )


            confidence_rate = (
                confidence_count
                / total_count
                * 100
            )


            # =================================================
            # 全台系判定
            # =================================================

            if high_rate >= STRONG_ALL_RATE:

                judge = "強い全台系候補"

            elif high_rate >= NORMAL_ALL_RATE:

                judge = "全台系候補"

            elif high_rate >= WEAK_ALL_RATE:

                judge = "弱い全台系候補"

            else:

                judge = ""


            # =================================================
            # 全台系判定スコア
            #
            # 台数ではなく割合を使用
            # =================================================

            all_setting_score = high_rate


            # =================================================
            # 結果強度
            #
            # 全台系だった場合に
            # どれだけ強く結果が出たか
            #
            # ◎・○を重視
            # △は基準値
            # ×はマイナス
            # =================================================

            result_strength = (

                star_rate * 1.5

                + circle_rate * 1.0

                + triangle_rate * 0.3

                - cross_rate * 0.5

            )


            # =================================================
            # G数補正
            #
            # 稼働が十分ある場合のみ
            # 結果強度を少し評価
            # =================================================

            if pd.notna(avg_games):

                if avg_games >= 7000:

                    result_strength += 10

                elif avg_games >= 5000:

                    result_strength += 5


            # =================================================
            # レコード追加
            # =================================================

            results.append(

                (

                    date,

                    island,

                    total_count,

                    high_count,

                    round(
                        high_rate,
                        2
                    ),

                    star_count,

                    circle_count,

                    triangle_count,

                    cross_count,

                    round(
                        star_rate,
                        2
                    ),

                    round(
                        circle_rate,
                        2
                    ),

                    round(
                        triangle_rate,
                        2
                    ),

                    round(
                        cross_rate,
                        2
                    ),

                    round(
                        avg_games,
                        1
                    )
                    if pd.notna(avg_games)
                    else None,

                    round(
                        avg_probability,
                        1
                    )
                    if avg_probability is not None
                    else None,

                    confidence_count,

                    round(
                        confidence_rate,
                        2
                    ),

                    round(
                        all_setting_score,
                        2
                    ),

                    round(
                        result_strength,
                        2
                    ),

                    judge,

                    update_date

                )

            )


    print(
        "登録件数:",
        len(results)
    )


    # ========================================================
    # DB登録
    # ========================================================

    cursor = conn.cursor()


    cursor.execute(
        """
        DELETE FROM island_all_setting_analysis
        """
    )


    cursor.executemany(

        """
        INSERT INTO island_all_setting_analysis

        (

            日付,
            島,
            対象台数,

            △以上台数,
            △以上率,

            ◎台数,
            ○台数,
            △台数,
            ×台数,

            ◎率,
            ○率,
            △率,
            ×率,

            平均G数,
            平均合成確率,

            信頼度高台数,
            信頼度率,

            全台系スコア,
            結果強度,

            判定,
            最終更新日

        )

        VALUES

        (
            ?,?,?,?,?,?,?,?,?,?,
            ?,?,?,?,?,?,?,?,?,?,?
        )

        """,

        results

    )


    conn.commit()

    conn.close()


    print()
    print("island_all_setting_analysis 完了")
    print("=" * 70)


# ============================================================
# 実行
# ============================================================

if __name__ == "__main__":

    create_island_all_setting_analysis()