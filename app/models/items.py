from sqlmodel import SQLModel, Field


class Items(SQLModel, table =True):
    item_id: int | None = Field(default=None, primary_key=True)
    item_name: str
    description: str
    price: float
    stock_quantity: int
