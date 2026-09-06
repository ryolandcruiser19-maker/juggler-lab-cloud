from fastapi import FastAPI

app = FastAPI()


@app.get("/sync-test")
def sync_test():
    return {"status": "ok"}
