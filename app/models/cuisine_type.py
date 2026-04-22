from uuid import UUID

from sqlalchemy import String, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from app.extensions import db
from app.utils.uuid7 import new_uuid7


class CuisineTypeModel(db.Model):
    __tablename__ = "cuisine_types"

    id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), primary_key=True, default=new_uuid7
    )
    slug: Mapped[str] = mapped_column(String(30), nullable=False, unique=True)
    label: Mapped[str] = mapped_column(String(100), nullable=False)
