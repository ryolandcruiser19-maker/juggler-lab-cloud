import pandas as pd

from db import (
    fetch_all,
    fetch_one
)



# ==============================
# 最新日取得
# ==============================

def get_latest_date():

    row = fetch_one(
        """
        SELECT
            MAX(日付) AS 最新日
        FROM daily_data
        """
    )

    return row["最新日"]



# ==============================
# 最新日データ取得
# ==============================

def get_latest_data():

    latest_date = get_latest_date()


    rows = fetch_all(
        """
        SELECT
            日付,
            店舗,
            機種,
            台番号,
            BB,
            RB,
            G数,
            合成確率,
            評価,
            信頼度補正,
            島
        FROM daily_data
        WHERE 日付 = ?
        ORDER BY 台番号
        """,
        [
            latest_date
        ]
    )


    return pd.DataFrame(
        rows,
        columns=[
            "日付",
            "店舗",
            "機種",
            "台番号",
            "BB",
            "RB",
            "G数",
            "合成確率",
            "評価",
            "信頼度補正",
            "島"
        ]
    )



# ==============================
# 台番号履歴取得
# ==============================

def get_machine_history(
    machine_no
):

    rows = fetch_all(
        """
        SELECT
            日付,
            機種,
            台番号,
            BB,
            RB,
            G数,
            合成確率,
            評価,
            島
        FROM daily_data
        WHERE 台番号 = ?
        ORDER BY 日付
        """,
        [
            machine_no
        ]
    )


    return pd.DataFrame(
        rows,
        columns=[
            "日付",
            "機種",
            "台番号",
            "BB",
            "RB",
            "G数",
            "合成確率",
            "評価",
            "島"
        ]
    )



# ==============================
# 島別データ取得
# ==============================

def get_island_data():

    latest_date = get_latest_date()


    rows = fetch_all(
        """
        SELECT
            島,
            台番号,
            機種,
            BB,
            RB,
            G数,
            合成確率,
            評価
        FROM daily_data
        WHERE 日付 = ?
        ORDER BY 島, 台番号
        """,
        [
            latest_date
        ]
    )


    return pd.DataFrame(
        rows,
        columns=[
            "島",
            "台番号",
            "機種",
            "BB",
            "RB",
            "G数",
            "合成確率",
            "評価"
        ]
    )



# ==============================
# 動作確認
# ==============================

if __name__ == "__main__":


    print(
        "最新日:",
        get_latest_date()
    )


    print("\n【最新データ】")

    print(
        get_latest_data()
        .head()
    )


    print("\n【969番台履歴】")

    print(
        get_machine_history(969)
    )


    print("\n【島データ】")

    print(
        get_island_data()
        .head()
    )