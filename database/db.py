import sqlite3
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

    """
    SQLite接続を取得
    """

    conn = sqlite3.connect(
        DB_PATH
    )

    # カラム名アクセス対応
    conn.row_factory = sqlite3.Row

    return conn



# ==============================
# SQL実行
# ==============================

def execute_query(
    query,
    params=None
):

    """
    更新系SQL実行
    """

    conn = get_connection()

    cursor = conn.cursor()


    if params:

        cursor.execute(
            query,
            params
        )

    else:

        cursor.execute(
            query
        )


    conn.commit()

    conn.close()



# ==============================
# データ取得
# ==============================

def fetch_all(
    query,
    params=None
):

    """
    複数行取得
    """

    conn = get_connection()

    cursor = conn.cursor()


    if params:

        cursor.execute(
            query,
            params
        )

    else:

        cursor.execute(
            query
        )


    rows = cursor.fetchall()


    conn.close()


    return rows



# ==============================
# 1件取得
# ==============================

def fetch_one(
    query,
    params=None
):

    """
    1行取得
    """

    conn = get_connection()

    cursor = conn.cursor()


    if params:

        cursor.execute(
            query,
            params
        )

    else:

        cursor.execute(
            query
        )


    row = cursor.fetchone()


    conn.close()


    return row



# ==============================
# DB確認
# ==============================

if __name__ == "__main__":


    print(
        "DB:",
        DB_PATH
    )


    row = fetch_one(
        """
        SELECT
            COUNT(*) AS cnt
        FROM juggler_data
        """
    )


    print(
        "登録件数:",
        row["cnt"]
    )