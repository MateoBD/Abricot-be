import logging

from flask import request
from flask_bcrypt import Bcrypt
from flask_jwt_extended import create_access_token
from flask_restx import Namespace, Resource

from project.blueprints.models.auth_models import (
    auth_response_model,
    login_model,
    register_model,
)
from project.exceptions.auth_exception import AuthException
from project.repositories.user_repository import UserRepository

logger = logging.getLogger(__name__)

bcrypt = Bcrypt()

namespace = Namespace(
    name="Auth",
    path="/auth",
    description="Authentication endpoints: register and login.",
)

# Register swagger models with the namespace
namespace.models[register_model.name] = register_model
namespace.models[login_model.name] = login_model
namespace.models[auth_response_model.name] = auth_response_model
namespace.models[auth_response_model["user"].model.name] = auth_response_model[
    "user"
].model


@namespace.route("/register")
class RegisterEndpoint(Resource):
    """Endpoint to create a new user account."""

    @namespace.expect(register_model, validate=True)
    @namespace.response(201, "User registered successfully.", auth_response_model)
    @namespace.response(400, "Validation error or email already in use.")
    def post(self):
        """
        Register a new user.

        Accepts email, password, name, and surname. Hashes the password before storing.
        Returns a JWT access token and the user's profile on success.
        """
        data = request.json

        email: str = data.get("email", "").strip().lower()
        password: str = data.get("password", "")
        name: str = data.get("name", "").strip()
        surname: str = data.get("surname", "").strip()

        if len(password) < 8:
            raise AuthException(
                "Password must be at least 8 characters.",
                {"password": "Too short"},
            )

        if UserRepository.get_by_email(email):
            raise AuthException(
                "An account with this email already exists.",
                {"email": "Already in use"},
            )

        password_hash = bcrypt.generate_password_hash(password).decode("utf-8")
        user = UserRepository.create(
            email=email, password_hash=password_hash, name=name, surname=surname
        )

        access_token = create_access_token(identity=str(user.id))

        logger.info(f"New user registered: id={user.id} email={user.email}")

        return {"accessToken": access_token, "user": user.to_dict()}, 201


@namespace.route("/login")
class LoginEndpoint(Resource):
    """Endpoint to authenticate an existing user."""

    @namespace.expect(login_model, validate=True)
    @namespace.response(200, "Login successful.", auth_response_model)
    @namespace.response(401, "Invalid email or password.")
    def post(self):
        """
        Log in with email and password.

        Verifies the credentials against the stored bcrypt hash.
        Returns a JWT access token and the user's profile on success.
        """
        data = request.json

        email: str = data.get("email", "").strip().lower()
        password: str = data.get("password", "")

        user = UserRepository.get_by_email(email)

        if not user or not bcrypt.check_password_hash(user.password_hash, password):
            raise AuthException("Invalid email or password.")

        access_token = create_access_token(identity=str(user.id))

        logger.info(f"User logged in: id={user.id} email={user.email}")

        return {"accessToken": access_token, "user": user.to_dict()}, 200
