from pathlib import Path
import csv
from datetime import datetime


def save_csv(data):

    # プロジェクト直下
    project_root = (
        Path(__file__)
        .resolve()
        .parent
        .parent
    )


    # 日付取得
    today = datetime.now().strftime(
        "%Y%m%d"
    )


    filename = (
        f"ps_cube_{today}.csv"
    )


    filepath = (
        project_root
        / "data"
        / filename
    )


    # dataフォルダ作成
    filepath.parent.mkdir(
        parents=True,
        exist_ok=True
    )


    with open(
        filepath,
        "w",
        newline="",
        encoding="utf-8-sig"
    ) as f:

        writer = csv.DictWriter(
            f,
            fieldnames=data[0].keys()
        )

        writer.writeheader()

        writer.writerows(data)


    print(
        "CSV保存完了"
    )

    print(filepath)