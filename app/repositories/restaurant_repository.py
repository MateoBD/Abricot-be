from uuid import UUID

from sqlalchemy import and_, delete, exists, func, select

from app.extensions import db
from app.models.location import CityModel, ProvinceModel
from app.models.restaurant import RestaurantModel
from app.models.restaurant_cuisine import RestaurantCuisineModel
from app.models.restaurant_review import RestaurantReviewModel

CUISINE_UNSET = object()


class RestaurantRepository:
    @staticmethod
    def _replace_cuisine_rows(
        restaurant_id: UUID, cuisine_type_ids: list[UUID] | None
    ) -> None:
        db.session.execute(
            delete(RestaurantCuisineModel).where(
                RestaurantCuisineModel.restaurant_id == restaurant_id
            )
        )
        if not cuisine_type_ids:
            return
        for cid in dict.fromkeys(cuisine_type_ids):
            db.session.add(
                RestaurantCuisineModel(
                    restaurant_id=restaurant_id, cuisine_type_id=cid
                )
            )

    @staticmethod
    def create(
        name: str,
        address: str,
        phone: str,
        city_id: UUID,
        email: str | None = None,
        description: str | None = None,
        neighbourhood_id: UUID | None = None,
        price_range_id: UUID | None = None,
        *,
        cuisine_type_ids: list[UUID] | None = None,
        auto_commit: bool = True,
    ) -> RestaurantModel:
        restaurant = RestaurantModel(
            name=name,
            address=address,
            phone=phone,
            city_id=city_id,
            neighbourhood_id=neighbourhood_id,
            price_range_id=price_range_id,
            email=email,
            description=description,
        )
        db.session.add(restaurant)
        db.session.flush()
        RestaurantRepository._replace_cuisine_rows(restaurant.id, cuisine_type_ids or [])
        if auto_commit:
            db.session.commit()
        return restaurant

    @staticmethod
    def search(
        *,
        name: str | None = None,
        country_id: UUID | None = None,
        province_id: UUID | None = None,
        city_id: UUID | None = None,
        neighbourhood_id: UUID | None = None,
        price_range_id: UUID | None = None,
        cuisine_type_ids: list[UUID] | None = None,
        sort: str = "name",
        page: int = 1,
        per_page: int = 20,
    ) -> tuple[list[RestaurantModel], int]:
        conds: list = []
        if name and name.strip():
            conds.append(RestaurantModel.name.ilike(f"%{name.strip()}%"))
        if city_id is not None:
            conds.append(RestaurantModel.city_id == city_id)
        if neighbourhood_id is not None:
            conds.append(RestaurantModel.neighbourhood_id == neighbourhood_id)
        if price_range_id is not None:
            conds.append(RestaurantModel.price_range_id == price_range_id)
        if province_id is not None:
            conds.append(
                exists(
                    select(CityModel.id).where(
                        CityModel.id == RestaurantModel.city_id,
                        CityModel.province_id == province_id,
                    )
                )
            )
        if country_id is not None:
            conds.append(
                exists(
                    select(CityModel.id)
                    .join(ProvinceModel, CityModel.province_id == ProvinceModel.id)
                    .where(
                        CityModel.id == RestaurantModel.city_id,
                        ProvinceModel.country_id == country_id,
                    )
                )
            )
        if cuisine_type_ids:
            conds.append(
                exists(
                    select(RestaurantCuisineModel.id).where(
                        RestaurantCuisineModel.restaurant_id == RestaurantModel.id,
                        RestaurantCuisineModel.cuisine_type_id.in_(cuisine_type_ids),
                    )
                )
            )

        where_clause = and_(*conds) if conds else True

        total = int(
            db.session.scalar(
                select(func.count()).select_from(RestaurantModel).where(where_clause)
            )
            or 0
        )

        page = max(page, 1)
        per_page = max(min(per_page, 100), 1)
        offset = (page - 1) * per_page

        if sort == "newest":
            order_clause = RestaurantModel.created_at.desc()
        elif sort == "rating":
            avg_sub = (
                select(
                    func.coalesce(func.avg(RestaurantReviewModel.score * 1.0), 0.0)
                )
                .where(RestaurantReviewModel.restaurant_id == RestaurantModel.id)
                .correlate(RestaurantModel)
                .scalar_subquery()
            )
            order_clause = avg_sub.desc()
        else:
            order_clause = RestaurantModel.name.asc()

        rows = list(
            db.session.execute(
                select(RestaurantModel)
                .where(where_clause)
                .order_by(order_clause)
                .offset(offset)
                .limit(per_page)
            ).scalars()
        )
        return rows, total

    @staticmethod
    def get_cuisine_type_ids_for_restaurant(restaurant_id: UUID) -> list[UUID]:
        return list(
            db.session.execute(
                select(RestaurantCuisineModel.cuisine_type_id).where(
                    RestaurantCuisineModel.restaurant_id == restaurant_id
                )
            ).scalars()
        )

    @staticmethod
    def get_cuisine_type_ids_bulk(
        restaurant_ids: list[UUID],
    ) -> dict[UUID, list[UUID]]:
        if not restaurant_ids:
            return {}
        rows = db.session.execute(
            select(
                RestaurantCuisineModel.restaurant_id,
                RestaurantCuisineModel.cuisine_type_id,
            ).where(RestaurantCuisineModel.restaurant_id.in_(restaurant_ids))
        ).all()
        out: dict[UUID, list[UUID]] = {}
        for rid, cid in rows:
            out.setdefault(rid, []).append(cid)
        return out

    @staticmethod
    def get_by_id(restaurant_id: UUID) -> RestaurantModel | None:
        return db.session.get(RestaurantModel, restaurant_id)

    @staticmethod
    def get_by_ids(restaurant_ids: list[UUID]) -> list[RestaurantModel]:
        if not restaurant_ids:
            return []
        return list(
            db.session.execute(
                select(RestaurantModel)
                .where(RestaurantModel.id.in_(restaurant_ids))
                .order_by(RestaurantModel.name)
            ).scalars()
        )

    @staticmethod
    def update(
        restaurant: RestaurantModel,
        name: str,
        address: str,
        phone: str,
        email: str | None = None,
        description: str | None = None,
        city_id: UUID | None = None,
        neighbourhood_id: UUID | None = None,
        price_range_id: UUID | None = None,
        *,
        patch_neighbourhood: bool = False,
        patch_price_range: bool = False,
        cuisine_type_ids: object = CUISINE_UNSET,
    ) -> RestaurantModel:
        restaurant.name = name
        restaurant.address = address
        restaurant.phone = phone
        restaurant.email = email
        restaurant.description = description
        if city_id is not None:
            restaurant.city_id = city_id
        if patch_neighbourhood:
            restaurant.neighbourhood_id = neighbourhood_id
        if patch_price_range:
            restaurant.price_range_id = price_range_id
        if cuisine_type_ids is not CUISINE_UNSET:
            RestaurantRepository._replace_cuisine_rows(
                restaurant.id,
                list(cuisine_type_ids) if cuisine_type_ids is not None else [],
            )
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
