import sqlite3
from pathlib import Path
import pandas as pd
import numpy as np


# ============================================================
# 設定
# ============================================================

BASE_DIR = Path(__file__).resolve().parent.parent
DB_PATH = BASE_DIR / "database" / "juggler.db"
OUTPUT_DIR = BASE_DIR / "analysis" / "backtest_output"

START_DATE = "2026-03-01"

TOP_N = 3

# 予測スコアを作るための重み
STRONG_WEIGHT = 1.0
CANDIDATE_WEIGHT = 0.35

# 最低過去実績回数
MIN_HISTORY = 1


# ============================================================
# 共通関数
# ============================================================

def safe_float(value, default=0.0):
    try:
        if pd.isna(value):
            return default
        return float(value)
    except Exception:
        return default


def classify_day(date_value):
    """
    9の日 / 通常日
    """
    date = pd.to_datetime(date_value)

    if date.day in (9, 19, 29):
        return "9の日"

    return "通常日"


def normalize_island_name(value):
    if pd.isna(value):
        return ""
    return str(value).strip()


# ============================================================
# DB読み込み
# ============================================================

def load_daily_data():
    print("=" * 80)
    print("9の日 全台系島ローテーション制約バックテスト")
    print("=" * 80)
    print()

    print(f"DB: {DB_PATH}")

    conn = sqlite3.connect(DB_PATH)

    df = pd.read_sql_query(
        """
        SELECT
            日付,
            機種,
            台番号,
            G数,
            合成確率,
            評価,
            島
        FROM daily_data
        WHERE 日付 >= ?
        """,
        conn,
        params=[START_DATE],
    )

    conn.close()

    df["日付"] = pd.to_datetime(df["日付"])
    df["島"] = df["島"].apply(normalize_island_name)

    return df


# ============================================================
# 島実績作成
# ============================================================

def build_island_actual(df):
    """
    daily_dataから島×日単位の実績を作成する。

    強い全台系:
        ◎率を基準に判定

    候補以上:
        ◎ + ○ の比率を基準に判定

    ここは既存の島分析で使用している考え方に合わせる。
    """

    work = df.copy()

    work["is_good"] = work["評価"].isin(["◎", "○"])
    work["is_strong"] = work["評価"] == "◎"

    grouped = (
        work.groupby(["日付", "島"], dropna=False)
        .agg(
            台数=("台番号", "count"),
            avg_games=("G数", "mean"),
            strong_count=("is_strong", "sum"),
            candidate_count=("is_good", "sum"),
        )
        .reset_index()
    )

    grouped["strong_rate"] = (
        grouped["strong_count"] / grouped["台数"]
    )

    grouped["candidate_rate"] = (
        grouped["candidate_count"] / grouped["台数"]
    )

    grouped["score"] = (
        grouped["strong_rate"] * 100
        + grouped["candidate_rate"] * 35
    )

    # --------------------------------------------------------
    # 既存分析と完全一致させる場合は、
    # ここを check_nine_day_island_backtest.py の
    # 強い全台系 / 候補判定条件に合わせる。
    #
    # 現段階では相対ランキング用として利用する。
    # --------------------------------------------------------

    grouped["day_type"] = grouped["日付"].apply(classify_day)

    return grouped


# ============================================================
# 実績ラベル作成
# ============================================================

def create_actual_labels(island_actual):
    """
    各9の日について、島の実績を強い/候補に分類する。
    """

    df = island_actual.copy()

    nine_days = sorted(
        df.loc[df["day_type"] == "9の日", "日付"].unique()
    )

    rows = []

    for date in nine_days:

        day_df = df[df["日付"] == date].copy()

        if day_df.empty:
            continue

        # ----------------------------------------------------
        # 強い全台系
        # ----------------------------------------------------
        strong_threshold = 0.50

        candidate_threshold = 0.70

        for _, row in day_df.iterrows():

            strong = row["strong_rate"] >= strong_threshold
            candidate = row["candidate_rate"] >= candidate_threshold

            rows.append(
                {
                    "date": date,
                    "island": row["島"],
                    "strong": int(strong),
                    "candidate": int(candidate),
                    "strong_rate": row["strong_rate"],
                    "candidate_rate": row["candidate_rate"],
                }
            )

    return pd.DataFrame(rows)


# ============================================================
# 過去実績から予測スコアを作る
# ============================================================

def calculate_prediction_scores(actual_df, target_date):
    """
    target_dateより前の9の日だけを使用する。

    重要:
        target_date当日の情報は絶対に使わない。
    """

    history = actual_df[
        (actual_df["date"] < target_date)
    ].copy()

    if history.empty:
        return pd.DataFrame()

    result = []

    for island in sorted(history["island"].unique()):

        island_history = history[
            history["island"] == island
        ]

        history_count = len(island_history)

        if history_count < MIN_HISTORY:
            continue

        strong_rate = island_history["strong"].mean()
        candidate_rate = island_history["candidate"].mean()

        score = (
            strong_rate * STRONG_WEIGHT
            + candidate_rate * CANDIDATE_WEIGHT
        )

        result.append(
            {
                "island": island,
                "history_count": history_count,
                "strong_rate": strong_rate,
                "candidate_rate": candidate_rate,
                "score": score,
            }
        )

    result_df = pd.DataFrame(result)

    if result_df.empty:
        return result_df

    result_df = result_df.sort_values(
        ["score", "strong_rate", "candidate_rate", "history_count"],
        ascending=False,
    ).reset_index(drop=True)

    result_df["base_rank"] = np.arange(1, len(result_df) + 1)

    return result_df


# ============================================================
# 制約適用
# ============================================================

def apply_constraint(
    scores_df,
    previous_strong,
    previous_candidate,
    previous_two_strong,
    mode,
):
    """
    各制約モデルを適用する。

    BASE:
        制約なし

    PREV_STRONG:
        前回強い全台系を除外

    PREV_CANDIDATE:
        前回候補以上を除外

    LAST2_STRONG:
        直近2回の強い全台系を除外
    """

    df = scores_df.copy()

    if df.empty:
        return df

    if mode == "BASE":
        return df

    if mode == "PREV_STRONG":
        excluded = set(previous_strong)
        df = df[~df["island"].isin(excluded)]

    elif mode == "PREV_CANDIDATE":
        excluded = set(previous_candidate)
        df = df[~df["island"].isin(excluded)]

    elif mode == "LAST2_STRONG":
        excluded = set(previous_two_strong)
        df = df[~df["island"].isin(excluded)]

    return df.reset_index(drop=True)


# ============================================================
# 的中判定
# ============================================================

def evaluate_prediction(predictions, actual):
    rows = []

    for _, pred in predictions.iterrows():

        target_date = pred["date"]
        island = pred["island"]
        rank = int(pred["rank"])
        model = pred["model"]

        actual_row = actual[
            (actual["date"] == target_date)
            & (actual["island"] == island)
        ]

        if actual_row.empty:
            strong = 0
            candidate = 0
        else:
            strong = int(actual_row.iloc[0]["strong"])
            candidate = int(actual_row.iloc[0]["candidate"])

        rows.append(
            {
                "date": target_date,
                "model": model,
                "rank": rank,
                "island": island,
                "strong": strong,
                "candidate": candidate,
            }
        )

    return pd.DataFrame(rows)


# ============================================================
# メインバックテスト
# ============================================================

def main():

    daily_df = load_daily_data()

    print()
    print(f"daily_data 行数: {len(daily_df):,}")

    island_actual = build_island_actual(daily_df)

    actual = create_actual_labels(island_actual)

    nine_days = sorted(
        actual["date"].unique()
    )

    print(f"検証対象9の日数: {len(nine_days)}")
    print()

    models = [
        "BASE",
        "PREV_STRONG",
        "PREV_CANDIDATE",
        "LAST2_STRONG",
    ]

    prediction_rows = []

    # --------------------------------------------------------
    # 各9の日を時系列バックテスト
    # --------------------------------------------------------

    for idx, target_date in enumerate(nine_days):

        # 最初の9の日は過去9の日がないため除外
        if idx == 0:
            continue

        scores = calculate_prediction_scores(
            actual,
            target_date,
        )

        if scores.empty:
            continue

        previous_date = nine_days[idx - 1]

        previous_actual = actual[
            actual["date"] == previous_date
        ]

        previous_strong = set(
            previous_actual.loc[
                previous_actual["strong"] == 1,
                "island",
            ]
        )

        previous_candidate = set(
            previous_actual.loc[
                previous_actual["candidate"] == 1,
                "island",
            ]
        )

        previous_two_strong = set()

        if idx >= 2:

            date1 = nine_days[idx - 1]
            date2 = nine_days[idx - 2]

            tmp = actual[
                actual["date"].isin([date1, date2])
            ]

            previous_two_strong = set(
                tmp.loc[
                    tmp["strong"] == 1,
                    "island",
                ]
            )

        for model in models:

            ranked = apply_constraint(
                scores,
                previous_strong,
                previous_candidate,
                previous_two_strong,
                model,
            )

            ranked = ranked.head(TOP_N)

            for rank, (_, row) in enumerate(
                ranked.iterrows(),
                start=1,
            ):

                prediction_rows.append(
                    {
                        "date": target_date,
                        "model": model,
                        "rank": rank,
                        "island": row["island"],
                        "score": row["score"],
                        "history_count": row["history_count"],
                        "strong_rate": row["strong_rate"],
                        "candidate_rate": row["candidate_rate"],
                        "previous_strong": (
                            row["island"] in previous_strong
                        ),
                        "previous_candidate": (
                            row["island"] in previous_candidate
                        ),
                        "previous_two_strong": (
                            row["island"] in previous_two_strong
                        ),
                    }
                )

    predictions = pd.DataFrame(prediction_rows)

    if predictions.empty:
        print("予測結果がありません。")
        return

    evaluated = evaluate_prediction(
        predictions,
        actual,
    )

    # ========================================================
    # モデル別集計
    # ========================================================

    print()
    print("=" * 80)
    print("=== モデル別バックテスト ===")
    print("=" * 80)

    summary_rows = []

    for model in models:

        df = evaluated[
            evaluated["model"] == model
        ].copy()

        dates = df["date"].nunique()

        if dates == 0:
            continue

        top1 = df[df["rank"] == 1]

        top3 = df[df["rank"] <= 3]

        top1_strong = int(
            top1["strong"].sum()
        )

        top1_candidate = int(
            top1["candidate"].sum()
        )

        top3_strong_dates = (
            top3.groupby("date")["strong"]
            .max()
        )

        top3_candidate_dates = (
            top3.groupby("date")["candidate"]
            .max()
        )

        top3_strong = int(
            top3_strong_dates.sum()
        )

        top3_candidate = int(
            top3_candidate_dates.sum()
        )

        girl = df[
            df["island"] == "ガール島"
        ]

        girl_days = girl["date"].nunique()

        summary_rows.append(
            {
                "モデル": model,
                "検証日数": dates,
                "TOP1強い全台系的中率": (
                    top1_strong / dates * 100
                ),
                "TOP1候補以上率": (
                    top1_candidate / dates * 100
                ),
                "TOP3強い全台系あり率": (
                    top3_strong / dates * 100
                ),
                "TOP3候補以上あり率": (
                    top3_candidate / dates * 100
                ),
                "ガール島予測日数": girl_days,
                "ガール島予測率": (
                    girl_days / dates * 100
                ),
            }
        )

    summary = pd.DataFrame(summary_rows)

    print(
        summary.to_string(
            index=False,
            float_format=lambda x: f"{x:.2f}",
        )
    )

    # ========================================================
    # 島別予測偏り
    # ========================================================

    print()
    print("=" * 80)
    print("=== モデル別 島予測偏り ===")
    print("=" * 80)

    bias_rows = []

    for model in models:

        df = evaluated[
            evaluated["model"] == model
        ]

        if df.empty:
            continue

        dates = df["date"].nunique()

        counts = (
            df.groupby("island")["date"]
            .nunique()
            .reset_index(
                name="予測日数"
            )
        )

        counts["モデル"] = model
        counts["予測日占有率"] = (
            counts["予測日数"]
            / dates
            * 100
        )

        bias_rows.append(counts)

    bias = pd.concat(
        bias_rows,
        ignore_index=True,
    )

    print(
        bias.sort_values(
            ["モデル", "予測日数"],
            ascending=[True, False],
        ).to_string(
            index=False,
            float_format=lambda x: f"{x:.2f}",
        )
    )

    # ========================================================
    # 直前島除外効果
    # ========================================================

    print()
    print("=" * 80)
    print("=== 直前使用島除外効果 ===")
    print("=" * 80)

    base_summary = summary[
        summary["モデル"] == "BASE"
    ]

    if not base_summary.empty:

        base = base_summary.iloc[0]

        for model_name in [
            "PREV_STRONG",
            "PREV_CANDIDATE",
            "LAST2_STRONG",
        ]:

            target = summary[
                summary["モデル"] == model_name
            ]

            if target.empty:
                continue

            target = target.iloc[0]

            print()
            print(model_name)

            print(
                "TOP3強い全台系あり率:",
                f"{target['TOP3強い全台系あり率']:.2f}%",
                "(",
                f"{target['TOP3強い全台系あり率'] - base['TOP3強い全台系あり率']:+.2f}pt",
                ")",
            )

            print(
                "TOP3候補以上あり率:",
                f"{target['TOP3候補以上あり率']:.2f}%",
                "(",
                f"{target['TOP3候補以上あり率'] - base['TOP3候補以上あり率']:+.2f}pt",
                ")",
            )

            print(
                "ガール島予測率:",
                f"{target['ガール島予測率']:.2f}%",
                "(",
                f"{target['ガール島予測率'] - base['ガール島予測率']:+.2f}pt",
                ")",
            )

    # ========================================================
    # 日別結果
    # ========================================================

    daily_rows = []

    for date in sorted(
        evaluated["date"].unique()
    ):

        for model in models:

            df = evaluated[
                (evaluated["date"] == date)
                & (evaluated["model"] == model)
            ]

            if df.empty:
                continue

            top1 = df[
                df["rank"] == 1
            ]

            top3 = df[
                df["rank"] <= 3
            ]

            daily_rows.append(
                {
                    "予測日": date,
                    "モデル": model,
                    "TOP1": (
                        top1.iloc[0]["island"]
                        if not top1.empty
                        else ""
                    ),
                    "TOP1強い": (
                        int(top1["strong"].max())
                        if not top1.empty
                        else 0
                    ),
                    "TOP1候補": (
                        int(top1["candidate"].max())
                        if not top1.empty
                        else 0
                    ),
                    "TOP3強い": (
                        int(top3["strong"].max())
                        if not top3.empty
                        else 0
                    ),
                    "TOP3候補": (
                        int(top3["candidate"].max())
                        if not top3.empty
                        else 0
                    ),
                }
            )

    daily_result = pd.DataFrame(
        daily_rows
    )

    # ========================================================
    # CSV
    # ========================================================

    OUTPUT_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    detail_path = (
        OUTPUT_DIR
        / "nine_day_rotation_constraint_detail.csv"
    )

    summary_path = (
        OUTPUT_DIR
        / "nine_day_rotation_constraint_summary.csv"
    )

    bias_path = (
        OUTPUT_DIR
        / "nine_day_rotation_constraint_bias.csv"
    )

    daily_path = (
        OUTPUT_DIR
        / "nine_day_rotation_constraint_daily.csv"
    )

    evaluated.to_csv(
        detail_path,
        index=False,
        encoding="utf-8-sig",
    )

    summary.to_csv(
        summary_path,
        index=False,
        encoding="utf-8-sig",
    )

    bias.to_csv(
        bias_path,
        index=False,
        encoding="utf-8-sig",
    )

    daily_result.to_csv(
        daily_path,
        index=False,
        encoding="utf-8-sig",
    )

    print()
    print("=" * 80)
    print("=== CSV保存 ===")
    print("=" * 80)

    print(f"詳細: {detail_path}")
    print(f"モデル比較: {summary_path}")
    print(f"島別偏り: {bias_path}")
    print(f"日別結果: {daily_path}")

    print()
    print("=" * 80)
    print("9の日 全台系島ローテーション制約バックテスト終了")
    print("=" * 80)


if __name__ == "__main__":
    main()