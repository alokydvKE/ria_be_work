from fastapi import APIRouter
from app.services.auth import hash_password
from app.models.users import UserCreate, User
from app.models.roles import UserRole
from app.utils.db import engine
from sqlmodel import Session, select

router = APIRouter()

@router.post("/register")
def register(user: UserCreate):
    with Session(engine) as session:

        # check if user exists
        existing = session.execute(
            select(User).where(User.email == user.email)
        ).scalar_one_or_none()

        if existing:
            return {"message": "User already exists"}

        # hash password and create user
        hashed_password = hash_password(user.password)
        db_user = User(
            email=user.email,
            password=hashed_password,
        )
        session.add(db_user)
        session.commit()
        session.refresh(db_user)  # needed to get the auto-generated user id

        # assign default role R-002 (user)
        user_role = UserRole(
            user_id=db_user.id,
            role_id="R-002"
        )
        session.add(user_role)
        session.commit()

        return {"message": "User created"}