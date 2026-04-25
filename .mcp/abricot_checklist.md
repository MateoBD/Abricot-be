# Abricot — Checklist de Implementación

Cada ítem es una unidad de trabajo atómica. Marcar con `[x]` al completar.
Los ítems marcados con ✅ ya existen y están correctos. Los marcados con 🔧 existen pero necesitan modificación.

---

## 0. Basics (cimientos — alineado con `backend_tickets.md` § Basics)

> Objetivo: cerrar el “módulo Basics” antes o en paralelo con el resto del dominio. Ver también **Backend: Basics** en `backend_tickets.md`.

### 0.1 Auth y tokens
- [x] `POST /auth/register`, `POST /auth/login`, `POST /auth/refresh` (`app/api/auth/routes.py`, `AuthService`)
- [x] JWT access + refresh configurados (`app/config.py`, Flask-JWT-Extended)
- [x] `require_authentication()` y `require_refresh_token()` (`app/middleware/auth.py`)

### 0.2 Usuario, roles y perfil (pendiente de propuesta completa)
- [x] `UserModel` — columna `role` + enum `UserRole` (`app/models/enums.py`, default `CUSTOMER`)
- [x] `user_summary` / respuestas auth — campo `role` en JSON (`app/api/auth/schemas.py`, `UserModel.to_dict()`); `id` como UUID string (§1)
- [x] `UserService` + rutas `GET /users/{user_id}`, `PUT /users/{user_id}`, `PUT /users/{user_id}/password` (schemas §7.13); el `user_id` de la URL debe coincidir con el sujeto del JWT (`require_path_user_matches_jwt`)
- [x] `GET /users/{user_id}/restaurants/` — implementado en `UserService.get_my_restaurants` + ruta `/users/{id}/restaurants`

### 0.3 Operación y permisos
- [x] `GET /health` (o `/status`) — liveness para balanceadores / k8s
- [x] `GET /version` — semver o git sha expuesto de forma segura
- [x] `require_restaurant_admin(restaurant_id_param)` — §6; validación estricta por restaurante vía `restaurant_admins` + bypass para `SUPER_ADMIN`

### 0.4 Infra transversal ya cubierta (Basics / chores)
- [x] Manejo centralizado de errores API (`AppError`, handlers en `app/api/__init__.py`)
- [x] Logging (`app/logging_config.py`)
- [x] Migraciones Alembic existentes para `users` y `restaurants` (más allá: §1 del checklist)
- [x] Swagger en raíz (`Flask-RESTX` en `register_blueprints`)

---

## 1. Migraciones de Base de Datos

> **Todos los campos `id` son UUID v7** (tipo `UUID` en PostgreSQL, generado en la capa de aplicación o con `gen_random_uuid()` en PG ≥ 13 + extensión `pgcrypto`). Todas las FK referencian esos UUIDs. No usar `SERIAL` ni `BIGSERIAL`.
> Estado actual: migración a UUID v7 aplicada en modelos y migración Alembic; ver §1.1.

### 1.1 Modificar tablas existentes
- [x] `users` — columna `role` (string `UserRole`, default `CUSTOMER`, índice) — migración `c8f4a2b91d3e` (`2026-04-19T12-00-00_add_user_role.py`)
- [x] `users` — cambiar `id` de `int` a `uuid v7` (PK)
- [x] `restaurants` — cambiar `id` de `int` a `uuid v7` (PK); agregar `city_id FK (uuid)`, `neighbourhood_id FK (uuid, nullable)`, `price_range_id FK (uuid, nullable)`, `allow_table_joining` (bool, default false), `default_slot_duration_minutes` (int, default 90)
- [x] `restaurants` — eliminar columnas de strings de ubicación si existían (`country`, `city`, `province`, `neighbourhood`)

### 1.2 Tablas de referencia (lookup — pre-seed)
- [x] `countries` — id (uuid v7), name, iso_code
- [x] `provinces` — id (uuid v7), country_id (uuid FK), name
- [x] `cities` — id (uuid v7), province_id (uuid FK), name
- [x] `neighbourhoods` — id (uuid v7), city_id (uuid FK), name
- [x] `price_ranges` — id (uuid v7), slug, label, description, sort_order
- [x] `cuisine_types` — id (uuid v7), slug, label

### 1.3 Tablas transversales
- [x] `restaurant_admins` — id (uuid v7), user_id (uuid FK), restaurant_id (uuid FK), UNIQUE(user_id, restaurant_id)
- [x] `restaurant_cuisines` — id (uuid v7), restaurant_id (uuid FK), cuisine_type_id (uuid FK), UNIQUE(restaurant_id, cuisine_type_id)
- [x] `notification_preferences` — id (uuid v7), user_id (uuid FK), restaurant_id (uuid FK), receive_promotions, receive_order_updates, receive_reservation_reminders, UNIQUE(user_id, restaurant_id)

### 1.4 F1 — Mesas y Horarios
- [x] `tables` — id (uuid v7), restaurant_id (uuid FK), number, capacity, name, is_joinable, is_active, UNIQUE(restaurant_id, number)
- [x] `business_hours` — id (uuid v7), restaurant_id (uuid FK), day_of_week, opens_at, closes_at, is_closed, UNIQUE(restaurant_id, day_of_week)

### 1.5 F2 — Reservas
- [x] `reservations` — id (uuid v7), restaurant_id (uuid FK), user_id (uuid FK, nullable), guest_name, guest_phone, guest_email, source (enum), party_size, date, time_slot, status (enum), notes, confirmation_code UK, created_at
- [x] `reservation_tables` — id (uuid v7), reservation_id (uuid FK), table_id (uuid FK), UNIQUE(reservation_id, table_id)

### 1.6 F3 — Menú y Pedidos
- [x] `menus` — id (uuid v7), restaurant_id (uuid FK), name, is_active, created_at
- [x] `menu_categories` — id (uuid v7), menu_id (uuid FK), name, display_order, is_active
- [x] `menu_items` — id (uuid v7), category_id (uuid FK), name, description, price, photo_url, is_available, created_at
- [x] `orders` — id (uuid v7), restaurant_id (uuid FK), user_id (uuid FK), status (enum), total_amount, notes, estimated_ready_at, created_at
- [x] `order_items` — id (uuid v7), order_id (uuid FK), menu_item_id (uuid FK), quantity, unit_price, notes

### 1.7 F4 — Promociones
- [x] `promotions` — id (uuid v7), restaurant_id (uuid FK), title, description, discount_type (enum), discount_value, start_date, end_date, is_active, notify_users, created_at
- [x] `promotion_items` — id (uuid v7), promotion_id (uuid FK), menu_item_id (uuid FK), UNIQUE(promotion_id, menu_item_id)

### 1.8 Seed inicial
- [x] Seed de `price_ranges` (4 filas: ECONOMICO $, MODERADO $$, ELEGANTE $$$, EXCLUSIVO $$$$)
- [x] Seed de `cuisine_types` (14 filas: ARGENTINA, ITALIANA, JAPONESA, MEDITERRANEA, MEXICANA, PERUANA, AMERICANA, CHINA, FRANCESA, CAFE_BAR, VEGANA_VEGETARIANA, MARISCOS, FUSION, OTRA)
- [x] Seed de ubicación base: `countries/provinces/cities/neighbourhoods` para Argentina > Buenos Aires > Buenos Aires (CABA) + 48 barrios
- [x] Seed de categorías default en `menu_categories` para menús existentes (`Entradas`, `Principales`, `Postres`, `Bebidas`)

---

## 2. Modelos SQLAlchemy (app/models/)

### 2.1 Modificar modelos existentes
- [x] `UserModel` — `role: Mapped[UserRole]` + `app/models/enums.py`
- [x] `UserModel` — cambiar `id` a `Mapped[uuid]` con `default=uuid7` (pendiente §1)
- [x] `RestaurantModel` — cambiar `id` a `Mapped[uuid]` con `default=uuid7`; agregar `city_id (uuid FK)`, `neighbourhood_id (uuid FK)`, `price_range_id (uuid FK)`, `allow_table_joining`, `default_slot_duration_minutes`; relaciones ORM con `City`, `Neighbourhood`, `PriceRange`, `RestaurantCuisine`

### 2.2 Nuevos modelos de referencia
- [x] `CountryModel` (`app/models/location.py`)
- [x] `ProvinceModel` (`app/models/location.py`)
- [x] `CityModel` (`app/models/location.py`)
- [x] `NeighbourhoodModel` (`app/models/location.py`)
- [x] `PriceRangeModel` (`app/models/price_range.py`)
- [x] `CuisineTypeModel` (`app/models/cuisine_type.py`)

### 2.3 Nuevos modelos transversales
- [x] `RestaurantAdminModel` (`app/models/restaurant_admin.py`)
- [x] `RestaurantCuisineModel` (`app/models/restaurant_cuisine.py`)
- [x] `NotificationPreferenceModel` (`app/models/notification_preference.py`)

### 2.4 F1 — Mesas y Horarios
- [x] `TableModel` (`app/models/table.py`)
- [x] `BusinessHoursModel` (`app/models/business_hours.py`)

### 2.5 F2 — Reservas
- [x] `ReservationModel` (`app/models/reservation.py`) — con `user_id` nullable, campos de huésped, `source`
- [x] `ReservationTableModel` (`app/models/reservation_table.py`)

### 2.6 F3 — Menú y Pedidos
- [x] `MenuModel` (`app/models/menu.py`)
- [x] `MenuCategoryModel` (`app/models/menu_category.py`)
- [x] `MenuItemModel` (`app/models/menu_item.py`)
- [x] `OrderModel` (`app/models/order.py`) — sin `order_type` ni `delivery_address`
- [x] `OrderItemModel` (`app/models/order_item.py`)

### 2.7 F4 — Promociones
- [x] `PromotionModel` (`app/models/promotion.py`)
- [x] `PromotionItemModel` (`app/models/promotion_item.py`)

---

## 3. Enums (app/models/enums.py o por módulo)

- [x] `UserRole` — CUSTOMER, RESTAURANT_ADMIN, SUPER_ADMIN (`app/models/enums.py`)
- [x] `ReservationSource` — ONLINE, PHONE, EVENT
- [x] `ReservationStatus` — CONFIRMED, CANCELLED, COMPLETED, NO_SHOW
- [x] `OrderStatus` — PENDING, CONFIRMED, IN_PREPARATION, READY, COMPLETED, CANCELLED
- [x] `DiscountType` — PERCENTAGE, FIXED_AMOUNT, FREE_ITEM

---

## 4. Repositorios (app/repositories/)

### 4.1 Modificar repositorios existentes
- [x] `UserRepository` — `update_role(user_id, role)`; `create(..., role=...)` opcional (default `CUSTOMER`)
- [x] `RestaurantRepository` — reemplazar `get_all()` por `search(filters)` con JOINs a `cities`, `price_ranges`, `restaurant_cuisines`; actualizar `create()` y `update()` para manejar `cuisine_type_ids`

### 4.2 Nuevos repositorios de referencia
- [x] `LookupRepository` — métodos para countries, provinces, cities, neighbourhoods, price_ranges, cuisine_types; `get_or_create_city`, `get_or_create_neighbourhood`

### 4.3 Transversales
- [x] `RestaurantAdminRepository` — `is_admin(user_id, restaurant_id)`, `add(user_id, restaurant_id)`, `remove(user_id, restaurant_id)`, `get_restaurants_for_user(user_id)`
- [x] `NotificationPreferenceRepository` — `get_by_user(user_id)`, `get_or_create(user_id, restaurant_id)`, `update(...)`, `get_subscribed_emails(restaurant_id, field)`

### 4.4 F1
- [x] `TableRepository` — `get_all(restaurant_id)`, `get_by_id(restaurant_id, table_id)`, `get_max_number(restaurant_id)`, `bulk_insert(tables)`, `get_active(restaurant_id)`
- [x] `BusinessHoursRepository` — `get_all(restaurant_id)`, `upsert_bulk(restaurant_id, data)`, `get_for_date(restaurant_id, day_of_week)`

### 4.5 F2
- [x] `ReservationRepository` — `create(reservation)`, `get_by_id(id)`, `get_by_code(code)`, `list_for_restaurant(restaurant_id, filters, page, per_page)`, `get_occupied_table_ids_at(restaurant_id, date, time_slot)`
- [x] `ReservationTableRepository` — `create_bulk(reservation_id, table_ids)`, `delete_by_reservation(reservation_id)`

### 4.6 F3
- [x] `MenuRepository` — `get_all(restaurant_id)`, `get_by_id(restaurant_id, menu_id)`, `get_active(restaurant_id)`, `deactivate_all(restaurant_id)`
- [x] `MenuCategoryRepository` — `get_all(menu_id)`, `get_by_id(menu_id, cat_id)`, `bulk_reorder(ordered_ids)`
- [x] `MenuItemRepository` — `get_all(category_id)`, `get_by_id(item_id)`, `validate_items_for_restaurant(item_ids, restaurant_id)`
- [x] `OrderRepository` — `create(order)`, `get_by_id(order_id)`, `list_for_restaurant(restaurant_id, filters, page, per_page)`, `list_for_user(user_id, page, per_page)`
- [x] `OrderItemRepository` — `bulk_insert(order_id, items)`

### 4.7 F4
- [x] `PromotionRepository` — `get_active(restaurant_id)`, `get_all(restaurant_id)`, `get_global_feed()`, `get_by_id(restaurant_id, promo_id)`
- [x] `PromotionItemRepository` — `replace_items(promotion_id, menu_item_ids)`

---

## 5. Servicios (app/services/)

### 5.1 Modificar servicios existentes
- [x] 🔧 `RestaurantService.get_all()` → renombrar a `search(name?, country_id?, province_id?, city_id?, neighbourhood_id?, price_range_id?, cuisine_type_ids?, page, per_page)`
- [x] 🔧 `RestaurantService.create()` — aceptar `city_id`, `neighbourhood_id`, `price_range_id`, `cuisine_type_ids`; crear fila en `RestaurantAdmin` y elevar rol en la misma transacción
- [x] 🔧 `RestaurantService.update()` — aceptar nuevos campos; reemplazar `RestaurantCuisine` (delete + insert)

### 5.2 LookupService (nuevo)
- [x] `LookupService.get_all_cuisines()`
- [x] `LookupService.get_all_price_ranges()`
- [x] `LookupService.get_all_countries()`
- [x] `LookupService.get_provinces_by_country(country_id)`
- [x] `LookupService.get_cities_by_province(province_id)`
- [x] `LookupService.get_neighbourhoods_by_city(city_id)`
- [x] `LookupService.get_or_create_city(city_name, province_id)`
- [x] `LookupService.get_or_create_neighbourhood(neighbourhood_name, city_id)`

### 5.3 UserService (nuevo)
- [x] `UserService.get_profile(user_id)`
- [x] `UserService.update_profile(user_id, name, surname)`
- [x] `UserService.change_password(user_id, current_password, new_password)`
- [x] `UserService.get_my_reservations(user_id, page, per_page)`
- [x] `UserService.get_my_orders(user_id, page, per_page)`
- [x] `UserService.get_my_restaurants(user_id)`

### 5.4 RestaurantAdminService (nuevo)
- [x] `RestaurantAdminService.is_admin(user_id, restaurant_id)`
- [x] `RestaurantAdminService.add_admin(restaurant_id, user_id)` — crea fila + eleva rol si CUSTOMER
- [x] `RestaurantAdminService.remove_admin(restaurant_id, user_id)` — baja rol si ya no tiene restaurantes
- [x] `RestaurantAdminService.get_restaurants_for_admin(user_id)`

### 5.5 TableService (nuevo — F1)
- [x] `TableService.get_all(restaurant_id)`
- [x] `TableService.get_by_id(restaurant_id, table_id)`
- [x] `TableService.create(restaurant_id, number, capacity, name, is_joinable)`
- [x] `TableService.create_bulk(restaurant_id, groups)` — grupos: `[{quantity, capacity, isJoinable?}]`; numeración secuencial; una transacción
- [x] `TableService.update(restaurant_id, table_id, ...)`
- [x] `TableService.delete(restaurant_id, table_id)` — falla si tiene reservas futuras confirmadas
- [x] `TableService.get_total_capacity(restaurant_id)`

### 5.6 BusinessHoursService (nuevo — F1)
- [x] `BusinessHoursService.get_all(restaurant_id)`
- [x] `BusinessHoursService.bulk_update(restaurant_id, hours_data)` — upsert 7 filas
- [x] `BusinessHoursService.is_open_on(restaurant_id, date)`
- [x] `BusinessHoursService.get_time_range(restaurant_id, date)` → `(opens_at, closes_at) | None`

### 5.7 AvailabilityService (nuevo — F1, corazón de F2)
- [x] `AvailabilityService.get_available_slots(restaurant_id, date, party_size)` — genera todos los slots del día y ejecuta `find_table_assignment` para cada uno
- [x] `AvailabilityService.find_table_assignment(restaurant_id, date, time_slot, party_size)` → `list[TableModel] | None` — algoritmo: primero mesa individual; si `allow_table_joining=True`, luego combinaciones de mesas `is_joinable`; mínimo desperdicio
- [x] `AvailabilityService.assign_tables_for_reservation(reservation_id, table_ids)` — crea filas en `reservation_tables` dentro de una transacción
- [x] `AvailabilityService.get_occupied_table_ids_at(restaurant_id, date, time_slot)` → `set[uuid]`

### 5.8 ReservationService (nuevo — F2)
- [x] `ReservationService.create(restaurant_id, user_id, party_size, date, time_slot, notes)` — `source=ONLINE`; auto-confirma; transacción atómica con `SELECT FOR UPDATE`
- [x] `ReservationService.create_for_admin(restaurant_id, admin_user_id, party_size, date, time_slot, source, guest_name, guest_phone, guest_email, user_id, notes)` — valida `user_id XOR guest_name`; `source ∈ {PHONE, EVENT}`
- [x] `ReservationService.get_by_id(reservation_id, requesting_user_id)` — valida ownership o admin
- [x] `ReservationService.get_by_confirmation_code(code)` — público
- [x] `ReservationService.list_for_restaurant(restaurant_id, date_from, date_to, status, source, page, per_page)`
- [x] `ReservationService.reassign_tables(reservation_id, table_ids)` — valida disponibilidad en el slot
- [x] `ReservationService.cancel(reservation_id, requesting_user_id, reason)` — libera mesas; notifica
- [x] `ReservationService.complete(reservation_id)`
- [x] `ReservationService.mark_no_show(reservation_id)` — libera mesas

### 5.9 MenuService (nuevo — F3)
- [x] `MenuService.get_all(restaurant_id)`
- [x] `MenuService.get_by_id(restaurant_id, menu_id)`
- [x] `MenuService.get_detail(restaurant_id, menu_id)` — incluye categorías e ítems anidados
- [x] `MenuService.create(restaurant_id, name)`
- [x] `MenuService.update(restaurant_id, menu_id, name)`
- [x] `MenuService.delete(restaurant_id, menu_id)`
- [x] `MenuService.activate(restaurant_id, menu_id)` — desactiva el anterior en la misma transacción
- [x] `MenuService.get_active_menu(restaurant_id)`

### 5.10 MenuCategoryService (nuevo — F3)
- [x] `MenuCategoryService.get_all(menu_id)`
- [x] `MenuCategoryService.create(menu_id, name, display_order)`
- [x] `MenuCategoryService.update(menu_id, category_id, name, display_order, is_active)`
- [x] `MenuCategoryService.delete(menu_id, category_id)`
- [x] `MenuCategoryService.reorder(menu_id, ordered_ids)` — asigna `display_order = índice`

### 5.11 MenuItemService (nuevo — F3)
- [x] `MenuItemService.get_all(category_id)`
- [x] `MenuItemService.get_by_id(item_id)`
- [x] `MenuItemService.create(category_id, name, description, price, is_available)`
- [x] `MenuItemService.update(item_id, name, description, price, is_available)`
- [x] `MenuItemService.delete(item_id)`
- [x] `MenuItemService.upload_photo(item_id, file_storage)` — reutiliza `S3Client`
- [x] `MenuItemService.set_availability(item_id, is_available)`

### 5.12 OrderService (nuevo — F3)
- [x] `OrderService.create(restaurant_id, user_id, items, notes)` — sin `order_type`; snapshot de precios; valida ítems en menú activo
- [x] `OrderService.get_by_id(order_id, requesting_user_id)`
- [x] `OrderService.list_for_restaurant(restaurant_id, status_filter, page, per_page)`
- [x] `OrderService.update_status(order_id, new_status, estimated_ready_at)` — valida transición válida
- [x] `OrderService.cancel(order_id, requesting_user_id)` — solo si `status=PENDING`

### 5.13 PromotionService (nuevo — F4)
- [x] `PromotionService.get_all_active(restaurant_id)`
- [x] `PromotionService.get_all_for_admin(restaurant_id)` — incluye inactivas
- [x] `PromotionService.get_feed()` — todas las activas en la plataforma
- [x] `PromotionService.get_by_id(restaurant_id, promotion_id)`
- [x] `PromotionService.create(restaurant_id, title, description, discount_type, discount_value, start_date, end_date, notify_users, menu_item_ids)` — si `notify_users=True`, dispara notificación asíncrona
- [x] `PromotionService.update(restaurant_id, promotion_id, ...)`
- [x] `PromotionService.deactivate(restaurant_id, promotion_id)`
- [x] `PromotionService.activate(restaurant_id, promotion_id)`
- [x] `PromotionService.delete(restaurant_id, promotion_id)`

### 5.14 NotificationService (nuevo — F2, F3, F4)
- [x] `NotificationService.send_reservation_confirmation(reservation_id)` — a `user.email` o `guest_email`
- [x] `NotificationService.send_reservation_cancelled(reservation_id)`
- [x] `NotificationService.send_order_confirmation(order_id)`
- [x] `NotificationService.send_order_status_update(order_id)`
- [x] `NotificationService.send_promotion_notification(promotion_id)` — a todos los suscriptos con `receive_promotions=True`
- [x] `NotificationService._get_subscribed_user_emails(restaurant_id, preference_field)` — interno

### 5.15 NotificationPreferenceService (nuevo)
- [x] `NotificationPreferenceService.get_all_for_user(user_id)`
- [x] `NotificationPreferenceService.get_or_create(user_id, restaurant_id)`
- [x] `NotificationPreferenceService.update(user_id, restaurant_id, receive_promotions, receive_order_updates, receive_reservation_reminders)`

### 5.16 AnalyticsService (nuevo — F5)
- [x] `AnalyticsService.get_occupancy_report(restaurant_id, date_from, date_to)`
- [x] `AnalyticsService.get_orders_report(restaurant_id, date_from, date_to)`
- [x] `AnalyticsService.get_popular_items(restaurant_id, date_from, date_to, limit)`
- [x] `AnalyticsService.get_promotions_report(restaurant_id, date_from, date_to)`
- [x] `AnalyticsService.get_peak_hours(restaurant_id, date_from, date_to)`

---

## 6. Middleware y Guards (app/middleware/)

- [x] ✅ `require_authentication()` — verifica access token
- [x] ✅ `require_refresh_token()` — verifica refresh token
- [x] `require_restaurant_admin(restaurant_id_param)` — verifica pertenencia del usuario al restaurante (`restaurant_admins`) y admite `SUPER_ADMIN`

---

## 7. Schemas Flask-RESTX (app/api/.../schemas.py)

### 7.1 Lookup
- [x] `CuisineTypeResponse` (inline en `lookup_routes.py`)
- [x] `PriceRangeResponse` (inline en `lookup_routes.py`)
- [x] `CountryResponse` (inline en `lookup_routes.py`)
- [x] `ProvinceResponse` (inline en `lookup_routes.py`)
- [x] `CityResponse` (inline en `lookup_routes.py`)
- [x] `NeighbourhoodResponse` (inline en `lookup_routes.py`)

### 7.2 Restaurante
- [x] `RestaurantCreateRequest` — con `cityId`, `neighbourhoodId?`, `priceRangeId?`, `cuisineTypeIds[]`
- [x] `RestaurantUpdateRequest` — ídem
- [x] `RestaurantResponse` — con IDs de ciudad/barrio/precio + `cuisineTypeIds[]`
- [x] `RestaurantListResponse` (`PaginatedRestaurantListResponse`)

### 7.3 Mesas
- [x] `TableCreateRequest`
- [x] `TableUpdateRequest`
- [x] `TableBulkCreateRequest` + `TableBulkGroup`
- [x] `TableResponse`
- [x] `PaginatedTableListResponse`

### 7.4 Horarios
- [x] `BusinessHoursBulkUpdateRequest` + `BusinessHoursItem`
- [x] `BusinessHoursResponse`
- [x] `PaginatedBusinessHoursResponse`

### 7.5 Disponibilidad
- [x] `AvailabilityResponse` — con `slots[].tableAssignment`

### 7.6 Reservas
- [x] `ReservationCreateRequest` — cliente
- [x] `ReservationAdminCreateRequest` — admin
- [ ] `ReservationReassignTablesRequest`
- [x] `ReservationCancelRequest`
- [x] `ReservationResponse`
- [x] `PaginatedReservationListResponse`

### 7.7 Menús
- [ ] `MenuCreateRequest` / `MenuUpdateRequest`
- [ ] `MenuResponse`
- [ ] `MenuDetailResponse` — con categorías e ítems anidados

### 7.8 Categorías
- [ ] `MenuCategoryCreateRequest` / `MenuCategoryUpdateRequest`
- [ ] `MenuCategoryReorderRequest`
- [ ] `MenuCategoryResponse`
- [ ] `MenuCategoryDetailResponse` — con ítems anidados

### 7.9 Ítems de Menú
- [ ] `MenuItemCreateRequest` / `MenuItemUpdateRequest`
- [ ] `MenuItemAvailabilityRequest`
- [ ] `MenuItemResponse`

### 7.10 Pedidos
- [ ] `OrderCreateRequest` — sin `orderType` ni `deliveryAddress`
- [ ] `OrderStatusUpdateRequest`
- [ ] `OrderItemResponse`
- [ ] `OrderResponse`
- [ ] `OrderListResponse`

### 7.11 Promociones
- [ ] `PromotionCreateRequest` / `PromotionUpdateRequest`
- [ ] `PromotionResponse`

### 7.12 Notificaciones
- [ ] `NotificationPreferenceUpdateRequest`
- [ ] `NotificationPreferenceResponse`

### 7.13 Usuario
- [x] `UserProfileUpdateRequest`
- [x] `UserPasswordChangeRequest`
- [x] `UserProfileResponse`
- [x] `PaginatedUserReservationResponse`
- [x] `PaginatedUserOrderResponse`
- [x] `UserRestaurantsListResponse`

### 7.14 Analytics
- [ ] `OccupancyReportResponse`
- [ ] `OrdersReportResponse`
- [ ] `PopularItemsResponse`
- [ ] `PromotionsReportResponse`
- [ ] `PeakHoursResponse`

---

## 8. Endpoints REST (app/api/.../routes.py)

### 8.1 Lookup (nuevo namespace)
- [x] `GET /lookup/cuisine-types`
- [x] `GET /lookup/price-ranges`
- [x] `GET /lookup/countries`
- [x] `GET /lookup/provinces?countryId=`
- [x] `GET /lookup/cities?provinceId=`
- [x] `GET /lookup/neighbourhoods?cityId=`

### 8.2 Auth (existente)
- [x] `POST /auth/register`
- [x] `POST /auth/login`
- [x] `POST /auth/refresh`

### 8.3 Restaurantes
- [x] `GET /restaurants/` — con filtros: name, countryId, provinceId, cityId, neighbourhoodId, priceRangeId, cuisineTypeIds
- [x] `POST /restaurants/` — con cityId, cuisineTypeIds; auto-crea RestaurantAdmin
- [x] `GET /restaurants/{id}`
- [x] `PUT /restaurants/{id}` — reemplaza cuisines
- [x] `DELETE /restaurants/{id}`
- [x] `POST /restaurants/{id}/photo`
- [x] `GET /restaurants/{id}/admins`
- [x] `POST /restaurants/{id}/admins`
- [x] `DELETE /restaurants/{id}/admins/{user_id}`
- [x] `GET /restaurants/{id}/analytics/orders`
- [x] `GET /restaurants/{id}/analytics/metrics`

### 8.4 Mesas — F1
- [x] `GET /restaurants/{id}/tables`
- [x] `POST /restaurants/{id}/tables`
- [x] `POST /restaurants/{id}/tables/bulk`
- [x] `GET /restaurants/{id}/tables/{table_id}`
- [x] `PUT /restaurants/{id}/tables/{table_id}`
- [x] `DELETE /restaurants/{id}/tables/{table_id}`

### 8.5 Horarios — F1
- [x] `GET /restaurants/{id}/business-hours`
- [x] `PUT /restaurants/{id}/business-hours`

### 8.6 Disponibilidad — F1
- [x] `GET /restaurants/{id}/availability`

### 8.7 Reservas — F2
- [x] `POST /restaurants/{id}/reservations` — cliente online
- [x] `POST /restaurants/{id}/reservations/admin` — admin (PHONE/EVENT)
- [x] `GET /restaurants/{id}/reservations` — lista con filtros
- [x] `GET /restaurants/{id}/reservations/{reservation_id}`
- [x] `POST /restaurants/{id}/reservations/{reservation_id}/cancel`
- [ ] `PATCH /reservations/{reservation_id}/reassign-tables`
- [x] `PATCH /reservations/{reservation_id}/complete`
- [x] `PATCH /reservations/{reservation_id}/no-show`
- [ ] `GET /reservations/lookup`

### 8.8 Menús — F3
- [ ] `GET /restaurants/{id}/menus/`
- [ ] `POST /restaurants/{id}/menus/`
- [ ] `GET /restaurants/{id}/menus/{menu_id}`
- [ ] `PUT /restaurants/{id}/menus/{menu_id}`
- [ ] `DELETE /restaurants/{id}/menus/{menu_id}`
- [ ] `PATCH /restaurants/{id}/menus/{menu_id}/activate`

### 8.9 Categorías de Menú — F3
- [ ] `GET /menus/{menu_id}/categories/`
- [ ] `POST /menus/{menu_id}/categories/`
- [ ] `PUT /menus/{menu_id}/categories/{cat_id}`
- [ ] `DELETE /menus/{menu_id}/categories/{cat_id}`
- [ ] `PATCH /menus/{menu_id}/categories/reorder`

### 8.10 Ítems de Menú — F3
- [ ] `GET /categories/{cat_id}/items/`
- [ ] `POST /categories/{cat_id}/items/`
- [ ] `GET /items/{item_id}`
- [ ] `PUT /items/{item_id}`
- [ ] `DELETE /items/{item_id}`
- [ ] `POST /items/{item_id}/photo`
- [ ] `PATCH /items/{item_id}/availability`

### 8.11 Pedidos — F3
- [ ] `POST /restaurants/{id}/orders/`
- [ ] `GET /restaurants/{id}/orders/`
- [ ] `GET /orders/{order_id}`
- [ ] `PATCH /orders/{order_id}/status`
- [ ] `PATCH /orders/{order_id}/cancel`

### 8.12 Promociones — F4
- [ ] `GET /restaurants/{id}/promotions/`
- [ ] `POST /restaurants/{id}/promotions/`
- [ ] `GET /restaurants/{id}/promotions/{promo_id}`
- [ ] `PUT /restaurants/{id}/promotions/{promo_id}`
- [ ] `PATCH /restaurants/{id}/promotions/{promo_id}/deactivate`
- [ ] `PATCH /restaurants/{id}/promotions/{promo_id}/activate`
- [ ] `DELETE /restaurants/{id}/promotions/{promo_id}`
- [ ] `GET /promotions/feed`

### 8.13 Perfil de Usuario
- [x] `GET /users/{user_id}`
- [x] `PUT /users/{user_id}`
- [x] `PUT /users/{user_id}/password`
- [x] `GET /users/{user_id}/reservations`
- [x] `GET /users/{user_id}/orders`
- [x] `GET /users/{user_id}/restaurants`

### 8.14 Preferencias de Notificación
- [ ] `GET /users/{user_id}/notification-preferences/`
- [ ] `PUT /users/{user_id}/notification-preferences/{restaurant_id}`

### 8.15 Analytics — F5
- [ ] `GET /restaurants/{id}/analytics/occupancy`
- [ ] `GET /restaurants/{id}/analytics/orders`
- [ ] `GET /restaurants/{id}/analytics/popular-items`
- [ ] `GET /restaurants/{id}/analytics/promotions`
- [ ] `GET /restaurants/{id}/analytics/peak-hours`

---

## 9. Integrations (app/integrations/)

- [ ] ✅ `S3Client.get()` — singleton, soporta LocalStack
- [ ] ✅ `S3Client.upload_restaurant_photo(file_storage, restaurant_id)`
- [ ] `S3Client.upload_menu_item_photo(file_storage, item_id)` — nuevo path en S3
- [ ] `SESClient` (o mock) — envío de emails para `NotificationService`
  - [ ] `SESClient.send(to, subject, html_body)`
  - [ ] `MockSESClient` — loguea en consola en entornos `TESTING`/`DEVELOPMENT`

---

## 10. Configuración y Variables de Entorno

- [ ] 🔧 `.env.example` — agregar `AWS_SES_REGION`, `FROM_EMAIL`, `FRONTEND_URL` (para links en emails)
- [ ] 🔧 `app/config.py` — agregar variables SES; validar en `ProductionConfig.validate()`

---

## Conteo de ítems por categoría

| Categoría | Total | ✅ Ya hecho | 🔧 Modificar | 🔴 Nuevo |
|---|---|---|---|---|
| Basics (§0) | 14 | 9 | 0 | 5 |
| Migraciones | 25 | 1 | 3 | 21 |
| Modelos | 23 | 3 | 2 | 18 |
| Enums | 5 | 1 | 0 | 4 |
| Repositorios | 30 | 3 | 1 | 26 |
| Servicios / Funciones | 70 | 3 | 3 | 64 |
| Middleware | 3 | 2 | 0 | 1 |
| Schemas | 42 | 5 | 4 | 33 |
| Endpoints | 57 | 3 | 4 | 50 |
| Integrations | 5 | 2 | 0 | 3 |
| Config / .env | 2 | 0 | 2 | 0 |
| **Total** | **276** | **32** | **19** | **225** |
