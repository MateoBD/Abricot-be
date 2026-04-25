from flask import request
from flask_restx import Namespace, Resource

from app.api.auth.schemas import (
    auth_response_model,
    login_model,
    refresh_response_model,
    register_model,
    user_summary_model,
)
from app.middleware.auth import require_refresh_token
from app.services.auth_service import AuthService

namespace = Namespace(
    name="Auth",
    path="/auth",
    description="Authentication endpoints: register, login, and token refresh.",
)

for _model in (
    register_model,
    login_model,
    user_summary_model,
    auth_response_model,
    refresh_response_model,
):
    namespace.models[_model.name] = _model


@namespace.route("/register")
class RegisterEndpoint(Resource):
    """Endpoint to create a new user account."""

    @namespace.expect(register_model, validate=True)
    @namespace.response(201, "User registered successfully.", auth_response_model)
    @namespace.response(400, "Validation error.")
    @namespace.response(409, "Email already in use.")
    def post(self):
        """
        Register a new user.

        Returns both an access token (15 min) and a refresh token (30 days).
        Send tokens via the Authorization header: ``Authorization: Bearer <token>``.
        """
        data = request.json
        return AuthService.register(
            email=data.get("email", ""),
            password=data.get("password", ""),
            name=data.get("name", ""),
            surname=data.get("surname", ""),
            role=data.get("role"),
        ), 201


@namespace.route("/login")
class LoginEndpoint(Resource):
    """Endpoint to authenticate an existing user."""

    @namespace.expect(login_model, validate=True)
    @namespace.response(200, "Login successful.", auth_response_model)
    @namespace.response(401, "Invalid email or password.")
    def post(self):
        """
        Log in with email and password.

        Returns both an access token (15 min) and a refresh token (30 days).
        Send tokens via the Authorization header: ``Authorization: Bearer <token>``.
        """
        data = request.json
        return AuthService.login(
            email=data.get("email", ""),
            password=data.get("password", ""),
        ), 200


@namespace.route("/refresh")
class RefreshEndpoint(Resource):
    """Exchanges a valid refresh token for a new access token."""

    @require_refresh_token()
    @namespace.response(200, "Token refreshed successfully.", refresh_response_model)
    @namespace.response(401, "Missing, expired, or invalid refresh token.")
    def post(self):
        """
        Refresh the access token.

        Requires the refresh token (not the access token) in the Authorization header:
        ``Authorization: Bearer <refreshToken>``

        Flask-JWT-Extended enforces that only refresh tokens are accepted here —
        sending an access token returns 401.
        """
        return AuthService.refresh(), 200
