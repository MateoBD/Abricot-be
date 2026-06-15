# API routes (source of truth)

**Source of truth:** `infra/locals.tf` `api_routes` map (`infra/locals.tf:204-270`). Each route
declares `route_key = "METHOD /path"`, the target `service` (Lambda), `jwt` (attach Cognito
authorizer?), and `enabled`. API Gateway routes purely by `route_key`; the Lambda's dispatcher
then re-matches `method + path`. **Both must agree** — a route in `locals.tf` with no dispatcher
branch returns 404 from the Lambda; a dispatcher branch with no `locals.tf` route is unreachable.

`jwt = false` = public (no authorizer). `jwt = true` = valid Cognito token required; **role/owner
checks still happen in the service layer**, not the gateway.

Cross-check status below: **all 65 routes map to a dispatcher branch; no stranded routes; no
orphan branches.** One constraint flagged on catalog menus.

## health / auth (users_service unless noted)

| route_key | service | jwt | dispatcher branch |
|---|---|---|---|
| `GET /health` | health | no | `lambdas/health/handler.py` (static ok) |
| `GET /callback` | users_service | no | `_handle_callback` (`users_service/handler.py:352`) — OAuth code exchange |
| `GET /auth-test` | users_service | yes | `_handle_auth_test` (`:355`) — echoes claims, no DB |

## users_service — `lambdas/users_service/handler.py`

| route_key | jwt | dispatcher branch | CognitoUserService method |
|---|---|---|---|
| `POST /users` | yes | `:358` | `provision_user` (idempotent on cognito sub) |
| `GET /users/{userId}/restaurants` | yes | `:361` `_is_user_restaurants_list` | `list_restaurants_for_principal` |
| `GET /users/{userId}` | yes | `:364` | `get_profile_for_principal` |
| `PUT /users/{userId}` | yes | `:367` | `update_profile_for_principal` |

Order matters: the `…/restaurants` check runs before the generic `GET /users/` check. No `DELETE /users`.

## catalog_service — `lambdas/catalog_service/handler.py` (all public, GET-only)

| route_key | jwt | dispatcher branch | calls |
|---|---|---|---|
| `GET /lookups` | no | `:264` `_handle_lookups` | `LookupService` (country/province/city/neighbourhood/price-range/cuisine-type; `parentId` required for nested) |
| `GET /restaurants` | no | `:267` `_handle_list_restaurants` | `RestaurantService.search` (filters: name, location ids, priceRangeId, cuisineTypeIds, sort, page) |
| `GET /restaurants/{restaurantId}` | no | `:277` `_handle_get_restaurant` | `RestaurantService.get_by_id` |
| `GET /restaurants/{restaurantId}/menus` | no | `:272` `_handle_active_menu` | `MenuService.get_active_menu` — **⚠ only when `?isActive=true`, else 404** |

The dispatcher rejects any non-GET (`:261`).

## orders_service — `lambdas/orders_service/handler.py`

| route_key | jwt | dispatcher branch | CognitoOrderService method |
|---|---|---|---|
| `POST /restaurants/{restaurantId}/orders` | yes | `:273` | `create_order` → emits `order.created` |
| `GET /users/{userId}/orders` | yes | `:276` | `list_user_orders` (page/perPage) |
| `GET /restaurants/{restaurantId}/orders` | yes | `:279` | `list_restaurant_orders` (status/page/perPage) |
| `GET /restaurants/{restaurantId}/orders/{orderId}` | yes | `:282` | `get_restaurant_order` |
| `PATCH /restaurants/{restaurantId}/orders/{orderId}` | yes | `:285` | `patch_restaurant_order` → emits `order.status_changed` |

## restaurants_service — `lambdas/restaurants_service/handler.py` (CognitoRestaurantService, all jwt=true)

| route_key | dispatcher branch |
|---|---|
| `POST /restaurants` | `:175` create_restaurant |
| `PUT /restaurants/{restaurantId}` | `:189` update_restaurant |
| `DELETE /restaurants/{restaurantId}` | `:204` delete_restaurant (204) |
| `POST /restaurants/{restaurantId}/photo` | `:211` upload_photo (multipart → S3 key) |
| `PUT /restaurants/{restaurantId}/reviews/{userId}` | `:227` put_review |
| `GET /restaurants/{restaurantId}/admins` | `:248` list_admins |
| `POST /restaurants/{restaurantId}/admins` | `:256` add_admin |
| `DELETE /restaurants/{restaurantId}/admins/{userId}` | `:272` remove_admin (204) |
| `GET /restaurants/{restaurantId}/admin/menus` | `:288` list_admin_menus |
| `POST /restaurants/{restaurantId}/admin/menus` | `:296` create_admin_menu |
| `POST /restaurants/{restaurantId}/menus` | `:296` (same branch — `_is_admin_menus_collection` matches both shapes) |
| `GET /restaurants/{restaurantId}/admin/menus/{menuId}` | `:312` get_admin_menu |
| `GET /restaurants/{restaurantId}/menus/{menuId}` | `:312` (same branch) |
| `PUT /restaurants/{restaurantId}/admin/menus/{menuId}` | `:327` update_admin_menu |
| `PUT /restaurants/{restaurantId}/menus/{menuId}` | `:327` (same branch) |
| `PATCH /restaurants/{restaurantId}/admin/menus/{menuId}` | `:343` patch_admin_menu |
| `PATCH /restaurants/{restaurantId}/menus/{menuId}` | `:343` (same branch) |
| `DELETE /restaurants/{restaurantId}/admin/menus/{menuId}` | `:359` delete_admin_menu (204) |
| `DELETE /restaurants/{restaurantId}/menus/{menuId}` | `:359` (same branch) |
| `GET /restaurants/{restaurantId}/menus/{menuId}/categories` | `:370` list_menu_categories |
| `POST /restaurants/{restaurantId}/menus/{menuId}/categories` | `:385` create_menu_category |
| `GET …/categories/{categoryId}` | `:402` get_menu_category |
| `PUT …/categories/{categoryId}` | `:424` update_menu_category |
| `DELETE …/categories/{categoryId}` | `:447` delete_menu_category (204) |
| `GET …/categories/{categoryId}/items` | `:465` list_menu_items |
| `POST …/categories/{categoryId}/items` | `:481` create_menu_item |
| `GET …/items/{itemId}` | `:499` get_menu_item |
| `PUT …/items/{itemId}` | `:523` update_menu_item |
| `DELETE …/items/{itemId}` | `:548` delete_menu_item (204) |
| `GET /restaurants/{restaurantId}/tables` | `:568` list_tables |
| `POST /restaurants/{restaurantId}/tables` | `:576` create_table |
| `GET /restaurants/{restaurantId}/tables/{tableId}` | `:592` get_table |
| `PUT /restaurants/{restaurantId}/tables/{tableId}` | `:607` update_table |
| `DELETE /restaurants/{restaurantId}/tables/{tableId}` | `:623` delete_table (204) |
| `GET /restaurants/{restaurantId}/business-hours` | `:634` get_business_hours |
| `PUT /restaurants/{restaurantId}/business-hours` | `:642` update_business_hours |
| `GET /restaurants/{restaurantId}/availability` | `:658` get_availability |
| `GET /restaurants/{restaurantId}/public-availability` (**jwt=false**) | `:673` get_availability (same logic, public) |

Note: admin menu routes accept both `/admin/menus/...` and `/menus/...` path shapes at the
dispatcher; `locals.tf` exposes both as distinct route_keys. Categories/items live only under the
non-admin `/menus/{menuId}/...` shape. There is no PATCH for categories or items.

## reservations_service — `lambdas/reservations_service/handler.py`

| route_key | jwt | dispatcher branch | CognitoReservationService method |
|---|---|---|---|
| `POST /restaurants/{restaurantId}/reservations` | yes | `:142` | `create` (ONLINE requires confirmed SNS sub; PHONE/EVENT require restaurant admin) |
| `POST /restaurants/{restaurantId}/public-reservations` | **no** | `:163` | `create_public` (guest, no email) |
| `GET /restaurants/{restaurantId}/reservations` | yes | `:183` | `list_for_restaurant` |
| `GET /reservations/{reservationId}` | yes | `:203` | `get_by_id` |
| `PATCH /reservations/{reservationId}` | yes | `:216` | `transition_status` |
| `GET /users/{userId}/reservations` | yes | `:233` | `list_for_user` |

## promotions_service — `lambdas/promotions_service/handler.py` (all jwt=true)

| route_key | dispatcher branch | CognitoPromotionService method |
|---|---|---|
| `GET /restaurants/{restaurantId}/promotions` | `:59` | `list_for_restaurant` |
| `POST /restaurants/{restaurantId}/promotions` | `:77` | `create` |
| `GET /restaurants/{restaurantId}/promotions/{promotionId}` | `:96` | `get_by_id` |
| `DELETE /restaurants/{restaurantId}/promotions/{promotionId}` | `:117` | `delete` (204) |

> `promotion.notify` email fan-out is NOT a route. It is triggered from
> `NotificationService` (`app/services/notification_service.py:407`) — see `event-flow.md`.

## analytics_service — `lambdas/analytics_service/handler.py`

| route_key | jwt | dispatcher branch | method |
|---|---|---|---|
| `GET /restaurants/{restaurantId}/analytics` | yes | `:45` | `CognitoAnalyticsService.get_report` |

`?report=` selects the view (required, else 400; `cognito_analytics_service.py:56`):
- `report=dashboard` — snapshot-backed daily view: sealed snapshots for `period_date < today` +
  live SQL for today (`AnalyticsService.get_snapshot_dashboard`, `app/services/analytics_service.py:232`).
- `report=orders` — live SQL orders report.
- `report=metrics` — live SQL general metrics (orders + reservations + revenue).
- All require `start` and `end` query params together (`_parse_date_range`, `analytics_service.py:62`).

## Cross-check summary

- **Stranded routes (route_key with no dispatcher branch): none.**
- **Orphan dispatcher branches (branch with no route_key): none.**
- **Constraint, not a bug:** `GET /restaurants/{id}/menus` (catalog) only returns a body with
  `?isActive=true`; otherwise the dispatcher 404s. Frontend/clients must send `isActive=true`.
- Public (`jwt=false`) routes: `GET /health`, `GET /callback`, `GET /lookups`, `GET /restaurants`,
  `GET /restaurants/{id}`, `GET /restaurants/{id}/menus`, `GET /restaurants/{id}/public-availability`,
  `POST /restaurants/{id}/public-reservations`. Everything else requires a Cognito JWT.
- Routes other than `health`/`callback`/`auth-test` are gated by `enabled = local.*_routes_enabled`,
  which all derive from `lambda_private_attachment_enabled` (full private stack). With it off they 404.
