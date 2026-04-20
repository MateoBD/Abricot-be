from sqlalchemy import Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.extensions import db


class PriceRangeModel(db.Model):
    __tablename__ = "price_ranges"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    slug: Mapped[str] = mapped_column(String(20), nullable=False, unique=True)
    label: Mapped[str] = mapped_column(String(10), nullable=False)
    description: Mapped[str | None] = mapped_column(String(200), nullable=True)
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
