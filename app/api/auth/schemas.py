from flask_restx import Model, fields

# Regex patterns — defined once, reused in multiple models
_EMAIL_PATTERN = r"^[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}$"
# Names allow Spanish letters (accented vowels + ñ), hyphens, apostrophes, and spaces
_NAME_PATTERN = r"^[a-zA-ZáéíóúüñÁÉÍÓÚÜÑ'\- ]{1,100}$"

register_model = Model(
    "RegisterRequest",
    {
        "email": fields.String(
            required=True,
            description="Dirección de correo electrónico del usuario.",
            example="usuario@ejemplo.com",
            pattern=_EMAIL_PATTERN,
            max_length=255,
        ),
        "password": fields.String(
            required=True,
            description="Contraseña en texto plano (mínimo 8 caracteres).",
            example="ContraseñaSegura1",
            min_length=8,
            max_length=128,
        ),
        "name": fields.String(
            required=True,
            description="Nombre del usuario. Solo letras (incluye acentos y ñ), guiones y espacios.",
            example="Juan",
            pattern=_NAME_PATTERN,
        ),
        "surname": fields.String(
            required=True,
            description="Apellido del usuario. Solo letras (incluye acentos y ñ), guiones y espacios.",
            example="García",
            pattern=_NAME_PATTERN,
        ),
    },
)

login_model = Model(
    "LoginRequest",
    {
        "email": fields.String(
            required=True,
            description="Correo electrónico registrado.",
            example="usuario@ejemplo.com",
            pattern=_EMAIL_PATTERN,
            max_length=255,
        ),
        "password": fields.String(
            required=True,
            description="Contraseña de la cuenta.",
            example="ContraseñaSegura1",
            min_length=8,
            max_length=128,
        ),
    },
)

user_summary_model = Model(
    "UserSummary",
    {
        "id": fields.Integer(
            description="ID del usuario.",
            example=1,
        ),
        "email": fields.String(
            description="Correo electrónico del usuario.",
            example="usuario@ejemplo.com",
        ),
        "name": fields.String(
            description="Nombre.",
            example="Juan",
        ),
        "surname": fields.String(
            description="Apellido.",
            example="García",
        ),
        "role": fields.String(
            required=True,
            description="Rol: CUSTOMER | RESTAURANT_ADMIN | SUPER_ADMIN.",
            example="CUSTOMER",
        ),
        "createdAt": fields.String(
            description="Fecha de creación en formato ISO 8601 UTC.",
            example="2026-04-07T19:00:00+00:00",
        ),
    },
)

auth_response_model = Model(
    "AuthResponse",
    {
        "accessToken": fields.String(
            description=(
                "Token de acceso JWT de corta duración (15 min). "
                "Enviarlo como: Authorization: Bearer <accessToken> en cada request protegido."
            ),
            example="eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
        ),
        "refreshToken": fields.String(
            description=(
                "Token de refresco de larga duración (30 días). "
                "Enviarlo como: Authorization: Bearer <refreshToken> a POST /auth/refresh "
                "para obtener un nuevo accessToken sin volver a autenticarse."
            ),
            example="eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
        ),
        "user": fields.Nested(
            user_summary_model,
            description="Perfil básico del usuario autenticado.",
        ),
    },
)

refresh_response_model = Model(
    "RefreshResponse",
    {
        "accessToken": fields.String(
            description="Nuevo token de acceso JWT de corta duración (15 min).",
            example="eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
        ),
    },
)
