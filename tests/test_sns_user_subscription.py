from datetime import UTC, date, datetime, time
from uuid import UUID

import pytest

import app.services.cognito_reservation_service as cognito_reservation_module
import app.services.cognito_user_service as cognito_user_module
import app.services.sns_user_notification_service as sns_module
from app.exceptions.errors import ForbiddenError
from app.models.enums import UserRole, UserSnsSubscriptionStatus
from app.models.reservation import ReservationModel
from app.models.restaurant import RestaurantModel
from app.models.user import UserModel
from app.services.cognito_user_service import AccountType, CognitoUserService
from app.services.cognito_reservation_service import CognitoReservationService
from app.services.sns_user_notification_service import SnsUserNotificationService


USER_ID = UUID("00000000-0000-0000-0000-000000000101")
RESTAURANT_ID = UUID("00000000-0000-0000-0000-000000000202")
RESERVATION_ID = UUID("00000000-0000-0000-0000-000000000303")


def _user(status=None):
    return UserModel(
        id=USER_ID,
        email="customer@example.com",
        password_hash="COGNITO_ONLY:test",  # noqa: S106
        name="Customer",
        surname="Test",
        role=UserRole.CUSTOMER,
        cognito_sub="sub-123",
        sns_topic_arn="arn:aws:sns:us-east-1:123:abricot-user",
        sns_subscription_arn="PendingConfirmation",
        sns_subscription_status=status,
        sns_subscription_requested_at=datetime.now(UTC),
        created_at=datetime.now(UTC),
    )


def _patch_update(monkeypatch):
    def update(user, *, topic_arn, subscription_arn, status, requested_at):
        user.sns_topic_arn = topic_arn
        user.sns_subscription_arn = subscription_arn
        user.sns_subscription_status = status
        user.sns_subscription_requested_at = requested_at
        return user

    monkeypatch.setattr(sns_module.UserRepository, "update_sns_subscription", update)


def test_ensure_subscription_creates_user_topic_and_pending_subscription(monkeypatch):
    user = _user()
    user.sns_topic_arn = None
    user.sns_subscription_arn = None
    user.sns_subscription_status = None
    calls = {}

    class FakeSns:
        def create_topic(self, *, Name):
            calls["topic_name"] = Name
            return {"TopicArn": "arn:aws:sns:us-east-1:123:abricot-user-topic"}

        def subscribe(self, *, TopicArn, Protocol, Endpoint, ReturnSubscriptionArn):
            calls["subscribe"] = {
                "TopicArn": TopicArn,
                "Protocol": Protocol,
                "Endpoint": Endpoint,
                "ReturnSubscriptionArn": ReturnSubscriptionArn,
            }
            return {"SubscriptionArn": "PendingConfirmation"}

    _patch_update(monkeypatch)
    monkeypatch.setattr(sns_module, "_sns_client", lambda: FakeSns())
    monkeypatch.setattr(sns_module, "_topic_prefix", lambda: "abricot-user")

    result = SnsUserNotificationService.ensure_subscription(user)

    assert calls["topic_name"] == f"abricot-user-{USER_ID}-notifications"
    assert calls["subscribe"] == {
        "TopicArn": "arn:aws:sns:us-east-1:123:abricot-user-topic",
        "Protocol": "email",
        "Endpoint": "customer@example.com",
        "ReturnSubscriptionArn": True,
    }
    assert result.sns_subscription_status == UserSnsSubscriptionStatus.PENDING_CONFIRMATION


def test_cognito_provisioning_does_not_block_on_sns_subscription(monkeypatch):
    user = _user(None)
    user.sns_topic_arn = None
    user.sns_subscription_arn = None
    user.sns_subscription_status = None

    monkeypatch.setattr(
        cognito_user_module.UserRepository,
        "get_by_cognito_sub",
        lambda cognito_sub: None,
    )
    monkeypatch.setattr(
        cognito_user_module.UserRepository,
        "get_by_email_case_insensitive",
        lambda email: None,
    )
    monkeypatch.setattr(cognito_user_module.UserRepository, "create", lambda **kwargs: user)

    monkeypatch.setattr(
        cognito_user_module.SnsUserNotificationService,
        "ensure_subscription",
        lambda created_user: pytest.fail("SNS must not block user provisioning"),
    )

    result = CognitoUserService.provision_user(
        cognito_sub="sub-123",
        email="customer@example.com",
        account_type=AccountType.CUSTOMER,
    )

    assert result.created is True
    assert result.user["id"] == str(USER_ID)
    assert result.user["snsSubscriptionStatus"] is None


def test_refresh_subscription_marks_confirmed_when_sns_has_real_arn(monkeypatch):
    user = _user(UserSnsSubscriptionStatus.PENDING_CONFIRMATION)

    class FakePaginator:
        def paginate(self, *, TopicArn):
            assert TopicArn == user.sns_topic_arn
            return [
                {
                    "Subscriptions": [
                        {
                            "Protocol": "email",
                            "Endpoint": "customer@example.com",
                            "SubscriptionArn": "arn:aws:sns:us-east-1:123:sub-id",
                        }
                    ]
                }
            ]

    class FakeSns:
        def get_paginator(self, name):
            assert name == "list_subscriptions_by_topic"
            return FakePaginator()

    _patch_update(monkeypatch)
    monkeypatch.setattr(sns_module, "_sns_client", lambda: FakeSns())

    result = SnsUserNotificationService.refresh_subscription_status(user)

    assert result.sns_subscription_status == UserSnsSubscriptionStatus.CONFIRMED
    assert result.sns_subscription_arn == "arn:aws:sns:us-east-1:123:sub-id"


def test_online_reservation_blocks_until_sns_confirmed(monkeypatch):
    user = _user(UserSnsSubscriptionStatus.PENDING_CONFIRMATION)
    monkeypatch.setattr(
        cognito_reservation_module.CognitoAuthorizationService,
        "principal_user",
        lambda cognito_sub: user,
    )
    monkeypatch.setattr(
        cognito_reservation_module.SnsUserNotificationService,
        "refresh_subscription_status",
        lambda principal: principal,
    )

    with pytest.raises(ForbiddenError) as exc:
        CognitoReservationService.create(
            restaurant_id=RESTAURANT_ID,
            cognito_sub="sub-123",
            body={"date": "2026-06-01", "timeSlot": "21:00", "partySize": 2},
        )

    assert exc.value.public_message == "Confirma la suscripcion de email antes de reservar."


def test_online_reservation_publishes_only_principal_topic_when_confirmed(monkeypatch):
    user = _user(UserSnsSubscriptionStatus.CONFIRMED)
    created_payload = {"id": str(RESERVATION_ID), "restaurantId": str(RESTAURANT_ID)}
    published = []

    monkeypatch.setattr(
        cognito_reservation_module.CognitoAuthorizationService,
        "principal_user",
        lambda cognito_sub: user,
    )
    monkeypatch.setattr(
        cognito_reservation_module.SnsUserNotificationService,
        "refresh_subscription_status",
        lambda principal: principal,
    )
    monkeypatch.setattr(
        cognito_reservation_module.ReservationService,
        "create",
        lambda **kwargs: created_payload,
    )
    monkeypatch.setattr(
        cognito_reservation_module.SnsUserNotificationService,
        "publish_reservation_confirmation",
        lambda reservation_id: published.append(reservation_id),
    )

    result = CognitoReservationService.create(
        restaurant_id=RESTAURANT_ID,
        cognito_sub="sub-123",
        body={"date": "2026-06-01", "timeSlot": "21:00", "partySize": 2},
    )

    assert result == created_payload
    assert published == [RESERVATION_ID]


def test_sns_reservation_confirmation_publishes_to_user_topic(monkeypatch):
    user = _user(UserSnsSubscriptionStatus.CONFIRMED)
    user.sns_topic_arn = "arn:aws:sns:us-east-1:123:user-a-topic"
    reservation = ReservationModel(
        id=RESERVATION_ID,
        restaurant_id=RESTAURANT_ID,
        user_id=USER_ID,
        party_size=4,
        date=date(2026, 6, 1),
        time_slot=time(21, 0),
        confirmation_code="ABCD1234",
    )
    restaurant = RestaurantModel(
        id=RESTAURANT_ID,
        name="Abricot",
        address="Av Test 123",
        city_id=UUID("00000000-0000-0000-0000-000000000404"),
        phone="1234",
    )
    publishes = []

    class FakeSns:
        def publish(self, **kwargs):
            publishes.append(kwargs)

    monkeypatch.setattr(
        sns_module.ReservationRepository,
        "get_by_id",
        lambda reservation_id: reservation,
    )
    monkeypatch.setattr(sns_module.UserRepository, "get_by_id", lambda user_id: user)
    monkeypatch.setattr(
        sns_module.RestaurantRepository,
        "get_by_id",
        lambda restaurant_id: restaurant,
    )
    monkeypatch.setattr(sns_module, "_sns_client", lambda: FakeSns())

    SnsUserNotificationService.publish_reservation_confirmation(RESERVATION_ID)

    assert publishes[0]["TopicArn"] == "arn:aws:sns:us-east-1:123:user-a-topic"
    assert "ABCD1234" in publishes[0]["Message"]
    assert "Abricot" in publishes[0]["Message"]
