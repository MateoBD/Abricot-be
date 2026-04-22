from uuid import UUID

from sqlalchemy import Integer, String, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from app.extensions import db
from app.utils.uuid7 import new_uuid7


class PriceRangeModel(db.Model):
    __tablename__ = "price_ranges"

    id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), primary_key=True, default=new_uuid7
    )
    slug: Mapped[str] = mapped_column(String(20), nullable=False, unique=True)
    label: Mapped[str] = mapped_column(String(10), nullable=False)
    description: Mapped[str | None] = mapped_column(String(200), nullable=True)
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
