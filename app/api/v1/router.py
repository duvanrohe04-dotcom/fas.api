from fastapi import APIRouter

from app.api.v1 import auth, categories, kitchen, orders, products, tables

api_router = APIRouter()
api_router.include_router(auth.router)
api_router.include_router(categories.router)
api_router.include_router(products.router)
api_router.include_router(tables.router)
api_router.include_router(orders.router)
api_router.include_router(kitchen.router)
