from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.routes import login
from app.routes import items
from app.routes import register

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],
    expose_headers=["*"],
)

app.include_router(login.router)
app.include_router(items.router)
app.include_router(register.router)