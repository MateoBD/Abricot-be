from flask_restx import Model, fields

# --- Request models ---

restaurant_create_model = Model(
    "RestaurantCreateRequest",
    {
        "name": fields.String(
            required=True,
            description="Name of the restaurant.",
            example="La Parolaccia",
        ),
        "address": fields.String(
            required=True,
            description="Physical address of the restaurant.",
            example="Av. Corrientes 1234, CABA",
        ),
        "phone": fields.String(
            required=True,
            description="Contact phone number.",
            example="+54 11 4444-5555",
        ),
        "email": fields.String(
            required=False,
            description="Optional contact email.",
            example="reservas@laparolaccia.com",
        ),
        "description": fields.String(
            required=False,
            description="Optional description of the restaurant.",
            example="Tradicional restaurante italiano en el corazón de Buenos Aires.",
        ),
    },
)

restaurant_update_model = Model(
    "RestaurantUpdateRequest",
    {
        "name": fields.String(
            required=True,
            description="Updated name of the restaurant.",
            example="La Parolaccia",
        ),
        "address": fields.String(
            required=True,
            description="Updated physical address.",
            example="Av. Corrientes 1234, CABA",
        ),
        "phone": fields.String(
            required=True,
            description="Updated contact phone number.",
            example="+54 11 4444-5555",
        ),
        "email": fields.String(
            required=False,
            description="Updated contact email (omit to clear).",
            example="reservas@laparolaccia.com",
        ),
        "description": fields.String(
            required=False,
            description="Updated description (omit to clear).",
            example="Tradicional restaurante italiano en el corazón de Buenos Aires.",
        ),
    },
)

# --- Response model ---

restaurant_response_model = Model(
    "RestaurantResponse",
    {
        "id": fields.Integer(description="Restaurant ID.", example=1),
        "name": fields.String(
            description="Name of the restaurant.", example="La Parolaccia"
        ),
        "address": fields.String(
            description="Physical address.", example="Av. Corrientes 1234, CABA"
        ),
        "phone": fields.String(
            description="Contact phone.", example="+54 11 4444-5555"
        ),
        "email": fields.String(
            description="Contact email.", example="reservas@laparolaccia.com"
        ),
        "description": fields.String(
            description="Description of the restaurant.",
            example="Tradicional restaurante italiano.",
        ),
        "photoUrl": fields.String(
            description="URL of the restaurant's photo.",
            example="https://example.com/photos/laparolaccia.jpg",
        ),
        "createdAt": fields.String(
            description="ISO 8601 creation timestamp.", example="2026-04-07T00:00:00"
        ),
    },
)
