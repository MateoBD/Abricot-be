from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import DateTime, Enum, String, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from app.extensions import db
from app.models.enums import UserRole
from app.utils.uuid7 import new_uuid7


class UserModel(db.Model):
    __tablename__ = "users"

    id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), primary_key=True, default=new_uuid7
    )
    email: Mapped[str] = mapped_column(String(255), nullable=False, unique=True, index=True)
    cognito_sub: Mapped[str | None] = mapped_column(
        String(255), nullable=True, unique=True, index=True
    )
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    surname: Mapped[str] = mapped_column(String(100), nullable=False)
    role: Mapped[UserRole] = mapped_column(
        Enum(UserRole, native_enum=False, validate_strings=True, length=32),
        nullable=False,
        default=UserRole.CUSTOMER,
        server_default=UserRole.CUSTOMER.value,
        index=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(UTC)
    )

    def to_dict(self) -> dict:
        return {
            "id": str(self.id),
            "email": self.email,
            "cognitoSub": self.cognito_sub,
            "name": self.name,
            "surname": self.surname,
            "role": self.role.value,
            "createdAt": self.created_at.isoformat(),
        }
