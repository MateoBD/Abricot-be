import json
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
from app.services.sns_user_notification_service import (
    SnsUserNotificationService,
    publish_user_notification,
)


USER_ID = UUID("00000000-0000-0000-0000-000000000101")
RESTAURANT_ID = UUID("00000000-0000-0000-0000-000000000202")
RESERVATION_ID = UUID("00000000-0000-0000-0000-000000000303")
# All users share ONE notification topic; targeting is by filter policy.
SHARED_TOPIC_ARN = "arn:aws:sns:us-east-1:123:abricot-email-notifications"


def _user(status=None):
    return UserModel(
        id=USER_ID,
        email="customer@example.com",
        password_hash="COGNITO_ONLY:test",  # noqa: S106
        name="Customer",
        surname="Test",
        role=UserRole.CUSTOMER,
        cognito_sub="sub-123",
        sns_topic_arn=SHARED_TOPIC_ARN,
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


def _patch_shared_topic(monkeypatch):
    monkeypatch.setattr(sns_module, "_shared_topic_arn", lambda: SHARED_TOPIC_ARN)


def test_ensure_subscription_subscribes_to_shared_topic_with_user_filter_policy(monkeypatch):
    user = _user()
    user.sns_topic_arn = None
    user.sns_subscription_arn = None
    user.sns_subscription_status = None
    calls = {}

    class FakeSns:
        def subscribe(self, *, TopicArn, Protocol, Endpoint, Attributes, ReturnSubscriptionArn):
            calls["subscribe"] = {
                "TopicArn": TopicArn,
                "Protocol": Protocol,
                "Endpoint": Endpoint,
                "Attributes": Attributes,
                "ReturnSubscriptionArn": ReturnSubscriptionArn,
            }
            return {"SubscriptionArn": "PendingConfirmation"}

    _patch_update(monkeypatch)
    _patch_shared_topic(monkeypatch)
    monkeypatch.setattr(sns_module, "_sns_client", lambda: FakeSns())

    result = SnsUserNotificationService.ensure_subscription(user)

    # Subscribes the user's EMAIL to the ONE shared topic...
    assert calls["subscribe"]["TopicArn"] == SHARED_TOPIC_ARN
    assert calls["subscribe"]["Protocol"] == "email"
    assert calls["subscribe"]["Endpoint"] == "customer@example.com"
    assert calls["subscribe"]["ReturnSubscriptionArn"] is True
    # ...with a filter policy that targets exactly this user's id.
    assert json.loads(calls["subscribe"]["Attributes"]["FilterPolicy"]) == {
        "userId": [str(USER_ID)]
    }
    # The persisted topic ARN is the shared topic (not a per-user topic).
    assert result.sns_topic_arn == SHARED_TOPIC_ARN
    assert result.sns_subscription_status == UserSnsSubscriptionStatus.PENDING_CONFIRMATION


def test_publish_user_notification_always_sets_user_id_attribute(monkeypatch):
    captured = {}

    class FakeSns:
        def publish(self, **kwargs):
            captured.update(kwargs)
            return {"MessageId": "mid-1"}

    _patch_shared_topic(monkeypatch)
    monkeypatch.setattr(sns_module, "_sns_client", lambda: FakeSns())

    message_id = publish_user_notification(USER_ID, "Asunto", "Cuerpo")

    assert message_id == "mid-1"
    assert captured["TopicArn"] == SHARED_TOPIC_ARN
    # The userId attribute is mandatory: a filter policy drops the message
    # silently if it is missing.
    assert captured["MessageAttributes"]["userId"] == {
        "DataType": "String",
        "StringValue": str(USER_ID),
    }


def test_cognito_provisioning_provisions_and_persists_sns_for_new_user(monkeypatch):
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

    provisioned = {}

    def ensure_subscription(created_user):
        provisioned["user_id"] = created_user.id
        created_user.sns_topic_arn = SHARED_TOPIC_ARN
        created_user.sns_subscription_arn = "PendingConfirmation"
        created_user.sns_subscription_status = UserSnsSubscriptionStatus.PENDING_CONFIRMATION
        created_user.sns_subscription_requested_at = datetime.now(UTC)
        return created_user

    monkeypatch.setattr(
        cognito_user_module.SnsUserNotificationService,
        "ensure_subscription",
        ensure_subscription,
    )

    result = CognitoUserService.provision_user(
        cognito_sub="sub-123",
        email="customer@example.com",
        account_type=AccountType.CUSTOMER,
    )

    assert result.created is True
    # signup MUST subscribe the user to the shared topic
    assert provisioned["user_id"] == USER_ID
    # ...and the POST /users response MUST carry the persisted ARNs/status, not nulls
    assert result.user["snsTopicArn"] == SHARED_TOPIC_ARN
    assert result.user["snsSubscriptionArn"] == "PendingConfirmation"
    assert result.user["snsSubscriptionStatus"] == "PENDING_CONFIRMATION"
    assert result.user["snsSubscriptionRequestedAt"] is not None


def test_ensure_subscription_failure_surfaces_failed_status_not_null(monkeypatch):
    user = _user()
    user.sns_topic_arn = None
    user.sns_subscription_arn = None
    user.sns_subscription_status = None

    class ExplodingSns:
        def subscribe(self, **kwargs):
            raise RuntimeError("AccessDenied: not authorized to perform sns:Subscribe")

    _patch_update(monkeypatch)
    _patch_shared_topic(monkeypatch)
    monkeypatch.setattr(sns_module, "_sns_client", lambda: ExplodingSns())

    # Best-effort: a provisioning failure must NOT raise into signup...
    result = SnsUserNotificationService.ensure_subscription(user)

    # ...and must be surfaced as FAILED, not swallowed into a null status.
    assert result.sns_subscription_status is not None
    assert result.sns_subscription_status == UserSnsSubscriptionStatus.FAILED


def test_refresh_subscription_marks_confirmed_when_sns_has_real_arn(monkeypatch):
    user = _user(UserSnsSubscriptionStatus.PENDING_CONFIRMATION)

    class FakePaginator:
        def paginate(self, *, TopicArn):
            assert TopicArn == SHARED_TOPIC_ARN
            return [
                {
                    "Subscriptions": [
                        {
                            "Protocol": "email",
                            "Endpoint": "customer@example.com",
                            "SubscriptionArn": "arn:aws:sns:us-east-1:123:abricot-email-notifications:sub-id",
                        }
                    ]
                }
            ]

    class FakeSns:
        def get_paginator(self, name):
            assert name == "list_subscriptions_by_topic"
            return FakePaginator()

    _patch_update(monkeypatch)
    _patch_shared_topic(monkeypatch)
    monkeypatch.setattr(sns_module, "_sns_client", lambda: FakeSns())

    result = SnsUserNotificationService.refresh_subscription_status(user)

    assert result.sns_subscription_status == UserSnsSubscriptionStatus.CONFIRMED
    assert result.sns_subscription_arn == "arn:aws:sns:us-east-1:123:abricot-email-notifications:sub-id"


def _refresh_with_subscriptions(monkeypatch, user, subscriptions):
    class FakePaginator:
        def paginate(self, *, TopicArn):
            assert TopicArn == SHARED_TOPIC_ARN
            return [{"Subscriptions": subscriptions}]

    class FakeSns:
        def get_paginator(self, name):
            assert name == "list_subscriptions_by_topic"
            return FakePaginator()

    _patch_update(monkeypatch)
    _patch_shared_topic(monkeypatch)
    monkeypatch.setattr(sns_module, "_sns_client", lambda: FakeSns())
    return SnsUserNotificationService.refresh_subscription_status(user)


def test_refresh_prefers_confirmed_when_stale_pending_duplicate_listed_first(monkeypatch):
    # AWS may return a stale "PendingConfirmation" duplicate BEFORE the real
    # confirmed subscription for the same email. First-match-wins would wrongly
    # report PENDING and leave the user blocked.
    user = _user(UserSnsSubscriptionStatus.PENDING_CONFIRMATION)
    result = _refresh_with_subscriptions(
        monkeypatch,
        user,
        [
            {
                "Protocol": "email",
                "Endpoint": "customer@example.com",
                "SubscriptionArn": "PendingConfirmation",
            },
            {
                "Protocol": "email",
                "Endpoint": "customer@example.com",
                "SubscriptionArn": "arn:aws:sns:us-east-1:123:abricot-email-notifications:sub-id",
            },
        ],
    )

    assert result.sns_subscription_status == UserSnsSubscriptionStatus.CONFIRMED
    assert result.sns_subscription_arn == "arn:aws:sns:us-east-1:123:abricot-email-notifications:sub-id"


def test_refresh_ignores_other_users_subscriptions_on_shared_topic(monkeypatch):
    # The shared topic lists EVERY user's subscription; only this user's email
    # endpoint counts. A confirmed sub for a different email must not confirm us.
    user = _user(UserSnsSubscriptionStatus.PENDING_CONFIRMATION)
    result = _refresh_with_subscriptions(
        monkeypatch,
        user,
        [
            {
                "Protocol": "email",
                "Endpoint": "someone-else@example.com",
                "SubscriptionArn": "arn:aws:sns:us-east-1:123:abricot-email-notifications:other",
            },
            {
                "Protocol": "email",
                "Endpoint": "customer@example.com",
                "SubscriptionArn": "PendingConfirmation",
            },
        ],
    )

    assert result.sns_subscription_status == UserSnsSubscriptionStatus.PENDING_CONFIRMATION


def test_refresh_stays_pending_when_no_confirmed_subscription(monkeypatch):
    user = _user(UserSnsSubscriptionStatus.PENDING_CONFIRMATION)
    result = _refresh_with_subscriptions(
        monkeypatch,
        user,
        [
            {
                "Protocol": "email",
                "Endpoint": "customer@example.com",
                "SubscriptionArn": "PendingConfirmation",
            }
        ],
    )

    assert result.sns_subscription_status == UserSnsSubscriptionStatus.PENDING_CONFIRMATION
    assert result.sns_subscription_arn == "PendingConfirmation"


def test_refresh_treats_deleted_arn_as_not_confirmed(monkeypatch):
    user = _user(UserSnsSubscriptionStatus.PENDING_CONFIRMATION)
    result = _refresh_with_subscriptions(
        monkeypatch,
        user,
        [
            {
                "Protocol": "email",
                "Endpoint": "customer@example.com",
                "SubscriptionArn": "Deleted",
            }
        ],
    )

    assert result.sns_subscription_status == UserSnsSubscriptionStatus.PENDING_CONFIRMATION


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


def test_online_reservation_publishes_only_for_principal_when_confirmed(monkeypatch):
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


def test_sns_reservation_confirmation_publishes_to_shared_topic_with_user_filter(monkeypatch):
    user = _user(UserSnsSubscriptionStatus.CONFIRMED)
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
            return {"MessageId": "mid-2"}

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
    _patch_shared_topic(monkeypatch)
    monkeypatch.setattr(sns_module, "_sns_client", lambda: FakeSns())

    SnsUserNotificationService.publish_reservation_confirmation(RESERVATION_ID)

    assert publishes[0]["TopicArn"] == SHARED_TOPIC_ARN
    assert publishes[0]["MessageAttributes"]["userId"]["StringValue"] == str(USER_ID)
    assert "ABCD1234" in publishes[0]["Message"]
    assert "Abricot" in publishes[0]["Message"]


def test_sns_reservation_confirmation_skipped_when_not_confirmed(monkeypatch):
    # The synchronous path must verify a CONFIRMED subscription before publishing.
    user = _user(UserSnsSubscriptionStatus.PENDING_CONFIRMATION)
    reservation = ReservationModel(
        id=RESERVATION_ID,
        restaurant_id=RESTAURANT_ID,
        user_id=USER_ID,
        party_size=2,
        date=date(2026, 6, 1),
        time_slot=time(21, 0),
        confirmation_code="ZZZZ9999",
    )
    publishes = []

    class FakeSns:
        def publish(self, **kwargs):
            publishes.append(kwargs)
            return {"MessageId": "should-not-happen"}

    monkeypatch.setattr(
        sns_module.ReservationRepository,
        "get_by_id",
        lambda reservation_id: reservation,
    )
    monkeypatch.setattr(sns_module.UserRepository, "get_by_id", lambda user_id: user)
    _patch_shared_topic(monkeypatch)
    monkeypatch.setattr(sns_module, "_sns_client", lambda: FakeSns())

    SnsUserNotificationService.publish_reservation_confirmation(RESERVATION_ID)

    assert publishes == []
