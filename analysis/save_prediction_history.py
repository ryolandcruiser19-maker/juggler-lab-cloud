import sqlite3
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent.parent

DB_PATH = (
    BASE_DIR
    / "database"
    / "juggler.db"
)



def save_prediction_history():

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row

    cursor = conn.cursor()



    # prediction_score最新日

    latest_date = cursor.execute(
        """
        SELECT MAX(日付)
        FROM prediction_score
        """
    ).fetchone()[0]



    print(
        "予想日:",
        latest_date
    )



    rows = cursor.execute(
        """
        SELECT

            日付,
            台番号,
            機種,
            島,
            総合スコア

        FROM prediction_score

        ORDER BY 総合スコア DESC

        LIMIT 10

        """
    ).fetchall()



    for rank,row in enumerate(rows,start=1):


        cursor.execute(
            """
            INSERT OR REPLACE INTO prediction_history
            (
                日付,
                台番号,
                機種,
                島,
                順位,
                総合スコア,
                採用フラグ,
                備考
            )

            VALUES
            (
                ?,
                ?,
                ?,
                ?,
                ?,
                ?,
                0,
                ?
            )

            """,

            (
                latest_date,
                row["台番号"],
                row["機種"],
                row["島"],
                rank,
                row["総合スコア"],
                "スコア上位候補"
            )

        )



    conn.commit()
    conn.close()


    print(
        "prediction_history登録完了"
    )

    print(
        len(rows),
        "台登録"
    )



if __name__ == "__main__":

    save_prediction_history()