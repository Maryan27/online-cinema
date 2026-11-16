from fastapi import FastAPI

app = FastAPI(
    title="Online Cinema API",
    description="REST API for an online cinema (coursework, variant 17)",
    version="0.1.0",
)


@app.get("/api/health", tags=["system"])
def health():
    return {"status": "ok"}