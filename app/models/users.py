from sqlalchemy.orm import Mapped, mapped_column, declarative_base
from sqlalchemy import String
from sqlmodel import SQLModel


Base = declarative_base()

class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(String(50), unique=True)
    password: Mapped[str] = mapped_column(String(255))
    role: str = "user"

class UserCreate(SQLModel):
    email:str
    password:str



 


    