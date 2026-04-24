from uuid import UUID

from sqlalchemy import Boolean, ForeignKey, Integer, String, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from app.extensions import db
from app.utils.uuid7 import new_uuid7


class MenuCategoryModel(db.Model):
    __tablename__ = "menu_categories"

    id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), primary_key=True, default=new_uuid7
    )
    menu_id: Mapped[UUID] = mapped_column(ForeignKey("menus.id"), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    display_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        server_default="true",
    )

    def to_dict(self) -> dict:
        return {
            "id": str(self.id),
            "menuId": str(self.menu_id),
            "name": self.name,
            "displayOrder": self.display_order,
            "isActive": self.is_active,
        }
