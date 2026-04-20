from flask_restx import Model, fields

# Regex patterns — defined once, shared across create and update models
_EMAIL_PATTERN = r"^[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}$"
# Phone: optional leading +, then digits, spaces, parentheses, hyphens and dots
_PHONE_PATTERN = r"^\+?[\d\s\(\)\-\.]{7,30}$"

# Mutable fields shared between create and update (same contract, DRY definition)
_RESTAURANT_WRITABLE_FIELDS = {
    "name": fields.String(
        required=True,
        description="Nombre del restaurante.",
        example="El Gaucho Rojo",
        min_length=1,
        max_length=150,
    ),
    "address": fields.String(
        required=True,
        description="Dirección física del restaurante.",
        example="Av. Corrientes 1234, CABA",
        min_length=1,
        max_length=255,
    ),
    "phone": fields.String(
        required=True,
        description="Teléfono de contacto. Formato internacional aceptado.",
        example="+54 11 4444-5555",
        pattern=_PHONE_PATTERN,
    ),
    "email": fields.String(
        required=False,
        description="Correo electrónico de contacto (opcional).",
        example="contacto@elgauchorojo.com",
        pattern=_EMAIL_PATTERN,
        max_length=255,
    ),
    "description": fields.String(
        required=False,
        description="Descripción del restaurante (opcional).",
        example="Parrilla tradicional argentina en el corazón de Buenos Aires.",
        max_length=2000,
    ),
}

restaurant_create_model = Model(
    "RestaurantCreateRequest",
    {**_RESTAURANT_WRITABLE_FIELDS},
)

restaurant_update_model = Model(
    "RestaurantUpdateRequest",
    {**_RESTAURANT_WRITABLE_FIELDS},
)

restaurant_response_model = Model(
    "RestaurantResponse",
    {
        "id": fields.Integer(
            description="ID del restaurante.",
            example=1,
        ),
        "name": fields.String(
            description="Nombre del restaurante.",
            example="El Gaucho Rojo",
        ),
        "address": fields.String(
            description="Dirección física.",
            example="Av. Corrientes 1234, CABA",
        ),
        "phone": fields.String(
            description="Teléfono de contacto.",
            example="+54 11 4444-5555",
        ),
        "email": fields.String(
            description="Correo electrónico de contacto.",
            example="contacto@elgauchorojo.com",
        ),
        "description": fields.String(
            description="Descripción del restaurante.",
            example="Parrilla tradicional argentina en el corazón de Buenos Aires.",
        ),
        "photoUrl": fields.String(
            description="URL de la foto del restaurante.",
            example="https://bucket.s3.us-east-1.amazonaws.com/restaurants/1/abc123.jpg",
        ),
        "createdAt": fields.String(
            description="Fecha de creación en formato ISO 8601 UTC.",
            example="2026-04-07T19:00:00+00:00",
        ),
    },
)

restaurant_admin_add_model = Model(
    "RestaurantAdminAddRequest",
    {
        "userId": fields.Integer(
            required=True,
            description="ID del usuario a asignar como administrador.",
            example=42,
            min=1,
        )
    },
)

restaurant_admin_response_model = Model(
    "RestaurantAdminResponse",
    {
        "id": fields.Integer(description="ID del usuario.", example=42),
        "email": fields.String(
            description="Correo electrónico del usuario.",
            example="admin@ejemplo.com",
        ),
        "name": fields.String(description="Nombre del usuario.", example="Ana"),
        "surname": fields.String(description="Apellido del usuario.", example="Pérez"),
        "role": fields.String(
            description="Rol actual del usuario.",
            example="RESTAURANT_ADMIN",
        ),
        "createdAt": fields.String(
            description="Fecha de creación en formato ISO 8601 UTC.",
            example="2026-04-07T19:00:00+00:00",
        ),
    },
)
