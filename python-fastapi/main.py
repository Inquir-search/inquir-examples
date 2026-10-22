from datetime import datetime, timezone

from fastapi import FastAPI

app = FastAPI()


# Health check: the platform calls it before sending traffic to a new version.
@app.get("/healthz")
def healthz():
    return {"ok": True}


@app.get("/api/hello")
def hello():
    return {"message": "Hello from Inquir Compute", "time": datetime.now(timezone.utc).isoformat()}
