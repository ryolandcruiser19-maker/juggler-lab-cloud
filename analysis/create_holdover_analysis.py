import sqlite3
from datetime import datetime


DB_PATH = "database/juggler.db"


def confidence_rate(count):

    if count >= 20:
        return 1.0

    if count >= 10:
        return 0.8

    if count >= 5:
        return 0.5

    return 0.2



def confidence(count):

    if count >= 20:
        return "高"

    if count >= 10:
        return "中"

    if count >= 5:
        return "低"

    return "不足"



def judge_holdover(count, score):

    if count < 5:
        return "データ不足"

    if score >= 30:
        return "据え置き候補"

    if score >= 15:
        return "弱い傾向"

    return "根拠薄"



def create_holdover_analysis():

    conn = sqlite3.connect(DB_PATH)

    conn.row_factory = sqlite3.Row

    cursor = conn.cursor()


    cursor.execute(
        "DELETE FROM machine_holdover_analysis"
    )


    query = """

    SELECT

        d1.台番号,
        d1.機種,
        d1.島,

        COUNT(*) AS 前日高評価回数,

        SUM(
            CASE
            WHEN d2.評価 IN ('◎','○')
            THEN 1
            ELSE 0
            END
        ) AS 翌日高評価回数

    FROM daily_data d1


    LEFT JOIN daily_data d2

    ON

        d1.台番号=d2.台番号

        AND date(d2.日付)
        =
        date(d1.日付,'+1 day')


    WHERE

        d1.評価 IN ('◎','○')


    GROUP BY

        d1.台番号,
        d1.機種,
        d1.島

    """



    rows = cursor.execute(query).fetchall()


    today=datetime.now().strftime("%Y-%m-%d")



    for r in rows:


        before=r["前日高評価回数"]

        after=r["翌日高評価回数"] or 0


        rate=0

        if before:

            rate=after/before*100



        score = rate * confidence_rate(before)



        cursor.execute(
        """

        INSERT INTO machine_holdover_analysis

        (

        台番号,
        機種,
        島,

        分析期間,

        前日高評価回数,
        翌日高評価回数,

        据え置き率,

        前日◎回数,
        翌日◎回数,

        更新日,

        有効データ数,

        信頼度,

        据え置き判定,

        稼働日数,

        据え置きスコア

        )


        VALUES

        (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)

        """,

        (

        r["台番号"],
        r["機種"],
        r["島"],

        180,

        before,
        after,

        round(rate,1),

        0,
        0,

        today,

        before,

        confidence(before),

        judge_holdover(
            before,
            score
        ),

        0,

        round(score,1)

        ))



    conn.commit()


    print("machine_holdover_analysis更新完了")

    print(f"{len(rows)}台登録")


    conn.close()



if __name__=="__main__":

    create_holdover_analysis()