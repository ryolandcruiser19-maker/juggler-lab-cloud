import sqlite3

from pathlib import Path



# ==============================
# パス設定
# ==============================

BASE_DIR = Path(__file__).resolve().parent.parent

DB_PATH = (
    BASE_DIR
    /
    "database"
    /
    "juggler.db"
)



# ==============================
# カラム存在確認
# ==============================

def column_exists(
    cursor,
    table_name,
    column_name
):

    cursor.execute(
        f"PRAGMA table_info({table_name})"
    )

    columns = [
        row[1]
        for row in cursor.fetchall()
    ]

    return column_name in columns




# ==============================
# カラム追加
# ==============================

def add_column(
    cursor,
    table,
    column,
    column_type
):

    if not column_exists(
        cursor,
        table,
        column
    ):

        print(
            f"追加: {table}.{column}"
        )


        cursor.execute(
            f"""
            ALTER TABLE {table}
            ADD COLUMN {column} {column_type}
            """
        )

    else:

        print(
            f"確認済: {table}.{column}"
        )




# ==============================
# Phase2 Migration
# ==============================

def migrate_phase2():


    print(
        "Phase2 DB移行開始"
    )


    print(
        "DB:",
        DB_PATH
    )



    conn = sqlite3.connect(
        DB_PATH
    )

    cursor = conn.cursor()



    # =====================================
    # raw_data
    # =====================================

    cursor.execute(
        """
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

            作成日時 TEXT

        )
        """
    )


    print(
        "raw_data確認完了"
    )



    add_column(
        cursor,
        "raw_data",
        "営業日",
        "TEXT"
    )


    add_column(
        cursor,
        "raw_data",
        "取得種別",
        "TEXT"
    )


    add_column(
        cursor,
        "raw_data",
        "取得回数",
        "INTEGER"
    )




    # =====================================
    # daily_job_status
    # =====================================

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS daily_job_status (

            id INTEGER PRIMARY KEY AUTOINCREMENT,

            job_id TEXT,

            実行日時 TEXT,

            処理 TEXT,

            状態 TEXT,

            件数 INTEGER,

            エラー内容 TEXT

        )
        """
    )


    print(
        "daily_job_status確認完了"
    )



    add_column(
        cursor,
        "daily_job_status",
        "job_id",
        "TEXT"
    )


    add_column(
        cursor,
        "daily_job_status",
        "終了日時",
        "TEXT"
    )


    add_column(
        cursor,
        "daily_job_status",
        "取得種別",
        "TEXT"
    )


    add_column(
        cursor,
        "daily_job_status",
        "リトライ回数",
        "INTEGER"
    )


    add_column(
        cursor,
        "daily_job_status",
        "処理時間秒",
        "REAL"
    )

    # =====================================
    # weekday_analysis
    # =====================================

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS weekday_analysis (

            曜日 TEXT PRIMARY KEY,

            総台数 INTEGER,

            高評価台数 INTEGER,

            高評価率 REAL,

            平均BB REAL,

            平均RB REAL,

            平均G数 REAL,

            平均合成確率 REAL,

            前日平均との差 REAL,

            傾向有効 INTEGER,

            傾向強度 REAL,

            最終更新日 TEXT

        )
        """
    )


    print(
        "weekday_analysis確認完了"
    )


    # =====================================
    # machine_tail_analysis
    # =====================================

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS machine_tail_analysis (

            台末尾 INTEGER PRIMARY KEY,

            台数 INTEGER,

            高評価数 INTEGER,

            高評価率 REAL,

            平均BB REAL,

            平均RB REAL,

            平均G数 REAL,

            平均合成確率 REAL,

            全体平均との差 REAL,

            傾向有効 INTEGER,

            傾向強度 REAL,

            最終更新日 TEXT

        )
        """
    )


    print(
        "machine_tail_analysis確認完了"
    )


    # =====================================
    # island_all_setting_analysis
    # =====================================

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS island_all_setting_analysis (

            日付 TEXT,

            島 TEXT,

            対象台数 INTEGER,

            △以上台数 INTEGER,

            △以上率 REAL,

            ◎台数 INTEGER,

            ○台数 INTEGER,

            △台数 INTEGER,

            平均G数 REAL,

            平均合成確率 REAL,

            信頼度高台数 INTEGER,

            通常期待台数 REAL,

            全台系差分台数 REAL,

            全台系スコア REAL,

            判定 TEXT,

            最終更新日 TEXT,

            PRIMARY KEY(
                日付,
                島
            )

        )
        """
    )


    print(
        "island_all_setting_analysis確認完了"
    )

    add_column(
        cursor,
        "island_all_setting_analysis",
        "通常期待台数",
        "REAL"
    )


    add_column(
        cursor,
        "island_all_setting_analysis",
        "全台系差分台数",
        "REAL"
    )


    # =====================================
    # INDEX
    # =====================================


    cursor.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_daily_date
        ON daily_data(日付)
        """
    )



    cursor.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_machine_history
        ON daily_data(
            店舗,
            台番号,
            日付
        )
        """
    )



    cursor.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_raw_history
        ON raw_data(
            店舗,
            台番号,
            取得日時
        )
        """
    )



    cursor.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_raw_business
        ON raw_data(
            営業日,
            台番号,
            取得日時
        )
        """
    )



    cursor.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_job_status
        ON daily_job_status(
            job_id,
            状態
        )
        """
    )



    print(
        "Index確認完了"
    )



    conn.commit()

    conn.close()



    print("------------------------------")
    print(
        "Phase2 DB移行完了"
    )
    print("------------------------------")




# ==============================
# 実行
# ==============================

if __name__ == "__main__":

    migrate_phase2()