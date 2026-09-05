import sqlite3
from pathlib import Path

import numpy as np
import pandas as pd


# ============================================================
# 設定
# ============================================================

DB_PATH = Path(
    r"C:\Users\sphs4\OneDrive\デスクトップ\ジャグラーラボ\database\juggler.db"
)

OUTPUT_DIR = Path(
    r"C:\Users\sphs4\OneDrive\デスクトップ\ジャグラーラボ\analysis\backtest_output"
)

START_DATE = "2026-03-01"

TOP_N = 3

# 直近重視モデル
RECENT_ALL_WEIGHT = 0.30
RECENT_5_WEIGHT = 0.40
RECENT_3_WEIGHT = 0.30

# ローテーション補正
# 「除外」ではなくスコアへの加減点
PREV_STRONG_PENALTY = 8.0
PREV_CANDIDATE_PENALTY = 3.0

# 2回前・3回前に強かった島への軽い加点
LAG2_STRONG_BONUS = 2.0
LAG3_STRONG_BONUS = 3.0

# 営業日種別ごとの補正
TYPE_ROTATION_WEIGHT = 1.0


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


def safe_int(value, default=0):
    try:
        if pd.isna(value):
            return default
        return int(value)
    except Exception:
        return default


def classify_business_day(date_value):
    """
    9日・19日・29日を「9の日」とする。
    """
    try:
        day = pd.Timestamp(date_value).day
        if day in (9, 19, 29):
            return "9の日"
        return "通常日"
    except Exception:
        return "通常日"


def get_cycle_type(date_value):
    """
    9 / 19 / 29 の種別を返す。
    """
    day = pd.Timestamp(date_value).day

    if day == 9:
        return "9日"
    if day == 19:
        return "19日"
    if day == 29:
        return "29日"

    return None


def get_transition_type(previous_date, current_date):
    """
    前回9の日 → 今回9の日の移動タイプ。
    """
    prev_day = pd.Timestamp(previous_date).day
    curr_day = pd.Timestamp(current_date).day

    if prev_day == 9 and curr_day == 19:
        return "9→19"

    if prev_day == 19 and curr_day == 29:
        return "19→29"

    if prev_day == 29 and curr_day == 9:
        return "29→翌月9"

    return "その他"


def normalize_rate(value):
    """
    0～100の割合に正規化。
    """
    value = safe_float(value)

    if value <= 1.0:
        return value * 100.0

    return value


# ============================================================
# DB読み込み
# ============================================================

def load_daily_data():
    print("=" * 80)
    print("DB読み込み")
    print("=" * 80)

    conn = sqlite3.connect(DB_PATH)

    query = """
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
            信頼度補正,
            イベント種別,
            備考,
            島
        FROM daily_data
        WHERE 日付 >= ?
        ORDER BY 日付, 島, 台番号
    """

    df = pd.read_sql_query(
        query,
        conn,
        params=[START_DATE],
    )

    conn.close()

    if df.empty:
        raise RuntimeError("daily_data に対象データがありません。")

    df["日付"] = pd.to_datetime(df["日付"], errors="coerce")
    df["島"] = df["島"].fillna("不明")
    df["評価"] = df["評価"].fillna("")

    print(f"daily_data 行数: {len(df):,}")
    print(
        f"対象期間: "
        f"{df['日付'].min().date()} ～ {df['日付'].max().date()}"
    )

    return df


# ============================================================
# 9の日抽出
# ============================================================

def get_nine_days(df):
    work = df.copy()

    work["営業日タイプ"] = work["日付"].apply(
        classify_business_day
    )

    nine_dates = sorted(
        work.loc[
            work["営業日タイプ"] == "9の日",
            "日付"
        ].dropna().unique()
    )

    return [pd.Timestamp(x) for x in nine_dates]


# ============================================================
# 島別実績計算
# ============================================================

def calculate_island_actual(df, date_value):
    """
    1日の島別実績を計算。

    ここでは既存バックテストと同様に、
    島内の評価台数・評価率・平均G数等から
    実績スコアを作る。

    強い全台系 / 候補以上の判定は
    「島内の高評価率」を中心に行う。
    """

    day_df = df[df["日付"] == date_value].copy()

    if day_df.empty:
        return pd.DataFrame()

    rows = []

    for island, group in day_df.groupby("島"):
        machine_count = len(group)

        if machine_count == 0:
            continue

        evaluations = group["評価"].astype(str)

        strong_count = int(
            evaluations.str.contains("◎", regex=False).sum()
        )

        candidate_count = int(
            evaluations.str.contains(
                r"◎|○",
                regex=True
            ).sum()
        )

        delta_count = int(
            evaluations.str.contains(
                r"◎|○|△",
                regex=True
            ).sum()
        )

        strong_rate = strong_count / machine_count * 100.0
        candidate_rate = candidate_count / machine_count * 100.0
        delta_rate = delta_count / machine_count * 100.0

        avg_g = pd.to_numeric(
            group["G数"],
            errors="coerce"
        ).mean()

        avg_combined = pd.to_numeric(
            group["合成確率"],
            errors="coerce"
        ).mean()

        # 実績スコア
        #
        # ◎を強く評価しつつ、
        # ○以上・△以上も補助的に評価。
        actual_score = (
            strong_rate * 0.60
            + candidate_rate * 0.25
            + delta_rate * 0.15
        )

        # ----------------------------------------------------
        # 全台系判定
        #
        # 強い全台系:
        #   島内◎率 50%以上
        #
        # 候補以上:
        #   島内○以上率 50%以上
        #
        # ※ 既存バックテストと閾値が異なる場合は、
        #    ここだけ既存スクリプトと合わせる。
        # ----------------------------------------------------

        strong = strong_rate >= 50.0
        candidate = candidate_rate >= 50.0

        rows.append(
            {
                "日付": date_value,
                "島": island,
                "台数": machine_count,
                "◎台数": strong_count,
                "○以上台数": candidate_count,
                "△以上台数": delta_count,
                "◎率": strong_rate,
                "○以上率": candidate_rate,
                "△以上率": delta_rate,
                "平均G数": avg_g,
                "平均合成確率": avg_combined,
                "実績スコア": actual_score,
                "強い全台系": int(strong),
                "候補以上": int(candidate),
            }
        )

    return pd.DataFrame(rows)


# ============================================================
# 過去実績
# ============================================================

def build_history(actual_by_date, current_date):
    """
    current_dateより前の9の日実績を返す。
    """

    previous_dates = [
        d for d in actual_by_date.keys()
        if d < current_date
    ]

    previous_dates = sorted(previous_dates)

    return previous_dates


def calculate_base_score(
    island,
    history_dates,
    actual_by_date,
):
    strong_values = []
    candidate_values = []
    score_values = []

    for date_value in history_dates:
        actual = actual_by_date.get(date_value)

        if actual is None or actual.empty:
            continue

        row = actual[actual["島"] == island]

        if row.empty:
            continue

        row = row.iloc[0]

        strong_values.append(
            safe_float(row["強い全台系"])
        )

        candidate_values.append(
            safe_float(row["候補以上"])
        )

        score_values.append(
            safe_float(row["実績スコア"])
        )

    if not strong_values:
        return {
            "過去出現回数": 0,
            "過去強い率": 0.0,
            "過去候補率": 0.0,
            "過去スコア": 0.0,
        }

    return {
        "過去出現回数": len(strong_values),
        "過去強い率": np.mean(strong_values) * 100.0,
        "過去候補率": np.mean(candidate_values) * 100.0,
        "過去スコア": np.mean(score_values),
    }


# ============================================================
# 直近重視スコア
# ============================================================

def calculate_recent_score(
    island,
    history_dates,
    actual_by_date,
):
    if not history_dates:
        return 0.0

    all_score = calculate_base_score(
        island,
        history_dates,
        actual_by_date,
    )["過去スコア"]

    last5_dates = history_dates[-5:]
    last3_dates = history_dates[-3:]

    score5 = calculate_base_score(
        island,
        last5_dates,
        actual_by_date,
    )["過去スコア"]

    score3 = calculate_base_score(
        island,
        last3_dates,
        actual_by_date,
    )["過去スコア"]

    return (
        all_score * RECENT_ALL_WEIGHT
        + score5 * RECENT_5_WEIGHT
        + score3 * RECENT_3_WEIGHT
    )


# ============================================================
# 前回・2回前・3回前
# ============================================================

def get_previous_status(
    island,
    history_dates,
    actual_by_date,
):
    result = {
        "前回強い": False,
        "前回候補": False,
        "2回前強い": False,
        "3回前強い": False,
    }

    if len(history_dates) >= 1:
        row = actual_by_date[history_dates[-1]]
        row = row[row["島"] == island]

        if not row.empty:
            result["前回強い"] = bool(
                safe_int(row.iloc[0]["強い全台系"])
            )

            result["前回候補"] = bool(
                safe_int(row.iloc[0]["候補以上"])
            )

    if len(history_dates) >= 2:
        row = actual_by_date[history_dates[-2]]
        row = row[row["島"] == island]

        if not row.empty:
            result["2回前強い"] = bool(
                safe_int(row.iloc[0]["強い全台系"])
            )

    if len(history_dates) >= 3:
        row = actual_by_date[history_dates[-3]]
        row = row[row["島"] == island]

        if not row.empty:
            result["3回前強い"] = bool(
                safe_int(row.iloc[0]["強い全台系"])
            )

    return result


# ============================================================
# 種別ローテーション実績
# ============================================================

def calculate_transition_bonus(
    island,
    history_dates,
    actual_by_date,
    current_date,
):
    """
    直前の9の日 → 今回の9の日、という
    「移動タイプ」単位の再登場実績を計算。
    """

    if not history_dates:
        return 0.0

    transition = get_transition_type(
        history_dates[-1],
        current_date,
    )

    if transition == "その他":
        return 0.0

    values = []

    for i in range(1, len(history_dates)):
        prev_date = history_dates[i - 1]
        this_date = history_dates[i]

        if get_transition_type(
            prev_date,
            this_date,
        ) != transition:
            continue

        actual = actual_by_date.get(this_date)

        if actual is None:
            continue

        row = actual[actual["島"] == island]

        if row.empty:
            continue

        values.append(
            safe_float(
                row.iloc[0]["強い全台系"]
            )
        )

    if not values:
        return 0.0

    # 強い全台系率を補正値として利用
    rate = np.mean(values)

    return rate * 10.0 * TYPE_ROTATION_WEIGHT


# ============================================================
# モデルスコア
# ============================================================

def calculate_model_score(
    model,
    island,
    history_dates,
    actual_by_date,
    current_date,
):
    base = calculate_base_score(
        island,
        history_dates,
        actual_by_date,
    )

    base_score = (
        base["過去強い率"] * 0.60
        + base["過去候補率"] * 0.30
        + base["過去スコア"] * 0.10
    )

    recent_score = calculate_recent_score(
        island,
        history_dates,
        actual_by_date,
    )

    status = get_previous_status(
        island,
        history_dates,
        actual_by_date,
    )

    transition_bonus = calculate_transition_bonus(
        island,
        history_dates,
        actual_by_date,
        current_date,
    )

    # --------------------------------------------------------
    # BASE
    # --------------------------------------------------------

    if model == "BASE":
        return base_score

    # --------------------------------------------------------
    # RECENT
    # --------------------------------------------------------

    if model == "RECENT":
        return (
            base_score * 0.40
            + recent_score * 0.60
        )

    # --------------------------------------------------------
    # TYPE_ROTATION
    # --------------------------------------------------------

    if model == "TYPE_ROTATION":
        return (
            base_score
            + transition_bonus
        )

    # --------------------------------------------------------
    # SOFT_ROTATION
    # --------------------------------------------------------

    if model == "SOFT_ROTATION":
        score = base_score

        if status["前回強い"]:
            score -= PREV_STRONG_PENALTY

        elif status["前回候補"]:
            score -= PREV_CANDIDATE_PENALTY

        if status["2回前強い"]:
            score += LAG2_STRONG_BONUS

        if status["3回前強い"]:
            score += LAG3_STRONG_BONUS

        return score

    # --------------------------------------------------------
    # COMBINED
    # --------------------------------------------------------

    if model == "COMBINED":
        score = (
            base_score * 0.35
            + recent_score * 0.40
            + transition_bonus * 0.25
        )

        if status["前回強い"]:
            score -= PREV_STRONG_PENALTY

        elif status["前回候補"]:
            score -= PREV_CANDIDATE_PENALTY

        if status["2回前強い"]:
            score += LAG2_STRONG_BONUS

        if status["3回前強い"]:
            score += LAG3_STRONG_BONUS

        return score

    return base_score


# ============================================================
# バックテスト
# ============================================================

def run_backtest(df):
    nine_dates = get_nine_days(df)

    print()
    print("=" * 80)
    print("9の日 島予測・時系列重み＋ローテーション補正バックテスト")
    print("=" * 80)

    print()
    print(f"検証対象9の日数: {len(nine_dates)}")

    if len(nine_dates) < 2:
        raise RuntimeError(
            "バックテスト可能な9の日が不足しています。"
        )

    # --------------------------------------------------------
    # 各9日の実績を先に作成
    # --------------------------------------------------------

    actual_by_date = {}

    for date_value in nine_dates:
        actual = calculate_island_actual(
            df,
            date_value,
        )

        actual_by_date[date_value] = actual

    islands = sorted(
        df["島"].dropna().unique()
    )

    models = [
        "BASE",
        "RECENT",
        "TYPE_ROTATION",
        "SOFT_ROTATION",
        "COMBINED",
    ]

    detail_rows = []

    # --------------------------------------------------------
    # 未来を使わない逐次バックテスト
    # --------------------------------------------------------

    for idx, current_date in enumerate(nine_dates):

        history_dates = [
            d for d in nine_dates
            if d < current_date
        ]

        # 初回は過去データがないため予測しない
        if not history_dates:
            continue

        actual = actual_by_date[current_date]

        for model in models:

            scores = []

            for island in islands:

                score = calculate_model_score(
                    model,
                    island,
                    history_dates,
                    actual_by_date,
                    current_date,
                )

                scores.append(
                    {
                        "島": island,
                        "期待度スコア": score,
                    }
                )

            score_df = pd.DataFrame(scores)

            score_df = score_df.sort_values(
                ["期待度スコア", "島"],
                ascending=[False, True],
            ).reset_index(drop=True)

            score_df["予測順位"] = (
                score_df.index + 1
            )

            top3 = score_df.head(TOP_N)

            for _, pred in top3.iterrows():

                island = pred["島"]

                actual_row = actual[
                    actual["島"] == island
                ]

                if actual_row.empty:
                    strong = 0
                    candidate = 0
                    actual_score = 0.0
                    actual_strong_rate = 0.0
                else:
                    actual_row = actual_row.iloc[0]

                    strong = safe_int(
                        actual_row["強い全台系"]
                    )

                    candidate = safe_int(
                        actual_row["候補以上"]
                    )

                    actual_score = safe_float(
                        actual_row["実績スコア"]
                    )

                    actual_strong_rate = safe_float(
                        actual_row["◎率"]
                    )

                history_info = calculate_base_score(
                    island,
                    history_dates,
                    actual_by_date,
                )

                status = get_previous_status(
                    island,
                    history_dates,
                    actual_by_date,
                )

                detail_rows.append(
                    {
                        "予測日": current_date.date(),
                        "営業日種別": get_cycle_type(
                            current_date
                        ),
                        "モデル": model,
                        "予測順位": int(
                            pred["予測順位"]
                        ),
                        "島": island,
                        "期待度スコア": safe_float(
                            pred["期待度スコア"]
                        ),
                        "過去出現回数": history_info[
                            "過去出現回数"
                        ],
                        "過去強い率": history_info[
                            "過去強い率"
                        ],
                        "過去候補率": history_info[
                            "過去候補率"
                        ],
                        "前回強い": int(
                            status["前回強い"]
                        ),
                        "前回候補": int(
                            status["前回候補"]
                        ),
                        "2回前強い": int(
                            status["2回前強い"]
                        ),
                        "3回前強い": int(
                            status["3回前強い"]
                        ),
                        "強い全台系": strong,
                        "候補以上": candidate,
                        "実績◎率": actual_strong_rate,
                        "実績スコア": actual_score,
                    }
                )

    detail_df = pd.DataFrame(detail_rows)

    return detail_df


# ============================================================
# 集計
# ============================================================

def summarize(detail_df):

    rows = []

    for model, group in detail_df.groupby("モデル"):

        dates = sorted(
            group["予測日"].unique()
        )

        total_days = len(dates)

        top1 = group[
            group["予測順位"] == 1
        ]

        top3 = group[
            group["予測順位"] <= 3
        ]

        top1_strong_days = (
            top1.groupby("予測日")[
                "強い全台系"
            ].max()
            > 0
        ).sum()

        top1_candidate_days = (
            top1.groupby("予測日")[
                "候補以上"
            ].max()
            > 0
        ).sum()

        top3_strong_days = (
            top3.groupby("予測日")[
                "強い全台系"
            ].max()
            > 0
        ).sum()

        top3_candidate_days = (
            top3.groupby("予測日")[
                "候補以上"
            ].max()
            > 0
        ).sum()

        girl = top3[
            top3["島"] == "ガール島"
        ]

        girl_prediction_days = (
            girl["予測日"].nunique()
        )

        top1_girl = top1[
            top1["島"] == "ガール島"
        ]

        top1_girl_days = (
            top1_girl["予測日"].nunique()
        )

        avg_score = (
            top3.groupby("予測日")[
                "実績スコア"
            ].mean().mean()
        )

        rows.append(
            {
                "モデル": model,
                "検証日数": total_days,
                "TOP1強い全台系的中率":
                    top1_strong_days
                    / total_days
                    * 100,
                "TOP1候補以上率":
                    top1_candidate_days
                    / total_days
                    * 100,
                "TOP3強い全台系あり率":
                    top3_strong_days
                    / total_days
                    * 100,
                "TOP3候補以上あり率":
                    top3_candidate_days
                    / total_days
                    * 100,
                "平均TOP3実績スコア":
                    avg_score,
                "ガール島予測日数":
                    girl_prediction_days,
                "ガール島予測率":
                    girl_prediction_days
                    / total_days
                    * 100,
                "ガール島TOP1率":
                    top1_girl_days
                    / total_days
                    * 100,
            }
        )

    return pd.DataFrame(rows)


# ============================================================
# 島別偏り
# ============================================================

def island_bias(detail_df):

    rows = []

    for model, group in detail_df.groupby("モデル"):

        top3 = group[
            group["予測順位"] <= 3
        ]

        total_days = group[
            "予測日"
        ].nunique()

        for island, island_group in top3.groupby("島"):

            prediction_days = island_group[
                "予測日"
            ].nunique()

            prediction_rate = (
                prediction_days
                / total_days
                * 100
            )

            # 実際の強い全台系率
            actual_all = (
                group[
                    group["島"] == island
                ][
                    [
                        "予測日",
                        "強い全台系",
                    ]
                ]
                .drop_duplicates(
                    "予測日"
                )
            )

            actual_days = len(actual_all)

            strong_count = int(
                actual_all[
                    "強い全台系"
                ].sum()
            )

            strong_rate = (
                strong_count
                / actual_days
                * 100
                if actual_days > 0
                else 0.0
            )

            overconcentration = (
                prediction_rate
                / strong_rate
                if strong_rate > 0
                else np.nan
            )

            rows.append(
                {
                    "モデル": model,
                    "島": island,
                    "予測日数": prediction_days,
                    "予測日占有率": prediction_rate,
                    "強い全台系回数": strong_count,
                    "強い全台系率": strong_rate,
                    "過集中倍率": overconcentration,
                }
            )

    return pd.DataFrame(rows)


# ============================================================
# 日別結果
# ============================================================

def daily_result(detail_df):

    rows = []

    for (
        model,
        date_value
    ), group in detail_df.groupby(
        ["モデル", "予測日"]
    ):

        top1 = group[
            group["予測順位"] == 1
        ]

        top3 = group[
            group["予測順位"] <= 3
        ]

        top1_island = (
            top1.iloc[0]["島"]
            if not top1.empty
            else ""
        )

        top3_islands = " / ".join(
            top3.sort_values(
                "予測順位"
            )["島"].tolist()
        )

        rows.append(
            {
                "モデル": model,
                "予測日": date_value,
                "TOP1": top1_island,
                "TOP3": top3_islands,
                "TOP1強い全台系":
                    int(
                        top1[
                            "強い全台系"
                        ].max()
                    )
                    if not top1.empty
                    else 0,
                "TOP1候補以上":
                    int(
                        top1[
                            "候補以上"
                        ].max()
                    )
                    if not top1.empty
                    else 0,
                "TOP3強い全台系":
                    int(
                        top3[
                            "強い全台系"
                        ].max()
                    )
                    if not top3.empty
                    else 0,
                "TOP3候補以上":
                    int(
                        top3[
                            "候補以上"
                        ].max()
                    )
                    if not top3.empty
                    else 0,
            }
        )

    return pd.DataFrame(rows)


# ============================================================
# メイン
# ============================================================

def main():

    OUTPUT_DIR.mkdir(
        parents=True,
        exist_ok=True
    )

    df = load_daily_data()

    detail_df = run_backtest(df)

    if detail_df.empty:
        raise RuntimeError(
            "バックテスト結果がありません。"
        )

    summary_df = summarize(
        detail_df
    )

    bias_df = island_bias(
        detail_df
    )

    daily_df = daily_result(
        detail_df
    )

    # --------------------------------------------------------
    # 表示
    # --------------------------------------------------------

    print()
    print("=" * 80)
    print("=== モデル別バックテスト ===")
    print("=" * 80)

    display_summary = summary_df.copy()

    numeric_columns = [
        "TOP1強い全台系的中率",
        "TOP1候補以上率",
        "TOP3強い全台系あり率",
        "TOP3候補以上あり率",
        "平均TOP3実績スコア",
        "ガール島予測率",
        "ガール島TOP1率",
    ]

    for col in numeric_columns:
        display_summary[col] = display_summary[
            col
        ].round(2)

    print(
        display_summary.to_string(
            index=False
        )
    )

    # --------------------------------------------------------

    print()
    print("=" * 80)
    print("=== モデル別 島予測偏り ===")
    print("=" * 80)

    bias_display = bias_df.copy()

    for col in [
        "予測日占有率",
        "強い全台系率",
        "過集中倍率",
    ]:
        bias_display[col] = bias_display[
            col
        ].round(2)

    print(
        bias_display.sort_values(
            [
                "モデル",
                "予測日占有率",
            ],
            ascending=[True, False],
        ).to_string(
            index=False
        )
    )

    # --------------------------------------------------------

    print()
    print("=" * 80)
    print("=== ガール島集中比較 ===")
    print("=" * 80)

    girl = bias_df[
        bias_df["島"] == "ガール島"
    ].copy()

    if not girl.empty:
        print(
            girl[
                [
                    "モデル",
                    "予測日数",
                    "予測日占有率",
                    "強い全台系回数",
                    "強い全台系率",
                    "過集中倍率",
                ]
            ]
            .round(2)
            .to_string(index=False)
        )

    # --------------------------------------------------------

    print()
    print("=" * 80)
    print("=== 日別 TOP1 / TOP3 ===")
    print("=" * 80)

    for model in [
        "BASE",
        "RECENT",
        "TYPE_ROTATION",
        "SOFT_ROTATION",
        "COMBINED",
    ]:

        print()
        print(f"--- {model} ---")

        temp = daily_df[
            daily_df["モデル"] == model
        ].copy()

        print(
            temp.to_string(
                index=False
            )
        )

    # --------------------------------------------------------
    # CSV
    # --------------------------------------------------------

    detail_path = (
        OUTPUT_DIR
        / "nine_day_rotation_weighted_detail.csv"
    )

    summary_path = (
        OUTPUT_DIR
        / "nine_day_rotation_weighted_summary.csv"
    )

    bias_path = (
        OUTPUT_DIR
        / "nine_day_rotation_weighted_bias.csv"
    )

    daily_path = (
        OUTPUT_DIR
        / "nine_day_rotation_weighted_daily.csv"
    )

    detail_df.to_csv(
        detail_path,
        index=False,
        encoding="utf-8-sig",
    )

    summary_df.to_csv(
        summary_path,
        index=False,
        encoding="utf-8-sig",
    )

    bias_df.to_csv(
        bias_path,
        index=False,
        encoding="utf-8-sig",
    )

    daily_df.to_csv(
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
    print("9の日 島予測・時系列重み＋ローテーション補正バックテスト終了")
    print("=" * 80)


if __name__ == "__main__":
    main()