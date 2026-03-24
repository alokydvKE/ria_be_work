from app.utils.db import engine
from fastapi import APIRouter
from sqlmodel import Session, select
from app.models import Items

router = APIRouter()
@router.get("/items")
def get_dashboard_data():
    with Session(engine) as session:
        statement = select(Items)
        results = session.exec(statement).all()
        return results
