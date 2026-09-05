import sqlite3
from pathlib import Path
import pandas as pd


# ==============================
# パス設定
# ==============================

BASE_DIR = Path(__file__).resolve().parent.parent

DB_PATH = (
    BASE_DIR
    / "database"
    / "juggler.db"
)



# ==============================
# 総合分析作成
# ==============================

def create_analysis_summary():

    conn = sqlite3.connect(
        DB_PATH
    )


    # ------------------------------
    # 最新営業日
    # ------------------------------

    latest_date = pd.read_sql(
        """
        SELECT
            MAX(日付) AS 日付
        FROM daily_data
        """,
        conn
    ).iloc[0]["日付"]


    print(
        "分析日:",
        latest_date
    )


    # ------------------------------
    # 全体集計
    # ------------------------------

    daily = pd.read_sql(
        """
        SELECT *
        FROM daily_data
        WHERE 日付 = ?
        """,
        conn,
        params=[
            latest_date
        ]
    )


    if daily.empty:

        print(
            "分析対象なし"
        )

        conn.close()

        return



    total_count = len(daily)


    high_count = (
        daily["評価"]
        .eq("◎")
        .sum()
    )


    middle_count = (
        daily["評価"]
        .eq("○")
        .sum()
    )


    avg_game = round(
        daily["G数"]
        .mean(),
        1
    )


    avg_rate = round(
        daily["合成確率"]
        .dropna()
        .mean(),
        1
    )



    # ------------------------------
    # 強い島
    # ------------------------------

    island = pd.read_sql(
        """
        SELECT
            島,
            評価スコア
        FROM island_analysis
        WHERE 日付 = ?
        ORDER BY
            評価スコア DESC
        LIMIT 1
        """,
        conn,
        params=[
            latest_date
        ]
    )


    if not island.empty:

        best_island = island.iloc[0]["島"]

        best_score = island.iloc[0]["評価スコア"]

    else:

        best_island = ""

        best_score = 0



    # ------------------------------
    # 強化機種
    # ------------------------------

    machine = pd.read_sql(
        """
        SELECT
            機種,
            COUNT(*) AS 台数
        FROM machine_analysis
        WHERE 日付 = ?
        AND 評価 IN ('◎','○')
        GROUP BY 機種
        ORDER BY 台数 DESC
        LIMIT 1
        """,
        conn,
        params=[
            latest_date
        ]
    )


    if not machine.empty:

        strong_machine = machine.iloc[0]["機種"]

    else:

        strong_machine = ""



    # ------------------------------
    # コメント生成用
    # ------------------------------

    comment = (
        f"{best_island}が最高スコア。"
        f"{strong_machine}を中心に高評価台を確認。"
    )



    # ------------------------------
    # 登録
    # ------------------------------

    cursor = conn.cursor()


    cursor.execute(
        """
        INSERT OR REPLACE INTO analysis_summary
        (
            日付,
            総台数,
            ◎台数,
            ○台数,
            平均G数,
            平均合成確率,
            最高評価島,
            最高島スコア,
            強化機種,
            コメント
        )
        VALUES
        (?,?,?,?,?,?,?,?,?,?)
        """,
        (
            latest_date,
            total_count,
            int(high_count),
            int(middle_count),
            avg_game,
            avg_rate,
            best_island,
            best_score,
            strong_machine,
            comment
        )
    )


    conn.commit()

    conn.close()


    print(
        "analysis_summary登録完了"
    )



# ==============================
# 実行
# ==============================

if __name__ == "__main__":

    create_analysis_summary()