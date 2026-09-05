import sqlite3
from pathlib import Path
import pandas as pd


BASE_DIR = Path(__file__).resolve().parent.parent

DB_PATH = (
    BASE_DIR
    / "database"
    / "juggler.db"
)



def create_machine_analysis():

    conn = sqlite3.connect(DB_PATH)


    # ==============================
    # 最新営業日取得
    # ==============================

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



    # ==============================
    # 最新日データ取得
    # ==============================

    df = pd.read_sql(
        """
        SELECT
            日付,
            台番号,
            機種,
            島,
            G数,
            合成確率,
            評価
        FROM daily_data
        WHERE 日付 = ?
        """,
        conn,
        params=[
            latest_date
        ]
    )



    if df.empty:

        print(
            "対象データなし"
        )

        conn.close()

        return



    # ==============================
    # 分析値作成
    # ==============================

    result = []


    for _, row in df.iterrows():


        evaluation = row["評価"]


        if evaluation == "◎":

            high = 1
            middle = 0
            score = 10.0


        elif evaluation == "○":

            high = 0
            middle = 1
            score = 5.0


        else:

            high = 0
            middle = 0
            score = 0.0



        result.append(
            (
                row["日付"],
                int(row["台番号"]),
                row["機種"],
                row["島"],
                int(row["G数"]),
                float(row["合成確率"])
                if pd.notna(row["合成確率"])
                else None,
                evaluation,
                high,
                middle,
                score
            )
        )



    # ==============================
    # 登録
    # ==============================

    cursor = conn.cursor()


    for row in result:


        cursor.execute(
            """
            INSERT OR REPLACE INTO machine_analysis
            (
                日付,
                台番号,
                機種,
                島,
                G数,
                合成確率,
                評価,
                ◎回数,
                ○回数,
                評価スコア
            )
            VALUES
            (
                ?,?,?,?,?,?,?,?,?,?
            )
            """,
            row
        )


    conn.commit()

    conn.close()


    print(
        "台分析登録完了"
    )

    print(
        f"{len(result)}台登録"
    )



if __name__ == "__main__":

    create_machine_analysis()