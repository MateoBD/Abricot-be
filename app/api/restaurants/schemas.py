from flask_restx import Model, fields

# Regex patterns — defined once, shared across create and update models
_UUID_STRING_PATTERN = (
    r"^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$"
)
_EMAIL_PATTERN = r"^[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}$"
# Phone: optional leading +, then digits, spaces, parentheses, hyphens and dots
_PHONE_PATTERN = r"^\+?[\d\s\(\)\-\.]{7,30}$"
_RESERVATION_SOURCE_PATTERN = r"^(ONLINE|PHONE|EVENT)$"
_RESERVATION_ADMIN_SOURCE_PATTERN = r"^(PHONE|EVENT)$"
_RESERVATION_STATUS_PATTERN = r"^(CONFIRMED|CANCELLED|COMPLETED|NO_SHOW)$"

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
    "cityId": fields.String(
        required=True,
        description="ID de ciudad (UUID).",
        pattern=_UUID_STRING_PATTERN,
        example="018f1234-5678-7abc-8def-123456789abc",
    ),
    "neighbourhoodId": fields.String(
        required=False,
        description="ID de barrio (UUID, opcional).",
        pattern=_UUID_STRING_PATTERN,
        allow_null=True,
    ),
    "priceRangeId": fields.String(
        required=False,
        description="ID de rango de precios (UUID, opcional).",
        pattern=_UUID_STRING_PATTERN,
        allow_null=True,
    ),
    "cuisineTypeIds": fields.List(
        fields.String(pattern=_UUID_STRING_PATTERN),
        required=False,
        description="IDs de tipos de cocina (UUID).",
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
        "id": fields.String(
            description="ID del restaurante (UUID).",
            example="018f1234-5678-7abc-8def-123456789abc",
            pattern=_UUID_STRING_PATTERN,
        ),
        "name": fields.String(
            description="Nombre del restaurante.",
            example="El Gaucho Rojo",
        ),
        "address": fields.String(
            description="Dirección física.",
            example="Av. Corrientes 1234, CABA",
        ),
        "cityId": fields.String(
            description="ID de la ciudad (UUID).",
            example="018f1234-5678-7abc-8def-123456789abc",
            pattern=_UUID_STRING_PATTERN,
        ),
        "neighbourhoodId": fields.String(
            description="ID del barrio (opcional).",
            example="018f1234-5678-7abc-8def-123456789abd",
            allow_null=True,
            pattern=_UUID_STRING_PATTERN,
        ),
        "priceRangeId": fields.String(
            description="ID del rango de precios (opcional).",
            example="018f1234-5678-7abc-8def-123456789abe",
            allow_null=True,
            pattern=_UUID_STRING_PATTERN,
        ),
        "phone": fields.String(
            description="Teléfono de contacto.",
            example="+54 11 4444-5555",
        ),
        "email": fields.String(
            description="Correo electrónico de contacto.",
            example="contacto@elgauchorojo.com",
            allow_null=True,
        ),
        "description": fields.String(
            description="Descripción del restaurante.",
            example="Parrilla tradicional argentina en el corazón de Buenos Aires.",
            allow_null=True,
        ),
        "photoUrl": fields.String(
            description="URL de la foto del restaurante.",
            example="https://bucket.s3.us-east-1.amazonaws.com/restaurants/1/abc123.jpg",
            allow_null=True,
        ),
        "allowTableJoining": fields.Boolean(
            description="Permite unir mesas para grupos grandes.",
            example=False,
        ),
        "defaultSlotDurationMinutes": fields.Integer(
            description="Duración por defecto de un turno de reserva (minutos).",
            example=90,
        ),
        "cuisineTypeIds": fields.List(
            fields.String(pattern=_UUID_STRING_PATTERN),
            description="Tipos de cocina asociados al restaurante.",
        ),
        "createdAt": fields.String(
            description="Fecha de creación en formato ISO 8601 UTC.",
            example="2026-04-07T19:00:00+00:00",
        ),
    },
)

paginated_restaurant_response_model = Model(
    "PaginatedRestaurantListResponse",
    {
        "data": fields.List(
            fields.Nested(restaurant_response_model),
            description="Restaurantes en la página actual.",
        ),
        "total": fields.Integer(
            description="Cantidad total de ítems devueltos.",
            example=2,
        ),
        "page": fields.Integer(
            description="Página actual (1-based).",
            example=1,
        ),
        "perPage": fields.Integer(
            description="Tamaño de página (ítems en esta respuesta cuando no hay paginación).",
            example=2,
        ),
    },
)

restaurant_admin_add_model = Model(
    "RestaurantAdminAddRequest",
    {
        "userId": fields.String(
            required=True,
            description="ID del usuario a asignar como administrador (UUID).",
            example="018f1234-5678-7abc-8def-123456789abc",
            pattern=_UUID_STRING_PATTERN,
        )
    },
)

restaurant_admin_response_model = Model(
    "RestaurantAdminResponse",
    {
        "id": fields.String(
            description="ID del usuario (UUID).",
            example="018f1234-5678-7abc-8def-123456789abc",
            pattern=_UUID_STRING_PATTERN,
        ),
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

paginated_restaurant_admin_response_model = Model(
    "PaginatedRestaurantAdminListResponse",
    {
        "data": fields.List(
            fields.Nested(restaurant_admin_response_model),
            description="Administradores del restaurante en la página actual.",
        ),
        "total": fields.Integer(example=1),
        "page": fields.Integer(example=1),
        "perPage": fields.Integer(example=1),
    },
)

analytics_period_model = Model(
    "AnalyticsPeriod",
    {
        "start": fields.String(
            description="Fecha de inicio del período (YYYY-MM-DD).",
            example="2026-04-01",
        ),
        "end": fields.String(
            description="Fecha de fin del período (YYYY-MM-DD).",
            example="2026-04-30",
        ),
    },
)

orders_by_status_item_model = Model(
    "OrdersByStatusItem",
    {
        "status": fields.String(
            description="Estado del pedido.",
            example="COMPLETED",
        ),
        "count": fields.Integer(
            description="Cantidad de pedidos en ese estado.",
            example=310,
        ),
    },
)

revenue_by_day_item_model = Model(
    "RevenueByDayItem",
    {
        "date": fields.String(
            description="Fecha (YYYY-MM-DD).",
            example="2026-04-01",
        ),
        "revenue": fields.String(
            description="Ingresos del día.",
            example="28000.00",
            pattern=r"^\d+(\.\d{2})$",
        ),
        "orders": fields.Integer(
            description="Cantidad de pedidos del día.",
            example=11,
        ),
    },
)

orders_report_response_model = Model(
    "OrdersReportResponse",
    {
        "restaurantId": fields.String(
            description="ID del restaurante (UUID).",
            example="018f1234-5678-7abc-8def-123456789abc",
            pattern=_UUID_STRING_PATTERN,
        ),
        "period": fields.Nested(
            analytics_period_model,
            description="Período aplicado para calcular métricas.",
        ),
        "totalOrders": fields.Integer(
            description="Cantidad de pedidos del período.",
            example=340,
        ),
        "totalRevenue": fields.String(
            description="Ingresos totales de pedidos en el período.",
            example="850000.00",
            pattern=r"^\d+(\.\d{2})$",
        ),
        "averageOrderValue": fields.String(
            description="Ticket promedio de pedidos en el período.",
            example="2500.00",
            pattern=r"^\d+(\.\d{2})$",
        ),
        "ordersByStatus": fields.List(
            fields.Nested(orders_by_status_item_model),
            description="Desglose de pedidos por estado.",
        ),
        "revenueByDay": fields.List(
            fields.Nested(revenue_by_day_item_model),
            description="Ingresos y pedidos agrupados por día.",
        ),
    },
)

reservations_by_status_item_model = Model(
    "ReservationsByStatusItem",
    {
        "status": fields.String(
            description="Estado de la reserva.",
            example="CONFIRMED",
        ),
        "count": fields.Integer(
            description="Cantidad de reservas en ese estado.",
            example=42,
        ),
    },
)

orders_metrics_model = Model(
    "OrdersMetrics",
    {
        "total": fields.Integer(
            description="Cantidad total de pedidos.",
            example=340,
        ),
        "totalRevenue": fields.String(
            description="Ingresos totales de pedidos.",
            example="850000.00",
            pattern=r"^\d+(\.\d{2})$",
        ),
        "averageOrderValue": fields.String(
            description="Ticket promedio de pedidos.",
            example="2500.00",
            pattern=r"^\d+(\.\d{2})$",
        ),
        "byStatus": fields.List(
            fields.Nested(orders_by_status_item_model),
            description="Desglose de pedidos por estado.",
        ),
    },
)

reservations_metrics_model = Model(
    "ReservationsMetrics",
    {
        "total": fields.Integer(
            description="Cantidad total de reservas.",
            example=145,
        ),
        "totalGuests": fields.Integer(
            description="Cantidad total de comensales.",
            example=582,
        ),
        "byStatus": fields.List(
            fields.Nested(reservations_by_status_item_model),
            description="Desglose de reservas por estado.",
        ),
    },
)

general_metrics_response_model = Model(
    "GeneralMetricsResponse",
    {
        "restaurantId": fields.String(
            description="ID del restaurante (UUID).",
            example="018f1234-5678-7abc-8def-123456789abc",
            pattern=_UUID_STRING_PATTERN,
        ),
        "period": fields.Nested(
            analytics_period_model,
            description="Período aplicado para calcular métricas.",
        ),
        "orders": fields.Nested(
            orders_metrics_model,
            description="Métricas de pedidos.",
        ),
        "reservations": fields.Nested(
            reservations_metrics_model,
            description="Métricas de reservas.",
        ),
    },
)

reservation_response_model = Model(
    "ReservationResponse",
    {
        "id": fields.String(
            description="ID de la reserva (UUID).",
            pattern=_UUID_STRING_PATTERN,
            example="018f1234-5678-7abc-8def-123456789abc",
        ),
        "restaurantId": fields.String(
            description="ID del restaurante (UUID).",
            pattern=_UUID_STRING_PATTERN,
            example="018f1234-5678-7abc-8def-123456789abd",
        ),
        "userId": fields.String(
            description="ID del usuario (UUID, opcional).",
            pattern=_UUID_STRING_PATTERN,
            allow_null=True,
            example="018f1234-5678-7abc-8def-123456789abe",
        ),
        "guestName": fields.String(
            description="Nombre del invitado.",
            allow_null=True,
            example="Juan Perez",
        ),
        "guestPhone": fields.String(
            description="Telefono del invitado.",
            allow_null=True,
            example="+54 11 4444-5555",
        ),
        "guestEmail": fields.String(
            description="Email del invitado.",
            allow_null=True,
            example="juan@example.com",
        ),
        "source": fields.String(
            description="Origen de la reserva.",
            pattern=_RESERVATION_SOURCE_PATTERN,
            example="ONLINE",
        ),
        "partySize": fields.Integer(
            description="Cantidad de comensales.",
            example=4,
        ),
        "date": fields.String(
            description="Fecha de la reserva (YYYY-MM-DD).",
            example="2026-04-22",
        ),
        "timeSlot": fields.String(
            description="Horario de la reserva (HH:MM:SS).",
            example="21:00:00",
        ),
        "status": fields.String(
            description="Estado de la reserva.",
            pattern=_RESERVATION_STATUS_PATTERN,
            example="CONFIRMED",
        ),
        "notes": fields.String(
            description="Notas adicionales.",
            allow_null=True,
            example="Mesa cerca de la ventana.",
        ),
        "confirmationCode": fields.String(
            description="Codigo de confirmacion.",
            example="ABR123XYZ789",
        ),
        "createdAt": fields.String(
            description="Fecha de creacion en formato ISO 8601 UTC.",
            example="2026-04-07T19:00:00+00:00",
        ),
    },
)

paginated_reservation_response_model = Model(
    "PaginatedReservationListResponse",
    {
        "data": fields.List(
            fields.Nested(reservation_response_model),
            description="Reservas en la pagina actual.",
        ),
        "total": fields.Integer(
            description="Cantidad total de items.",
            example=25,
        ),
        "page": fields.Integer(
            description="Pagina actual (1-based).",
            example=1,
        ),
        "perPage": fields.Integer(
            description="Tamano de pagina aplicado.",
            example=20,
        ),
    },
)

reservation_admin_create_model = Model(
    "ReservationAdminCreateRequest",
    {
        "partySize": fields.Integer(
            required=True,
            description="Cantidad de comensales.",
            min=1,
            example=8,
        ),
        "date": fields.String(
            required=True,
            description="Fecha de la reserva (YYYY-MM-DD).",
            example="2026-05-10",
        ),
        "timeSlot": fields.String(
            required=True,
            description="Horario de la reserva (HH:MM o HH:MM:SS).",
            example="21:00:00",
        ),
        "source": fields.String(
            required=True,
            description="Origen de la reserva creada por admin.",
            pattern=_RESERVATION_ADMIN_SOURCE_PATTERN,
            example="PHONE",
        ),
        "guestName": fields.String(
            required=False,
            allow_null=True,
            description="Nombre del invitado/grupo si no hay usuario registrado.",
            max_length=150,
            example="Grupo Perez",
        ),
        "guestPhone": fields.String(
            required=False,
            allow_null=True,
            description="Telefono de contacto del invitado/grupo.",
            pattern=_PHONE_PATTERN,
            example="+54 11 4444-5555",
        ),
        "guestEmail": fields.String(
            required=False,
            allow_null=True,
            description="Email de contacto del invitado/grupo.",
            pattern=_EMAIL_PATTERN,
            max_length=255,
            example="grupo@example.com",
        ),
        "userId": fields.String(
            required=False,
            allow_null=True,
            description="Usuario registrado a asociar (UUID), opcional.",
            pattern=_UUID_STRING_PATTERN,
            example="018f1234-5678-7abc-8def-123456789abc",
        ),
        "notes": fields.String(
            required=False,
            allow_null=True,
            description="Notas adicionales de la reserva.",
            max_length=2000,
            example="Cumpleanos - traer torta a las 22:00.",
        ),
    },
)

reservation_cancel_model = Model(
    "ReservationCancelRequest",
    {
        "reason": fields.String(
            required=False,
            description="Motivo opcional de la cancelacion.",
            max_length=500,
            example="El cliente aviso que no podia asistir.",
        )
    },
)

reservation_create_model = Model(
    "ReservationCreateRequest",
    {
        "partySize": fields.Integer(
            required=True,
            description="Cantidad de comensales.",
            min=1,
            example=4,
        ),
        "date": fields.String(
            required=True,
            description="Fecha de la reserva (YYYY-MM-DD).",
            example="2026-05-10",
        ),
        "timeSlot": fields.String(
            required=True,
            description="Horario de la reserva (HH:MM o HH:MM:SS).",
            example="21:00",
        ),
        "notes": fields.String(
            required=False,
            allow_null=True,
            description="Notas adicionales.",
            max_length=2000,
            example="Festejo de cumpleaños.",
        ),
    },
)

# ── Tables ──────────────────────────────────────────────────────────────────

_TABLE_WRITABLE_FIELDS = {
    "number": fields.Integer(
        required=True,
        description="Número de la mesa (único por restaurante).",
        min=1,
        example=5,
    ),
    "capacity": fields.Integer(
        required=True,
        description="Capacidad máxima de comensales.",
        min=1,
        example=4,
    ),
    "name": fields.String(
        required=False,
        allow_null=True,
        description="Nombre descriptivo opcional.",
        max_length=100,
        example="Mesa del jardín",
    ),
    "isJoinable": fields.Boolean(
        required=False,
        description="Puede unirse con otras mesas para grupos grandes.",
        example=True,
    ),
}

table_create_model = Model("TableCreateRequest", {**_TABLE_WRITABLE_FIELDS})

table_update_model = Model(
    "TableUpdateRequest",
    {
        **_TABLE_WRITABLE_FIELDS,
        "isActive": fields.Boolean(
            required=False,
            description="Si la mesa está activa.",
            example=True,
        ),
    },
)

table_response_model = Model(
    "TableResponse",
    {
        "id": fields.String(
            description="ID de la mesa (UUID).",
            example="018f1234-5678-7abc-8def-123456789abc",
            pattern=_UUID_STRING_PATTERN,
        ),
        "restaurantId": fields.String(
            description="ID del restaurante (UUID).",
            example="018f1234-5678-7abc-8def-123456789abd",
            pattern=_UUID_STRING_PATTERN,
        ),
        "number": fields.Integer(description="Número de la mesa.", example=5),
        "capacity": fields.Integer(description="Capacidad máxima.", example=4),
        "name": fields.String(
            description="Nombre descriptivo.", allow_null=True, example="Mesa del jardín"
        ),
        "isJoinable": fields.Boolean(description="Puede unirse con otras.", example=True),
        "isActive": fields.Boolean(description="Mesa activa.", example=True),
    },
)

paginated_table_response_model = Model(
    "PaginatedTableListResponse",
    {
        "data": fields.List(
            fields.Nested(table_response_model),
            description="Mesas del restaurante.",
        ),
        "total": fields.Integer(description="Cantidad total de mesas.", example=12),
        "page": fields.Integer(description="Página actual (1-based).", example=1),
        "perPage": fields.Integer(description="Tamaño de página.", example=12),
    },
)

table_group_model = Model(
    "TableBulkGroup",
    {
        "quantity": fields.Integer(
            required=True,
            description="Cantidad de mesas del grupo.",
            min=1,
            example=5,
        ),
        "capacity": fields.Integer(
            required=True,
            description="Capacidad de cada mesa del grupo.",
            min=1,
            example=4,
        ),
        "isJoinable": fields.Boolean(
            required=False,
            description="Pueden unirse con otras.",
            example=True,
        ),
    },
)

table_bulk_create_model = Model(
    "TableBulkCreateRequest",
    {
        "groups": fields.List(
            fields.Nested(table_group_model),
            required=True,
            description="Grupos de mesas a crear.",
        )
    },
)

# ── Business Hours ───────────────────────────────────────────────────────────

business_hours_item_model = Model(
    "BusinessHoursItem",
    {
        "dayOfWeek": fields.Integer(
            required=True,
            description="Día de la semana: 0=Lunes, 6=Domingo.",
            min=0,
            max=6,
            example=0,
        ),
        "isClosed": fields.Boolean(
            required=True,
            description="Si el restaurante está cerrado ese día.",
            example=False,
        ),
        "opensAt": fields.String(
            required=False,
            allow_null=True,
            description="Hora de apertura (HH:MM). Requerido si isClosed=false.",
            example="12:00",
        ),
        "closesAt": fields.String(
            required=False,
            allow_null=True,
            description="Hora de cierre (HH:MM). Requerido si isClosed=false.",
            example="23:00",
        ),
    },
)

business_hours_bulk_update_model = Model(
    "BusinessHoursBulkUpdateRequest",
    {
        "hours": fields.List(
            fields.Nested(business_hours_item_model),
            required=True,
            description="Lista de horarios a actualizar (puede incluir todos los días).",
        )
    },
)

business_hours_response_model = Model(
    "BusinessHoursResponse",
    {
        "id": fields.String(
            description="ID del registro (UUID).",
            example="018f1234-5678-7abc-8def-123456789abc",
            pattern=_UUID_STRING_PATTERN,
        ),
        "restaurantId": fields.String(
            description="ID del restaurante (UUID).",
            example="018f1234-5678-7abc-8def-123456789abd",
            pattern=_UUID_STRING_PATTERN,
        ),
        "dayOfWeek": fields.Integer(description="0=Lunes, 6=Domingo.", example=0),
        "opensAt": fields.String(
            description="Hora de apertura (HH:MM:SS).", allow_null=True, example="12:00:00"
        ),
        "closesAt": fields.String(
            description="Hora de cierre (HH:MM:SS).", allow_null=True, example="23:00:00"
        ),
        "isClosed": fields.Boolean(description="Cerrado ese día.", example=False),
    },
)

paginated_business_hours_response_model = Model(
    "PaginatedBusinessHoursResponse",
    {
        "data": fields.List(
            fields.Nested(business_hours_response_model),
            description="Horarios del restaurante.",
        ),
        "total": fields.Integer(example=7),
        "page": fields.Integer(example=1),
        "perPage": fields.Integer(example=7),
    },
)

# ── Availability ─────────────────────────────────────────────────────────────

table_assignment_item_model = Model(
    "TableAssignmentItem",
    {
        "tableId": fields.String(
            description="ID de la mesa (UUID).",
            example="018f1234-5678-7abc-8def-123456789abc",
            pattern=_UUID_STRING_PATTERN,
        ),
        "number": fields.Integer(description="Número de la mesa.", example=3),
        "capacity": fields.Integer(description="Capacidad de la mesa.", example=4),
    },
)

availability_slot_model = Model(
    "AvailabilitySlot",
    {
        "timeSlot": fields.String(
            description="Horario del turno (HH:MM:SS).", example="20:00:00"
        ),
        "available": fields.Boolean(description="Hay disponibilidad para ese turno.", example=True),
        "tableAssignment": fields.List(
            fields.Nested(table_assignment_item_model),
            description="Mesas asignadas para este turno.",
        ),
    },
)

availability_response_model = Model(
    "AvailabilityResponse",
    {
        "date": fields.String(
            description="Fecha consultada (YYYY-MM-DD).", example="2026-05-10"
        ),
        "partySize": fields.Integer(description="Tamaño del grupo consultado.", example=4),
        "slots": fields.List(
            fields.Nested(availability_slot_model),
            description="Turnos disponibles para esa fecha y tamaño de grupo.",
        ),
    },
)
