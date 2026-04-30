from jose import jwt  
from datetime import datetime, timedelta
from dotenv import load_dotenv
from fastapi import HTTPException, Depends
import os 
from passlib.context import CryptContext
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from app.database import SessionLocal
from app.models.roles import UserRole, Role


load_dotenv()

ACCESS_TOKEN_EXPIRE_MINUTES = os.getenv('ACCESS_TOKEN_EXPIRE_MINUTES')
SECRET_KEY = os.getenv('SECRET_KEY')
ALGORITHM = os.getenv('ALGORITHM')

def create_token(data: dict):
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(minutes=int(ACCESS_TOKEN_EXPIRE_MINUTES))
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

def verify_token(token: str):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload 
    except:
        return None

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def hash_password(password: str) -> str:
    return pwd_context.hash(password[:72])

def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain[:72], hashed)

security = HTTPBearer()

def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    token = credentials.credentials
    payload = verify_token(token)

    if not payload:
        raise HTTPException(status_code=401, detail="Invalid token")

    # permissions = get_user_permissions(payload.get("user_id"))

    return {
        "user_id": payload.get("user_id"),
        "email": payload.get("email"),
        # **permissions
    }

# from fastapi import Depends, HTTPException, Request
# import jwt

# ORCHESTRATOR_PUBLIC_KEY = open("./keys/orchestrator_public.pem").read()
# SESSION_COOKIE_NAME = "myapp_session"

# def get_current_user(request: Request) -> str:
#     # Try cookie first (browser), then Bearer header (Swagger/scripts)
#     token = request.cookies.get(SESSION_COOKIE_NAME)
#     if not token:
#         auth = request.headers.get("Authorization", "")
#         if auth.startswith("Bearer "):
#             token = auth.split(" ")[1]
#     if not token:
#         raise HTTPException(status_code=401, detail="Not authenticated")

#     try:
#         payload = jwt.decode(
#             token, ORCHESTRATOR_PUBLIC_KEY,
#             algorithms=["RS256"],
#             options={"require": ["exp", "iss", "user_id"]}
#         )
#         if payload["iss"] != "orchestrator":
#             raise HTTPException(status_code=401, detail="Invalid token issuer")
#         return payload["user_id"]   # always a string (UUID)
#     except jwt.ExpiredSignatureError:
#         raise HTTPException(status_code=401, detail="Token expired")
#     except jwt.InvalidTokenError as e:
#         raise HTTPException(status_code=401, detail=f"Invalid token: {e}")


def get_user_permissions(user_id: int) -> dict:
    db = SessionLocal()
    try:
        user_role = db.query(UserRole).filter(UserRole.user_id == user_id).first()

        if not user_role:
            return {"can_edit": False, "can_add": False, "can_delete": False}

        role = db.query(Role).filter(Role.role_id == user_role.role_id).first()

        if not role:
            return {"can_edit": False, "can_add": False, "can_delete": False}

        return {
            "can_edit": bool(role.can_edit),
            "can_add": bool(role.can_add),
            "can_delete": bool(role.can_delete),
        }
    finally:
        db.close()

def create_verification_token(email: str) -> str:
    expire = datetime.utcnow() + timedelta(hours=24)
    return jwt.encode({"email": email, "exp": expire}, SECRET_KEY, algorithm=ALGORITHM)

def verify_verification_token(token: str):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload.get("email")
    except:
        return None