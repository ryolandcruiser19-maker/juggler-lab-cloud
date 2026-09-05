"""
ジャグラーラボ
特定日（9・19・29日）×機種ローテーション分析

目的
-----
・9日、19日、29日に強くなりやすい機種を調べる
・マイジャグラーは除外する
・古い手動記録と現在の全台データを分離する
・古い手動記録は「強かった機種の履歴」として利用する
・全台データの期間だけ、全台系の強さを定量評価する

重要
-----
古いデータでは「△以上の台だけ」を手動記録しているため、
対象台数・△以上率を現在のデータと同じ意味では扱わない。
"""

import sqlite3
from pathlib import Path
from collections import defaultdict

import pandas as pd


# ============================================================
# DB設定
# ============================================================

BASE_DIR = Path(__file__).resolve().parent.parent

DB_PATH = BASE_DIR / "database" / "juggler.db"


# ============================================================
# 分析設定
# ============================================================

START_DATE = "2026-02-01"

SPECIAL_DAYS = {9, 19, 29}


# ============================================================
# 表示設定
# ============================================================

pd.set_option("display.max_columns", None)
pd.set_option("display.width", 200)
pd.set_option("display.max_rows", 500)


# ============================================================
# データ取得
# ============================================================

def load_data():

    print("=" * 70)
    print("特定日×機種ローテーション分析")
    print("=" * 70)

    print()
    print(f"DB: {DB_PATH}")
    print(f"分析開始日: {START_DATE}")
    print("対象日: 9日・19日・29日")
    print("マイジャグラー: 除外")
    print()

    conn = sqlite3.connect(DB_PATH)

    try:

        # SQLでは日付だけを条件にする。
        # 日本語カラム名や % をSQL側で複雑に扱わない。
        sql = """
        SELECT
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
        FROM island_all_setting_analysis
        WHERE 日付 >= ?
        ORDER BY 日付 DESC
        """

        df = pd.read_sql_query(
            sql,
            conn,
            params=(START_DATE,)
        )

    finally:
        conn.close()

    if df.empty:
        print("対象データがありません。")
        return df

    # --------------------------------------------------------
    # 日付をdatetime化
    # --------------------------------------------------------

    df["日付"] = pd.to_datetime(
        df["日付"],
        errors="coerce"
    )

    # --------------------------------------------------------
    # 特定日だけ抽出
    # --------------------------------------------------------

    df = df[
        df["日付"].dt.day.isin(SPECIAL_DAYS)
    ].copy()

    # --------------------------------------------------------
    # マイジャグラー除外
    #
    # 「マイジャグ」が島名に含まれるものを除外
    # --------------------------------------------------------

    df = df[
        ~df["島"].astype(str).str.contains(
            "マイジャグ",
            na=False
        )
    ].copy()

    # --------------------------------------------------------
    # 島名の前後空白を除去
    # --------------------------------------------------------

    df["島"] = (
        df["島"]
        .astype(str)
        .str.strip()
    )

    # --------------------------------------------------------
    # データ種別判定
    #
    # 平均G数・平均合成確率がある
    # → 現在の全台データ
    #
    # どちらかが欠損
    # → 古い手動記録の可能性が高い
    # --------------------------------------------------------

    df["データ種別"] = "完全データ"

    manual_mask = (
        df["平均G数"].isna()
        | df["平均合成確率"].isna()
    )

    df.loc[
        manual_mask,
        "データ種別"
    ] = "手動記録"

    return df


# ============================================================
# 基本確認
# ============================================================

def show_basic(df):

    print()
    print("=" * 70)
    print("基本確認")
    print("=" * 70)

    print()

    print(f"対象件数: {len(df)}")

    print()

    print("データ種別:")
    print(
        df["データ種別"]
        .value_counts()
        .to_string()
    )

    print()

    print("特定日別件数:")

    day_counts = (
        df["日付"]
        .dt.day
        .value_counts()
        .sort_index()
    )

    print(day_counts.to_string())

    print()

    print("対象機種:")

    machines = sorted(
        df["島"]
        .dropna()
        .unique()
        .tolist()
    )

    for machine in machines:
        print(f"  {machine}")


# ============================================================
# 各特定日の結果
# ============================================================

def show_date_results(df):

    print()
    print("=" * 70)
    print("特定日ごとの強機種")
    print("=" * 70)

    print()

    # 日付単位で処理
    for date in sorted(
        df["日付"].dropna().unique(),
        reverse=True
    ):

        day_df = df[
            df["日付"] == date
        ].copy()

        if day_df.empty:
            continue

        print()
        print("-" * 70)
        print(
            f"{pd.Timestamp(date).strftime('%Y-%m-%d')}"
            f"  "
            f"（{pd.Timestamp(date).day}日）"
        )
        print("-" * 70)

        # 結果強度で並べる
        day_df = day_df.sort_values(
            "結果強度",
            ascending=False,
            na_position="last"
        )

        columns = [
            "島",
            "データ種別",
            "対象台数",
            "△以上台数",
            "△以上率",
            "◎率",
            "○率",
            "△率",
            "平均G数",
            "平均合成確率",
            "全台系スコア",
            "結果強度",
            "判定",
        ]

        print(
            day_df[columns]
            .to_string(index=False)
        )


# ============================================================
# 機種別ローテーション集計
# ============================================================

def create_machine_summary(df):

    rows = []

    for machine, group in df.groupby("島"):

        group = group.sort_values("日付")

        full = group[
            group["データ種別"] == "完全データ"
        ]

        manual = group[
            group["データ種別"] == "手動記録"
        ]

        # ----------------------------------------------------
        # 完全データ
        # ----------------------------------------------------

        full_count = len(full)

        full_strong_count = len(
            full[
                full["判定"] == "強い全台系候補"
            ]
        )

        full_candidate_count = len(
            full[
                full["判定"].isin(
                    [
                        "強い全台系候補",
                        "全台系候補",
                        "弱い全台系候補",
                    ]
                )
            ]
        )

        if full_count > 0:

            avg_strength = full[
                "結果強度"
            ].mean()

            avg_score = full[
                "全台系スコア"
            ].mean()

            avg_rate = full[
                "△以上率"
            ].mean()

            avg_big_rate = full[
                "◎率"
            ].mean()

        else:

            avg_strength = None
            avg_score = None
            avg_rate = None
            avg_big_rate = None

        # ----------------------------------------------------
        # 手動記録
        #
        # ここでは「割合」を使わない。
        # その機種が強かった日が存在したかを見る。
        # ----------------------------------------------------

        manual_count = len(manual)

        manual_recorded_count = manual[
            "△以上台数"
        ].fillna(0).sum()

        # ----------------------------------------------------
        # 特定日別の実績
        # ----------------------------------------------------

        day9 = group[
            group["日付"].dt.day == 9
        ]

        day19 = group[
            group["日付"].dt.day == 19
        ]

        day29 = group[
            group["日付"].dt.day == 29
        ]

        # ----------------------------------------------------
        # 直近採用日
        # ----------------------------------------------------

        latest_date = group["日付"].max()

        # ----------------------------------------------------
        # 最終的な行
        # ----------------------------------------------------

        rows.append(
            {
                "機種": machine,

                "特定日出現回数": len(group),

                "完全データ回数": full_count,

                "手動記録回数": manual_count,

                "完全データ_強い全台系": full_strong_count,

                "完全データ_全台系候補": full_candidate_count,

                "平均結果強度": avg_strength,

                "平均全台系スコア": avg_score,

                "平均△以上率": avg_rate,

                "平均◎率": avg_big_rate,

                "手動記録_△以上台数合計":
                    int(manual_recorded_count),

                "9日出現回数": len(day9),

                "19日出現回数": len(day19),

                "29日出現回数": len(day29),

                "直近特定日": latest_date.strftime(
                    "%Y-%m-%d"
                ),
            }
        )

    summary = pd.DataFrame(rows)

    return summary


# ============================================================
# 機種別サマリー表示
# ============================================================

def show_machine_summary(df):

    summary = create_machine_summary(df)

    if summary.empty:
        print("機種別集計データがありません。")
        return summary

    print()
    print("=" * 70)
    print("機種別・特定日ローテーション集計")
    print("=" * 70)

    print()

    # 完全データでの強い全台系回数
    # → 手動記録とは混ぜない
    summary = summary.sort_values(
        [
            "完全データ_強い全台系",
            "平均結果強度",
            "特定日出現回数",
        ],
        ascending=[
            False,
            False,
            False,
        ],
        na_position="last"
    )

    display_columns = [
        "機種",
        "特定日出現回数",
        "完全データ回数",
        "手動記録回数",
        "完全データ_強い全台系",
        "完全データ_全台系候補",
        "平均結果強度",
        "平均全台系スコア",
        "平均△以上率",
        "平均◎率",
        "手動記録_△以上台数合計",
        "9日出現回数",
        "19日出現回数",
        "29日出現回数",
        "直近特定日",
    ]

    print(
        summary[
            display_columns
        ].to_string(index=False)
    )

    return summary


# ============================================================
# 特定日ごとの機種順位
# ============================================================

def show_special_day_machine_ranking(df):

    print()
    print("=" * 70)
    print("特定日別・機種ランキング")
    print("=" * 70)

    for special_day in [9, 19, 29]:

        day_df = df[
            df["日付"].dt.day == special_day
        ].copy()

        if day_df.empty:
            continue

        print()
        print(f"========== {special_day}日 ==========")

        # ----------------------------------------------------
        # 完全データ
        # ----------------------------------------------------

        full = day_df[
            day_df["データ種別"] == "完全データ"
        ].copy()

        if not full.empty:

            # 結果強度を基本順位にする
            full = full.sort_values(
                "結果強度",
                ascending=False,
                na_position="last"
            )

            print()
            print("【完全データ】")

            print(
                full[
                    [
                        "日付",
                        "島",
                        "△以上率",
                        "◎率",
                        "平均G数",
                        "平均合成確率",
                        "全台系スコア",
                        "結果強度",
                        "判定",
                    ]
                ].to_string(index=False)
            )

        # ----------------------------------------------------
        # 手動記録
        # ----------------------------------------------------

        manual = day_df[
            day_df["データ種別"] == "手動記録"
        ].copy()

        if not manual.empty:

            manual = manual.sort_values(
                "△以上台数",
                ascending=False,
                na_position="last"
            )

            print()
            print("【手動記録】")

            print(
                manual[
                    [
                        "日付",
                        "島",
                        "△以上台数",
                        "◎台数",
                        "○台数",
                        "△台数",
                    ]
                ].to_string(index=False)
            )


# ============================================================
# 次回分析用候補
# ============================================================

def show_rotation_candidates(df):

    print()
    print("=" * 70)
    print("ローテーション候補")
    print("=" * 70)

    print()
    print(
        "※ここではまだPrediction Engineのスコアには"
        "組み込みません。"
    )

    print()

    summary = create_machine_summary(df)

    if summary.empty:
        return

    # 強い全台系実績
    summary["強い実績"] = (
        summary["完全データ_強い全台系"]
    )

    # 全台系候補実績
    summary["候補実績"] = (
        summary["完全データ_全台系候補"]
    )

    # 単純な確認用スコア
    #
    # まだ正式なPrediction Scoreではない。
    #
    summary["確認用スコア"] = (
        summary["強い実績"] * 10
        + summary["候補実績"] * 3
        + summary["手動記録回数"] * 1
    )

    summary = summary.sort_values(
        "確認用スコア",
        ascending=False
    )

    print(
        summary[
            [
                "機種",
                "強い実績",
                "候補実績",
                "手動記録回数",
                "9日出現回数",
                "19日出現回数",
                "29日出現回数",
                "確認用スコア",
            ]
        ].to_string(index=False)
    )


# ============================================================
# メイン
# ============================================================

def main():

    df = load_data()

    if df.empty:
        return

    show_basic(df)

    show_date_results(df)

    summary = show_machine_summary(df)

    show_special_day_machine_ranking(df)

    show_rotation_candidates(df)

    print()
    print("=" * 70)
    print("分析終了")
    print("=" * 70)


if __name__ == "__main__":
    main()