import sqlite3
import requests

CLOUD_SYNC_URL = "https://juggler-lab-cloud-production.up.railway.app/sync"
DB_PATH = "database/juggler.db"

TARGET_DATE = None

if TARGET_DATE is None:
    conn = sqlite3.connect(DB_PATH)
    TARGET_DATE = conn.execute(
        "SELECT MAX(日付) FROM daily_data"
    ).fetchone()[0]
    conn.close()

conn = sqlite3.connect(DB_PATH)
conn.row_factory = sqlite3.Row

rows = conn.execute(
    """
    SELECT
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
    FROM daily_data
    WHERE 日付 = ?
    ORDER BY 台番号
    """,
    (TARGET_DATE,),
).fetchall()

conn.close()

print(f"対象日: {TARGET_DATE}")
print(f"取得件数: {len(rows)}")

for row in rows:
    data = dict(row)

    data["信頼度補正"] = data["信頼度補正"] or ""
    data["備考"] = data["備考"] or ""

    response = requests.post(
        CLOUD_SYNC_URL,
        json=data,
        timeout=30,
    )

    if response.status_code != 200:
        print("同期失敗:", data["台番号"], response.status_code, response.text)
        raise RuntimeError(
            f"クラウド同期失敗: 台番号 {data['台番号']}"
        )

    print("同期成功:", data["台番号"])

print("全台同期完了")
