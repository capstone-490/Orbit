#!/usr/bin/env python3
# No substantial AI-generated code
from fastapi import Depends, FastAPI, Header

from app.feature_flags import get_variant

app = FastAPI()

def get_user_id(user_id: str | None = Header(default=None)) -> str:
    #Temporary: to be replaced with authenticated user when login is implemented.
    return user_id or "unknown"

@app.get("/")
def read_root():
    return {"Hello": "World"}


@app.get("/health")
def health():
    return {"status": "ok"}

#Temporary endpoint for testing A/B feature flags. Add flag check to feature endpoint when needed.
@app.get("/ab-test")
def ab_test(user_id: str = Depends(get_user_id)):
    variant = get_variant("demo-ab", user_id)
    return { "Variant": variant}
