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
_DATE_PATTERN = r"^\d{4}-\d{2}-\d{2}$"
_TIME_PATTERN = r"^([01]\d|2[0-3]):[0-5]\d(:[0-5]\d)?$"

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
        "averageScore": fields.Float(
            description="Promedio de puntuaciones (1–5). null si aún no hay reseñas.",
            allow_null=True,
            example=4.25,
        ),
        "reviewCount": fields.Integer(
            description="Cantidad de reseñas (un usuario, una reseña por restaurante).",
            example=12,
        ),
        "createdAt": fields.String(
            description="Fecha de creación en formato ISO 8601 UTC.",
            example="2026-04-07T19:00:00+00:00",
        ),
    },
)

menu_item_response_model = Model(
    "MenuItemResponse",
    {
        "id": fields.String(
            description="ID del ítem de menú (UUID).",
            pattern=_UUID_STRING_PATTERN,
            example="018f1234-5678-7abc-8def-123456789abc",
        ),
        "categoryId": fields.String(
            description="ID de la categoría de menú (UUID).",
            pattern=_UUID_STRING_PATTERN,
            example="018f1234-5678-7abc-8def-123456789abd",
        ),
        "name": fields.String(description="Nombre del plato.", example="Milanesa napolitana"),
        "description": fields.String(description="Descripción del plato.", allow_null=True),
        "price": fields.String(description="Precio del plato.", example="12500.00"),
        "photoUrl": fields.String(description="URL de la foto del plato.", allow_null=True),
        "isAvailable": fields.Boolean(description="Si el ítem está disponible.", example=True),
        "createdAt": fields.String(description="Fecha de creación ISO 8601 UTC."),
    },
)

menu_category_response_model = Model(
    "MenuCategoryResponse",
    {
        "id": fields.String(
            description="ID de la categoría de menú (UUID).",
            pattern=_UUID_STRING_PATTERN,
            example="018f1234-5678-7abc-8def-123456789abd",
        ),
        "menuId": fields.String(
            description="ID del menú (UUID).",
            pattern=_UUID_STRING_PATTERN,
            example="018f1234-5678-7abc-8def-123456789abe",
        ),
        "name": fields.String(description="Nombre de la categoría.", example="Principales"),
        "displayOrder": fields.Integer(description="Orden de visualización.", example=1),
        "isActive": fields.Boolean(description="Categoría activa.", example=True),
    },
)

menu_category_detail_response_model = Model(
    "MenuCategoryDetailResponse",
    {
        "id": fields.String(
            description="ID de la categoría de menú (UUID).",
            pattern=_UUID_STRING_PATTERN,
            example="018f1234-5678-7abc-8def-123456789abd",
        ),
        "menuId": fields.String(
            description="ID del menú (UUID).",
            pattern=_UUID_STRING_PATTERN,
            example="018f1234-5678-7abc-8def-123456789abe",
        ),
        "name": fields.String(description="Nombre de la categoría.", example="Principales"),
        "displayOrder": fields.Integer(description="Orden de visualización.", example=1),
        "isActive": fields.Boolean(description="Categoría activa.", example=True),
        "items": fields.List(
            fields.Nested(menu_item_response_model),
            description="Ítems anidados de la categoría.",
        ),
    },
)

menu_category_create_model = Model(
    "MenuCategoryCreateRequest",
    {
        "name": fields.String(
            required=True,
            description="Nombre de la categoría.",
            example="Entradas",
            min_length=1,
            max_length=100,
        ),
        "displayOrder": fields.Integer(
            required=False,
            description="Orden de visualización de la categoría.",
            min=0,
            example=0,
        ),
    },
)

menu_category_update_model = Model(
    "MenuCategoryUpdateRequest",
    {
        "name": fields.String(
            required=True,
            description="Nombre de la categoría.",
            example="Platos principales",
            min_length=1,
            max_length=100,
        ),
        "displayOrder": fields.Integer(
            required=True,
            description="Orden de visualización de la categoría.",
            min=0,
            example=1,
        ),
        "isActive": fields.Boolean(
            required=True,
            description="Si la categoría está activa.",
            example=True,
        ),
    },
)

menu_item_create_model = Model(
    "MenuItemCreateRequest",
    {
        "name": fields.String(
            required=True,
            description="Nombre del plato.",
            example="Ravioles de ricota",
            min_length=1,
            max_length=150,
        ),
        "description": fields.String(
            required=False,
            description="Descripción opcional del plato.",
            allow_null=True,
            max_length=5000,
        ),
        "price": fields.Float(
            required=True,
            description="Precio del plato.",
            min=0,
            example=8900.00,
        ),
        "isAvailable": fields.Boolean(
            required=False,
            description="Disponibilidad inicial del plato.",
            example=True,
        ),
    },
)

menu_item_update_model = Model(
    "MenuItemUpdateRequest",
    {
        "name": fields.String(
            required=True,
            description="Nombre del plato.",
            example="Ravioles de ricota y nuez",
            min_length=1,
            max_length=150,
        ),
        "description": fields.String(
            required=False,
            description="Descripción opcional del plato.",
            allow_null=True,
            max_length=5000,
        ),
        "price": fields.Float(
            required=True,
            description="Precio del plato.",
            min=0,
            example=9900.00,
        ),
        "isAvailable": fields.Boolean(
            required=True,
            description="Disponibilidad del plato.",
            example=True,
        ),
    },
)

menu_create_model = Model(
    "MenuCreateRequest",
    {
        "name": fields.String(
            required=True,
            description="Nombre del menú.",
            example="Carta de invierno",
            min_length=1,
            max_length=150,
        ),
    },
)

menu_update_model = Model(
    "MenuUpdateRequest",
    {
        "name": fields.String(
            required=True,
            description="Nombre del menú.",
            example="Carta de verano",
            min_length=1,
            max_length=150,
        ),
    },
)

menu_patch_model = Model(
    "MenuPatchRequest",
    {
        "isActive": fields.Boolean(
            required=True,
            description="Whether this menu is the active menu for the restaurant.",
            example=True,
        ),
    },
)

menu_response_model = Model(
    "MenuResponse",
    {
        "id": fields.String(
            description="ID del menú (UUID).",
            pattern=_UUID_STRING_PATTERN,
            example="018f1234-5678-7abc-8def-123456789abc",
        ),
        "restaurantId": fields.String(
            description="ID del restaurante (UUID).",
            pattern=_UUID_STRING_PATTERN,
            example="018f1234-5678-7abc-8def-123456789abd",
        ),
        "name": fields.String(description="Nombre del menú.", example="Carta principal"),
        "isActive": fields.Boolean(description="Si el menú está vigente.", example=True),
        "createdAt": fields.String(description="Fecha de creación ISO 8601 UTC."),
    },
)

menu_detail_response_model = Model(
    "MenuDetailResponse",
    {
        "id": fields.String(
            description="ID del menú (UUID).",
            pattern=_UUID_STRING_PATTERN,
            example="018f1234-5678-7abc-8def-123456789abc",
        ),
        "restaurantId": fields.String(
            description="ID del restaurante (UUID).",
            pattern=_UUID_STRING_PATTERN,
            example="018f1234-5678-7abc-8def-123456789abd",
        ),
        "name": fields.String(description="Nombre del menú.", example="Carta principal"),
        "isActive": fields.Boolean(description="Si el menú está vigente.", example=True),
        "createdAt": fields.String(description="Fecha de creación ISO 8601 UTC."),
        "categories": fields.List(
            fields.Nested(menu_category_detail_response_model),
            description="Categorías anidadas del menú.",
        ),
    },
)

menu_list_response_model = Model(
    "MenuListResponse",
    {
        "data": fields.List(fields.Nested(menu_response_model)),
        "total": fields.Integer(example=1),
        "page": fields.Integer(example=1),
        "perPage": fields.Integer(example=1),
    },
)

menu_category_list_response_model = Model(
    "MenuCategoryListResponse",
    {
        "data": fields.List(fields.Nested(menu_category_response_model)),
        "total": fields.Integer(example=2),
        "page": fields.Integer(example=1),
        "perPage": fields.Integer(example=2),
    },
)

menu_item_list_response_model = Model(
    "MenuItemListResponse",
    {
        "data": fields.List(fields.Nested(menu_item_response_model)),
        "total": fields.Integer(example=4),
        "page": fields.Integer(example=1),
        "perPage": fields.Integer(example=4),
    },
)

my_restaurant_review_request_model = Model(
    "MyRestaurantReviewRequest",
    {
        "score": fields.Integer(
            required=True,
            description="Puntuación de 1 a 5 (entero). Crea o actualiza la reseña del usuario autenticado.",
            min=1,
            max=5,
            example=4,
        ),
    },
)

my_restaurant_review_response_model = Model(
    "MyRestaurantReviewResponse",
    {
        "restaurantId": fields.String(
            description="ID del restaurante (UUID).",
            pattern=_UUID_STRING_PATTERN,
        ),
        "userId": fields.String(
            description="ID del usuario (UUID).",
            pattern=_UUID_STRING_PATTERN,
        ),
        "score": fields.Integer(description="Puntuación 1–5.", min=1, max=5, example=4),
        "createdAt": fields.String(
            description="Fecha de creación ISO 8601 UTC del primer voto en este par.",
        ),
        "updatedAt": fields.String(
            description="Fecha de última actualización de la puntuación.",
        ),
    },
)

_ORDER_STATUS_STRING_PATTERN = r"^(PENDING|CONFIRMED|READY|COMPLETED|CANCELLED)$"

restaurant_order_create_item_model = Model(
    "RestaurantOrderCreateItemRequest",
    {
        "menuItemId": fields.String(
            required=True,
            description="ID del plato (UUID) dentro del menú activo.",
            pattern=_UUID_STRING_PATTERN,
        ),
        "quantity": fields.Integer(
            required=True,
            description="Cantidad solicitada del ítem.",
            min=1,
            example=2,
        ),
        "notes": fields.String(
            required=False,
            description="Notas opcionales para esta línea.",
            allow_null=True,
            max_length=500,
        ),
    },
)

restaurant_order_create_model = Model(
    "RestaurantOrderCreateRequest",
    {
        "items": fields.List(
            fields.Nested(restaurant_order_create_item_model),
            required=True,
            description="Líneas del pedido. Debe incluir al menos una.",
            min_items=1,
        ),
        "notes": fields.String(
            required=False,
            description="Notas generales del pedido.",
            allow_null=True,
            max_length=1000,
        ),
    },
)

restaurant_order_item_admin_model = Model(
    "RestaurantOrderItemAdmin",
    {
        "id": fields.String(description="ID de la línea (UUID).", pattern=_UUID_STRING_PATTERN),
        "orderId": fields.String(description="ID del pedido (UUID).", pattern=_UUID_STRING_PATTERN),
        "menuItemId": fields.String(description="ID del plato (UUID).", pattern=_UUID_STRING_PATTERN),
        "quantity": fields.Integer(example=2),
        "unitPrice": fields.String(description="Precio unitario al momento del pedido.", example="1500.00"),
        "notes": fields.String(description="Notas de la línea.", allow_null=True),
    },
)

restaurant_order_list_admin_model = Model(
    "RestaurantOrderListAdmin",
    {
        "id": fields.String(description="ID del pedido (UUID).", pattern=_UUID_STRING_PATTERN),
        "restaurantId": fields.String(description="ID del restaurante (UUID).", pattern=_UUID_STRING_PATTERN),
        "userId": fields.String(description="ID del cliente (UUID).", pattern=_UUID_STRING_PATTERN),
        "status": fields.String(
            description="Estado del pedido (takeout).",
            example="READY",
            pattern=_ORDER_STATUS_STRING_PATTERN,
        ),
        "totalAmount": fields.String(description="Total del pedido.", example="3500.00"),
        "notes": fields.String(description="Notas del pedido.", allow_null=True),
        "estimatedReadyAt": fields.String(description="Hora estimada de listo (ISO 8601).", allow_null=True),
        "createdAt": fields.String(description="Fecha de creación ISO 8601."),
    },
)

restaurant_order_detail_admin_model = Model(
    "RestaurantOrderDetailAdmin",
    {
        "id": fields.String(pattern=_UUID_STRING_PATTERN),
        "restaurantId": fields.String(pattern=_UUID_STRING_PATTERN),
        "userId": fields.String(pattern=_UUID_STRING_PATTERN),
        "status": fields.String(pattern=_ORDER_STATUS_STRING_PATTERN, example="READY"),
        "totalAmount": fields.String(example="3500.00"),
        "notes": fields.String(allow_null=True),
        "estimatedReadyAt": fields.String(allow_null=True),
        "createdAt": fields.String(),
        "items": fields.List(
            fields.Nested(restaurant_order_item_admin_model),
            description="Líneas del pedido (solo en detalle y tras PATCH de estado).",
        ),
    },
)

restaurant_order_create_response_model = Model(
    "RestaurantOrderCreateResponse",
    {
        "id": fields.String(pattern=_UUID_STRING_PATTERN),
        "restaurantId": fields.String(pattern=_UUID_STRING_PATTERN),
        "userId": fields.String(pattern=_UUID_STRING_PATTERN),
        "status": fields.String(pattern=_ORDER_STATUS_STRING_PATTERN, example="PENDING"),
        "totalAmount": fields.String(example="3500.00"),
        "notes": fields.String(allow_null=True),
        "estimatedReadyAt": fields.String(allow_null=True),
        "createdAt": fields.String(),
        "items": fields.List(
            fields.Nested(restaurant_order_item_admin_model),
            description="Líneas del pedido creado.",
        ),
    },
)

paginated_restaurant_orders_admin_model = Model(
    "PaginatedRestaurantOrdersAdmin",
    {
        "data": fields.List(fields.Nested(restaurant_order_list_admin_model)),
        "total": fields.Integer(example=8),
        "page": fields.Integer(example=1),
        "perPage": fields.Integer(example=20),
    },
)

restaurant_order_status_patch_model = Model(
    "RestaurantOrderStatusPatch",
    {
        "status": fields.String(
            required=True,
            description="Nuevo estado. Flujo: PENDING -> CONFIRMED -> READY -> COMPLETED.",
            example="CONFIRMED",
            pattern=_ORDER_STATUS_STRING_PATTERN,
        ),
        "estimatedReadyAt": fields.String(
            required=False,
            description="Opcional. Hora estimada de listo (ISO 8601, con offset o Z).",
            example="2026-04-25T20:30:00+00:00",
        ),
    },
)

_DISCOUNT_TYPE_PATTERN = r"^(PERCENTAGE|FIXED_AMOUNT|FREE_ITEM)$"

promotion_response_model = Model(
    "PromotionResponse",
    {
        "id": fields.String(
            description="ID de la promoción (UUID).",
            pattern=_UUID_STRING_PATTERN,
        ),
        "restaurantId": fields.String(
            description="ID del restaurante (UUID).",
            pattern=_UUID_STRING_PATTERN,
        ),
        "title": fields.String(description="Título de la oferta.", example="2x1 en postres"),
        "description": fields.String(
            description="Texto descriptivo (opcional).",
            allow_null=True,
        ),
        "discountType": fields.String(
            description="PERCENTAGE | FIXED_AMOUNT | FREE_ITEM",
            example="PERCENTAGE",
            pattern=_DISCOUNT_TYPE_PATTERN,
        ),
        "discountValue": fields.String(
            description="Valor asociado al tipo (ej. porcentaje o monto, ≥ 0).",
            example="15.00",
        ),
        "startDate": fields.String(description="Inicio (YYYY-MM-DD).", example="2026-05-01"),
        "endDate": fields.String(description="Fin (YYYY-MM-DD).", example="2026-05-31"),
        "isActive": fields.Boolean(description="Vigente según negocio (activo/inactivo).", example=True),
        "notifyUsers": fields.Boolean(
            description="Si al crear con true se intenta notificar a usuarios suscriptos al restaurante.",
            example=False,
        ),
        "createdAt": fields.String(description="Fecha de creación ISO 8601 UTC."),
        "menuItemIds": fields.List(
            fields.String(pattern=_UUID_STRING_PATTERN),
            description="IDs de platos del menú incluidos en la oferta (vacío = aplica a criterio de negocio / sin filas).",
        ),
    },
)

promotion_create_model = Model(
    "PromotionCreateRequest",
    {
        "title": fields.String(
            required=True,
            description="Título de la promoción.",
            example="20% de descuento en bebidas",
            min_length=1,
            max_length=200,
        ),
        "description": fields.String(
            required=False,
            description="Descripción (opcional).",
            allow_null=True,
        ),
        "discountType": fields.String(
            required=True,
            description="PERCENTAGE, FIXED_AMOUNT o FREE_ITEM",
            example="PERCENTAGE",
            pattern=_DISCOUNT_TYPE_PATTERN,
        ),
        "discountValue": fields.String(
            required=True,
            description="Valor numérico (≥ 0). Uso según discountType (ej. %, monto fijo).",
            example="20.00",
        ),
        "startDate": fields.String(
            required=True,
            description="Fecha de inicio (YYYY-MM-DD).",
            example="2026-05-01",
        ),
        "endDate": fields.String(
            required=True,
            description="Fecha de fin (YYYY-MM-DD), ≥ startDate.",
            example="2026-05-15",
        ),
        "notifyUsers": fields.Boolean(
            required=False,
            description="Si true, se intenta enviar notificación a usuarios con avisos de promos (solo creación).",
            default=False,
        ),
        "menuItemIds": fields.List(
            fields.String(pattern=_UUID_STRING_PATTERN),
            required=False,
            description="Platos de este restaurante a los que aplica (opcional).",
        ),
    },
)

promotions_admin_list_envelope_model = Model(
    "PromotionsAdminListResponse",
    {
        "data": fields.List(
            fields.Nested(promotion_response_model),
            description="Todas las promociones del restaurante (admin).",
        ),
        "total": fields.Integer(example=3),
        "page": fields.Integer(example=1),
        "perPage": fields.Integer(example=3),
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
        "totalOrders": fields.Integer(
            description="Cantidad de pedidos del periodo.",
            example=340,
        ),
        "totalReservations": fields.Integer(
            description="Cantidad de reservas del periodo.",
            example=145,
        ),
        "totalRevenue": fields.String(
            description="Ingresos totales de pedidos en el periodo.",
            example="850000.00",
            pattern=r"^\d+(\.\d{2})$",
        ),
        "averageOrderValue": fields.String(
            description="Ticket promedio de pedidos en el periodo.",
            example="2500.00",
            pattern=r"^\d+(\.\d{2})$",
        ),
        "totalCovers": fields.Integer(
            description="Cantidad total de comensales reservados.",
            example=582,
        ),
        "completedReservations": fields.Integer(
            description="Cantidad de reservas completadas.",
            example=104,
        ),
        "cancelledReservations": fields.Integer(
            description="Cantidad de reservas canceladas.",
            example=16,
        ),
        "noShowReservations": fields.Integer(
            description="Cantidad de reservas marcadas como no-show.",
            example=5,
        ),
    },
)

reservation_table_assignment_item_model = Model(
    "ReservationTableAssignmentItem",
    {
        "tableId": fields.String(
            description="ID de la mesa asignada (UUID).",
            pattern=_UUID_STRING_PATTERN,
            example="018f1234-5678-7abc-8def-123456789abf",
        ),
        "number": fields.Integer(
            description="Numero de mesa dentro del restaurante.",
            example=12,
        ),
        "capacity": fields.Integer(
            description="Capacidad de la mesa.",
            example=4,
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
            pattern=_DATE_PATTERN,
            example="2026-04-22",
        ),
        "timeSlot": fields.String(
            description="Horario de la reserva (HH:MM:SS).",
            pattern=_TIME_PATTERN,
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
        "tableAssignment": fields.List(
            fields.Nested(reservation_table_assignment_item_model),
            description="Mesas asignadas para la reserva en el turno solicitado.",
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
            pattern=_DATE_PATTERN,
            example="2026-05-10",
        ),
        "timeSlot": fields.String(
            required=True,
            description="Horario de la reserva (HH:MM o HH:MM:SS).",
            pattern=_TIME_PATTERN,
            example="21:00:00",
        ),
        "notes": fields.String(
            required=False,
            allow_null=True,
            description="Notas adicionales de la reserva.",
            max_length=2000,
            example="Mesa tranquila, por favor.",
        ),
        "source": fields.String(
            required=False,
            description=(
                "Reservation origin. Omit or use ONLINE for customer self-service. "
                "PHONE and EVENT require restaurant-admin permissions."
            ),
            pattern=_RESERVATION_SOURCE_PATTERN,
            example="ONLINE",
        ),
        "guestName": fields.String(
            required=False,
            allow_null=True,
            description="Guest/group name for admin-created PHONE/EVENT reservations.",
            max_length=150,
            example="Grupo Perez",
        ),
        "guestPhone": fields.String(
            required=False,
            allow_null=True,
            description="Guest/group contact phone for admin-created PHONE/EVENT reservations.",
            pattern=_PHONE_PATTERN,
            example="+54 11 4444-5555",
        ),
        "guestEmail": fields.String(
            required=False,
            allow_null=True,
            description="Guest/group contact email for admin-created PHONE/EVENT reservations.",
            pattern=_EMAIL_PATTERN,
            max_length=255,
            example="grupo@example.com",
        ),
        "userId": fields.String(
            required=False,
            allow_null=True,
            description="Registered user UUID to associate with an admin-created reservation.",
            pattern=_UUID_STRING_PATTERN,
            example="018f1234-5678-7abc-8def-123456789abc",
        ),
    },
)

availability_slot_model = Model(
    "AvailabilitySlot",
    {
        "timeSlot": fields.String(
            description="Horario del turno disponible.",
            pattern=_TIME_PATTERN,
            example="20:30:00",
        ),
        "available": fields.Boolean(
            description="Indica si el turno esta disponible.",
            example=True,
        ),
        "tableAssignment": fields.List(
            fields.Nested(reservation_table_assignment_item_model),
            description="Mesas sugeridas para cubrir el tamano del grupo.",
        ),
    },
)

availability_response_model = Model(
    "AvailabilityResponse",
    {
        "date": fields.String(
            description="Fecha consultada (YYYY-MM-DD).",
            pattern=_DATE_PATTERN,
            example="2026-05-10",
        ),
        "partySize": fields.Integer(
            description="Tamano del grupo consultado.",
            example=4,
        ),
        "slots": fields.List(
            fields.Nested(availability_slot_model),
            description="Turnos con disponibilidad y sugerencia de mesas.",
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
            pattern=_DATE_PATTERN,
            example="2026-05-10",
        ),
        "timeSlot": fields.String(
            required=True,
            description="Horario de la reserva (HH:MM o HH:MM:SS).",
            pattern=_TIME_PATTERN,
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

# ── Tables ──────────────────────────────────────────────────────────────────

reservation_status_patch_model = Model(
    "ReservationStatusPatchRequest",
    {
        "status": fields.String(
            required=True,
            description="Target reservation status: CANCELLED, COMPLETED, or NO_SHOW.",
            pattern=r"^(CANCELLED|COMPLETED|NO_SHOW)$",
            example="CANCELLED",
        ),
        "reason": fields.String(
            required=False,
            description="Optional cancellation reason. Used only when status=CANCELLED.",
            max_length=500,
            example="El cliente aviso que no podia asistir.",
        ),
    },
)

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

table_collection_create_model = Model(
    "TableCollectionCreateRequest",
    {
        "number": fields.Integer(
            required=False,
            description="Single-table number. Required when groups is omitted.",
            min=1,
            example=5,
        ),
        "capacity": fields.Integer(
            required=False,
            description="Single-table capacity. Required when groups is omitted.",
            min=1,
            example=4,
        ),
        "name": fields.String(
            required=False,
            allow_null=True,
            description="Optional descriptive name for single-table creation.",
            max_length=100,
            example="Mesa del jardin",
        ),
        "isJoinable": fields.Boolean(
            required=False,
            description="Whether the single table can be joined with others.",
            example=True,
        ),
        "groups": fields.List(
            fields.Nested(table_group_model),
            required=False,
            description=(
                "Bulk-create groups. When present, number/capacity/name are ignored "
                "and the response is a paginated table list."
            ),
        ),
    },
)

business_hours_range_model = Model(
    "BusinessHoursRange",
    {
        "opensAt": fields.String(
            required=True,
            description="Hora de apertura del tramo (HH:MM).",
            example="11:00",
        ),
        "closesAt": fields.String(
            required=True,
            description="Hora de cierre del tramo (HH:MM). Debe ser posterior a opensAt.",
            example="15:00",
        ),
    },
)

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
            description="Si el restaurante está cerrado ese día. "
            "Cuando es true se ignoran los ranges y se eliminan los existentes.",
            example=False,
        ),
        "ranges": fields.List(
            fields.Nested(business_hours_range_model),
            required=False,
            description="Tramos de apertura del día. Requerido (mínimo 1) cuando isClosed=false. "
            "Los tramos no pueden superponerse y deben tener closesAt > opensAt.",
            example=[{"opensAt": "11:00", "closesAt": "15:00"}, {"opensAt": "19:00", "closesAt": "23:30"}],
        ),
    },
)

business_hours_bulk_update_model = Model(
    "BusinessHoursBulkUpdateRequest",
    {
        "hours": fields.List(
            fields.Nested(business_hours_item_model),
            required=True,
            description="Lista de días a actualizar. Puede ser parcial (solo los días que cambian).",
        )
    },
)

business_hours_response_model = Model(
    "BusinessHoursResponse",
    {
        "dayOfWeek": fields.Integer(description="0=Lunes, 6=Domingo.", example=0),
        "dayName": fields.String(description="Nombre del día en español.", example="Lunes"),
        "isClosed": fields.Boolean(description="True si no hay tramos configurados.", example=False),
        "ranges": fields.List(
            fields.Nested(business_hours_range_model),
            description="Tramos de apertura del día, ordenados por hora de inicio.",
        ),
    },
)

paginated_business_hours_response_model = Model(
    "PaginatedBusinessHoursResponse",
    {
        "data": fields.List(
            fields.Nested(business_hours_response_model),
            description="Horarios del restaurante (7 entradas, una por día).",
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
