import sqlite3
from pathlib import Path
import pandas as pd


# ==============================
# DB設定
# ==============================

BASE_DIR = Path(__file__).resolve().parent.parent

DB_PATH = Path("/app/data/juggler.db") if __import__("os").getenv("CLOUD_MODE") == "1" else BASE_DIR / "database" / "juggler.db"


# ==============================
# 島傾向分析
# ==============================

def create_island_trend_analysis():

    conn = sqlite3.connect(DB_PATH)

    print("=" * 60)
    print("島傾向分析開始")
    print("=" * 60)

    print("DB:")
    print(DB_PATH)

    # ==============================
    # 全履歴取得
    # ==============================

    df = pd.read_sql(
        """
        SELECT
            日付,
            島,
            G数,
            評価
        FROM daily_data
        WHERE 島 IS NOT NULL
        """,
        conn
    )

    if df.empty:

        print("分析対象データなし")

        conn.close()

        return

    print(
        "分析対象件数:",
        len(df)
    )

    # ==============================
    # 島別集計
    # ==============================

    result = []

    for island, group in df.groupby("島"):

        total_days = (
            group["日付"]
            .nunique()
        )

        total_machines = len(group)

        avg_game = (
            group["G数"]
            .mean()
        )

        high_count = (
            group["評価"]
            .eq("◎")
            .sum()
        )

        middle_count = (
            group["評価"]
            .eq("○")
            .sum()
        )

        total_count = len(group)

        if total_count > 0:

            high_rate = (
                high_count
                / total_count
                * 100
            )

        else:

            high_rate = 0

        score = (
            high_count * 10
            +
            middle_count * 5
        )

        average_score = (
            score / total_days
            if total_days > 0
            else 0
        )

        result.append(
            (
                island,
                int(total_days),
                int(total_machines),
                round(avg_game, 1),
                int(high_count),
                int(middle_count),
                round(high_rate, 2),
                round(average_score, 2),
                str(df["日付"].max())
            )
        )

    # ==============================
    # 既存データを全削除
    # ==============================

    print(
        "既存 island_trend_analysis を削除"
    )

    cursor = conn.cursor()

    cursor.execute(
        """
        DELETE FROM island_trend_analysis
        """
    )

    deleted_count = cursor.rowcount

    print(
        "削除件数:",
        deleted_count
    )

    # ==============================
    # 登録
    # ==============================

    for row in result:

        cursor.execute(
            """
            INSERT INTO island_trend_analysis
            (
                島,
                総日数,
                総台数,
                平均G数,
                ◎台数,
                ○台数,
                ◎率,
                平均評価スコア,
                更新日
            )
            VALUES
            (?,?,?,?,?,?,?,?,?)
            """,
            row
        )

    conn.commit()

    conn.close()

    print(
        "島傾向分析登録完了"
    )

    print(
        f"{len(result)}島登録"
    )


# ==============================
# 実行
# ==============================

if __name__ == "__main__":

    create_island_trend_analysis()
