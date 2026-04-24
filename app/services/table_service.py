import logging
from datetime import date
from uuid import UUID

from app.exceptions.errors import ConflictError, NotFoundError, ValidationError
from app.models.table import TableModel
from app.repositories.reservation_repository import ReservationRepository
from app.repositories.restaurant_repository import RestaurantRepository
from app.repositories.table_repository import TableRepository
from app.utils.list_envelope import list_envelope

logger = logging.getLogger(__name__)


class TableService:
    @staticmethod
    def get_all(restaurant_id: UUID) -> dict:
        if not RestaurantRepository.get_by_id(restaurant_id):
            raise NotFoundError(f"Restaurant with id={restaurant_id} not found.")
        tables = TableRepository.get_all(restaurant_id)
        return list_envelope([t.to_dict() for t in tables])

    @staticmethod
    def get_by_id(restaurant_id: UUID, table_id: UUID) -> dict:
        if not RestaurantRepository.get_by_id(restaurant_id):
            raise NotFoundError(f"Restaurant with id={restaurant_id} not found.")
        table = TableRepository.get_by_id(restaurant_id, table_id)
        if not table:
            raise NotFoundError(f"Table with id={table_id} not found.")
        return table.to_dict()

    @staticmethod
    def create(
        restaurant_id: UUID,
        number: int,
        capacity: int,
        name: str | None = None,
        is_joinable: bool = True,
    ) -> dict:
        if not RestaurantRepository.get_by_id(restaurant_id):
            raise NotFoundError(f"Restaurant with id={restaurant_id} not found.")
        if capacity < 1:
            raise ValidationError("Capacity must be at least 1.", {"capacity": "Must be >= 1"})
        table = TableModel(
            restaurant_id=restaurant_id,
            number=number,
            capacity=capacity,
            name=name,
            is_joinable=is_joinable,
        )
        try:
            saved = TableRepository.save(table)
        except Exception:
            raise ConflictError(f"Table number {number} already exists for this restaurant.")
        logger.info("Table created: restaurant_id=%s number=%s", restaurant_id, number)
        return saved.to_dict()

    @staticmethod
    def create_bulk(restaurant_id: UUID, groups: list[dict]) -> dict:
        if not RestaurantRepository.get_by_id(restaurant_id):
            raise NotFoundError(f"Restaurant with id={restaurant_id} not found.")
        if not groups:
            raise ValidationError("At least one group is required.", {"groups": "Cannot be empty"})

        current_max = TableRepository.get_max_number(restaurant_id) or 0
        tables: list[TableModel] = []
        next_number = current_max + 1

        for i, group in enumerate(groups):
            qty = group.get("quantity", 1)
            capacity = group.get("capacity")
            is_joinable = group.get("isJoinable", True)
            if not isinstance(qty, int) or qty < 1:
                raise ValidationError(
                    f"Group {i}: quantity must be a positive integer.",
                    {"quantity": "Must be >= 1"},
                )
            if not isinstance(capacity, int) or capacity < 1:
                raise ValidationError(
                    f"Group {i}: capacity must be a positive integer.",
                    {"capacity": "Must be >= 1"},
                )
            for _ in range(qty):
                tables.append(
                    TableModel(
                        restaurant_id=restaurant_id,
                        number=next_number,
                        capacity=capacity,
                        is_joinable=is_joinable,
                    )
                )
                next_number += 1

        created = TableRepository.bulk_insert(tables)
        logger.info(
            "Tables bulk created: restaurant_id=%s count=%s", restaurant_id, len(created)
        )
        return list_envelope([t.to_dict() for t in created])

    @staticmethod
    def update(
        restaurant_id: UUID,
        table_id: UUID,
        number: int,
        capacity: int,
        name: str | None = None,
        is_joinable: bool = True,
        is_active: bool = True,
    ) -> dict:
        if not RestaurantRepository.get_by_id(restaurant_id):
            raise NotFoundError(f"Restaurant with id={restaurant_id} not found.")
        table = TableRepository.get_by_id(restaurant_id, table_id)
        if not table:
            raise NotFoundError(f"Table with id={table_id} not found.")
        if capacity < 1:
            raise ValidationError("Capacity must be at least 1.", {"capacity": "Must be >= 1"})
        table.number = number
        table.capacity = capacity
        table.name = name
        table.is_joinable = is_joinable
        table.is_active = is_active
        TableRepository.save(table)
        logger.info("Table updated: table_id=%s", table_id)
        return table.to_dict()

    @staticmethod
    def delete(restaurant_id: UUID, table_id: UUID) -> None:
        if not RestaurantRepository.get_by_id(restaurant_id):
            raise NotFoundError(f"Restaurant with id={restaurant_id} not found.")
        table = TableRepository.get_by_id(restaurant_id, table_id)
        if not table:
            raise NotFoundError(f"Table with id={table_id} not found.")
        today = date.today()
        if ReservationRepository.table_has_future_confirmed_reservations(table_id, today):
            raise ConflictError(
                "Cannot delete a table that has future confirmed reservations.",
                {"tableId": "Has future reservations"},
            )
        TableRepository.delete(table)
        logger.info("Table deleted: table_id=%s", table_id)

    @staticmethod
    def get_total_capacity(restaurant_id: UUID) -> int:
        if not RestaurantRepository.get_by_id(restaurant_id):
            raise NotFoundError(f"Restaurant with id={restaurant_id} not found.")
        tables = TableRepository.get_active(restaurant_id)
        return sum(t.capacity for t in tables)
