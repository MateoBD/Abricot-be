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
        "snsTopicArn": fields.String(
            description="ARN del topic SNS individual del usuario.",
            allow_null=True,
        ),
        "snsSubscriptionArn": fields.String(
            description="ARN de la suscripción SNS de email.",
            allow_null=True,
        ),
        "snsSubscriptionStatus": fields.String(
            description="Estado: PENDING_CONFIRMATION | CONFIRMED | FAILED.",
            example="PENDING_CONFIRMATION",
            allow_null=True,
        ),
        "snsSubscriptionRequestedAt": fields.String(
            description="Fecha ISO 8601 de solicitud de suscripción SNS.",
            allow_null=True,
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

user_reservation_response_model = Model(
    "UserReservationResponse",
    {
        "id": fields.String(description="ID de la reserva (UUID).", example="018f1234-5678-7abc-8def-123456789abc"),
        "restaurantId": fields.String(description="ID del restaurante (UUID)."),
        "source": fields.String(description="Origen: ONLINE | PHONE | EVENT.", example="ONLINE"),
        "partySize": fields.Integer(description="Cantidad de comensales.", example=4),
        "date": fields.String(description="Fecha (YYYY-MM-DD).", example="2026-05-10"),
        "timeSlot": fields.String(description="Horario (HH:MM:SS).", example="21:00:00"),
        "status": fields.String(description="Estado: CONFIRMED | CANCELLED | COMPLETED | NO_SHOW.", example="CONFIRMED"),
        "notes": fields.String(description="Notas adicionales.", allow_null=True),
        "confirmationCode": fields.String(description="Código de confirmación.", example="ABR123XYZ789"),
        "createdAt": fields.String(description="Fecha de creación ISO 8601.", example="2026-04-07T19:00:00+00:00"),
    },
)

paginated_user_reservation_model = Model(
    "PaginatedUserReservationResponse",
    {
        "data": fields.List(fields.Nested(user_reservation_response_model)),
        "total": fields.Integer(example=5),
        "page": fields.Integer(example=1),
        "perPage": fields.Integer(example=20),
    },
)

user_order_response_model = Model(
    "UserOrderResponse",
    {
        "id": fields.String(description="ID del pedido (UUID).", example="018f1234-5678-7abc-8def-123456789abc"),
        "restaurantId": fields.String(description="ID del restaurante (UUID)."),
        "status": fields.String(description="Estado: PENDING | CONFIRMED | READY | COMPLETED | CANCELLED.", example="COMPLETED"),
        "totalAmount": fields.String(description="Total del pedido.", example="2500.00"),
        "notes": fields.String(description="Notas del pedido.", allow_null=True),
        "estimatedReadyAt": fields.String(description="Hora estimada de listo (ISO 8601).", allow_null=True),
        "createdAt": fields.String(description="Fecha de creación ISO 8601.", example="2026-04-07T19:00:00+00:00"),
    },
)

paginated_user_order_model = Model(
    "PaginatedUserOrderResponse",
    {
        "data": fields.List(fields.Nested(user_order_response_model)),
        "total": fields.Integer(example=3),
        "page": fields.Integer(example=1),
        "perPage": fields.Integer(example=20),
    },
)

user_restaurant_response_model = Model(
    "UserRestaurantResponse",
    {
        "id": fields.String(description="ID del restaurante (UUID).", example="018f1234-5678-7abc-8def-123456789abc"),
        "name": fields.String(description="Nombre del restaurante.", example="El Gaucho Rojo"),
        "address": fields.String(description="Dirección.", example="Av. Corrientes 1234, CABA"),
        "cityId": fields.String(description="ID de la ciudad (UUID).", allow_null=True),
        "cuisineTypeIds": fields.List(fields.String(), description="Tipos de cocina (UUIDs)."),
        "averageScore": fields.Float(
            description="Promedio de puntuaciones (1–5).",
            allow_null=True,
        ),
        "reviewCount": fields.Integer(description="Cantidad de reseñas.", example=5),
        "createdAt": fields.String(description="Fecha de creación ISO 8601."),
    },
)

user_restaurants_list_model = Model(
    "UserRestaurantsListResponse",
    {
        "data": fields.List(fields.Nested(user_restaurant_response_model)),
        "total": fields.Integer(example=2),
        "page": fields.Integer(example=1),
        "perPage": fields.Integer(example=2),
    },
)

notification_preference_response_model = Model(
    "NotificationPreferenceResponse",
    {
        "id": fields.String(
            description="ID de la preferencia (UUID).",
            example="018f1234-5678-7abc-8def-123456789abc",
            pattern=_UUID_STRING_PATTERN,
        ),
        "userId": fields.String(
            description="ID del usuario (UUID).",
            example="018f1234-5678-7abc-8def-123456789abc",
            pattern=_UUID_STRING_PATTERN,
        ),
        "restaurantId": fields.String(
            description="ID del restaurante (UUID).",
            example="018f1234-5678-7abc-8def-123456789abc",
            pattern=_UUID_STRING_PATTERN,
        ),
        "receivePromotions": fields.Boolean(
            description="Recibir notificaciones de promociones.",
            example=True,
        ),
        "receiveOrderUpdates": fields.Boolean(
            description="Recibir notificaciones de actualización de pedidos.",
            example=True,
        ),
        "receiveReservationReminders": fields.Boolean(
            description="Recibir recordatorios de reservas.",
            example=True,
        ),
    },
)

notification_preference_update_model = Model(
    "NotificationPreferenceUpdateRequest",
    {
        "receivePromotions": fields.Boolean(
            description="Recibir notificaciones de promociones.",
            example=True,
        ),
        "receiveOrderUpdates": fields.Boolean(
            description="Recibir notificaciones de actualización de pedidos.",
            example=True,
        ),
        "receiveReservationReminders": fields.Boolean(
            description="Recibir recordatorios de reservas.",
            example=True,
        ),
    },
)

paginated_notification_preference_model = Model(
    "PaginatedNotificationPreferenceResponse",
    {
        "data": fields.List(fields.Nested(notification_preference_response_model)),
        "total": fields.Integer(example=5),
        "page": fields.Integer(example=1),
        "perPage": fields.Integer(example=20),
    },
)
