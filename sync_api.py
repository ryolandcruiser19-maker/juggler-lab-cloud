from fastapi import FastAPI
from pydantic import BaseModel

app = FastAPI()


class SyncTestData(BaseModel):
    date: str
    machine_no: int
    machine_name: str


@app.post("/sync-test")
def sync_test(data: SyncTestData):
    return {
        "status": "ok",
        "received": {
            "date": data.date,
            "machine_no": data.machine_no,
            "machine_name": data.machine_name,
        },
    }
