from fastapi import APIRouter, response
from app.utils.db import SessionLocal
from app.models import User
from services.auth import create_token, verify_password

router = APIRouter()


@router.post("/login")
def login(data : dict):
    email = data.get("email")
    password = data.get("password")

    if not email or not password:
        return {"success": False, "message": "Email and password are required"}
    
    db = SessionLocal()

    try:
        user = db.query(User).filter(User.email ==email).first()

        if not user:
            return{"success": False, "message": "User not found"}

        elif not verify_password(password, user.password):
             return{"success": False, "message": "Incorrect Password"}

        else: 
            token = create_token(user)

            response.set_cookie(
                key="access_token",
                value=token,
                httponly=True,
                samesite="lax"
            )

            return {"success": True}


    finally:
        db.close()


    
