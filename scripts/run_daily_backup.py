"""
ジャグラーラボ
日次自動実行 Phase2

処理:

① Job開始登録
② Chrome確認
③ P's CUBEデータ取得
④ raw_data保存
⑤ 評価処理
⑥ daily_data登録
⑦ 島全台系分析
⑧ 台履歴分析
⑨ パターン分析
⑩ 島分析
⑪ 据置分析
⑫ 店舗分析
⑬ 並び分析
⑭ 並び履歴集計
⑮ 予測スコア作成
⑯ Job成功登録
⑰ ログ保存
"""

import os
import sys
import subprocess
import time

from datetime import datetime


# ==================================
# 基本設定
# ==================================

BASE_DIR = os.path.dirname(
    os.path.dirname(
        os.path.abspath(__file__)
    )
)


# ==================================
# Python import設定
# ==================================

sys.path.append(
    BASE_DIR
)


SCRIPT_DIR = os.path.join(
    BASE_DIR,
    "scripts"
)

PYTHON = "python"


# ==================================
# Job管理
# ==================================

from database.job_status import (
    start_job,
    success_job,
    failed_job
)


# ==================================
# ログ設定
# ==================================

LOG_DIR = os.path.join(
    BASE_DIR,
    "logs"
)

os.makedirs(
    LOG_DIR,
    exist_ok=True
)


LOG_FILE = os.path.join(
    LOG_DIR,
    f"daily_{datetime.now().strftime('%Y%m%d')}.log"
)


# ==================================
# Logger
# ==================================

class Logger:

    def __init__(
        self,
        filename
    ):

        self.terminal = sys.stdout

        self.log = open(
            filename,
            "a",
            encoding="utf-8"
        )


    def write(
        self,
        message
    ):

        self.terminal.write(
            message
        )

        self.log.write(
            message
        )

        self.log.flush()


    def flush(self):

        pass


# ==================================
# Chrome確認
# ==================================

def start_chrome():

    print("-" * 60)

    print(
        "① Chrome確認"
    )

    print("-" * 60)


    try:

        import requests


        response = requests.get(

            "http://localhost:9222/json/version",

            timeout=3

        )


        if response.status_code == 200:

            print(
                "Chromeは既に起動しています"
            )

            return


    except Exception:

        pass


    print(
        "Chromeを起動します"
    )


    chrome_path = (

        r"C:\Program Files\Google\Chrome\Application\chrome.exe"

    )


    user_data_dir = (

        r"C:\chrome_debug_profile"

    )


    subprocess.Popen([

        chrome_path,

        "--remote-debugging-port=9222",

        f"--user-data-dir={user_data_dir}"

    ])


    print(
        "Chrome起動待機"
    )


    time.sleep(5)


    print(
        "Chrome起動完了"
    )


# ==================================
# Script実行
# ==================================

def run_script(
    script_name,
    title
):

    print()
    print("-" * 60)
    print(title)
    print("-" * 60)

    start = time.perf_counter()


    # --------------------------
    # スクリプト配置フォルダ判定
    # --------------------------

    analysis_scripts = {

        "create_machine_history_analysis.py",

        "create_machine_pattern_analysis.py",

        "create_island_trend_analysis.py",

        "create_island_all_setting_analysis.py",

        "create_machine_holdover_analysis.py",

        "create_store_condition_analysis.py",

        "create_alignment_analysis.py",

        "create_alignment_history_analysis.py",

        "create_alignment_history_summary.py",

        "create_prediction_score.py",

    }


    if script_name in analysis_scripts:

        script_path = os.path.join(

            BASE_DIR,

            "analysis",

            script_name

        )

    else:

        script_path = os.path.join(

            SCRIPT_DIR,

            script_name

        )


    env = os.environ.copy()

    env["PYTHONIOENCODING"] = "utf-8"


    result = subprocess.run(

        [
            PYTHON,
            script_path
        ],

        capture_output=True,

        text=True,

        encoding="utf-8",

        errors="replace",

        env=env

    )


    print(result.stdout)


    if result.stderr:

        print(result.stderr)


    if result.returncode != 0:

        raise RuntimeError(

            f"{script_name} 実行失敗"

        )


    elapsed = (

        time.perf_counter()

        -

        start

    )


    print(
        f"{title} 完了"
    )

    print(
        f"処理時間: {elapsed:.1f}秒"
    )


    return elapsed


# ==================================
# メイン
# ==================================

def main():

    sys.stdout = Logger(
        LOG_FILE
    )


    start_all = time.perf_counter()


    print("=" * 60)

    print(
        "ジャグラーラボ 日次自動処理"
    )

    print("=" * 60)


    print(

        "開始:",

        datetime.now()

    )


    try:

        # --------------------------
        # Job開始
        # --------------------------

        job_id = start_job(

            "DAILY",

            "DAILY",

            0

        )


        print(

            "Job開始:",

            job_id

        )


        # --------------------------
        # Chrome
        # --------------------------

        start_chrome()


        # --------------------------
        # P's CUBE取得
        # --------------------------

        run_script(

            "get_all_slots_v3.py",

            "② 全台データ取得"

        )


        # --------------------------
        # raw_data保存
        # --------------------------

        run_script(

            "raw_import.py",

            "③ raw_data登録"

        )


        # --------------------------
        # 評価
        # --------------------------

        run_script(

            "evaluate_pscube.py",

            "④ 評価処理"

        )


        # --------------------------
        # daily_data登録
        # --------------------------

        run_script(

            "daily_import.py",

            "⑤ daily_data登録"

        )


        # --------------------------
        # 島全台系分析
        #
        # daily_data
        #      ↓
        # island_all_setting_analysis
        # --------------------------

        run_script(

            "create_island_all_setting_analysis.py",

            "⑥ 島全台系分析"

        )


        # --------------------------
        # 台履歴分析
        # --------------------------

        run_script(

            "create_machine_history_analysis.py",

            "⑦ 台履歴分析"

        )


        # --------------------------
        # パターン分析
        # --------------------------

        run_script(

            "create_machine_pattern_analysis.py",

            "⑧ パターン分析"

        )


        # --------------------------
        # 島分析
        # --------------------------

        run_script(

            "create_island_trend_analysis.py",

            "⑨ 島分析"

        )


        # --------------------------
        # 据置分析
        # --------------------------

        run_script(

            "create_machine_holdover_analysis.py",

            "⑩ 据置分析"

        )


        # --------------------------
        # 店舗分析
        # --------------------------

        run_script(

            "create_store_condition_analysis.py",

            "⑪ 店舗分析"

        )


        # --------------------------
        # 並び分析
        # --------------------------

        run_script(

            "create_alignment_analysis.py",

            "⑫ 並び分析"

        )


        # --------------------------
        # 並び履歴集計
        #
        # alignment_history
        #        ↓
        # alignment_history_analysis
        # --------------------------

        run_script(

            "create_alignment_history_analysis.py",

            "⑬ 並び実績作成"

        )


        run_script(

            "create_alignment_history_summary.py",

            "⑬ 並び履歴集計"

        )


        # --------------------------
        # 予測スコア作成
        # --------------------------

        run_script(

            "create_prediction_score.py",

            "⑭ 予測スコア作成"

        )


        # --------------------------
        # Job成功
        # --------------------------

        elapsed = (

            time.perf_counter()

            -

            start_all

        )


        success_job(

            "DAILY",

            0,

            elapsed

        )


        print()

        print(
            "正常終了"
        )


        print(

            f"総処理時間: {elapsed:.1f}秒"

        )


    except Exception as e:

        print()

        print(
            "エラー発生"
        )


        print(
            e
        )


        failed_job(

            "DAILY",

            e

        )


        raise


    finally:

        print()

        print(
            "ログ保存:"
        )

        print(
            LOG_FILE
        )


# ==================================
# 実行
# ==================================

if __name__ == "__main__":

    main()