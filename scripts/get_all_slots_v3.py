"""
ジャグラーラボ
全台データ取得メイン処理
"""

import time

from config import MACHINES
from fetch_html import get_html
from parse_pscube import parse_html
from save_csv import save_csv



# ==============================
# リトライ設定
# ==============================

MAX_RETRY = 3

RETRY_WAIT_SECONDS = 30



def main():

    all_data = []


    for machine_name, url in MACHINES.items():

        print("=" * 50)
        print(f"{machine_name} 取得開始")


        machines = []


        # ==========================
        # 機種単位リトライ
        # ==========================

        for retry in range(1, MAX_RETRY + 1):


            html = get_html(url)


            machines = parse_html(
                html,
                machine_name
            )


            if len(machines) > 0:

                break



            print(
                f"{machine_name}: 0台取得"
            )


            if retry < MAX_RETRY:

                print(
                    f"{RETRY_WAIT_SECONDS}秒後に再取得 ({retry}/{MAX_RETRY})"
                )

                time.sleep(
                    RETRY_WAIT_SECONDS
                )


            else:

                print(
                    f"{machine_name}: リトライ失敗"
                )



        all_data.extend(
            machines
        )


    save_csv(
        all_data
    )


    print("=" * 50)
    print("全機種取得完了")



if __name__ == "__main__":

    main()