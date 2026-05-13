import logging
from uuid import UUID

from app.exceptions.errors import NotFoundError, ValidationError
from app.extensions import db
from app.models.enums import UserRole
from app.models.restaurant import RestaurantModel
from app.integrations.s3 import S3Client
from app.repositories.restaurant_admin_repository import RestaurantAdminRepository
from app.repositories.restaurant_repository import (
    CUISINE_UNSET,
    RestaurantRepository,
)
from app.repositories.restaurant_review_repository import RestaurantReviewRepository
from app.repositories.user_repository import UserRepository
from app.utils.list_envelope import paginated_list_envelope

_UNSET = object()
# For routes: omit optional FK fields when not present in JSON body
FIELD_UNSET = _UNSET


def _parse_uuid(value: str | UUID | None, field: str) -> UUID:
    if value is None or value == "":
        raise ValidationError(f"{field} is required.", {field: "Required"})
    if isinstance(value, UUID):
        return value
    try:
        return UUID(str(value))
    except ValueError:
        raise ValidationError("Invalid identifier format.", {field: "Invalid UUID"})


def _parse_uuid_opt(value: str | UUID | None) -> UUID | None:
    if value is None or value == "":
        return None
    if isinstance(value, UUID):
        return value
    try:
        return UUID(str(value))
    except ValueError:
        raise ValidationError("Invalid identifier format.", {"value": "Invalid UUID"})


def _parse_uuid_list(value: object | None, field: str) -> list[UUID]:
    if value is None:
        return []
    if not isinstance(value, list):
        raise ValidationError(
            f"{field} must be a list of UUID strings.",
            {field: "Must be a list"},
        )
    out: list[UUID] = []
    for i, item in enumerate(value):
        out.append(_parse_uuid(item, f"{field}[{i}]"))
    return out

logger = logging.getLogger(__name__)


class RestaurantService:
    _ALLOWED_PHOTO_MIME_TYPES = {
        "image/jpeg",
        "image/png",
        "image/webp",
    }

    @staticmethod
    def _restaurant_payload(
        restaurant: RestaurantModel,
        cuisine_map: dict[UUID, list[UUID]] | None = None,
        review_stats: dict[UUID, tuple[float | None, int]] | None = None,
    ) -> dict:
        payload = restaurant.to_dict()
        if cuisine_map is None:
            cids = RestaurantRepository.get_cuisine_type_ids_for_restaurant(
                restaurant.id
            )
        else:
            cids = cuisine_map.get(restaurant.id, [])
        payload["cuisineTypeIds"] = [str(x) for x in cids]
        rid = restaurant.id
        if review_stats is None:
            review_stats = RestaurantReviewRepository.get_stats_by_restaurant_ids([rid])
        avg, rc = review_stats.get(rid, (None, 0))
        payload["averageScore"] = avg
        payload["reviewCount"] = rc
        return payload

    _VALID_SORT_VALUES = frozenset({"name", "newest", "rating"})

    @staticmethod
    def search(
        *,
        name: str | None = None,
        country_id: str | UUID | None = None,
        province_id: str | UUID | None = None,
        city_id: str | UUID | None = None,
        neighbourhood_id: str | UUID | None = None,
        price_range_id: str | UUID | None = None,
        cuisine_type_ids: list[str | UUID] | None = None,
        sort: str = "name",
        page: int = 1,
        per_page: int = 20,
    ) -> dict:
        page = max(page, 1)
        per_page = max(min(per_page, 100), 1)
        if sort not in RestaurantService._VALID_SORT_VALUES:
            sort = "name"
        cid_country = _parse_uuid_opt(country_id) if country_id else None
        cid_province = _parse_uuid_opt(province_id) if province_id else None
        cid_city = _parse_uuid_opt(city_id) if city_id else None
        cid_neigh = _parse_uuid_opt(neighbourhood_id) if neighbourhood_id else None
        cid_price = _parse_uuid_opt(price_range_id) if price_range_id else None
        c_cuisines: list[UUID] | None = None
        if cuisine_type_ids:
            c_cuisines = _parse_uuid_list(cuisine_type_ids, "cuisineTypeIds")

        rows, total = RestaurantRepository.search(
            name=name,
            country_id=cid_country,
            province_id=cid_province,
            city_id=cid_city,
            neighbourhood_id=cid_neigh,
            price_range_id=cid_price,
            cuisine_type_ids=c_cuisines,
            sort=sort,
            page=page,
            per_page=per_page,
        )
        cmap = RestaurantRepository.get_cuisine_type_ids_bulk([r.id for r in rows])
        rstats = RestaurantReviewRepository.get_stats_by_restaurant_ids(
            [r.id for r in rows]
        )
        data = [RestaurantService._restaurant_payload(r, cmap, rstats) for r in rows]
        return paginated_list_envelope(data, total=total, page=page, per_page=per_page)

    @staticmethod
    def get_by_id(restaurant_id: UUID) -> dict:
        restaurant = RestaurantRepository.get_by_id(restaurant_id)
        if not restaurant:
            raise NotFoundError(f"Restaurant with id={restaurant_id} not found.")
        return RestaurantService._restaurant_payload(restaurant)

    @staticmethod
    def create(
        name: str,
        address: str,
        phone: str,
        city_id: str | UUID,
        email: str | None = None,
        description: str | None = None,
        neighbourhood_id: str | UUID | None = None,
        price_range_id: str | UUID | None = None,
        cuisine_type_ids: object | None = None,
        creator_user_id: UUID | None = None,
    ) -> dict:
        name = name.strip()
        address = address.strip()
        phone = phone.strip()
        email = (email or "").strip() or None
        description = (description or "").strip() or None

        if not name:
            raise ValidationError("Name is required.", {"name": "Cannot be empty"})

        cid = _parse_uuid(city_id, "cityId")
        nid = _parse_uuid_opt(neighbourhood_id)
        prid = _parse_uuid_opt(price_range_id)
        cids: list[UUID] | None = None
        if cuisine_type_ids is not None:
            cids = _parse_uuid_list(cuisine_type_ids, "cuisineTypeIds")

        try:
            restaurant = RestaurantRepository.create(
                name=name,
                address=address,
                phone=phone,
                city_id=cid,
                email=email,
                description=description,
                neighbourhood_id=nid,
                price_range_id=prid,
                cuisine_type_ids=cids,
                auto_commit=False,
            )

            if creator_user_id is not None:
                RestaurantAdminRepository.add_if_missing(
                    user_id=creator_user_id,
                    restaurant_id=restaurant.id,
                    auto_commit=False,
                )
                user = UserRepository.get_by_id(creator_user_id)
                if user and user.role == UserRole.CUSTOMER:
                    UserRepository.update_role(
                        user_id=creator_user_id,
                        role=UserRole.RESTAURANT_ADMIN,
                        auto_commit=False,
                    )

            db.session.commit()
        except Exception:
            db.session.rollback()
            raise

        logger.info(f"Restaurant created: id={restaurant.id} name={restaurant.name}")
        return RestaurantService._restaurant_payload(restaurant)

    @staticmethod
    def update(
        restaurant_id: UUID,
        name: str,
        address: str,
        phone: str,
        city_id: str | UUID,
        email: str | None = None,
        description: str | None = None,
        neighbourhood_id: object | str | UUID | None = _UNSET,
        price_range_id: object | str | UUID | None = _UNSET,
        cuisine_type_ids: object = _UNSET,
    ) -> dict:
        restaurant = RestaurantRepository.get_by_id(restaurant_id)
        if not restaurant:
            raise NotFoundError(f"Restaurant with id={restaurant_id} not found.")

        name = name.strip()
        address = address.strip()
        phone = phone.strip()
        email = (email or "").strip() or None
        description = (description or "").strip() or None

        if not name:
            raise ValidationError("Name is required.", {"name": "Cannot be empty"})

        cid = _parse_uuid(city_id, "cityId")
        patch_n = neighbourhood_id is not _UNSET
        patch_p = price_range_id is not _UNSET
        nid = _parse_uuid_opt(neighbourhood_id) if patch_n else None
        prid = _parse_uuid_opt(price_range_id) if patch_p else None

        cuisine_arg: object = CUISINE_UNSET
        if cuisine_type_ids is not _UNSET:
            if cuisine_type_ids is None:
                cuisine_arg = []
            else:
                cuisine_arg = _parse_uuid_list(cuisine_type_ids, "cuisineTypeIds")

        restaurant = RestaurantRepository.update(
            restaurant=restaurant,
            name=name,
            address=address,
            phone=phone,
            email=email,
            description=description,
            city_id=cid,
            neighbourhood_id=nid,
            price_range_id=prid,
            patch_neighbourhood=patch_n,
            patch_price_range=patch_p,
            cuisine_type_ids=cuisine_arg,
        )
        logger.info(f"Restaurant updated: id={restaurant.id}")
        return RestaurantService._restaurant_payload(restaurant)

    @staticmethod
    def delete(restaurant_id: UUID) -> None:
        restaurant = RestaurantRepository.get_by_id(restaurant_id)
        if not restaurant:
            raise NotFoundError(f"Restaurant with id={restaurant_id} not found.")
        RestaurantRepository.delete(restaurant)
        logger.info(f"Restaurant deleted: id={restaurant_id}")

    @staticmethod
    def upload_photo(restaurant_id: UUID, file_storage) -> dict:
        if not file_storage:
            raise ValidationError("No file provided.", {"file": "Missing file"})

        mime_type = (getattr(file_storage, "mimetype", None) or "").lower()
        if mime_type not in RestaurantService._ALLOWED_PHOTO_MIME_TYPES:
            raise ValidationError(
                "Invalid file format.",
                {
                    "file": (
                        "Allowed MIME types are image/jpeg, image/png, image/webp."
                    )
                },
            )

        restaurant = RestaurantRepository.get_by_id(restaurant_id)
        if not restaurant:
            raise NotFoundError(f"Restaurant with id={restaurant_id} not found.")
        photo_url = S3Client.get().upload_restaurant_photo(file_storage, str(restaurant_id))
        restaurant = RestaurantRepository.update_photo(restaurant, photo_url)
        logger.info(f"Restaurant photo uploaded: id={restaurant_id}")
        return RestaurantService._restaurant_payload(restaurant)
