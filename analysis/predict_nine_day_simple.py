"""
ジャグラーラボ
9の日 Simple Probability Prediction

9の日専用・島TOP1予測

仕様
----
1. 各島の過去9の日「強い全台系」発生率を基本確率とする
2. 前回その島が強い全台系だった場合、
   「前回強い全台系 → 次回同一島が強い全台系」
   の全島共通実績率を使用する
3. 島別の遷移率は母数不足のため使用しない
4. 最終的にTOP1の1島だけを本命として出力する
"""

import sqlite3
from pathlib import Path

import pandas as pd


# ============================================================
# DB / ファイル設定
# ============================================================

BASE_DIR = Path(__file__).resolve().parent.parent

DB_PATH = (
    BASE_DIR
    / "database"
    / "juggler.db"
)

TRANSITION_PATH = (
    BASE_DIR
    / "analysis"
    / "backtest_output"
    / "nine_day_transition_pairs.csv"
)


# ============================================================
# 9の日判定
# ============================================================

def is_nine_day(date_value):
    """日付が9の日か判定する。"""

    date = pd.to_datetime(date_value)

    return date.day in (9, 19, 29)


# ============================================================
# メイン処理
# ============================================================

def predict_nine_day_simple():

    print("=" * 70)
    print("ジャグラーラボ")
    print("9の日 Simple Probability Prediction")
    print("=" * 70)

    print()
    print("DB:", DB_PATH)
    print("遷移データ:", TRANSITION_PATH)

    # ========================================================
    # DB接続
    # ========================================================

    conn = sqlite3.connect(DB_PATH)

    try:

        # ====================================================
        # 最新営業日
        # ====================================================

        latest = pd.read_sql(
            """
            SELECT MAX(日付) AS 日付
            FROM daily_data
            """,
            conn,
        ).iloc[0]["日付"]

        if pd.isna(latest):
            print()
            print("daily_data にデータがありません。")
            return

        latest_date = pd.to_datetime(latest)

        prediction_date = (
            latest_date
            + pd.Timedelta(days=1)
        )

        print()
        print("最新営業日:", latest_date.strftime("%Y-%m-%d"))
        print(
            "予測対象日:",
            prediction_date.strftime("%Y-%m-%d"),
        )

        # ====================================================
        # 9の日判定
        # ====================================================

        if not is_nine_day(prediction_date):

            print()
            print("予測対象日は9の日ではありません。")
            print("このスクリプトは9の日専用です。")
            return

        # ====================================================
        # 遷移データ読み込み
        # ====================================================

        if not TRANSITION_PATH.exists():

            print()
            print("遷移データがありません。")
            print(TRANSITION_PATH)
            return

        transition = pd.read_csv(
            TRANSITION_PATH
        )

        print()
        print("遷移データ行数:", len(transition))

        # ====================================================
        # 島一覧
        # ====================================================

        islands = sorted(
            transition["to_island"]
            .dropna()
            .astype(str)
            .unique()
            .tolist()
        )

        print("対象島数:", len(islands))

        # ====================================================
        # 基本確率
        #
        # 各島について、
        # 「その島が存在する9の日」のうち
        # 強い全台系だった割合を計算する。
        # ====================================================

        island_stats = []

        for island in islands:

            # その島が予測対象として存在する
            # 各9の日の遷移先行を抽出
            island_rows = transition[
                transition["to_island"] == island
            ].copy()

            if island_rows.empty:
                continue

            # current_date単位で評価
            date_stats = (
                island_rows
                .groupby("current_date")
                .agg(
                    is_strong=(
                        "to_is_strong",
                        "max",
                    )
                )
                .reset_index()
            )

            total_days = len(date_stats)

            strong_days = int(
                date_stats["is_strong"].sum()
            )

            if total_days > 0:
                base_rate = (
                    strong_days
                    / total_days
                    * 100
                )
            else:
                base_rate = 0.0

            island_stats.append(
                {
                    "島": island,
                    "対象9の日数": total_days,
                    "強い全台系回数": strong_days,
                    "基本確率": base_rate,
                }
            )

        stats = pd.DataFrame(
            island_stats
        )

        if stats.empty:

            print()
            print("島別実績を計算できませんでした。")
            return

        # ====================================================
        # 前回→次回同一島の実績率
        #
        # from_was_strong = 1
        # from_island == to_island
        #
        # を対象として、
        # to_is_strong の割合を計算。
        # ====================================================

        same_island_previous = transition[
            (transition["from_was_strong"] == 1)
            &
            (
                transition["from_island"]
                ==
                transition["to_island"]
            )
        ].copy()

        transition_count = len(
            same_island_previous
        )

        transition_success = int(
            same_island_previous[
                "to_is_strong"
            ].sum()
        )

        if transition_count > 0:

            transition_rate = (
                transition_success
                / transition_count
                * 100
            )

        else:

            transition_rate = 0.0

        print()
        print("=== 前回全台系 → 次回同一島 ===")
        print(
            "対象:",
            transition_count,
            "件",
        )
        print(
            "次回も強い全台系:",
            transition_success,
            "件",
        )
        print(
            "現在の遷移率:",
            round(
                transition_rate,
                2,
            ),
            "%",
        )

        # ====================================================
        # 最新9の日の各島状態
        #
        # latest_date が9の日なら、その日を前回とする。
        # 通常日の最新データしかない場合は、
        # latest_date以前の直近9の日を探す。
        # ====================================================

        nine_dates = (
            transition["current_date"]
            .dropna()
            .drop_duplicates()
        )

        nine_dates = pd.to_datetime(
            nine_dates,
            errors="coerce",
        )

        nine_dates = sorted(
            nine_dates.dropna()
        )

        previous_nine_dates = [
            d
            for d in nine_dates
            if d <= latest_date
        ]

        if not previous_nine_dates:

            print()
            print("過去の9の日が見つかりません。")
            return

        previous_nine_date = max(
            previous_nine_dates
        )

        print()
        print(
            "直近9の日:",
            previous_nine_date.strftime(
                "%Y-%m-%d"
            ),
        )

        # ====================================================
        # 直近9日の島別強い全台系
        # ====================================================

        previous_status = (
            transition[
                transition["current_date"]
                ==
                previous_nine_date.strftime(
                    "%Y-%m-%d"
                )
            ]
            .groupby("to_island")
            ["to_is_strong"]
            .max()
            .to_dict()
        )

        # ====================================================
        # 最終予測確率
        # ====================================================

        predictions = []

        for _, row in stats.iterrows():

            island = row["島"]

            base_rate = float(
                row["基本確率"]
            )

            was_strong = int(
                previous_status.get(
                    island,
                    0,
                )
            )

            # --------------------------------------------
            # 前回強い全台系だった場合
            # --------------------------------------------

            if (
                was_strong == 1
                and transition_count > 0
            ):

                prediction_rate = (
                    transition_rate
                )

                rule = (
                    "前回強い全台系"
                    "→全体遷移率"
                )

            else:

                prediction_rate = (
                    base_rate
                )

                rule = (
                    "過去9の日"
                    "基本発生率"
                )

            predictions.append(
                {
                    "島": island,
                    "基本確率": round(
                        base_rate,
                        2,
                    ),
                    "前回強い全台系": was_strong,
                    "予測確率": round(
                        prediction_rate,
                        2,
                    ),
                    "根拠": rule,
                    "対象9の日数": int(
                        row["対象9の日数"]
                    ),
                    "強い全台系回数": int(
                        row["強い全台系回数"]
                    ),
                }
            )

        prediction_df = pd.DataFrame(
            predictions
        )

        # ====================================================
        # TOP1
        # ====================================================

        prediction_df = (
            prediction_df
            .sort_values(
                [
                    "予測確率",
                    "強い全台系回数",
                    "対象9の日数",
                ],
                ascending=[
                    False,
                    False,
                    False,
                ],
            )
            .reset_index(drop=True)
        )

        top1 = prediction_df.iloc[0]

        # ====================================================
        # 結果表示
        # ====================================================

        print()
        print("=" * 70)
        print("9の日 島予測")
        print("=" * 70)

        print()
        print(
            "予測対象日:",
            prediction_date.strftime(
                "%Y-%m-%d"
            ),
        )

        print()
        print(
            "本命島:",
            top1["島"],
        )

        print(
            "予測確率:",
            f"{top1['予測確率']:.2f}%",
        )

        print(
            "基本確率:",
            f"{top1['基本確率']:.2f}%",
        )

        print(
            "前回強い全台系:",
            "はい"
            if top1["前回強い全台系"] == 1
            else "いいえ",
        )

        print(
            "根拠:",
            top1["根拠"],
        )

        print()
        print("=== 全島予測確率 ===")

        display_df = prediction_df[
            [
                "島",
                "予測確率",
                "基本確率",
                "前回強い全台系",
                "対象9の日数",
                "強い全台系回数",
            ]
        ]

        print(
            display_df.to_string(
                index=False
            )
        )

        # ====================================================
        # 保存
        # ====================================================

        output_path = (
            BASE_DIR
            / "analysis"
            / "backtest_output"
            / "nine_day_simple_prediction.csv"
        )

        prediction_df.to_csv(
            output_path,
            index=False,
            encoding="utf-8-sig",
        )

        print()
        print("出力ファイル:")
        print(output_path)

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
    predict_nine_day_simple()
