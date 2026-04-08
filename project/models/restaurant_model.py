from datetime import datetime, timezone

from project import db


class RestaurantModel(db.Model):
    """
    Represents a restaurant in the system.

    Attributes:
        id (int): Auto-incremented primary key.
        name (str): Name of the restaurant.
        address (str): Physical address.
        phone (str): Contact phone number.
        email (str): Optional contact email.
        description (str): Optional description of the restaurant.
        created_at (datetime): UTC timestamp of creation.
    """

    __tablename__ = "restaurants"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    name = db.Column(db.String(150), nullable=False)
    address = db.Column(db.String(255), nullable=False)
    phone = db.Column(db.String(30), nullable=False)
    email = db.Column(db.String(255), nullable=True)
    description = db.Column(db.Text, nullable=True)
    photo_url = db.Column(db.String(500), nullable=True)
    created_at = db.Column(
        db.DateTime, nullable=False, default=lambda: datetime.now(timezone.utc)
    )

    def to_dict(self):
        """Serializes the restaurant instance to a dictionary."""
        return {
            "id": self.id,
            "name": self.name,
            "address": self.address,
            "phone": self.phone,
            "email": self.email,
            "description": self.description,
            "photoUrl": self.photo_url,
            "createdAt": self.created_at.isoformat(),
        }
