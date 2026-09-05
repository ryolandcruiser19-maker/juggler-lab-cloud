import sqlite3
from pathlib import Path
import pandas as pd


BASE_DIR = Path(__file__).resolve().parent.parent

DB_PATH = (
    BASE_DIR
    / "database"
    / "juggler.db"
)



def create_machine_history_analysis():


    conn = sqlite3.connect(DB_PATH)



    print(
        "daily_data読み込み開始"
    )


    # =================================
    # daily_data取得
    # =================================

    df = pd.read_sql(
        """
        SELECT
            日付,
            台番号,
            機種,
            島,
            G数,
            合成確率,
            評価
        FROM daily_data
        """,
        conn
    )


    if df.empty:

        print(
            "daily_dataデータなし"
        )

        conn.close()

        return



    print(
        "総データ件数:",
        len(df)
    )


    print(
        "分析対象台数:",
        df["台番号"].nunique()
    )



    result = []



    # =================================
    # 台番号別集計
    # =================================

    for machine_no, group in df.groupby(
        "台番号"
    ):



        machine_name = (
            group["機種"]
            .iloc[-1]
        )


        island = (
            group["島"]
            .iloc[-1]
        )



        # 稼働日数

        days = int(
            len(group)
        )



        # 累計G数

        total_game = int(
            group["G数"]
            .fillna(0)
            .sum()
        )



        # 平均G数

        avg_game = float(
            round(
                group["G数"]
                .fillna(0)
                .mean(),
                1
            )
        )



        # 平均合成確率

        avg_rate = (
            group["合成確率"]
            .dropna()
            .mean()
        )


        if pd.notna(avg_rate):

            avg_rate = float(
                round(
                    avg_rate,
                    1
                )
            )

        else:

            avg_rate = None



        # ◎回数

        high_count = int(
            (
                group["評価"]
                ==
                "◎"
            )
            .sum()
        )



        # ○回数

        middle_count = int(
            (
                group["評価"]
                .isin(
                    [
                        "○",
                        "〇"
                    ]
                )
            )
            .sum()
        )



        # 高評価率

        if days > 0:

            high_rate = float(
                round(
                    (
                        (high_count + middle_count)
                        /
                        days
                        *
                        100
                    ),
                    1
                )
            )

        else:

            high_rate = 0.0



        # 最終日

        latest_date = (
            group["日付"]
            .max()
        )



        # 最終評価

        latest_eval = (
            group
            .sort_values(
                "日付"
            )
            ["評価"]
            .iloc[-1]
        )



        result.append(
            (
                int(machine_no),
                machine_name,
                island,
                days,
                total_game,
                avg_game,
                avg_rate,
                high_count,
                middle_count,
                high_rate,
                latest_date,
                latest_eval
            )
        )



    # =================================
    # 既存削除
    # =================================

    cursor = conn.cursor()


    cursor.execute(
        """
        DELETE FROM machine_history_analysis
        """
    )



    # =================================
    # 登録
    # =================================

    for row in result:


        cursor.execute(
            """
            INSERT INTO machine_history_analysis
            (
                台番号,
                機種,
                島,
                稼働日数,
                累計G数,
                平均G数,
                平均合成確率,
                ◎回数,
                ○回数,
                高評価率,
                最終日,
                最終評価
            )

            VALUES
            (
                ?,?,?,?,?,?,?,?,?,?,?,?
            )
            """,
            row
        )



    conn.commit()

    conn.close()



    print(
        "machine_history_analysis更新完了"
    )


    print(
        f"{len(result)}台登録"
    )



if __name__ == "__main__":

    create_machine_history_analysis()