"""
ChromeManager
- Local: keeps the existing Windows Chrome/CDP behavior.
- Cloud: CLOUD_MODE=1 -> browser lifecycle is handled by Playwright directly.
"""
from __future__ import annotations
import os
import subprocess
import time
from pathlib import Path
import psutil
import requests

class ChromeManager:
    def __init__(
        self,
        chrome_path=r"C:\Program Files\Google\Chrome\Application\chrome.exe",
        port=9222,
        profile_dir=None,
        startup_timeout=30,
    ):
        self.cloud_mode = os.getenv("CLOUD_MODE", "0") == "1"
        self.chrome_path = chrome_path
        self.port = port
        self.profile_dir = (
            Path(profile_dir) if profile_dir else
            Path(__file__).resolve().parent.parent / "chrome_profile"
        )
        self.startup_timeout = startup_timeout

    @property
    def debugger_url(self):
        return f"http://127.0.0.1:{self.port}/json/version"

    def is_running(self):
        if self.cloud_mode:
            return False
        try:
            r = requests.get(self.debugger_url, timeout=3)
            return r.status_code == 200
        except Exception:
            return False

    def start(self):
        if self.cloud_mode:
            return
        if self.is_running():
            print("Chromeは既に起動しています。")
            return
        self.profile_dir.mkdir(parents=True, exist_ok=True)
        subprocess.Popen(
            [
                self.chrome_path,
                f"--remote-debugging-port={self.port}",
                f"--user-data-dir={self.profile_dir}",
            ],
            creationflags=subprocess.CREATE_NEW_PROCESS_GROUP,
        )
        for _ in range(self.startup_timeout):
            if self.is_running():
                time.sleep(2)
                return
            time.sleep(1)
        raise RuntimeError("Chrome起動失敗")

    def stop(self):
        if self.cloud_mode:
            return
        target = str(self.profile_dir.resolve()).lower()
        for proc in psutil.process_iter(["name", "cmdline"]):
            try:
                if proc.info["name"] != "chrome.exe":
                    continue
                cmd = " ".join(proc.info["cmdline"] or []).lower()
                if target in cmd:
                    proc.kill()
            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                pass
        time.sleep(3)

    def restart(self):
        self.stop()
        self.start()
