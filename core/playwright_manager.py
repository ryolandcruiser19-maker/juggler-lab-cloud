"""
Playwright Manager
Local: connect to the existing Windows Chrome via CDP.
Cloud: launch a bundled Chromium directly in headless mode.
"""
from __future__ import annotations
import os
import time
from playwright.sync_api import sync_playwright
from core.chrome_manager import ChromeManager

class PlaywrightManager:
    def __init__(self, debugger_url="http://127.0.0.1:9222", retry_count=3):
        self.cloud_mode = os.getenv("CLOUD_MODE", "0") == "1"
        self.debugger_url = debugger_url
        self.retry_count = retry_count
        self.chrome = ChromeManager()
        self.playwright = None
        self.browser = None
        self.context = None

    def connect(self):
        last_error = None
        for attempt in range(1, self.retry_count + 1):
            try:
                self.playwright = self.playwright or sync_playwright().start()

                if self.cloud_mode:
                    print(f"Cloud Chromium起動 {attempt}/{self.retry_count}")
                    self.browser = self.playwright.chromium.launch(
                        headless=True,
                        args=[
                            "--no-sandbox",
                            "--disable-dev-shm-usage",
                            "--disable-gpu",
                        ],
                    )
                    self.context = self.browser.new_context(
                        locale="ja-JP",
                        timezone_id="Asia/Tokyo",
                    )
                    print("Cloud Chromium起動成功")
                    return

                self.chrome.start()
                self.browser = self.playwright.chromium.connect_over_cdp(
                    self.debugger_url, timeout=15000
                )
                contexts = self.browser.contexts
                if not contexts:
                    raise RuntimeError("Chrome Contextが存在しません")
                self.context = contexts[0]
                print("CDP接続成功")
                return

            except Exception as e:
                last_error = e
                print("Playwright接続失敗:", type(e).__name__, e)
                if self.browser:
                    try:
                        self.browser.close()
                    except Exception:
                        pass
                self.browser = None
                self.context = None
                if attempt < self.retry_count and not self.cloud_mode:
                    self.chrome.restart()
                    time.sleep(10)

        if self.playwright:
            try:
                self.playwright.stop()
            except Exception:
                pass
            self.playwright = None
        raise RuntimeError(f"ブラウザ接続失敗: {last_error}")

    def new_page(self):
        if self.context is None:
            self.connect()
        return self.context.new_page()

    def close_page(self, page):
        if page:
            try:
                page.close()
            except Exception:
                pass

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
