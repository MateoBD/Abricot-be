import logging
from uuid import UUID

from app.exceptions.errors import NotFoundError, UnauthorizedError, ValidationError
from app.extensions import bcrypt
from app.repositories.order_repository import OrderRepository
from app.repositories.reservation_repository import ReservationRepository
from app.repositories.restaurant_admin_repository import RestaurantAdminRepository
from app.repositories.restaurant_repository import RestaurantRepository
from app.repositories.restaurant_review_repository import RestaurantReviewRepository
from app.repositories.user_repository import UserRepository
from app.utils.list_envelope import list_envelope, paginated_list_envelope

logger = logging.getLogger(__name__)


def _reservation_payload(reservation) -> dict:
    return {
        "id": str(reservation.id),
        "restaurantId": str(reservation.restaurant_id),
        "userId": str(reservation.user_id) if reservation.user_id else None,
        "guestName": reservation.guest_name,
        "guestPhone": reservation.guest_phone,
        "guestEmail": reservation.guest_email,
        "source": reservation.source.value,
        "partySize": reservation.party_size,
        "date": reservation.date.isoformat(),
        "timeSlot": reservation.time_slot.isoformat(),
        "status": reservation.status.value,
        "notes": reservation.notes,
        "confirmationCode": reservation.confirmation_code,
        "createdAt": reservation.created_at.isoformat(),
    }


def _order_payload(order) -> dict:
    return {
        "id": str(order.id),
        "restaurantId": str(order.restaurant_id),
        "userId": str(order.user_id),
        "status": order.status.value,
        "totalAmount": f"{order.total_amount:.2f}",
        "notes": order.notes,
        "estimatedReadyAt": order.estimated_ready_at.isoformat()
        if order.estimated_ready_at
        else None,
        "createdAt": order.created_at.isoformat(),
    }


def _restaurant_payload(
    restaurant,
    cuisine_ids: list[UUID],
    review_stats: dict[UUID, tuple[float | None, int]] | None = None,
) -> dict:
    payload = restaurant.to_dict()
    payload["cuisineTypeIds"] = [str(cid) for cid in cuisine_ids]
    rid = restaurant.id
    if review_stats is None:
        review_stats = RestaurantReviewRepository.get_stats_by_restaurant_ids([rid])
    avg, rc = review_stats.get(rid, (None, 0))
    payload["averageScore"] = avg
    payload["reviewCount"] = rc
    return payload


class UserService:
    @staticmethod
    def get_profile(user_id: UUID) -> dict:
        user = UserRepository.get_by_id(user_id)
        if not user:
            raise NotFoundError(f"User with id={user_id} not found.")
        return user.to_dict()

    @staticmethod
    def update_profile(user_id: UUID, name: str, surname: str) -> dict:
        user = UserRepository.get_by_id(user_id)
        if not user:
            raise NotFoundError(f"User with id={user_id} not found.")

        name = name.strip()
        surname = surname.strip()

        if not name:
            raise ValidationError("Name is required.", {"name": "Cannot be empty"})
        if not surname:
            raise ValidationError("Surname is required.", {"surname": "Cannot be empty"})

        user = UserRepository.update_profile(user, name=name, surname=surname)
        logger.info("User profile updated: id=%s", user.id)
        return user.to_dict()

    @staticmethod
    def change_password(user_id: UUID, current_password: str, new_password: str) -> None:
        user = UserRepository.get_by_id(user_id)
        if not user:
            raise NotFoundError(f"User with id={user_id} not found.")

        if not bcrypt.check_password_hash(user.password_hash, current_password):
            raise UnauthorizedError(
                "Current password is incorrect.",
                {"currentPassword": "Invalid password"},
            )

        if len(new_password) < 8:
            raise ValidationError(
                "New password must be at least 8 characters.",
                {"newPassword": "Too short"},
            )

        new_hash = bcrypt.generate_password_hash(new_password).decode("utf-8")
        UserRepository.update_password_hash(user, password_hash=new_hash)
        logger.info("User password changed: id=%s", user.id)

    @staticmethod
    def get_my_reservations(user_id: UUID, page: int = 1, per_page: int = 20) -> dict:
        user = UserRepository.get_by_id(user_id)
        if not user:
            raise NotFoundError(f"User with id={user_id} not found.")

        rows, total = ReservationRepository.list_for_user(
            user_id=user_id,
            page=page,
            per_page=per_page,
        )
        return paginated_list_envelope(
            [_reservation_payload(row) for row in rows],
            total=total,
            page=max(page, 1),
            per_page=max(min(per_page, 100), 1),
        )

    @staticmethod
    def get_my_orders(user_id: UUID, page: int = 1, per_page: int = 20) -> dict:
        user = UserRepository.get_by_id(user_id)
        if not user:
            raise NotFoundError(f"User with id={user_id} not found.")

        rows, total = OrderRepository.list_for_user(
            user_id=user_id,
            page=page,
            per_page=per_page,
        )
        return paginated_list_envelope(
            [_order_payload(row) for row in rows],
            total=total,
            page=max(page, 1),
            per_page=max(min(per_page, 100), 1),
        )

    @staticmethod
    def get_my_restaurants(user_id: UUID) -> dict:
        user = UserRepository.get_by_id(user_id)
        if not user:
            raise NotFoundError(f"User with id={user_id} not found.")

        restaurant_ids = RestaurantAdminRepository.get_restaurants_for_user(user_id)
        restaurants = RestaurantRepository.get_by_ids(restaurant_ids)
        cuisine_map = RestaurantRepository.get_cuisine_type_ids_bulk(
            [restaurant.id for restaurant in restaurants]
        )
        rstats = RestaurantReviewRepository.get_stats_by_restaurant_ids(
            [r.id for r in restaurants]
        )
        data = [
            _restaurant_payload(
                restaurant, cuisine_map.get(restaurant.id, []), rstats
            )
            for restaurant in restaurants
        ]
        return list_envelope(data)
