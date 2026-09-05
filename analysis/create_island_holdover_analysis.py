import sqlite3
from datetime import datetime


DB_PATH = "database/juggler.db"



def confidence(count):

    if count >= 50:
        return "高"

    if count >= 20:
        return "中"

    if count >= 10:
        return "低"

    return "不足"



def create_island_holdover_analysis():


    conn = sqlite3.connect(DB_PATH)

    conn.row_factory = sqlite3.Row

    cursor = conn.cursor()


    cursor.execute(
        "DELETE FROM island_holdover_analysis"
    )


    query = """

    SELECT

        a.島,

        COUNT(*) AS 前日高評価日数,

        SUM(

            CASE

            WHEN b.島 IS NOT NULL

            THEN 1

            ELSE 0

            END

        ) AS 翌日島継続日数


    FROM

    (

        SELECT DISTINCT

            日付,

            島

        FROM daily_data

        WHERE 評価 IN ('◎','○')

    ) a


    LEFT JOIN

    (

        SELECT DISTINCT

            日付,

            島

        FROM daily_data

        WHERE 評価 IN ('◎','○')

    ) b


    ON

        a.島=b.島

        AND date(b.日付)

        =

        date(a.日付,'+1 day')


    GROUP BY

        a.島

    """



    rows=cursor.execute(query).fetchall()



    today=datetime.now().strftime("%Y-%m-%d")



    for r in rows:


        before=r["前日高評価日数"]

        after=r["翌日島継続日数"] or 0


        rate=0


        if before:

            rate=after/before*100



        if before>=50:

            score=rate

        elif before>=20:

            score=rate*0.8

        else:

            score=rate*0.5



        cursor.execute(
        """

        INSERT INTO island_holdover_analysis

        (

        島,

        分析期間,

        前日高評価台数,

        翌日高評価台数,

        据え置き率,

        信頼度,

        据え置きスコア,

        更新日

        )

        VALUES

        (?,?,?,?,?,?,?,?)

        """,

        (

        r["島"],

        180,

        before,

        after,

        round(rate,1),

        confidence(before),

        round(score,1),

        today

        ))



    conn.commit()

    conn.close()


    print("島据え置き分析更新完了")

    print(f"{len(rows)}島登録")



if __name__=="__main__":

    create_island_holdover_analysis()