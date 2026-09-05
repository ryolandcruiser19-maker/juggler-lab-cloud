"""
9の日 全台系実績・構成確認

目的
----
過去の9の日について、島単位で
◎・○・△の構成を確認する。

重要
----
簡易データ期間も含める。

ただし簡易データ期間では、
「未記録」と「低評価」を完全には区別できないため、
現在の島台数を分母とする現行方式を再現しつつ、
記録台数・記録率も併記する。

確認内容
--------
1. 9の日ごとの島別結果
2. STRONG / CANDIDATE の判定
3. ◎率 / ○以上率 / △以上率
4. 記録率
5. STRONG島の平均・中央値
6. STRONG島の分布
7. STRONG判定なのに○以上率が低い島
8. 簡易データ期間を含めた全期間の傾向

出力
----
analysis/backtest_output/
    nine_day_all_setting_distribution.csv
"""

import sqlite3
from pathlib import Path

import pandas as pd


# ============================================================
# 設定
# ============================================================

BASE_DIR = Path(__file__).resolve().parent.parent

DB_PATH = BASE_DIR / "database" / "juggler.db"

OUTPUT_DIR = BASE_DIR / "analysis" / "backtest_output"

OUTPUT_DETAIL = (
    OUTPUT_DIR / "nine_day_all_setting_distribution.csv"
)


# ============================================================
# 現行判定
# ============================================================

STRONG_RATE = 80.0
CANDIDATE_RATE = 70.0

MIN_MACHINES = 5


# ============================================================
# 現在の島台数
#
# 重要:
# 現在の島構成を分母として使用する。
# ============================================================

CURRENT_ISLAND_MACHINES = {
    "ガール島": 10,
    "ゴー島①": 10,
    "ゴー島②": 10,

    "ネオアイム島②": 8,
    "ネオアイム島③": 8,
    "ネオアイム島④": 12,
    "ネオアイム島⑤": 12,
    "ネオアイム島⑥": 8,

    "ハッピ島": 8,

    "ファン島①": 10,
    "ファン島②": 10,

    "マイジャグ島A": 15,
    "マイジャグ島B": 10,
    "マイジャグ島C": 10,
    "マイジャグ島D": 15,

    "ミスタ島": 10,
    "ミラクル島": 10,
}


# ============================================================
# 9の日判定
# ============================================================

def is_nine_day(value):
    """
    日付の「日」が9 / 19 / 29ならTrue。
    """
    try:
        day = pd.Timestamp(value).day
        return day in (9, 19, 29)
    except Exception:
        return False


# ============================================================
# 評価値を正規化
# ============================================================

def normalize_evaluation(value):
    """
    DB上の評価値を正規化する。

    想定:
        ◎
        ○
        △

    それ以外:
        未記録
    """

    if pd.isna(value):
        return ""

    value = str(value).strip()

    if value in ("◎", "○", "△"):
        return value

    return ""


# ============================================================
# メイン
# ============================================================

def main():

    print("=" * 80)
    print("9の日 全台系実績・構成確認")
    print("=" * 80)

    # ========================================================
    # DB読み込み
    # ========================================================

    conn = sqlite3.connect(DB_PATH)

    df = pd.read_sql_query(
        """
        SELECT
            日付,
            島,
            評価
        FROM daily_data
        WHERE 島 IS NOT NULL
        """,
        conn,
    )

    conn.close()

    print()
    print("DB読み込み")
    print("-" * 80)

    print("rows:", len(df))

    print("columns:", list(df.columns))

    # ========================================================
    # データ整形
    # ========================================================

    df["日付"] = pd.to_datetime(
        df["日付"],
        errors="coerce",
    )

    df["評価"] = df["評価"].apply(
        normalize_evaluation
    )

    # ========================================================
    # 9の日のみ
    # ========================================================

    df = df[
        df["日付"].apply(is_nine_day)
    ].copy()

    print()
    print("9の日")
    print("-" * 80)

    print("9の日 rows:", len(df))

    # ========================================================
    # 現在の島だけに限定
    # ========================================================

    df = df[
        df["島"].isin(
            CURRENT_ISLAND_MACHINES.keys()
        )
    ].copy()

    # ========================================================
    # 9の日一覧
    # ========================================================

    dates = sorted(
        df["日付"]
        .dropna()
        .unique()
    )

    print()
    print("9の日数:", len(dates))

    for i, date in enumerate(dates, start=1):

        date_df = df[
            df["日付"] == date
        ]

        island_count = date_df["島"].nunique()

        print(
            f"{i:2d}: "
            f"{pd.Timestamp(date).strftime('%Y-%m-%d')} "
            f"islands={island_count}"
        )

    # ========================================================
    # 島別集計
    # ========================================================

    results = []

    for date in dates:

        day_df = df[
            df["日付"] == date
        ]

        for island, machine_count in (
            CURRENT_ISLAND_MACHINES.items()
        ):

            if machine_count < MIN_MACHINES:
                continue

            group = day_df[
                day_df["島"] == island
            ]

            # ------------------------------------------------
            # 評価台数
            # ------------------------------------------------

            star_count = int(
                (group["評価"] == "◎").sum()
            )

            circle_count = int(
                (group["評価"] == "○").sum()
            )

            triangle_count = int(
                (group["評価"] == "△").sum()
            )

            recorded_count = (
                star_count
                + circle_count
                + triangle_count
            )

            # ------------------------------------------------
            # 現在島台数を分母とする
            # ------------------------------------------------

            total = machine_count

            # ------------------------------------------------
            # 記録率
            # ------------------------------------------------

            recorded_rate = (
                recorded_count
                / total
                * 100
            )

            # ------------------------------------------------
            # ◎率
            # ------------------------------------------------

            star_rate = (
                star_count
                / total
                * 100
            )

            # ------------------------------------------------
            # ○以上
            # ------------------------------------------------

            circle_or_better_count = (
                star_count
                + circle_count
            )

            circle_or_better_rate = (
                circle_or_better_count
                / total
                * 100
            )

            # ------------------------------------------------
            # △以上
            # ------------------------------------------------

            triangle_or_better_count = (
                star_count
                + circle_count
                + triangle_count
            )

            triangle_or_better_rate = (
                triangle_or_better_count
                / total
                * 100
            )

            # ------------------------------------------------
            # 現行判定
            # ------------------------------------------------

            if (
                triangle_or_better_rate
                >= STRONG_RATE
            ):

                judge = "STRONG"

            elif (
                triangle_or_better_rate
                >= CANDIDATE_RATE
            ):

                judge = "CANDIDATE"

            else:

                judge = ""

            # ------------------------------------------------
            # 結果
            # ------------------------------------------------

            results.append(
                {
                    "日付":
                        pd.Timestamp(date).strftime(
                            "%Y-%m-%d"
                        ),

                    "島":
                        island,

                    "現在島台数":
                        total,

                    "記録台数":
                        recorded_count,

                    "記録率":
                        round(
                            recorded_rate,
                            2,
                        ),

                    "◎台数":
                        star_count,

                    "○台数":
                        circle_count,

                    "△台数":
                        triangle_count,

                    "◎率":
                        round(
                            star_rate,
                            2,
                        ),

                    "○以上率":
                        round(
                            circle_or_better_rate,
                            2,
                        ),

                    "△以上率":
                        round(
                            triangle_or_better_rate,
                            2,
                        ),

                    "現行判定":
                        judge,
                }
            )

    result_df = pd.DataFrame(results)

    # ========================================================
    # 保存
    # ========================================================

    OUTPUT_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    result_df.to_csv(
        OUTPUT_DETAIL,
        index=False,
        encoding="utf-8-sig",
    )

    # ========================================================
    # STRONG / CANDIDATE
    # ========================================================

    strong_df = result_df[
        result_df["現行判定"] == "STRONG"
    ].copy()

    candidate_df = result_df[
        result_df["現行判定"] == "CANDIDATE"
    ].copy()

    print()
    print("=" * 80)
    print("現行strong実績")
    print("=" * 80)

    print(
        "strong島数:",
        len(strong_df),
    )

    print(
        "candidate島数:",
        len(candidate_df),
    )

    # ========================================================
    # STRONG平均
    # ========================================================

    if not strong_df.empty:

        print()
        print("strong島の平均")

        print(
            "平均 ◎率       :",
            round(
                strong_df["◎率"].mean(),
                2,
            ),
        )

        print(
            "平均 ○以上率   :",
            round(
                strong_df["○以上率"].mean(),
                2,
            ),
        )

        print(
            "平均 △以上率   :",
            round(
                strong_df["△以上率"].mean(),
                2,
            ),
        )

        print(
            "平均 記録率     :",
            round(
                strong_df["記録率"].mean(),
                2,
            ),
        )

        print()
        print("strong島の中央値")

        print(
            "中央値 ◎率     :",
            round(
                strong_df["◎率"].median(),
                2,
            ),
        )

        print(
            "中央値 ○以上率 :",
            round(
                strong_df["○以上率"].median(),
                2,
            ),
        )

        print(
            "中央値 △以上率 :",
            round(
                strong_df["△以上率"].median(),
                2,
            ),
        )

        print(
            "中央値 記録率   :",
            round(
                strong_df["記録率"].median(),
                2,
            ),
        )

    # ========================================================
    # STRONG島一覧
    # ========================================================

    print()
    print("=" * 80)
    print("strong島一覧")
    print("=" * 80)

    if strong_df.empty:

        print("なし")

    else:

        show_cols = [
            "日付",
            "島",
            "現在島台数",
            "記録台数",
            "記録率",
            "◎率",
            "○以上率",
            "△以上率",
        ]

        print(
            strong_df[
                show_cols
            ].to_string(index=False)
        )

    # ========================================================
    # ○以上率分布
    # ========================================================

    print()
    print("=" * 80)
    print("strong島の○以上率分布")
    print("=" * 80)

    if not strong_df.empty:

        bins = [
            -0.01,
            20,
            40,
            50,
            60,
            70,
            80,
            90,
            100.01,
        ]

        labels = [
            "0-20%",
            "20-40%",
            "40-50%",
            "50-60%",
            "60-70%",
            "70-80%",
            "80-90%",
            "90-100%",
        ]

        distribution = (
            pd.cut(
                strong_df["○以上率"],
                bins=bins,
                labels=labels,
            )
            .value_counts(
                sort=False
            )
        )

        print(distribution)

    # ========================================================
    # ◎率分布
    # ========================================================

    print()
    print("=" * 80)
    print("strong島の◎率分布")
    print("=" * 80)

    if not strong_df.empty:

        bins = [
            -0.01,
            10,
            20,
            30,
            40,
            50,
            60,
            70,
            80,
            90,
            100.01,
        ]

        labels = [
            "0-10%",
            "10-20%",
            "20-30%",
            "30-40%",
            "40-50%",
            "50-60%",
            "60-70%",
            "70-80%",
            "80-90%",
            "90-100%",
        ]

        distribution = (
            pd.cut(
                strong_df["◎率"],
                bins=bins,
                labels=labels,
            )
            .value_counts(
                sort=False
            )
        )

        print(distribution)

    # ========================================================
    # STRONGなのに○以上率が低い島
    #
    # 現行判定は△以上80%以上なので、
    # △が大量に含まれるケースを確認する。
    # ========================================================

    print()
    print("=" * 80)
    print(
        "strongだが○以上率が低い島"
    )
    print("=" * 80)

    suspicious = strong_df[
        strong_df["○以上率"] < 50
    ].copy()

    if suspicious.empty:

        print("なし")

    else:

        show_cols = [
            "日付",
            "島",
            "現在島台数",
            "記録台数",
            "記録率",
            "◎率",
            "○以上率",
            "△以上率",
        ]

        print(
            suspicious[
                show_cols
            ].to_string(index=False)
        )

    # ========================================================
    # 記録率が低いSTRONG
    #
    # 簡易データ期間の影響を確認するための重要指標
    # ========================================================

    print()
    print("=" * 80)
    print(
        "strongだが記録率が低い島"
    )
    print("=" * 80)

    low_record = strong_df[
        strong_df["記録率"] < 70
    ].copy()

    if low_record.empty:

        print("なし")

    else:

        show_cols = [
            "日付",
            "島",
            "現在島台数",
            "記録台数",
            "記録率",
            "◎率",
            "○以上率",
            "△以上率",
        ]

        print(
            low_record[
                show_cols
            ].to_string(index=False)
        )

    # ========================================================
    # 9の日ごとのSTRONG島数
    # ========================================================

    print()
    print("=" * 80)
    print("9の日ごとのSTRONG島数")
    print("=" * 80)

    if not result_df.empty:

        date_summary = (
            result_df
            .groupby("日付")
            .agg(
                島数=("島", "count"),
                STRONG=("現行判定",
                        lambda x:
                        (x == "STRONG").sum()),
                CANDIDATE=("現行判定",
                           lambda x:
                           (x == "CANDIDATE").sum()),
            )
            .reset_index()
        )

        print(
            date_summary.to_string(
                index=False
            )
        )

    # ========================================================
    # 島別STRONG回数
    # ========================================================

    print()
    print("=" * 80)
    print("島別STRONG回数")
    print("=" * 80)

    island_summary = (
        strong_df
        .groupby("島")
        .size()
        .reset_index(
            name="STRONG回数"
        )
        .sort_values(
            "STRONG回数",
            ascending=False,
        )
    )

    if island_summary.empty:

        print("なし")

    else:

        print(
            island_summary.to_string(
                index=False
            )
        )

    # ========================================================
    # 終了
    # ========================================================

    print()
    print("=" * 80)
    print("保存完了")
    print("=" * 80)

    print(
        "detail:",
        OUTPUT_DETAIL,
    )


# ============================================================
# 実行
# ============================================================

if __name__ == "__main__":
    main()