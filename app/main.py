from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.routes import login
from app.routes import items

#comment
app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(login.router)
app.include_router(items.router)