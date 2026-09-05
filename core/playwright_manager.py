"""
ジャグラーラボ
Playwright Manager

ローカル：
Chrome Remote Debugging（CDP）接続

クラウド：
PlaywrightからChromiumを直接起動
"""

from playwright.sync_api import sync_playwright

import os
import time

from core.chrome_manager import ChromeManager


class PlaywrightManager:

    def __init__(
        self,
        debugger_url="http://127.0.0.1:9222",
        retry_count=3,
    ):

        self.debugger_url = debugger_url
        self.retry_count = retry_count

        # クラウド判定
        self.cloud_mode = os.getenv("CLOUD_MODE") == "1"

        # ローカル用ChromeManager
        self.chrome = None

        if not self.cloud_mode:
            self.chrome = ChromeManager()

        self.playwright = None
        self.browser = None
        self.context = None


    # ==================================
    # Playwright接続
    # ==================================

    def connect(self):

        last_error = None

        for attempt in range(
            1,
            self.retry_count + 1
        ):

            try:

                print(
                    f"接続試行 {attempt}/{self.retry_count}"
                )

                # --------------------------
                # Playwright起動
                # --------------------------

                if self.playwright is None:

                    print(
                        "Playwright起動"
                    )

                    self.playwright = (
                        sync_playwright()
                        .start()
                    )


                # ==================================
                # クラウド
                # ==================================

                if self.cloud_mode:

                    print(
                        "クラウドモード"
                    )

                    print(
                        "Chromium直接起動"
                    )

                    self.browser = (
                        self.playwright.chromium.launch(
                            headless=True
                        )
                    )

                    print(
                        "Chromium起動成功"
                    )

                    self.context = (
                        self.browser.new_context()
                    )

                    print(
                        "Browser Context作成成功"
                    )

                    return


                # ==================================
                # ローカル
                # ==================================

                else:

                    print(
                        "ローカルモード"
                    )

                    # --------------------------
                    # Chrome確認
                    # --------------------------

                    self.chrome.start()


                    # --------------------------
                    # CDP接続
                    # --------------------------

                    print(
                        "CDP接続開始"
                    )

                    self.browser = (

                        self.playwright.chromium
                        .connect_over_cdp(

                            self.debugger_url,

                            timeout=15000

                        )

                    )

                    print(
                        "CDP接続成功"
                    )


                    # --------------------------
                    # Context確認
                    # --------------------------

                    contexts = (
                        self.browser.contexts
                    )

                    if not contexts:

                        raise RuntimeError(
                            "Chrome Contextが存在しません"
                        )

                    self.context = contexts[0]

                    print(
                        "Browser Context取得成功"
                    )

                    return


            except Exception as e:

                last_error = e

                print(
                    "Playwright接続失敗"
                )

                print(
                    type(e).__name__
                )

                print(
                    e
                )


                # --------------------------
                # 後処理
                # --------------------------

                if self.browser:

                    try:

                        self.browser.close()

                    except Exception:

                        pass

                    self.browser = None

                self.context = None


                # --------------------------
                # リトライ
                # --------------------------

                if attempt < self.retry_count:

                    # ローカルのみChrome再起動
                    if not self.cloud_mode:

                        print(
                            "Chrome再起動"
                        )

                        self.chrome.restart()

                        print(
                            "Chrome安定待機 10秒"
                        )

                        time.sleep(10)

                    else:

                        print(
                            "Chromium再起動"
                        )

                        time.sleep(3)


        # ------------------------------
        # 最終失敗
        # ------------------------------

        if self.playwright:

            try:

                self.playwright.stop()

            except Exception:

                pass

        self.playwright = None

        raise RuntimeError(

            f"Playwright接続失敗: {last_error}"

        )


    # ==================================
    # Page作成
    # ==================================

    def new_page(self):

        if self.context is None:

            self.connect()

        page = (
            self.context.new_page()
        )

        return page


    # ==================================
    # Page終了
    # ==================================

    def close_page(
        self,
        page
    ):

        if page:

            try:

                page.close()

            except Exception:

                pass


    # ==================================
    # 終了
    # ==================================

    def close(self):

        if self.browser:

            try:

                self.browser.close()

            except Exception:

                pass

        if self.playwright:

            try:

                self.playwright.stop()

            except Exception:

                pass

        self.playwright = None
        self.browser = None
        self.context = None
