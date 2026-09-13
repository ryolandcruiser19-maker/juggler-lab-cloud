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
