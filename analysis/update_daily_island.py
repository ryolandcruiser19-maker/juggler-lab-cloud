import sqlite3
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent.parent

DB_PATH = (
    BASE_DIR
    /
    "database"
    /
    "juggler.db"
)


def update_daily_island():

    conn = sqlite3.connect(DB_PATH)

    cursor = conn.cursor()


    print("島情報補完開始")


    cursor.execute(
        """
        UPDATE daily_data

        SET 島 = (

            SELECT island

            FROM machines

            WHERE machines.number = daily_data.台番号

        )

        WHERE 島 IS NULL

        """
    )


    print(
        "更新件数:",
        cursor.rowcount
    )


    conn.commit()


    conn.close()


    print("完了")



if __name__ == "__main__":

    update_daily_island()