from project import db
from project.models.restaurant_model import RestaurantModel


class RestaurantRepository:
    """Handles all database operations related to RestaurantModel."""

    @classmethod
    def create(
        cls,
        name: str,
        address: str,
        phone: str,
        email: str | None = None,
        description: str | None = None,
    ) -> RestaurantModel:
        """
        Inserts a new restaurant into the database.

        Args:
            name: Name of the restaurant.
            address: Physical address.
            phone: Contact phone number.
            email: Optional contact email.
            description: Optional description.

        Returns:
            The newly created RestaurantModel instance.
        """
        restaurant = RestaurantModel(
            name=name,
            address=address,
            phone=phone,
            email=email,
            description=description,
        )
        db.session.add(restaurant)
        db.session.commit()
        return restaurant

    @classmethod
    def get_all(cls) -> list[RestaurantModel]:
        """Returns all restaurants ordered by name."""
        return RestaurantModel.query.order_by(RestaurantModel.name).all()

    @classmethod
    def get_by_id(cls, restaurant_id: int) -> RestaurantModel | None:
        """
        Retrieves a restaurant by its primary key.

        Args:
            restaurant_id: The restaurant's ID.

        Returns:
            The matching RestaurantModel instance, or None if not found.
        """
        return RestaurantModel.query.get(restaurant_id)

    @classmethod
    def update(
        cls,
        restaurant: RestaurantModel,
        name: str,
        address: str,
        phone: str,
        email: str | None = None,
        description: str | None = None,
    ) -> RestaurantModel:
        """
        Updates the fields of an existing restaurant.

        Args:
            restaurant: The RestaurantModel instance to update.
            name: New name.
            address: New address.
            phone: New phone number.
            email: New email (or None to clear it).
            description: New description (or None to clear it).

        Returns:
            The updated RestaurantModel instance.
        """
        restaurant.name = name
        restaurant.address = address
        restaurant.phone = phone
        restaurant.email = email
        restaurant.description = description
        db.session.commit()
        return restaurant

    @classmethod
    def delete(cls, restaurant: RestaurantModel) -> None:
        """
        Deletes a restaurant from the database.

        Args:
            restaurant: The RestaurantModel instance to delete.
        """
        db.session.delete(restaurant)
        db.session.commit()
