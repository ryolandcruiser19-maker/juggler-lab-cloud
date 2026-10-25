from fastapi import FastAPI
from pydantic import BaseModel
import sqlite3
import subprocess
import sys

app = FastAPI()

DB_PATH = "/app/data/juggler.db"


class DailyData(BaseModel):
    日付: str
    店舗: str
    機種: str
    台番号: int
    BB: int
    RB: int
    G数: int
    合成確率: float | None
    評価: str
    信頼度補正: str
    イベント種別: str
    備考: str
    島: str


class RealtimeData(BaseModel):
    取得日時: str
    日付: str
    店舗: str
    機種: str
    台番号: int
    BB: int
    RB: int
    G数: int
    合成確率: float | None
    最終ゲーム: int
    BIG過去最高: int
    作成日時: str
    営業日: str
    取得種別: str
    取得回数: int
    P_CUBE更新時刻: str | None


class StoreDailyData(BaseModel):
    日付: str
    店舗: str
    機種: str
    台番号: int
    BB: int
    RB: int
    G数: int
    合成確率: float | None = None
    # 評価など。送られてこない場合は None（既存の保存値は消さない）
    評価: str | None = None
    信頼度補正: str | None = None
    イベント種別: str | None = None
    備考: str | None = None
    島: str | None = None


@app.post("/sync")
def sync_data(data: DailyData):

    conn = sqlite3.connect(DB_PATH)

    conn.execute(
        """
        INSERT OR REPLACE INTO daily_data (
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
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            data.日付,
            data.店舗,
            data.機種,
            data.台番号,
            data.BB,
            data.RB,
            data.G数,
            data.合成確率,
            data.評価,
            data.信頼度補正,
            data.イベント種別,
            data.備考,
            data.島,
        ),
    )

    conn.commit()
    conn.close()

    return {
        "status": "ok",
        "date": data.日付,
        "machine_no": data.台番号,
    }


@app.post("/realtime-sync")
def realtime_sync(data: list[RealtimeData]):

    conn = sqlite3.connect(DB_PATH)

    conn.executemany(
        """
        INSERT OR REPLACE INTO raw_data (
            取得日時,
            日付,
            店舗,
            機種,
            台番号,
            BB,
            RB,
            G数,
            合成確率,
            最終ゲーム,
            BIG過去最高,
            作成日時,
            営業日,
            取得種別,
            取得回数,
            P_CUBE更新時刻
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        [
            (
                row.取得日時,
                row.日付,
                row.店舗,
                row.機種,
                row.台番号,
                row.BB,
                row.RB,
                row.G数,
                row.合成確率,
                row.最終ゲーム,
                row.BIG過去最高,
                row.作成日時,
                row.営業日,
                row.取得種別,
                row.取得回数,
                row.P_CUBE更新時刻,
            )
            for row in data
        ],
    )

    conn.commit()
    conn.close()

    return {
        "status": "ok",
        "count": len(data),
    }


@app.post("/sync-store-daily")
def sync_store_daily(data: list[StoreDailyData]):
    # 追加店舗（豊平Hなど）の日次データ専用。
    # 既存の daily_data / machines には一切触れず、別テーブルに保存する。

    conn = sqlite3.connect(DB_PATH)

    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS store_daily_data (
            日付 TEXT NOT NULL,
            店舗 TEXT NOT NULL,
            機種 TEXT,
            台番号 INTEGER NOT NULL,
            BB INTEGER,
            RB INTEGER,
            G数 INTEGER,
            合成確率 REAL,
            PRIMARY KEY (日付, 店舗, 台番号)
        )
        """
    )

    # 評価などの列がなければ足す（既存のデータはそのまま残る）
    existing = {row[1] for row in conn.execute("PRAGMA table_info(store_daily_data)")}
    for column in ("評価", "信頼度補正", "イベント種別", "備考", "島"):
        if column not in existing:
            conn.execute(f"ALTER TABLE store_daily_data ADD COLUMN {column} TEXT")

    # 同じ日・店舗・台番号は上書き。ただし評価などが送られてこない（None）ときは、
    # すでに保存されている値を残す。
    conn.executemany(
        """
        INSERT INTO store_daily_data (
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
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(日付, 店舗, 台番号) DO UPDATE SET
            機種 = excluded.機種,
            BB = excluded.BB,
            RB = excluded.RB,
            G数 = excluded.G数,
            合成確率 = excluded.合成確率,
            評価 = COALESCE(excluded.評価, store_daily_data.評価),
            信頼度補正 = COALESCE(excluded.信頼度補正, store_daily_data.信頼度補正),
            イベント種別 = COALESCE(excluded.イベント種別, store_daily_data.イベント種別),
            備考 = COALESCE(excluded.備考, store_daily_data.備考),
            島 = COALESCE(excluded.島, store_daily_data.島)
        """,
        [
            (
                row.日付,
                row.店舗,
                row.機種,
                row.台番号,
                row.BB,
                row.RB,
                row.G数,
                row.合成確率,
                row.評価,
                row.信頼度補正,
                row.イベント種別,
                row.備考,
                row.島,
            )
            for row in data
        ],
    )

    conn.commit()
    conn.close()

    return {
        "status": "ok",
        "count": len(data),
    }


@app.post("/sync-complete")
def sync_complete():
    result = subprocess.run(
        [sys.executable, "/app/analysis/run_daily_analysis.py"],
        check=False,
    )

    if result.returncode != 0:
        return {
            "status": "error",
            "returncode": result.returncode,
        }

    return {
        "status": "analysis_completed",
    }
