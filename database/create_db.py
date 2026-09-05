import sqlite3
from pathlib import Path


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
# DB作成
# ==============================

def create_tables():

    conn = sqlite3.connect(DB_PATH)

    cursor = conn.cursor()


    # ------------------------------
    # raw_data
    # ------------------------------

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS raw_data (

        id INTEGER PRIMARY KEY AUTOINCREMENT,

        取得日時 TEXT,

        日付 TEXT,

        店舗 TEXT,

        機種 TEXT,

        台番号 INTEGER,

        BB INTEGER,

        RB INTEGER,

        G数 INTEGER,

        合成確率 REAL,

        最終ゲーム INTEGER,

        BIG過去最高 INTEGER,

        作成日時 TEXT,

        UNIQUE(
            取得日時,
            店舗,
            台番号
        )

    )
    """)



    # ------------------------------
    # daily_data
    # ------------------------------

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS daily_data (

        id INTEGER PRIMARY KEY AUTOINCREMENT,

        日付 TEXT,

        店舗 TEXT,

        機種 TEXT,

        台番号 INTEGER,

        BB INTEGER,

        RB INTEGER,

        G数 INTEGER,

        合成確率 REAL,

        評価 TEXT,

        信頼度補正 TEXT,

        イベント種別 TEXT,

        備考 TEXT,

        島 TEXT,


        UNIQUE(
            日付,
            店舗,
            台番号
        )

    )
    """)



    # ------------------------------
    # daily_job_status
    # ------------------------------

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS daily_job_status (

        id INTEGER PRIMARY KEY AUTOINCREMENT,

        実行日時 TEXT,

        処理 TEXT,

        状態 TEXT,

        件数 INTEGER,

        エラー内容 TEXT

    )
    """)



    # ------------------------------
    # Index
    # ------------------------------

    cursor.execute("""
    CREATE INDEX IF NOT EXISTS idx_daily_date
    ON daily_data(日付)
    """)



    cursor.execute("""
    CREATE INDEX IF NOT EXISTS idx_machine_history
    ON daily_data(
        店舗,
        台番号,
        日付
    )
    """)



    cursor.execute("""
    CREATE INDEX IF NOT EXISTS idx_raw_history
    ON raw_data(
        店舗,
        台番号,
        取得日時
    )
    """)



    conn.commit()

    conn.close()



    print(
        "Phase2 DB構築完了"
    )



# ==============================
# 実行
# ==============================

if __name__ == "__main__":

    create_tables()