from fastapi_mail import FastMail, MessageSchema, ConnectionConfig
import os
from dotenv import load_dotenv
from pathlib import Path

load_dotenv()


env_path = Path(__file__).resolve().parent.parent.parent / ".env"
print("Looking for .env at:", env_path)
load_dotenv(dotenv_path=env_path, override=True)

print("MAIL_PORT:", os.getenv("MAIL_PORT"))
print("MAIL_SERVER:", os.getenv("MAIL_SERVER"))
print("MAIL_USERNAME:", os.getenv("MAIL_USERNAME"))

conf = ConnectionConfig(
    MAIL_USERNAME=os.getenv("MAIL_USERNAME"),
    MAIL_PASSWORD=os.getenv("MAIL_PASSWORD"),
    MAIL_FROM=os.getenv("MAIL_FROM"),
    MAIL_PORT=int(os.getenv("MAIL_PORT")),
    MAIL_SERVER=os.getenv("MAIL_SERVER"),
    MAIL_STARTTLS=True,
    MAIL_SSL_TLS=False,
    USE_CREDENTIALS=True,
)

async def send_verification_email(email: str, token: str):
    link = f"http://localhost:8000/verify?token={token}"
    print(f"Sending email to {email}")
    message = MessageSchema(
        subject="Verify your email",
        recipients=[email],
        body=f"Click to verify your account: {link}",
        subtype="plain"
    )
    await FastMail(conf).send_message(message)
    print(f"Email sent to {email}")