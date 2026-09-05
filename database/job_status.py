"""
ジャグラーラボ
Job Status 管理

日次処理・リアルタイム処理の
実行状態管理

Phase2:
job_id単位管理版
"""


import sqlite3

from pathlib import Path
from datetime import datetime



# ==============================
# DB設定
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
# 接続
# ==============================

def get_connection():

    return sqlite3.connect(
        DB_PATH
    )



# ==============================
# Job開始
# ==============================

def start_job(
    process,
    job_type="DAILY",
    retry_count=0
):

    """
    ジョブ開始登録

    戻り値:
        job_id
    """


    conn = get_connection()

    cursor = conn.cursor()



    now = datetime.now()


    job_id = now.strftime(
        "%Y%m%d_%H%M%S_%f"
    )



    cursor.execute(
        """
        INSERT INTO daily_job_status
        (
            実行日時,
            処理,
            取得種別,
            状態,
            件数,
            リトライ回数
        )
        VALUES
        (
            ?,?,?,?,?,?
        )
        """,
        (
            now.strftime(
                "%Y-%m-%d %H:%M:%S"
            ),

            process,

            job_type,

            "RUNNING",

            0,

            retry_count
        )
    )



    conn.commit()

    conn.close()



    print(
        f"JOB START : {job_id}"
    )


    return job_id




# ==============================
# 成功更新
# ==============================

def success_job(
    job_id,
    count=0,
    elapsed=None
):

    """
    ジョブ成功更新
    """


    conn = get_connection()

    cursor = conn.cursor()



    cursor.execute(
        """
        UPDATE daily_job_status

        SET

            終了日時 = ?,

            状態 = ?,

            件数 = ?,

            処理時間秒 = ?

        WHERE

            id = ?

        """,
        (
            datetime.now().strftime(
                "%Y-%m-%d %H:%M:%S"
            ),

            "SUCCESS",

            count,

            elapsed,

            get_status_id(
                cursor,
                job_id
            )

        )
    )



    conn.commit()

    conn.close()




# ==============================
# 失敗更新
# ==============================

def failed_job(
    job_id,
    error
):

    """
    ジョブ失敗更新
    """


    conn = get_connection()

    cursor = conn.cursor()



    cursor.execute(
        """
        UPDATE daily_job_status

        SET

            終了日時 = ?,

            状態 = ?,

            エラー内容 = ?

        WHERE

            id = ?

        """,
        (
            datetime.now().strftime(
                "%Y-%m-%d %H:%M:%S"
            ),

            "FAILED",

            str(error),

            get_status_id(
                cursor,
                job_id
            )

        )
    )


    conn.commit()

    conn.close()




# ==============================
# job_id → DB id変換
# ==============================

def get_status_id(
    cursor,
    job_id
):

    """
    現在は日時ベース管理
    将来的にjob_id列追加予定
    """


    cursor.execute(
        """
        SELECT id
        FROM daily_job_status
        ORDER BY id DESC
        LIMIT 1
        """
    )


    row = cursor.fetchone()


    if row:

        return row[0]


    return None