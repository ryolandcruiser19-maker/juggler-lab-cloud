import sqlite3
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent

DB_FILE = BASE_DIR / "juggler.db"


def main():

    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()


    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS machines
        (
            id INTEGER PRIMARY KEY AUTOINCREMENT,

            store TEXT NOT NULL,

            island TEXT,

            machine_name TEXT NOT NULL,

            machine_number INTEGER NOT NULL UNIQUE
        )
        """
    )


    conn.commit()
    conn.close()


    print("machinesテーブル作成完了")


if __name__ == "__main__":
    main()