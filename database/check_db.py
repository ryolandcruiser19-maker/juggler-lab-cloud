import sqlite3
import pandas as pd
from pathlib import Path


# ==============================
# パス設定
# ==============================

BASE_DIR = Path(__file__).resolve().parent

DB_PATH = BASE_DIR / "juggler.db"



# ==============================
# DB接続
# ==============================

def get_connection():

    return sqlite3.connect(DB_PATH)



# ==============================
# 総登録件数
# ==============================

def check_count():

    conn = get_connection()

    df = pd.read_sql(
        """
        SELECT COUNT(*) AS 件数
        FROM daily_data
        """,
        conn
    )

    conn.close()

    print("\n【総登録件数】")
    print(df)



# ==============================
# 日別登録状況
# ==============================

def check_dates():

    conn = get_connection()

    df = pd.read_sql(
        """
        SELECT
            日付,
            COUNT(*) AS 台数
        FROM daily_data
        GROUP BY 日付
        ORDER BY 日付
        """,
        conn
    )

    conn.close()

    print("\n【日別登録状況】")
    print(df.to_string(index=False))



# ==============================
# 最新データ
# ==============================

def check_latest():

    conn = get_connection()

    df = pd.read_sql(
        """
        SELECT
            日付,
            機種,
            台番号,
            BB,
            RB,
            G数,
            合成確率,
            評価,
            信頼度補正,
            島
        FROM daily_data
        ORDER BY 日付 DESC, 台番号
        LIMIT 10
        """,
        conn
    )

    conn.close()

    print("\n【最新10件】")
    print(df.to_string(index=False))



# ==============================
# 島別分析
# ==============================

def check_island():

    conn = get_connection()

    df = pd.read_sql(
        """
        SELECT
            島,
            COUNT(*) AS 台数,
            ROUND(AVG(G数),0) AS 平均G数,
            ROUND(AVG(合成確率),1) AS 平均合成,
            SUM(
                CASE
                    WHEN 評価='◎'
                    THEN 1
                    ELSE 0
                END
            ) AS ◎台数
        FROM daily_data
        WHERE 日付 = (
            SELECT MAX(日付)
            FROM daily_data
        )
        GROUP BY 島
        ORDER BY ◎台数 DESC
        """,
        conn
    )

    conn.close()


    print("\n【最新日 島別状況】")
    print(df.to_string(index=False))



# ==============================
# 最新日の高評価台
# ==============================

def check_good_machines():

    conn = get_connection()

    df = pd.read_sql(
        """
        SELECT
            台番号,
            機種,
            島,
            BB,
            RB,
            G数,
            合成確率,
            評価
        FROM daily_data
        WHERE 日付 = (
            SELECT MAX(日付)
            FROM daily_data
        )
        AND 評価 IN ('◎','○')
        ORDER BY 評価, 合成確率
        """,
        conn
    )


    conn.close()


    print("\n【最新日の高評価台】")
    print(df.to_string(index=False))



# ==============================
# 台番号履歴
# ==============================

def check_machine(machine_no):

    conn = get_connection()


    df = pd.read_sql(
        """
        SELECT
            日付,
            機種,
            台番号,
            BB,
            RB,
            G数,
            合成確率,
            評価,
            島
        FROM daily_data
        WHERE 台番号 = ?
        ORDER BY 日付
        """,
        conn,
        params=[machine_no]
    )


    conn.close()


    print(
        f"\n【台番号 {machine_no} 履歴】"
    )


    if len(df) == 0:

        print("データなし")

    else:

        print(
            df.to_string(index=False)
        )



# ==============================
# 実行
# ==============================

if __name__ == "__main__":


    check_count()

    check_dates()

    check_latest()

    check_island()

    check_good_machines()

    # 確認台
    check_machine(969)