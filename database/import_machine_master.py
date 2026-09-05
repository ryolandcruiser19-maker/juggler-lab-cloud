import sqlite3
import csv
from pathlib import Path


# ==============================
# パス設定
# ==============================

BASE_DIR = Path(__file__).resolve().parent

DB_FILE = BASE_DIR / "juggler.db"

CSV_FILE = BASE_DIR / "machine_master.csv"


# ==============================
# machine master 登録
# ==============================

def import_machine_master():

    print("machine master 登録開始")


    # DB接続
    conn = sqlite3.connect(DB_FILE)

    cursor = conn.cursor()


    # ==============================
    # machines テーブル再作成
    # ==============================

    cursor.execute(
        """
        DROP TABLE IF EXISTS machines
        """
    )


    cursor.execute(
        """
        CREATE TABLE machines (

            id INTEGER PRIMARY KEY AUTOINCREMENT,

            store TEXT NOT NULL,

            island TEXT,

            machine TEXT,

            number INTEGER UNIQUE

        )
        """
    )


    # ==============================
    # CSV読み込み
    # ==============================

    count = 0


    with open(
        CSV_FILE,
        "r",
        encoding="utf-8-sig"
    ) as f:


        reader = csv.reader(f)


        for row in reader:


            # 空行除外
            if not row:
                continue


            # 列数チェック
            if len(row) != 4:

                continue


            # ヘッダー除外
            if row[0] in (
                "store",
                "店舗"
            ):

                continue


            try:

                number = int(row[3])


            except ValueError:

                print(
                    f"台番号変換エラー スキップ: {row}"
                )

                continue


            store = row[0]

            island = row[1]

            machine = row[2]


            # ==============================
            # 登録
            # ==============================

            cursor.execute(
                """
                INSERT INTO machines
                (
                    store,
                    island,
                    machine,
                    number
                )

                VALUES
                (
                    ?,
                    ?,
                    ?,
                    ?
                )
                """,

                (
                    store,
                    island,
                    machine,
                    number
                )

            )


            count += 1



    conn.commit()

    conn.close()



    print("machine master 登録完了")

    print(f"登録台数: {count}台")



# ==============================
# 実行
# ==============================

if __name__ == "__main__":

    import_machine_master()