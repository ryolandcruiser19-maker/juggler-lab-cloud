"""
ジャグラーラボ
Excel日次DB更新

juggler_lab_YYYYMMDD.csv
↓

02_JG_日次DB_ひまわりタワー_v15.xlsx
へ追記する
"""

from pathlib import Path
from datetime import datetime, timedelta
from shutil import copy2

import pandas as pd
from openpyxl import load_workbook


# ==================================================
# 営業日取得
# ==================================================

def get_pscube_date():

    now = datetime.now()

    if now.hour < 9:
        target = now - timedelta(days=1)
    else:
        target = now

    return target.strftime("%Y-%m-%d")


TARGET_DATE = get_pscube_date()

DATE_TEXT = TARGET_DATE.replace("-", "")


# ==================================================
# パス設定
# ==================================================

BASE_DIR = Path(__file__).resolve().parent.parent

DATA_DIR = BASE_DIR / "data"

BACKUP_DIR = BASE_DIR / "backup"

BACKUP_DIR.mkdir(exist_ok=True)


MASTER_DB = Path(
    r"C:\ジャグラー\01_マスターファイル\02_JG_日次DB_TEST.xlsx"
)

INPUT_FILE = (
    DATA_DIR
    /
    f"juggler_lab_{DATE_TEXT}.csv"
)


EXPECTED_MACHINE_COUNT = 218


# ==================================================
# バックアップ
# ==================================================

def backup_database():

    backup_name = (

        "02_JG_日次DB_ひまわりタワー_"

        f"{datetime.now():%Y%m%d_%H%M%S}.xlsx"

    )

    backup_path = BACKUP_DIR / backup_name

    copy2(
        MASTER_DB,
        backup_path
    )

    print()

    print("バックアップ作成")

    print(backup_path)

    return backup_path


# ==================================================
# Excel読込
# ==================================================

def load_workbook_file():

    wb = load_workbook(MASTER_DB)

    ws = wb.active

    return wb, ws


# ==================================================
# 最終データ行取得
# ==================================================

def get_last_data_row(ws):

    row = ws.max_row

    while row >= 4:

        if ws.cell(row=row, column=1).value is not None:

            return row

        row -= 1

    return 3


# ==================================================
# 既存キー取得
# ==================================================

def load_existing_keys(ws):

    existing_keys = set()

    existing_count = 0

    for row in ws.iter_rows(
        min_row=4,
        values_only=True
    ):

        if row[0] is None:
            continue

        existing_count += 1

        key = (

            str(row[0]),

            str(row[1]),

            str(row[2]),

            str(row[3]).zfill(4)

        )

        existing_keys.add(key)

    return existing_keys, existing_count

# ==================================================
# レコード追加
# ==================================================

def append_records(ws, df, existing_keys):

    current_row = get_last_data_row(ws) + 1

    added = 0
    duplicated = 0

    for _, row in df.iterrows():

        key = (

            str(row["日付"]),
            str(row["店舗"]),
            str(row["機種"]),
            str(row["台番号"]).zfill(4)

        )

        if key in existing_keys:

            duplicated += 1
            continue

        values = [

            row["日付"],
            row["店舗"],
            row["機種"],
            str(row["台番号"]).zfill(4),
            row["BB"],
            row["RB"],
            row["G数"],
            row["合成確率"],
            row["評価"],
            row["信頼度補正"],
            row["イベント種別"],
            row["備考"],
            row["島"]

        ]

        for col, value in enumerate(values, start=1):

            ws.cell(
                row=current_row,
                column=col
            ).value = value

        existing_keys.add(key)

        current_row += 1

        added += 1

    return added, duplicated


# ==================================================
# CSV読込
# ==================================================

def load_csv():

    if not INPUT_FILE.exists():

        raise FileNotFoundError(
            f"CSVが見つかりません\n{INPUT_FILE}"
        )

    df = pd.read_csv(
        INPUT_FILE,
        dtype={
            "台番号": str
        }
    )

    return df


# ==================================================
# CSVチェック
# ==================================================

def check_csv(df):

    count = len(df)

    print("CSV件数 :", count)

    if count != EXPECTED_MACHINE_COUNT:

        raise Exception(

            f"取得件数異常\n"
            f"期待値:{EXPECTED_MACHINE_COUNT}\n"
            f"取得値:{count}"

        )


# ==================================================
# Excel存在確認
# ==================================================

def check_master():

    if not MASTER_DB.exists():

        raise FileNotFoundError(

            f"Excelが存在しません\n"
            f"{MASTER_DB}"

        )


# ==================================================
# 保存
# ==================================================

def save_database(wb):

    wb.save(MASTER_DB)

    print()

    print("Excel保存完了")

# ==================================================
# メイン処理
# ==================================================

def main():

    print("=" * 60)
    print("ジャグラーラボ 日次DB更新")
    print("=" * 60)
    print()

    print("営業日 :", TARGET_DATE)
    print()

    # ------------------------------
    # ファイル存在確認
    # ------------------------------

    check_master()

    # ------------------------------
    # CSV読込
    # ------------------------------

    df = load_csv()

    check_csv(df)

    print()

    # ------------------------------
    # バックアップ
    # ------------------------------

    backup_database()

    print()

    # ------------------------------
    # Excel読込
    # ------------------------------

    wb, ws = load_workbook_file()

    existing_keys, existing_count = load_existing_keys(ws)

    print(f"既存データ : {existing_count} 件")

    print()

    # ------------------------------
    # データ追加
    # ------------------------------

    added, duplicated = append_records(

        ws,
        df,
        existing_keys

    )

    print(f"追加件数 : {added}")

    print(f"重複件数 : {duplicated}")

    print()

    # ------------------------------
    # 保存
    # ------------------------------

    # ------------------------------
    # 整合性チェック
    # ------------------------------

    if added + duplicated != len(df):

        raise Exception(

            "CSV件数と処理件数が一致しません。\n"
            f"CSV : {len(df)}\n"
            f"追加 : {added}\n"
            f"重複 : {duplicated}"

        )

    save_database(wb)

    print()

    print("=" * 60)
    print("DB更新完了")
    print("=" * 60)

    print(f"営業日     : {TARGET_DATE}")
    print(f"CSV件数    : {len(df)}")
    print(f"追加件数   : {added}")
    print(f"重複件数   : {duplicated}")
    print(f"総データ数 : {existing_count + added}")

    print("=" * 60)

# ==================================================
# 実行
# ==================================================

if __name__ == "__main__":

    start = datetime.now()

    try:

        main()

        end = datetime.now()

        print()
        print("処理開始 :", start.strftime("%Y-%m-%d %H:%M:%S"))
        print("処理終了 :", end.strftime("%Y-%m-%d %H:%M:%S"))
        print(f"処理時間 : {end - start}")

    except Exception as e:

        print()
        print("=" * 60)
        print("エラーが発生しました")
        print("=" * 60)

        print(e)

        raise