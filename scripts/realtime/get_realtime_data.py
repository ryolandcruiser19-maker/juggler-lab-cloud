"""
ジャグラーラボ
リアルタイムデータ取得

営業中のP's CUBEデータを取得し、
DataFrameとして返す。
"""

import sys
import os

import pandas as pd

# scriptsフォルダをimport対象に追加
SCRIPT_DIR = os.path.dirname(
    os.path.dirname(
        os.path.abspath(__file__)
    )
)

if SCRIPT_DIR not in sys.path:
    sys.path.append(SCRIPT_DIR)

from config import MACHINES
from fetch_html import get_html
from parse_pscube import parse_html


def get_realtime_data():
    """
    P's CUBEから現在の全台データを取得する。
    """

    all_data = []

    for machine_name, url in MACHINES.items():

        html = get_html(url)

        machines = parse_html(
            html,
            machine_name
        )

        all_data.extend(
            machines
        )

    if not all_data:
        return pd.DataFrame()

    df = pd.DataFrame(
        all_data
    )

    return df


if __name__ == "__main__":

    print("リアルタイムデータ取得開始")

    df = get_realtime_data()

    print(
        f"取得台数: {len(df)}"
    )

    print()

    if not df.empty:

        print(
            df.head(10).to_string(
                index=False
            )
        )

    print()

    print("リアルタイムデータ取得完了")