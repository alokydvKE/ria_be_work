from fastapi import APIRouter, BackgroundTasks
from app.database import SessionLocal
from app.models.users import User
from app.services.auth import verify_verification_token, create_verification_token
from app.utils.mail import send_verification_email

router = APIRouter()

@router.get("/verify")
def verify_email(token: str):
    email = verify_verification_token(token)
    if not email:
        return {"message": "Invalid or expired link"}

    db = SessionLocal()
    try:
        user = db.query(User).filter(User.email == email).first()
        if not user:
            return {"message": "User not found"}
        if user.is_verified:
            return {"message": "Already verified"}

        if user.verification_token != token:
            return {"message": "This link has expired. Please request a new one."}

        user.is_verified = True
        user.verification_token = None  
        db.commit()
        return {"message": "Email verified. You can now log in."}
    finally:
        db.close()

@router.post("/resend-verification")
async def resend_verification(data: dict, background_tasks: BackgroundTasks):
    email = data.get("email")
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.email == email).first()
        if not user:
            return {"message": "User not found"}
        if user.is_verified:
            return {"message": "Already verified"}

        token = create_verification_token(email)
        user.verification_token = token
        db.commit()

        background_tasks.add_task(send_verification_email, email, token)
        return {"message": "Verification email resent"}
    finally:
        db.close()