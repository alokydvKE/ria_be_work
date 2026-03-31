from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select
from app.utils.db import engine
from app.models.items import Items, ItemCreate
from app.services.auth import get_current_user

router = APIRouter()


@router.get("/items")
def get_items(user=Depends(get_current_user)):
    with Session(engine) as session:
        return session.exec(select(Items).where(Items.is_deleted == False)).all()

@router.post("/items")
def create_item(item: ItemCreate, user=Depends(get_current_user)):
    if not user.get("can_add"):
        raise HTTPException(status_code=403, detail="Not authorized to add items")
    with Session(engine) as session:
        new_item = Items(**item.dict())
        session.add(new_item)
        session.commit()
        session.refresh(new_item)
        return new_item

@router.put("/items/{item_id}")
def update_item(item_id: int, item: ItemCreate, user=Depends(get_current_user)):
    if not user.get("can_edit"):
        raise HTTPException(status_code=403, detail="Not authorized to edit items")
    with Session(engine) as session:
        db_item = session.get(Items, item_id)
        if not db_item:
            raise HTTPException(status_code=404, detail="Item not found")
        db_item.item_name = item.item_name
        db_item.description = item.description
        db_item.price = item.price
        db_item.stock_quantity = item.stock_quantity
        session.commit()
        session.refresh(db_item)
        return db_item

@router.delete("/items/{item_id}")
def delete_item(item_id: int, user=Depends(get_current_user)):
    if not user.get("can_delete"):
        raise HTTPException(status_code=403, detail="Not authorized to delete items")
    with Session(engine) as session:
        db_item = session.get(Items, item_id)
        if not db_item:
            raise HTTPException(status_code=404, detail="Item not found")
        db_item.is_deleted = True
        session.commit()
        return {"success": True}
