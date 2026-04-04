"""Test configuration and fixtures.

- Ensures the repo root is importable for `import project`.
- Sets ENV=testing for an in-memory SQLite DB.
- Provides a CustomTestClient that can inject a Bearer token.
- Creates/tears down the DB per test function.

Fixture usage:
 - Useful to create instances of models to then use in tests.
    Example:
    def saved_model(_db):
        model = TemplateModel(some_field="value")
        _db.session.add(model)
        _db.session.commit()
        return model
"""

import os
import sys
from pathlib import Path
from wsgiref.headers import Headers

import pytest
from flask import testing
from sqlalchemy import text

# Ensure repo root is on sys.path so `import project` works when running pytest
repo_root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(repo_root))

from project import create_app, db  # noqa E402

os.environ["ENV"] = "testing"


class CustomTestClient(testing.FlaskClient):
    """A test client that can automatically attach a Bearer token to requests."""

    def __init__(self, *args, **kwargs) -> None:
        self.custom_token = None
        super().__init__(*args, **kwargs)

    def open(self, *args, **kwargs):
        # If a token is set, attach it as Authorization header
        if self.custom_token:
            api_key_headers = Headers({"Authorization": f"Bearer {self.custom_token}"})
            headers = kwargs.pop("headers", Headers())
            headers.extend(api_key_headers)
            kwargs["headers"] = headers
        return super().open(*args, **kwargs)

    def set_auth_token(self, token):
        """Configure the Authorization bearer token used in requests."""
        self.custom_token = token


# scope="session" means its reused in ALL tests, thus saving time
@pytest.fixture(scope="session", autouse=True)
def test_client():
    """Creates a Flask test client and pushes app/app_context for the test session."""
    flask_app = create_app()
    os.environ["SECRET_KEY"] = flask_app.config["SECRET_KEY"] or "test_secret_key"
    flask_app.test_client_class = CustomTestClient
    # Create a test client using the Flask application configured for testing
    with flask_app.test_client() as testing_client:
        # Establish an application context
        with flask_app.app_context():
            yield testing_client  # this is where the testing happens


@pytest.fixture(scope="session")
def test_request_context():
    """Provides a request context if needed by tests."""
    flask_app = create_app()
    flask_app.test_client_class = CustomTestClient
    with flask_app.test_request_context() as request_context:
        # with flask_app.app_context():
        yield request_context


@pytest.fixture(scope="session")
def flask_app():
    """Provides the Flask app object for tests that need direct access."""
    flask_app = create_app()
    flask_app.test_client_class = CustomTestClient
    return flask_app


@pytest.fixture(scope="function", autouse=True)
def init_database(test_client):
    """Creates all tables before each test and drops them afterwards."""
    # Create the database and the database table
    db.create_all()
    db.session.configure(autoflush=False)

    # Insert example data
    # ...

    db.session.commit()

    yield db  # this is where the testing happens!

    db.session.remove()
    # Disable foreign keys to drop all tables in sqlite without dependency errors
    with db.engine.connect() as conn:
        conn.execute(text("PRAGMA foreign_keys=OFF"))

    db.drop_all()


@pytest.fixture(scope="function")
def _db(init_database):
    """Exposes the db object for tests that need direct DB access."""
    return db
