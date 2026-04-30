from fastapi import APIRouter, BackgroundTasks, HTTPException
from app.utils.mail import send_verification_email
from app.services.auth import hash_password, create_verification_token
from app.models.users import UserCreate, User
from app.models.roles import UserRole
from app.database import engine
from sqlmodel import Session, select

import logging
logger = logging.getLogger(__name__)
security_logger = logging.getLogger("security")

router = APIRouter()

@router.post("/register", status_code=201)
async def register(user: UserCreate, background_tasks: BackgroundTasks):
    with Session(engine) as session:
        existing = session.execute(
            select(User).where(User.email == user.email)
        ).scalar_one_or_none()

        if existing:
            if not existing.is_verified:
                token = create_verification_token(existing.email)
                background_tasks.add_task(send_verification_email, existing.email, token)
                security_logger.warning(f"REGISTRATION FAILED | email={user.email} | reason=already exists but not verified")
                raise HTTPException(status_code=409, detail="Account already exists but is not verified. Verification email resent.")
            else:
                security_logger.warning(f"REGISTRATION FAILED | email={user.email} | reason=already exists")
                raise HTTPException(status_code=409, detail="An account with this email already exists.")

        db_user = User(
            email=user.email,
            password=hash_password(user.password),
            username=user.email.split("@")[0],
            is_verified=False
        )
        session.add(db_user)
        session.commit()
        session.refresh(db_user)

        #session.add(UserRole(user_id=db_user.id, role_id="R-002"))
        #session.commit()

        token = create_verification_token(user.email)
        db_user.verification_token = token
        session.commit()

        background_tasks.add_task(send_verification_email, user.email, token)

        logger.info(f"USER REGISTERED | user_id={db_user.id} | email={user.email}")
        return {"message": "Account created. Please verify your email before logging in."}