import importlib.util
import os

import pytest

# Load email_worker/handler.py under a UNIQUE module name. Other worker tests
# import a module literally named "handler"; loading from an explicit spec here
# avoids the sys.modules["handler"] collision between the two worker packages.
_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_HANDLER_PATH = os.path.join(_ROOT, "lambdas", "email_worker", "handler.py")
_spec = importlib.util.spec_from_file_location("email_worker_handler", _HANDLER_PATH)
email_worker = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(email_worker)

SHARED_TOPIC_ARN = "arn:aws:sns:us-east-1:123:abricot-email-notifications"
USER_ID = "00000000-0000-0000-0000-0000000000a1"


@pytest.fixture(autouse=True)
def _env(monkeypatch):
    monkeypatch.setattr(email_worker, "_SNS_CLIENT", None)
    monkeypatch.setenv("EMAIL_NOTIFICATIONS_TOPIC_ARN", SHARED_TOPIC_ARN)


def _capture_publish(monkeypatch):
    published = []

    class FakeSns:
        def publish(self, **kwargs):
            published.append(kwargs)
            return {"MessageId": "mid"}

    monkeypatch.setattr(email_worker, "_sns_client", lambda: FakeSns())
    return published


def test_order_created_publishes_to_shared_topic_with_user_id_attribute(monkeypatch):
    published = _capture_publish(monkeypatch)

    email_worker._process_event(
        {
            "eventType": "order.created",
            "userId": USER_ID,
            "data": {"orderId": "o1", "status": "PENDING", "total": 100},
        }
    )

    assert len(published) == 1
    assert published[0]["TopicArn"] == SHARED_TOPIC_ARN
    # The userId attribute is mandatory for the filter policy to deliver.
    assert published[0]["MessageAttributes"]["userId"] == {
        "DataType": "String",
        "StringValue": USER_ID,
    }


def test_event_without_user_id_does_not_publish(monkeypatch):
    published = _capture_publish(monkeypatch)

    email_worker._process_event({"eventType": "order.created", "data": {}})

    assert published == []


def test_unhandled_event_type_does_not_publish(monkeypatch):
    published = _capture_publish(monkeypatch)

    # reservation.created is delivered synchronously, not by this worker.
    email_worker._process_event(
        {"eventType": "reservation.created", "userId": USER_ID, "data": {}}
    )

    assert published == []
