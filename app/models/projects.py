from sqlmodel import SQLModel, Field
from typing import Optional
from datetime import date, datetime

class ProjectBase(SQLModel):
    id : int=Field(primary_key=True)
    name: str = Field(index=True)
    location: str
    is_live: bool = Field(default=False)
    is_archived: bool = Field(default=False)
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)

class ProjectCreate(ProjectBase):
    id:int= Field(default=None, primary_key=True)
    name: str
    location: str
    start_date: date
    end_date: date
    is_live: bool

class ProjectUpdate(ProjectBase):
    pass

class Projects(SQLModel, table=True):
    id: int= Field(default=None, primary_key=True)
    name: str
    location: str
    is_live: bool = Field(default=False)
    is_archived: bool = Field(default=False, index=True)
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)