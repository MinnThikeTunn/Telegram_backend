from app.messenger import router as messenger_router
from fastapi import FastAPI
from app.messenger import router as messenger_router

app = FastAPI()

app.include_router(messenger_router)