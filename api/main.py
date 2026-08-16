from fastapi import FastAPI

app = FastAPI(
    title="Financial Research AI Agent API",
    version="1.0.0"
)


@app.get("/")
def root():
    return {
        "message": "Financial Research AI Agent API is running"
    }


@app.get("/health")
def health():
    return {
        "status": "healthy"
    }