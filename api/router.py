from fastapi import APIRouter
from api.routes.delivery import router as delivery_router

api_router = APIRouter()

# Include sub-routers. Prefix is handled when registered in main.py
api_router.include_router(delivery_router, tags=["Delivery"])
