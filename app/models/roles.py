from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import String, Boolean, ForeignKey
from app.models.users import Base

class Role(Base):
    __tablename__ = "roles"

    role_id: Mapped[str] = mapped_column(String(20), primary_key=True)
    role_name: Mapped[str] = mapped_column(String(50))
    can_edit: Mapped[bool] = mapped_column(default=False)
    can_add: Mapped[bool] = mapped_column(default=False)
    can_delete: Mapped[bool] = mapped_column(default=False)

class UserRole(Base):
    __tablename__ = "user_roles"

    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), primary_key=True)
    role_id: Mapped[str] = mapped_column(String(20), ForeignKey("roles.role_id"))