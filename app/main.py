from fastapi import FastAPI

app = FastAPI(
    title="DevTrack API",
    description="Unified Developer Analytics Platform Backend API",
    version="1.0.0",
)

@app.get("/")
async def root() -> dict[str, str]:
    return {"message": "DevTrack API is running"}
