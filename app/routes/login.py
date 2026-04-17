from fastapi import APIRouter, Response
from app.database import SessionLocal
from app.models.users import User
from app.services.auth import create_token, verify_password, get_user_permissions


import logging
logger = logging.getLogger(__name__)
security_logger = logging.getLogger("security")


router = APIRouter()

@router.post("/login")
def login(data: dict, response: Response):
    email = data.get("email")
    password = data.get("password")

    if not email or not password:
        return {"success": False, "message": "Email and password are required"}

    db = SessionLocal()
    try:
        user = db.query(User).filter(User.email == email).first()

        if not user:
            security_logger.warning(f"LOGIN FAILED | user_email={email} | reason=user not found")
            return {"success": False, "message": "User not found"}
            
        if not verify_password(password, user.password):
            security_logger.warning(f"LOGIN FAILED | user_id={user.id} | reason=incorrect password")
            return {"success": False, "message": "Incorrect password"}

        if not user.is_verified:
            security_logger.warning(f"LOGIN FAILED | user_id={user.id} | reason=email not verified")
            return {"success": False, "message": "Please verify your email before logging in"}

        logger.info(f"LOGIN SUCCESS | user_id={user.id}")

        #permissions = get_user_permissions(user.id)

        token = create_token({
            "user_id": user.id,
            "email": user.email,
        })

        return {
            "success": True,
            "access_token": token,
            "token_type": "bearer",
            #"permissions": permissions
        }


    finally:
        db.close()