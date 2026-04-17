from sqlmodel import SQLModel, Field
from typing import Optional

class User(SQLModel, table=True):
    __tablename__ = "users"
    
    id: Optional[int] = Field(default=None, primary_key=True)

    email: str = Field(unique=True, index=True)
    password: str 
    username: Optional[str] = Field(default=None)
    is_verified: bool = Field(default=False)
    verification_token: Optional[str] = Field(default=None)

class UserCreate(SQLModel):
    email: str
    password: str