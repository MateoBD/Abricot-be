from app.extensions import db
from app.models.restaurant import RestaurantModel


class RestaurantRepository:
    @staticmethod
    def create(
        name: str,
        address: str,
        phone: str,
        email: str | None = None,
        description: str | None = None,
    ) -> RestaurantModel:
        restaurant = RestaurantModel(
            name=name, address=address, phone=phone, email=email, description=description
        )
        db.session.add(restaurant)
        db.session.commit()
        return restaurant

    @staticmethod
    def get_all() -> list[RestaurantModel]:
        return list(
            db.session.execute(
                db.select(RestaurantModel).order_by(RestaurantModel.name)
            ).scalars()
        )

    @staticmethod
    def get_by_id(restaurant_id: int) -> RestaurantModel | None:
        return db.session.get(RestaurantModel, restaurant_id)

    @staticmethod
    def update(
        restaurant: RestaurantModel,
        name: str,
        address: str,
        phone: str,
        email: str | None = None,
        description: str | None = None,
    ) -> RestaurantModel:
        restaurant.name = name
        restaurant.address = address
        restaurant.phone = phone
        restaurant.email = email
        restaurant.description = description
        db.session.commit()
        return restaurant

    @staticmethod
    def update_photo(restaurant: RestaurantModel, photo_url: str) -> RestaurantModel:
        restaurant.photo_url = photo_url
        db.session.commit()
        return restaurant

    @staticmethod
    def delete(restaurant: RestaurantModel) -> None:
        db.session.delete(restaurant)
        db.session.commit()
