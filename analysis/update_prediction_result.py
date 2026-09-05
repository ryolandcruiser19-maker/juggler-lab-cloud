import sqlite3
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent.parent

DB_PATH = (
    BASE_DIR
    / "database"
    / "juggler.db"
)



def update_prediction_result():

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row

    cursor = conn.cursor()



    # 未評価の予想を取得

    rows = cursor.execute(
        """
        SELECT

            日付,
            台番号,
            順位

        FROM prediction_history

        WHERE 実績評価 IS NULL

        """
    ).fetchall()



    print(
        "評価対象:",
        len(rows),
        "件"
    )



    update_count = 0



    for row in rows:


        predict_date = row["日付"]

        machine_no = row["台番号"]



        # 翌日データ取得

        result = cursor.execute(
            """
            SELECT

                評価

            FROM daily_data

            WHERE

                台番号 = ?

            AND

                date(日付)=date(?,'+1 day')

            """,
            (
                machine_no,
                predict_date
            )

        ).fetchone()



        if result is None:

            continue



        actual = result["評価"]



        # 判定

        if actual in ("◎","○"):

            judge = "的中"

        elif actual == "△":

            judge = "惜しい"

        else:

            judge = "ハズレ"



        cursor.execute(
            """
            UPDATE prediction_history

            SET

                実績評価 = ?

            WHERE

                日付 = ?

            AND

                台番号 = ?

            """,
            (
                f"{judge}:{actual}",
                predict_date,
                machine_no
            )
        )


        update_count += 1



    conn.commit()

    conn.close()



    print(
        "予想結果更新完了"
    )

    print(
        update_count,
        "件更新"
    )



if __name__ == "__main__":

    update_prediction_result()