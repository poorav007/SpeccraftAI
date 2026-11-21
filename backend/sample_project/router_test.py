from fastapi import FastAPI

app = FastAPI()

app.include_router(
    missing_router,
    prefix="/users"
)