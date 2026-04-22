from flask_restx import Model, fields

_EMAIL_PATTERN = r"^[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}$"
_NAME_PATTERN = r"^[a-zA-ZáéíóúüñÁÉÍÓÚÜÑ'\- ]{1,100}$"
_UUID_STRING_PATTERN = (
    r"^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$"
)

user_profile_response_model = Model(
    "UserProfileResponse",
    {
        "id": fields.String(
            description="ID del usuario (UUID).",
            example="018f1234-5678-7abc-8def-123456789abc",
            pattern=_UUID_STRING_PATTERN,
        ),
        "email": fields.String(
            description="Correo electrónico del usuario.",
            example="usuario@ejemplo.com",
            pattern=_EMAIL_PATTERN,
        ),
        "name": fields.String(description="Nombre.", example="Juan", pattern=_NAME_PATTERN),
        "surname": fields.String(
            description="Apellido.",
            example="García",
            pattern=_NAME_PATTERN,
        ),
        "role": fields.String(
            description="Rol: CUSTOMER | RESTAURANT_ADMIN | SUPER_ADMIN.",
            example="CUSTOMER",
        ),
        "createdAt": fields.String(
            description="Fecha de creación en formato ISO 8601 UTC.",
            example="2026-04-07T19:00:00+00:00",
        ),
    },
)

user_profile_update_model = Model(
    "UserProfileUpdateRequest",
    {
        "name": fields.String(
            required=True,
            description="Nombre del usuario.",
            example="Juan",
            pattern=_NAME_PATTERN,
        ),
        "surname": fields.String(
            required=True,
            description="Apellido del usuario.",
            example="García",
            pattern=_NAME_PATTERN,
        ),
    },
)

user_password_change_model = Model(
    "UserPasswordChangeRequest",
    {
        "currentPassword": fields.String(
            required=True,
            description="Contraseña actual del usuario.",
            example="ContraseñaSegura1",
            min_length=8,
            max_length=128,
        ),
        "newPassword": fields.String(
            required=True,
            description="Nueva contraseña del usuario.",
            example="OtraContraseñaSegura1",
            min_length=8,
            max_length=128,
        ),
    },
)

success_message_model = Model(
    "SuccessMessageResponse",
    {
        "message": fields.String(
            description="Mensaje de éxito.",
            example="Password updated successfully.",
        )
    },
)
