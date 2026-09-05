import sqlite3
import pandas as pd


# ==========================
# 設定
# ==========================

EXCEL_PATH = r"C:\ジャグラー\01_マスターファイル\02_JG_日次DB_ひまわりタワー_v15.xlsx"

DB_PATH = "database/juggler.db"

SHEET_NAME = "日次データ入力"


# ==========================
# Excel読み込み
# ==========================

def load_excel():

    print("Excel読み込み開始")


    df = pd.read_excel(
        EXCEL_PATH,
        sheet_name=SHEET_NAME,
        header=None
    )


    print("元データ行数:", len(df))


    # --------------------------------
    # Excel構造
    #
    # 0行目 : タイトル
    # 1行目 : 補足
    # 2行目 : ヘッダー
    # 3行目以降 : データ
    # --------------------------------

    df = df.iloc[3:].copy()


    df.columns = [
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
        "イベント種別",
        "備考",
        "島"
    ]


    # 日付が文字列「日付」の行などを除外

    df = df[
        df["日付"] != "日付"
    ]


    # 空行削除

    df = df.dropna(
        subset=[
            "日付",
            "台番号"
        ]
    )


    # 日付変換

    df["日付"] = pd.to_datetime(
        df["日付"],
        errors="coerce"
    )


    # 変換できなかった行削除

    df = df.dropna(
        subset=[
            "日付"
        ]
    )


    df["日付"] = (
        df["日付"]
        .dt.strftime("%Y-%m-%d")
    )


    # 台番号整数化

    df["台番号"] = (
        df["台番号"]
        .astype(int)
    )


    print(
        "読み込み件数:",
        len(df)
    )


    print(df.head())


    return df


# ==========================
# SQLite投入
# ==========================

def import_database(df):

    print("SQLite登録開始")


    conn = sqlite3.connect(DB_PATH)

    cursor = conn.cursor()


    # 既存daily_data削除

    print(
        "daily_data削除"
    )

    cursor.execute(
        "DELETE FROM daily_data"
    )


    sql = """

    INSERT INTO daily_data
    (
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
        イベント種別,
        備考,
        島
    )

    VALUES
    (
        ?,
        ?,
        ?,
        ?,
        ?,
        ?,
        ?,
        ?,
        ?,
        ?,
        ?,
        ?,
        ?
    )

    """


    records = []


    for _, row in df.iterrows():

        records.append(
            (
                row["日付"],
                row["店舗"],
                row["機種"],
                row["台番号"],
                row["BB"],
                row["RB"],
                row["G数"],
                row["合成確率"],
                row["評価"],
                row["信頼度補正"],
                row["イベント種別"],
                row["備考"],
                row["島"]
            )
        )


    cursor.executemany(
        sql,
        records
    )


    conn.commit()


    count = cursor.execute(
        "SELECT COUNT(*) FROM daily_data"
    ).fetchone()[0]


    print(
        "daily_data登録完了:",
        count,
        "件"
    )


    conn.close()



# ==========================
# 確認
# ==========================

def check_database():

    conn = sqlite3.connect(DB_PATH)


    count = conn.execute(
        "SELECT COUNT(*) FROM daily_data"
    ).fetchone()[0]


    date_range = conn.execute(
        """
        SELECT
            MIN(日付),
            MAX(日付)
        FROM daily_data
        """
    ).fetchone()


    print("--------------------")
    print("確認結果")
    print("件数:", count)
    print("期間:", date_range)
    print("--------------------")


    conn.close()



# ==========================
# メイン
# ==========================

if __name__ == "__main__":


    df = load_excel()


    import_database(
        df
    )


    check_database()


    print(
        "処理完了"
    )