from flask_restx import Model, fields

# --- Request models ---

register_model = Model(
    "RegisterRequest",
    {
        "email": fields.String(
            required=True,
            description="User's email address.",
            example="user@example.com",
        ),
        "password": fields.String(
            required=True,
            description="Plain-text password (min 8 characters).",
            example="securePassword123",
        ),
        "name": fields.String(
            required=True,
            description="User's first name.",
            example="Jane",
        ),
        "surname": fields.String(
            required=True,
            description="User's last name.",
            example="Doe",
        ),
    },
)

login_model = Model(
    "LoginRequest",
    {
        "email": fields.String(
            required=True,
            description="Registered email address.",
            example="user@example.com",
        ),
        "password": fields.String(
            required=True,
            description="Account password.",
            example="securePassword123",
        ),
    },
)

# --- Response models ---

auth_response_model = Model(
    "AuthResponse",
    {
        "accessToken": fields.String(
            description="JWT access token. Include as 'Bearer <token>' in the Authorization header.",
            example="eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
        ),
        "user": fields.Nested(
            Model(
                "UserSummary",
                {
                    "id": fields.Integer(description="User ID.", example=1),
                    "email": fields.String(
                        description="User email.", example="user@example.com"
                    ),
                    "name": fields.String(description="First name.", example="Jane"),
                    "surname": fields.String(description="Last name.", example="Doe"),
                    "createdAt": fields.String(
                        description="ISO 8601 creation timestamp.",
                        example="2026-04-07T00:00:00",
                    ),
                },
            ),
            description="Basic profile of the authenticated user.",
        ),
    },
)
