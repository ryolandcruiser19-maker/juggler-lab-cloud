"""
ジャグラーラボ
Prediction Engine

予測スコア作成
"""

import sqlite3
from pathlib import Path

import pandas as pd

from prediction_rules import (
    get_holdover_score,
    get_reset_score,
    get_event_score,
    get_weekday_score,
    get_store_score,
    get_tail_score,
)

from prediction_weight import (
    HISTORY_WEIGHT,
    PATTERN_WEIGHT,
    ISLAND_WEIGHT,
    ALIGNMENT_WEIGHT,
    ALIGNMENT_HISTORY_WEIGHT,
    EVENT_WEIGHT,
    STORE_WEIGHT,
    WEEKDAY_WEIGHT,
    TAIL_WEIGHT,
    BEFORE_WEIGHT,
    HOLDOVER_WEIGHT,
    RESET_WEIGHT,
)


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
# 過去並び補正
# ============================================================

def calculate_alignment_history_score(
    no,
    island_name,
    alignment_history_analysis,
    alignment_history,
    analysis_date,
):
    """過去の並び実績から予測用補正値を計算する。"""

    if alignment_history_analysis.empty:
        return 0.0

    clean_island_name = normalize_island_name(island_name)

    target = alignment_history_analysis.copy()

    if "島" not in target.columns:
        return 0.0

    target["島"] = target["島"].apply(normalize_island_name)

    target = target[
        target["島"] == clean_island_name
    ].copy()

    if target.empty:
        return 0.0

    required_columns = [
        "開始台番号",
        "終了台番号",
        "発生回数",
        "強い並び回数",
        "並び期待度",
    ]

    for column in required_columns:
        if column not in target.columns:
            return 0.0

    hit = target[
        (target["開始台番号"] <= no)
        &
        (target["終了台番号"] >= no)
    ].copy()

    if hit.empty:
        return 0.0

    hit = hit.sort_values(
        [
            "発生回数",
            "強い並び回数",
            "並び期待度",
        ],
        ascending=False,
    )

    best = hit.iloc[0]

    try:
        occurrence_count = float(best["発生回数"])
    except (ValueError, TypeError):
        occurrence_count = 0.0

    try:
        strong_count = float(best["強い並び回数"])
    except (ValueError, TypeError):
        strong_count = 0.0

    try:
        expectation = float(best["並び期待度"])
    except (ValueError, TypeError):
        expectation = 0.0

    base_score = min(occurrence_count, 5.0)
    strong_bonus = min(strong_count * 0.5, 2.0)
    expectation_bonus = min(expectation * 0.2, 2.0)

    score = (
        base_score
        + strong_bonus
        + expectation_bonus
    )

    recent_penalty = 0.0

    if not alignment_history.empty:

        history = alignment_history.copy()

        if "島" in history.columns:

            history["島"] = history["島"].apply(
                normalize_island_name
            )

            history = history[
                history["島"] == clean_island_name
            ].copy()

        else:
            history = pd.DataFrame()

        if not history.empty:

            required_history_columns = [
                "日付",
                "開始台番号",
                "終了台番号",
            ]

            if all(
                column in history.columns
                for column in required_history_columns
            ):

                history["日付"] = pd.to_datetime(
                    history["日付"],
                    errors="coerce",
                )

                history = history[
                    history["日付"].notna()
                ].copy()

                analysis_datetime = pd.to_datetime(
                    analysis_date
                )

                history = history[
                    history["日付"] <= analysis_datetime
                ].copy()

                history = history[
                    (history["開始台番号"] <= no)
                    &
                    (history["終了台番号"] >= no)
                ].copy()

                if not history.empty:

                    last_date = history["日付"].max()

                    days_since = (
                        analysis_datetime - last_date
                    ).days

                    if days_since <= 0:
                        recent_penalty = 6.0
                    elif days_since == 1:
                        recent_penalty = 5.0
                    elif days_since == 2:
                        recent_penalty = 3.5
                    elif days_since == 3:
                        recent_penalty = 1.5

    score -= recent_penalty
    score = max(score, 0.0)
    score = min(score, 10.0)

    return round(score, 2)


# ============================================================
# 安全な数値変換
# ============================================================

def safe_float(value, default=0.0):
    """None / NaN / 文字列などを安全にfloatへ変換する。"""

    try:
        if pd.isna(value):
            return default

        return float(value)

    except (ValueError, TypeError):
        return default


# ============================================================
# メイン処理
# ============================================================

def create_prediction_score():

    print("=" * 60)
    print("prediction_score 作成開始")
    print("=" * 60)

    print()
    print("DB:", DB_PATH)

    conn = sqlite3.connect(DB_PATH)

    try:

        # ====================================================
        # 分析基準日
        # ====================================================

        analysis_date = pd.read_sql(
            """
            SELECT MAX(日付) AS 日付
            FROM daily_data
            """,
            conn,
        ).iloc[0]["日付"]

        if pd.isna(analysis_date):
            print("daily_data に分析対象日がありません。")
            return

        analysis_date = pd.to_datetime(
            analysis_date
        ).strftime("%Y-%m-%d")

        # ====================================================
        # 予測対象日
        # ====================================================

        prediction_date = (
            pd.to_datetime(analysis_date)
            + pd.Timedelta(days=1)
        ).strftime("%Y-%m-%d")

        print()
        print("分析基準日:", analysis_date)
        print("予測対象日:", prediction_date)

        # ====================================================
        # 予測対象台
        # ====================================================

        machines = pd.read_sql(
            """
            SELECT DISTINCT
                台番号,
                機種,
                島
            FROM daily_data
            WHERE 日付 = ?
            ORDER BY 台番号
            """,
            conn,
            params=[analysis_date],
        )

        print()
        print("予測対象台数:", len(machines))

        if machines.empty:
            print("予測対象台がありません。")
            return

        # ====================================================
        # 各分析データ読み込み
        # ====================================================

        history = pd.read_sql(
            "SELECT * FROM machine_history_analysis",
            conn,
        )

        pattern = pd.read_sql(
            "SELECT * FROM machine_pattern_analysis",
            conn,
        )

        island = pd.read_sql(
            "SELECT * FROM island_analysis",
            conn,
        )

        alignment = pd.read_sql(
            """
            SELECT *
            FROM alignment_analysis
            WHERE 日付 = ?
            """,
            conn,
            params=[analysis_date],
        )

        try:
            alignment_history_analysis = pd.read_sql(
                "SELECT * FROM alignment_history_analysis",
                conn,
            )
        except Exception as error:
            print()
            print(
                "alignment_history_analysis 読み込み失敗:",
                error,
            )
            alignment_history_analysis = pd.DataFrame()

        try:
            alignment_history = pd.read_sql(
                "SELECT * FROM alignment_history",
                conn,
            )
        except Exception as error:
            print()
            print(
                "alignment_history 読み込み失敗:",
                error,
            )
            alignment_history = pd.DataFrame()

        # ====================================================
        # 前日評価
        # ====================================================

        yesterday = pd.read_sql(
            """
            SELECT
                台番号,
                評価
            FROM daily_data
            WHERE 日付 = date(?,'-1 day')
            """,
            conn,
            params=[analysis_date],
        )

        # ====================================================
        # 据置分析
        # ====================================================

        holdover = pd.read_sql(
            "SELECT * FROM machine_holdover_analysis",
            conn,
        )

        # ====================================================
        # 曜日分析
        # ====================================================

        weekday = pd.read_sql(
            "SELECT * FROM weekday_analysis",
            conn,
        )

        # ====================================================
        # 末尾分析
        # ====================================================

        tail = pd.read_sql(
            "SELECT * FROM number_tail_analysis",
            conn,
        )

        # ====================================================
        # 店舗状態
        # ====================================================

        store = pd.read_sql(
            "SELECT * FROM store_condition_analysis",
            conn,
        )

        # ====================================================
        # 島分析の最新日を取得
        # ====================================================

        island_latest = island.copy()

        if not island_latest.empty:
            if "日付" in island_latest.columns:

                island_latest["日付"] = pd.to_datetime(
                    island_latest["日付"],
                    errors="coerce",
                )

                latest_island_date = island_latest["日付"].max()

                island_latest = island_latest[
                    island_latest["日付"] == latest_island_date
                ]

        # ====================================================
        # 島評価スコアをPrediction Engine用に正規化
        # 0～10点
        # ====================================================

        island_score_max = 0.0

        if not island_latest.empty:
            if "評価スコア" in island_latest.columns:

                island_values = pd.to_numeric(
                    island_latest["評価スコア"],
                    errors="coerce",
                ).dropna()

                if not island_values.empty:
                    island_score_max = float(
                        island_values.max()
                    )

        print()
        print(
            "島評価最大値:",
            round(island_score_max, 2),
        )

        # ====================================================
        # 曜日
        # ====================================================

        weekday_map = {
            "Monday": "月",
            "Tuesday": "火",
            "Wednesday": "水",
            "Thursday": "木",
            "Friday": "金",
            "Saturday": "土",
            "Sunday": "日",
        }

        target_weekday = weekday_map[
            pd.to_datetime(prediction_date).day_name()
        ]

        weekday_row = pd.DataFrame()

        if not weekday.empty:
            if "曜日" in weekday.columns:
                weekday_row = weekday[
                    weekday["曜日"] == target_weekday
                ]

        # ====================================================
        # イベント
        # ====================================================

        event_score_value = safe_float(
            get_event_score("📅通常")
        )

        results = []

        # ====================================================
        # 台ごとの予測
        # ====================================================

        for _, row in machines.iterrows():

            no = row["台番号"]
            machine = row["機種"]
            island_name = row["島"]

            clean_island_name = normalize_island_name(
                island_name
            )

            base_score = 0.0
            pattern_score = 0.0
            island_score = 0.0
            align_score = 0.0
            alignment_history_score = 0.0
            event_score = event_score_value
            store_score = 0.0
            weekday_score = 0.0
            tail_score = 0.0
            before_score = 0.0
            hold_score = 0.0
            reset_score = 0.0

            # =================================================
            # 基礎台評価
            # =================================================

            if not history.empty:

                h = history[
                    history["台番号"] == no
                ]

                if not h.empty:
                    if "高評価率" in h.columns:
                        base_score = safe_float(
                            h.iloc[0]["高評価率"]
                        )

            # =================================================
            # 最近傾向
            # =================================================

            if not pattern.empty:

                p = pattern[
                    pattern["台番号"] == no
                ]

                if not p.empty:
                    if "傾向スコア" in p.columns:
                        pattern_score = safe_float(
                            p.iloc[0]["傾向スコア"]
                        )

            # =================================================
            # 島評価
            # =================================================

            if not island_latest.empty:

                if "島" in island_latest.columns:

                    island_data = island_latest[
                        island_latest["島"].apply(
                            normalize_island_name
                        ) == clean_island_name
                    ]

                    if not island_data.empty:
                        if "評価スコア" in island_data.columns:

                            raw_island_score = safe_float(
                                island_data.iloc[0]["評価スコア"]
                            )

                            if island_score_max > 0:
                                island_score = (
                                    raw_island_score
                                    / island_score_max
                                    * 10.0
                                )

                            island_score = min(
                                island_score,
                                10.0,
                            )

                            island_score = round(
                                island_score,
                                2,
                            )

            # =================================================
            # 当日並び評価
            # =================================================

            if not alignment.empty:

                alignment_data = alignment.copy()

                if "島" in alignment_data.columns:

                    alignment_data["島"] = (
                        alignment_data["島"].apply(
                            normalize_island_name
                        )
                    )

                    target_alignment = alignment_data[
                        alignment_data["島"] == clean_island_name
                    ]

                    for _, a in target_alignment.iterrows():

                        try:
                            start_no = int(a["開始台番号"])
                            end_no = int(a["終了台番号"])
                            current_no = int(no)
                        except (ValueError, TypeError):
                            continue

                        if start_no <= current_no <= end_no:

                            if "並びスコア" in a:
                                align_score = safe_float(
                                    a["並びスコア"]
                                )

                            break

            # =================================================
            # 過去並び期待
            # =================================================

            alignment_history_score = (
                calculate_alignment_history_score(
                    no=no,
                    island_name=island_name,
                    alignment_history_analysis=(
                        alignment_history_analysis
                    ),
                    alignment_history=alignment_history,
                    analysis_date=analysis_date,
                )
            )

            # =================================================
            # 前日評価
            # =================================================

            if not yesterday.empty:

                y = yesterday[
                    yesterday["台番号"] == no
                ]

                if not y.empty:

                    evaluation = y.iloc[0]["評価"]

                    if evaluation == "◎":
                        before_score = 5.0
                    elif evaluation == "○":
                        before_score = 3.0

            # =================================================
            # 据置・リセット
            # =================================================

            if not holdover.empty:

                ho = holdover[
                    holdover["台番号"] == no
                ]

                if not ho.empty:

                    try:
                        hold_score = safe_float(
                            get_holdover_score(
                                ho.iloc[0]
                            )
                        )
                    except Exception:
                        hold_score = 0.0

                    try:
                        reset_score = safe_float(
                            get_reset_score(
                                ho.iloc[0]
                            )
                        )
                    except Exception:
                        reset_score = 0.0

            # =================================================
            # 曜日補正
            # =================================================

            if not weekday_row.empty:

                try:
                    weekday_score = safe_float(
                        get_weekday_score(
                            weekday_row.iloc[0]
                        )
                    )
                except Exception:
                    weekday_score = 0.0

            # =================================================
            # 末尾補正
            # =================================================

            try:
                tail_number = int(str(no)[-1])
            except (ValueError, TypeError):
                tail_number = None

            if (
                tail_number is not None
                and not tail.empty
                and "台末尾" in tail.columns
            ):

                tail_row = tail[
                    tail["台末尾"] == tail_number
                ]

                if not tail_row.empty:
                    if "高評価率" in tail_row.columns:

                        try:
                            tail_score = safe_float(
                                get_tail_score(
                                    tail_row.iloc[0]["高評価率"]
                                )
                            )
                        except Exception:
                            tail_score = 0.0

            # =================================================
            # 店舗状態
            # =================================================

            if not store.empty:

                try:
                    store_score = safe_float(
                        get_store_score(
                            store.iloc[0]
                        )
                    )
                except Exception:
                    store_score = 0.0

            # =================================================
            # 総合スコア
            # =================================================

            total = (
                base_score * HISTORY_WEIGHT
                + pattern_score * PATTERN_WEIGHT
                + island_score * ISLAND_WEIGHT
                + align_score * ALIGNMENT_WEIGHT
                + alignment_history_score
                * ALIGNMENT_HISTORY_WEIGHT
                + event_score * EVENT_WEIGHT
                + store_score * STORE_WEIGHT
                + weekday_score * WEEKDAY_WEIGHT
                + tail_score * TAIL_WEIGHT
                + before_score * BEFORE_WEIGHT
                + hold_score * HOLDOVER_WEIGHT
                + reset_score * RESET_WEIGHT
            )

            total = round(
                safe_float(total),
                2,
            )

            # =================================================
            # 判定
            # =================================================

            if total >= 40:
                judgment = "◎"
            elif total >= 25:
                judgment = "○"
            elif total >= 15:
                judgment = "△"
            else:
                judgment = ""

            # =================================================
            # 保存
            # =================================================

            results.append(
                (
                    prediction_date,
                    no,
                    machine,
                    island_name,
                    base_score,
                    pattern_score,
                    island_score,
                    align_score + alignment_history_score,
                    event_score,
                    0,
                    before_score,
                    0,
                    store_score,
                    hold_score,
                    reset_score,
                    total,
                    judgment,
                    weekday_score,
                    tail_score,
                    alignment_history_score,
                )
            )

        # ====================================================
        # 保存
        # ====================================================

        cursor = conn.cursor()

        cursor.execute(
            """
            DELETE FROM prediction_score
            WHERE 日付 = ?
            """,
            (prediction_date,),
        )

        cursor.executemany(
            """
            INSERT INTO prediction_score
            (
                日付,
                台番号,
                機種,
                島,
                基礎台評価,
                最近傾向評価,
                島評価,
                並び評価,
                イベント補正,
                使用済補正,
                前日高評価補正,
                予想頻度補正,
                店舗状態補正,
                据置期待補正,
                リセット傾向補正,
                総合スコア,
                判定,
                曜日補正,
                末尾補正,
                並び期待補正
            )
            VALUES
            (
                ?, ?, ?, ?, ?, ?, ?, ?, ?, ?,
                ?, ?, ?, ?, ?, ?, ?, ?, ?, ?
            )
            """,
            results,
        )

        conn.commit()

        # ====================================================
        # 完了
        # ====================================================

        print()
        print("=" * 60)
        print("prediction_score 更新完了")
        print("=" * 60)

        print("予測対象日:", prediction_date)
        print("登録件数:", len(results), "台")

        # ====================================================
        # 判定別件数
        # ====================================================

        judgment_result = pd.read_sql(
            """
            SELECT
                判定,
                COUNT(*) AS 台数
            FROM prediction_score
            WHERE 日付 = ?
            GROUP BY 判定
            ORDER BY
                CASE 判定
                    WHEN '◎' THEN 1
                    WHEN '○' THEN 2
                    WHEN '△' THEN 3
                    ELSE 4
                END
            """,
            conn,
            params=[prediction_date],
        )

        print()
        print("=== 判定別件数 ===")

        if not judgment_result.empty:
            print(
                judgment_result.to_string(index=False)
            )

        # ====================================================
        # 総合スコア上位
        # ====================================================

        ranking = pd.read_sql(
            """
            SELECT
                台番号,
                機種,
                島,
                基礎台評価,
                最近傾向評価,
                島評価,
                並び評価,
                並び期待補正,
                イベント補正,
                店舗状態補正,
                曜日補正,
                末尾補正,
                前日高評価補正,
                据置期待補正,
                リセット傾向補正,
                総合スコア,
                判定
            FROM prediction_score
            WHERE 日付 = ?
            ORDER BY 総合スコア DESC
            LIMIT 20
            """,
            conn,
            params=[prediction_date],
        )

        print()
        print("=== 予測ランキング上位20台 ===")

        if not ranking.empty:
            print(
                ranking.to_string(index=False)
            )

        # ====================================================
        # 過去並び補正上位
        # ====================================================

        alignment_ranking = pd.read_sql(
            """
            SELECT
                台番号,
                機種,
                島,
                並び期待補正,
                並び評価,
                総合スコア,
                判定
            FROM prediction_score
            WHERE 日付 = ?
            ORDER BY
                並び期待補正 DESC,
                総合スコア DESC
            LIMIT 20
            """,
            conn,
            params=[prediction_date],
        )

        print()
        print("=== 過去並び補正上位20台 ===")

        if not alignment_ranking.empty:
            print(
                alignment_ranking.to_string(index=False)
            )

    finally:
        conn.close()


# ============================================================
# 実行
# ============================================================

if __name__ == "__main__":
    create_prediction_score()
