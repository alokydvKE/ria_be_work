from fastapi import APIRouter, Response
from app.utils.db import SessionLocal
from app.models.users import User
from app.services.auth import create_token, verify_password, get_user_permissions

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
            return {"success": False, "message": "User not found"}

        if not verify_password(password, user.password):
            return {"success": False, "message": "Incorrect Password"}

        permissions = get_user_permissions(user.id)

        token = create_token({
            "user_id": user.id,
            "email": user.email,
        })

        return {
            "success": True,
            "access_token": token,
            "token_type": "bearer",
            "permissions": permissions 
        }

    finally:
        db.close()