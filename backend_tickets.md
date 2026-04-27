# Backend Tickets

Tickets de backend organizados por modulo. Nivel high-level para avanzar rapido y sin sobre-fragmentar.

---

## Backend: Basics

Estado revisado contra el repo (`app/`). **Cerrado en Basics**: auth, perfil de usuario, health/version y permisos base por rol implementados.

### Features
- [x] Crear modelo de Usuario con roles (`UserRole`: CUSTOMER, RESTAURANT_ADMIN, SUPER_ADMIN) + migración — `app/models/enums.py`, `UserModel.role`, `migrations/versions/2026-04-19T12-00-00_add_user_role.py`, `UserRepository.update_role`, `role` en `user_summary` / `to_dict()`
- [x] Crear autenticacion con JWT (login, registro y refresh) — `POST /auth/register`, `/auth/login`, `/auth/refresh` + `AuthService` + refresh en header
- [x] Crear endpoint de perfil de usuario (ver/editar datos basicos y cambio de contraseña) — `GET/PUT /users/{user_id}`, `PUT /users/{user_id}/password` en `app/api/users/routes.py` + `app/services/user_service.py` (`user_id` debe coincidir con JWT)
- [x] Crear endpoint de healthcheck y version de API — `GET /health` y `GET /version` en `app/api/system/routes.py`
- [x] Crear capa base de permisos por rol en endpoints protegidos — `require_roles()` + `require_restaurant_admin()` en `app/middleware/auth.py`, con verificación estricta por restaurante en `restaurant_admins` y bypass de `SUPER_ADMIN`

### Chores
- [x] Configurar manejo centralizado de errores y respuestas estandar — `AppError` + `@api.errorhandler` en `app/api/__init__.py` (formato `message`, `code`, `errors`)
- [x] Configurar logging estructurado para requests y errores — `app/logging_config.py` + inicialización en factory
- [x] Configurar validaciones base de schemas (auth, usuarios, payloads comunes) — Flask-RESTX `expect(..., validate=True)` en auth + patrones en `app/api/auth/schemas.py` (`UserSummary` incluye `role`; perfiles en `/users/{user_id}`)
- [x] Agregar migraciones iniciales de tablas base — `users` + `restaurants` + migración de esquema de dominio (`migrations/versions/2026-04-19T20-30-00_add_full_domain_schema.py`)
- [x] Documentar contratos principales de API (auth + usuarios) — Swagger en `/` vía Flask-RESTX, incluyendo `/users/{user_id}` y `/users/{user_id}/password`

---

## Backend: Admin Dashboard

### Features
- [x] Crear endpoint de metricas generales por restaurante (reservas, ordenes, ingresos) — alineado a contrato analytics: `GET /restaurants/{id}/analytics/orders?start=&end=` en `app/api/restaurants/routes.py` + `app/services/analytics_service.py`
- [ ] Crear endpoint de resumen diario/semanal para panel admin
- [ ] Crear endpoint de actividad reciente (ultimas reservas y pedidos)
- [ ] Crear endpoint de estado operativo del restaurante (capacidad, slots, ordenes activas)
- [x] Crear endpoint para gestionar administradores de restaurante — `GET/POST /restaurants/{id}/admins`, `DELETE /restaurants/{id}/admins/{user_id}` en `app/api/restaurants/routes.py` + `app/services/restaurant_admin_service.py`

### Chores
- [x] Definir queries agregadas optimizadas para dashboard — `AnalyticsRepository.get_orders_report()` + queries agregadas reutilizables (`get_daily_summary`, `get_recent_activity`) en `app/repositories/analytics_repository.py`
- [ ] Agregar indices en columnas usadas por metricas y filtros
- [x] Estandarizar filtros por rango de fechas — parser reutilizable `start/end` (obligatorios en analytics) en `app/api/restaurants/routes.py` + validación centralizada (`formato`, `par completo`, `orden`) en `AnalyticsService._parse_date_range()`
- [ ] Agregar tests de integracion para endpoints de dashboard
- [ ] Documentar permisos de acceso para vistas admin

---

## Backend: Menus & Takeout

### Features
- [x] Crear modelo y CRUD de Menu — modelos/repos/services ya existentes + CRUD expuesto en `app/api/restaurants/routes.py` (`/restaurants/{id}/menus`)
- [x] Crear modelo y CRUD de Categoria de menu — CRUD expuesto en `app/api/restaurants/routes.py` (`/restaurants/{id}/menus/{menuId}/categories`)
- [x] Crear modelo y CRUD de Item de menu — CRUD expuesto en `app/api/restaurants/routes.py` (`/restaurants/{id}/menus/{menuId}/categories/{categoryId}/items`)
- [x] Crear funcion para activar/desactivar menu vigente
- [x] Crear funcion para crear pedido takeout con validacion de items
- [x] Crear funcion para actualizar estado de pedido (pending -> confirmed -> ready -> completed) — `PATCH /restaurants/{id}/orders/{order_id}` en `app/api/restaurants/routes.py` + validación de transiciones en `app/services/order_service.py`

### Chores
- [ ] Integrar subida de foto de item a S3
- [ ] Agregar validaciones de precio, disponibilidad y consistencia de catalogo
- [x] Agregar paginacion y filtros en listado de pedidos — `GET /restaurants/{id}/orders?page=&perPage=&status=` en `app/api/restaurants/routes.py` + `OrderService.list_for_restaurant`
- [ ] Agregar tests de reglas de transicion de estado de pedidos
- [ ] Documentar flujo de menu activo y creacion de orden

---

## Backend: Notifications

### Features
- [ ] Crear servicio de notificaciones para eventos de reserva
- [ ] Crear servicio de notificaciones para eventos de pedidos
- [ ] Crear envio de promociones a usuarios suscriptos
- [ ] Crear endpoint para gestionar preferencias de notificacion por usuario

### Chores
- [ ] Definir plantilla base de mensajes (confirmacion, cancelacion, recordatorio)
- [ ] Implementar disparo asincrono para notificaciones
- [ ] Agregar reintentos y manejo de fallos en envios
- [ ] Agregar logs y trazabilidad de eventos enviados
- [ ] Agregar tests de integracion para eventos principales

---

## Backend: Reservations

### Features
- [ ] Crear modelo de Mesa y horarios de negocio por restaurante
- [ ] Crear funcion para calcular disponibilidad de mesas por fecha y hora
- [ ] Crear funcion de reserva online con asignacion de mesa
- [ ] Crear funcion de reserva creada por admin (telefono/evento)
- [ ] Crear funcion para cancelar reserva y liberar mesas
- [ ] Crear funcion para completar reserva o marcar no-show
- [ ] Crear endpoint para listar reservas con filtros (fecha, estado, fuente)

### Chores
- [ ] Definir reglas de asignacion de mesas (mesa unica vs combinacion)
- [x] Asegurar transacciones atomicas para evitar sobre-reservas — lock pesimista de mesas con `SELECT ... FOR UPDATE` + escritura de reserva/mesas en una sola transaccion (`ReservationService.create/create_for_admin` con `lock_rows=True`, `ReservationRepository.create(auto_commit=False)`, `ReservationTableRepository.create_bulk(auto_commit=False)`, commit unico)
- [ ] Agregar indices para busquedas por restaurante, fecha y estado
- [ ] Agregar test de concurrencia para creacion de reservas
- [ ] Documentar flujo de reserva y reglas de negocio

---

## Notas
- Mantener tickets en formato feature/chore e iterar en detalle solo cuando se arranque la implementacion.
- Si un ticket crece demasiado, dividirlo en subtareas recien durante el sprint.
- El desglose atómico de **Basics** vive en `abricot_checklist.md` **§0 Basics** (cimientos).