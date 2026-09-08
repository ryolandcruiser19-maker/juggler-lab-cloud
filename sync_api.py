from fastapi import FastAPI
from pydantic import BaseModel
import sqlite3

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

@app.post("/sync-complete")
def sync_complete():
    return {"status": "received"}
