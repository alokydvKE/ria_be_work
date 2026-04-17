from fastapi.middleware.cors import CORSMiddleware
from fastapi import FastAPI, Request
from app.routes import projects
from app.routes import register
from app.routes import verify
from app.routes import login
from app.routes import logs

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],
    expose_headers=["*"],
)

#app.add_middleware(CorrelationIdMiddleware)

from app.services.auth import get_current_user

def bypass_get_current_user():
    return {"user_id": 1, "can_add": True, "can_edit": True, "can_delete": True}

app.dependency_overrides[get_current_user] = bypass_get_current_user

app.include_router(login.router)
app.include_router(projects.router)
app.include_router(register.router)
app.include_router(verify.router)
app.include_router(logs.router, prefix="/projects")