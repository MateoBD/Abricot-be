from datetime import date, datetime
from decimal import Decimal
from uuid import UUID

import pytest

import app.services.analytics_service as analytics_service_module
import app.services.cognito_analytics_service as cognito_analytics_module
from app.models.enums import OrderStatus
from app.services.analytics_service import AnalyticsService
from app.services.cognito_analytics_service import CognitoAnalyticsService


RESTAURANT_ID = UUID("00000000-0000-0000-0000-000000000001")


def _stub_restaurant(monkeypatch):
    monkeypatch.setattr(
        analytics_service_module.RestaurantRepository,
        "get_by_id",
        lambda restaurant_id: object(),
    )


def test_orders_report_returns_frontend_contract(monkeypatch):
    _stub_restaurant(monkeypatch)

    def get_orders_report(restaurant_id, start_date, end_date):
        assert restaurant_id == RESTAURANT_ID
        assert start_date == date(2026, 4, 12)
        assert end_date == date(2026, 5, 12)
        return {
            "totalOrders": 42,
            "totalRevenue": Decimal("350000"),
            "averageOrderValue": Decimal("8333.33"),
            "ordersByStatus": [
                {"status": "PENDING", "count": 2},
                {"status": "COMPLETED", "count": 40},
            ],
            "revenueByDay": [
                {
                    "date": "2026-05-10",
                    "revenue": Decimal("75000"),
                    "orders": 9,
                }
            ],
        }

    monkeypatch.setattr(
        analytics_service_module.AnalyticsRepository,
        "get_orders_report",
        get_orders_report,
    )

    assert AnalyticsService.get_orders_report(
        RESTAURANT_ID,
        start="2026-04-12",
        end="2026-05-12",
    ) == {
        "restaurantId": str(RESTAURANT_ID),
        "period": {
            "start": "2026-04-12",
            "end": "2026-05-12",
        },
        "totalOrders": 42,
        "totalRevenue": "350000.00",
        "averageOrderValue": "8333.33",
        "ordersByStatus": [
            {"status": "PENDING", "count": 2},
            {"status": "COMPLETED", "count": 40},
        ],
        "revenueByDay": [
            {"date": "2026-05-10", "revenue": "75000.00", "orders": 9},
        ],
    }


def test_orders_report_keeps_empty_arrays(monkeypatch):
    _stub_restaurant(monkeypatch)
    monkeypatch.setattr(
        analytics_service_module.AnalyticsRepository,
        "get_orders_report",
        lambda **kwargs: {
            "totalOrders": 0,
            "totalRevenue": Decimal("0"),
            "averageOrderValue": Decimal("0"),
            "ordersByStatus": [],
            "revenueByDay": [],
        },
    )

    result = AnalyticsService.get_orders_report(
        RESTAURANT_ID,
        start="2026-04-12",
        end="2026-05-12",
    )

    assert result["ordersByStatus"] == []
    assert result["revenueByDay"] == []


def test_general_metrics_returns_flat_frontend_contract(monkeypatch):
    _stub_restaurant(monkeypatch)
    monkeypatch.setattr(
        analytics_service_module.AnalyticsRepository,
        "get_orders_report",
        lambda **kwargs: {
            "totalOrders": 42,
            "totalRevenue": Decimal("350000"),
            "averageOrderValue": Decimal("8333.33"),
            "ordersByStatus": [],
            "revenueByDay": [],
        },
    )
    monkeypatch.setattr(
        analytics_service_module.AnalyticsRepository,
        "get_reservations_metrics",
        lambda **kwargs: {
            "totalReservations": 31,
            "totalGuests": 118,
            "reservationsByStatus": [
                {"status": "COMPLETED", "count": 24},
                {"status": "CANCELLED", "count": 4},
                {"status": "NO_SHOW", "count": 3},
            ],
        },
    )

    assert AnalyticsService.get_general_metrics(
        RESTAURANT_ID,
        start="2026-04-12",
        end="2026-05-12",
    ) == {
        "restaurantId": str(RESTAURANT_ID),
        "period": {
            "start": "2026-04-12",
            "end": "2026-05-12",
        },
        "totalOrders": 42,
        "totalReservations": 31,
        "totalRevenue": "350000.00",
        "averageOrderValue": "8333.33",
        "totalCovers": 118,
        "completedReservations": 24,
        "cancelledReservations": 4,
        "noShowReservations": 3,
    }


def test_snapshot_dashboard_merges_sealed_snapshots_with_live_today(monkeypatch):
    _stub_restaurant(monkeypatch)
    today = date(2026, 5, 12)

    def get_snapshots_range(restaurant_id, start_date, end_date):
        assert restaurant_id == RESTAURANT_ID
        assert start_date == date(2026, 5, 10)
        # snapshots stop the day BEFORE today (sealed past only).
        assert end_date == date(2026, 5, 11)
        return [
            {
                "date": "2026-05-10",
                "ordersCount": 5,
                "reservationsCount": 2,
                "revenue": Decimal("100"),
            },
            {
                "date": "2026-05-11",
                "ordersCount": 3,
                "reservationsCount": 1,
                "revenue": Decimal("50"),
            },
        ]

    def compute_day_aggregate(restaurant_id, day):
        assert day == today
        return {
            "ordersCount": 4,
            "reservationsCount": 6,
            "revenue": Decimal("200"),
        }

    monkeypatch.setattr(
        analytics_service_module.AnalyticsRepository,
        "get_snapshots_range",
        get_snapshots_range,
    )
    monkeypatch.setattr(
        analytics_service_module.AnalyticsRepository,
        "compute_day_aggregate",
        compute_day_aggregate,
    )

    result = AnalyticsService.get_snapshot_dashboard(
        RESTAURANT_ID,
        start="2026-05-10",
        end="2026-05-12",
        today=today,
    )

    assert result == {
        "restaurantId": str(RESTAURANT_ID),
        "period": {"start": "2026-05-10", "end": "2026-05-12"},
        "totals": {
            "orders": 12,
            "reservations": 9,
            "revenue": "350.00",
        },
        "byDay": [
            {
                "date": "2026-05-10",
                "source": "snapshot",
                "orders": 5,
                "reservations": 2,
                "revenue": "100.00",
            },
            {
                "date": "2026-05-11",
                "source": "snapshot",
                "orders": 3,
                "reservations": 1,
                "revenue": "50.00",
            },
            {
                "date": "2026-05-12",
                "source": "live",
                "orders": 4,
                "reservations": 6,
                "revenue": "200.00",
            },
        ],
    }


def test_snapshot_dashboard_excludes_today_when_outside_range(monkeypatch):
    _stub_restaurant(monkeypatch)
    today = date(2026, 5, 20)

    def get_snapshots_range(restaurant_id, start_date, end_date):
        # End is in the past, so the whole range is sealed; no live day.
        assert end_date == date(2026, 5, 12)
        return [
            {
                "date": "2026-05-12",
                "ordersCount": 7,
                "reservationsCount": 3,
                "revenue": Decimal("70"),
            }
        ]

    def compute_day_aggregate(restaurant_id, day):  # pragma: no cover
        raise AssertionError("live aggregate must not run for past-only ranges")

    monkeypatch.setattr(
        analytics_service_module.AnalyticsRepository,
        "get_snapshots_range",
        get_snapshots_range,
    )
    monkeypatch.setattr(
        analytics_service_module.AnalyticsRepository,
        "compute_day_aggregate",
        compute_day_aggregate,
    )

    result = AnalyticsService.get_snapshot_dashboard(
        RESTAURANT_ID,
        start="2026-05-10",
        end="2026-05-12",
        today=today,
    )

    assert [day["source"] for day in result["byDay"]] == ["snapshot"]
    assert result["totals"] == {
        "orders": 7,
        "reservations": 3,
        "revenue": "70.00",
    }


def test_dispatcher_dashboard_report_returns_snapshot_backed_data(monkeypatch):
    """The deployed dispatcher path (report=dashboard) must return snapshot-backed
    data: sealed snapshots for past days + live SQL for today."""
    _stub_restaurant(monkeypatch)

    # Auth: stub the principal lookup + admin gate the dispatcher enforces.
    monkeypatch.setattr(
        cognito_analytics_module.CognitoAuthorizationService,
        "principal_user",
        lambda cognito_sub: object(),
    )
    monkeypatch.setattr(
        cognito_analytics_module.CognitoAuthorizationService,
        "require_restaurant_admin",
        lambda **kwargs: None,
    )

    today = date(2026, 5, 12)

    class _FixedDateTime:
        @staticmethod
        def now(tz=None):
            return datetime(2026, 5, 12, 10, 0)

    # Pin "today" so the live-day boundary is deterministic.
    monkeypatch.setattr(analytics_service_module, "datetime", _FixedDateTime)

    def get_snapshots_range(restaurant_id, start_date, end_date):
        assert restaurant_id == RESTAURANT_ID
        # snapshots stop the day BEFORE today (sealed past only).
        assert end_date == date(2026, 5, 11)
        return [
            {
                "date": "2026-05-10",
                "ordersCount": 5,
                "reservationsCount": 2,
                "revenue": Decimal("100"),
            },
            {
                "date": "2026-05-11",
                "ordersCount": 3,
                "reservationsCount": 1,
                "revenue": Decimal("50"),
            },
        ]

    def compute_day_aggregate(restaurant_id, day):
        assert day == today
        return {
            "ordersCount": 4,
            "reservationsCount": 6,
            "revenue": Decimal("200"),
        }

    monkeypatch.setattr(
        analytics_service_module.AnalyticsRepository,
        "get_snapshots_range",
        get_snapshots_range,
    )
    monkeypatch.setattr(
        analytics_service_module.AnalyticsRepository,
        "compute_day_aggregate",
        compute_day_aggregate,
    )

    result = CognitoAnalyticsService.get_report(
        restaurant_id=str(RESTAURANT_ID),
        cognito_sub="sub-123",
        query={"report": "dashboard", "start": "2026-05-10", "end": "2026-05-12"},
    )

    # Dispatcher returned get_snapshot_dashboard output (snapshots + live today).
    assert [day["source"] for day in result["byDay"]] == ["snapshot", "snapshot", "live"]
    assert result["totals"] == {
        "orders": 12,
        "reservations": 9,
        "revenue": "350.00",
    }
    assert result["byDay"][2] == {
        "date": "2026-05-12",
        "source": "live",
        "orders": 4,
        "reservations": 6,
        "revenue": "200.00",
    }


def test_dispatcher_rejects_unknown_report_but_keeps_orders_metrics(monkeypatch):
    """orders/metrics still valid; unknown report names rejected with the
    updated allowed-set message."""
    monkeypatch.setattr(
        cognito_analytics_module.CognitoAuthorizationService,
        "principal_user",
        lambda cognito_sub: object(),
    )
    monkeypatch.setattr(
        cognito_analytics_module.CognitoAuthorizationService,
        "require_restaurant_admin",
        lambda **kwargs: None,
    )

    from app.exceptions.errors import ValidationError

    with pytest.raises(ValidationError) as exc:
        CognitoAnalyticsService.get_report(
            restaurant_id=str(RESTAURANT_ID),
            cognito_sub="sub-123",
            query={"report": "bogus"},
        )

    assert exc.value.payload == {"report": "Must be one of: orders, metrics, dashboard"}


def test_order_status_does_not_include_in_preparation():
    assert [status.value for status in OrderStatus] == [
        "PENDING",
        "CONFIRMED",
        "READY",
        "COMPLETED",
        "CANCELLED",
    ]
    with pytest.raises(ValueError):
        OrderStatus("IN_PREPARATION")
