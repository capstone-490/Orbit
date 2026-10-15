from contextlib import asynccontextmanager
from fastapi import FastAPI
from migrations.migrate import migrate

@asynccontextmanager
async def lifespan(app: FastAPI):
    migrate()
    yield

app = FastAPI(lifespan=lifespan)

@app.get("/health")
def health():
    return {"status": "ok"}