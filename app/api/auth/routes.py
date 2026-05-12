from flask import request
from flask_restx import Namespace, Resource

from app.api.auth.schemas import (
    auth_response_model,
    login_model,
    refresh_response_model,
    user_summary_model,
)
from app.middleware.auth import require_refresh_token
from app.services.auth_service import AuthService

namespace = Namespace(
    name="Sessions",
    path="/sessions",
    description="Session resources for authenticating users.",
)

access_tokens_namespace = Namespace(
    name="AccessTokens",
    path="/access-tokens",
    description="Access-token resources created from refresh tokens.",
)

for _model in (login_model, user_summary_model, auth_response_model):
    namespace.models[_model.name] = _model

for _model in (refresh_response_model,):
    access_tokens_namespace.models[_model.name] = _model


@namespace.route("")
class SessionCollection(Resource):
    """Session collection endpoint."""

    @namespace.expect(login_model, validate=True)
    @namespace.response(201, "Session created successfully.", auth_response_model)
    @namespace.response(401, "Invalid email or password.")
    def post(self):
        """
        Create a session with email and password.

        Returns both an access token (15 min) and a refresh token (30 days).
        Send tokens via the Authorization header: ``Authorization: Bearer <token>``.
        """
        data = request.json
        return AuthService.login(
            email=data.get("email", ""),
            password=data.get("password", ""),
        ), 201


@access_tokens_namespace.route("")
class AccessTokenCollection(Resource):
    """Access-token collection endpoint."""

    @require_refresh_token()
    @access_tokens_namespace.response(
        201, "Access token created successfully.", refresh_response_model
    )
    @access_tokens_namespace.response(401, "Missing, expired, or invalid refresh token.")
    def post(self):
        """
        Create an access token from a valid refresh token.

        Requires the refresh token (not the access token) in the Authorization header:
        ``Authorization: Bearer <refreshToken>``.
        """
        return AuthService.refresh(), 201
