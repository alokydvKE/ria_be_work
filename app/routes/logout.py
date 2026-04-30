from fastapi import APIRouter, Response

router = APIRouter()

SESSION_COOKIE_NAME = "logger_session"

@router.post("/logout")
def logout(response: Response):
    response.delete_cookie(
        key=SESSION_COOKIE_NAME,
        httponly=True,
        samesite="lax"
    )
    return {"success": True}