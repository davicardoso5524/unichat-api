from fastapi import FastAPI

app = FastAPI(
    title="Unichat API",
    version="0.1.0",
)

@app.get("/")
def root():
    return {
        "message": "UniChat API is running"
    }