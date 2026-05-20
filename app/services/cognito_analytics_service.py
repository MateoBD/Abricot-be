from uuid import UUID

from app.exceptions.errors import ValidationError
from app.services.analytics_service import AnalyticsService
from app.services.cognito_authorization_service import CognitoAuthorizationService


def _parse_uuid(value: str | UUID | None, field: str) -> UUID:
    if value is None or value == "":
        raise ValidationError(f"{field} is required.", {field: "Required"})
    if isinstance(value, UUID):
        return value
    try:
        return UUID(str(value))
    except ValueError as error:
        raise ValidationError("Invalid identifier format.", {field: "Invalid UUID"}) from error


class CognitoAnalyticsService:
    @staticmethod
    def get_report(
        *,
        restaurant_id: str | UUID,
        cognito_sub: str | None,
        query: dict[str, str],
        is_cognito_admin: bool = False,
    ) -> dict:
        restaurant_uuid = _parse_uuid(restaurant_id, "restaurantId")
        principal = CognitoAuthorizationService.principal_user(cognito_sub)
        CognitoAuthorizationService.require_restaurant_admin(
            principal=principal,
            restaurant_id=restaurant_uuid,
            is_cognito_admin=is_cognito_admin,
        )
        report = str(query.get("report", "")).strip().lower()
        if report == "orders":
            return AnalyticsService.get_orders_report(
                restaurant_id=restaurant_uuid,
                start=query.get("start"),
                end=query.get("end"),
            )
        if report == "metrics":
            return AnalyticsService.get_general_metrics(
                restaurant_id=restaurant_uuid,
                start=query.get("start"),
                end=query.get("end"),
            )
        raise ValidationError(
            "Invalid analytics report.",
            {"report": "Must be one of: orders, metrics"},
        )
