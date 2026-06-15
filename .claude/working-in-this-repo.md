# Working in this repo

## The rules that prevent the recurring bugs

1. **Dispatcher, not Flask.** Deployed Lambdas run the path dispatcher in
   `lambdas/<service>/handler.py`, not Flask. `app/api/**/routes.py`, `app/__init__.py`'s
   blueprints, and `application.py` are the **legacy TP2 monolith and do not run in production**.
   Editing a Flask route changes nothing in the deployed system.

2. **A feature is "wired" only when all of these exist:**
   - a `route_key` entry in `infra/locals.tf` `api_routes` (correct `service`, `jwt`, `enabled`);
   - a matching branch in that service's `handler.py` dispatcher (`method + path`);
   - usually a `Cognito<X>Service` method (auth boundary) + domain service/repository.
   Miss the dispatcher branch → Lambda returns `route_not_found()` (404) even though the gateway
   route exists. Miss the `locals.tf` route → unreachable. **This dual-registration is the #1 bug source.**

3. **Route source of truth = `infra/locals.tf` + the dispatcher.** NOT `.mcp/`. See `api-routes.md`.

4. **`.mcp/` is DEPRECATED.** `abricot_proposal.md`, `abricot_frontend_guide.md`,
   `abricot_checklist.md`, `BEST_PRACTICES.md` are aspirational / legacy-monolith docs that call
   themselves "fuente de verdad" but do not match deployment. Do not derive contracts from them.

5. **Auth is enforced in services, not the gateway.** `jwt=true` only proves a valid token. Role /
   ownership is checked by `require_restaurant_admin` / `require_same_user_or_super_admin`
   (`app/services/cognito_authorization_service.py`). Public routes are `jwt=false`.

6. **Two handler helper styles.** `restaurants/reservations/promotions/analytics/catalog` use
   `lambdas/common/api.py`. `users_service` and `orders_service` carry **private copies** — their
   `_json_body` does not base64-decode. Keep edits consistent with whichever a handler uses.

## End-to-end examples (trace the layers)

**Create order — `POST /restaurants/{restaurantId}/orders`**
```
infra/locals.tf:217            api_routes.orders_create -> service=orders_service, jwt=true
lambdas/orders_service/handler.py:273   dispatcher: POST + restaurant orders collection
  -> _handle_create_order:182   CognitoOrderService.create_order(restaurant_id, cognito_sub, body)
app/services/cognito_order_service.py   principal_user + (auth) -> OrderService -> OrderRepository
  :46                           publish_order_created(order)  [order.created -> SNS]
lambdas/common/flask_db.py:87   backend_app_context() opens the session, rolls back on error
```
Side effect: `order.created` → SNS `domain_events` → email_worker (email) + analytics_worker (snapshot).

**Get analytics dashboard — `GET /restaurants/{restaurantId}/analytics?report=dashboard&start=..&end=..`**
```
infra/locals.tf:269            api_routes.analytics_get -> service=analytics_service, jwt=true
lambdas/analytics_service/handler.py:45  dispatcher: GET + /analytics
  -> CognitoAnalyticsService.get_report   require_restaurant_admin
app/services/analytics_service.py:232    get_snapshot_dashboard:
  period_date < today  -> AnalyticsRepository.get_snapshots_range (analytics_snapshots table)
  period_date == today -> AnalyticsRepository.compute_day_aggregate (live SQL)
```

## Data model

ORM models in `app/models/` (Flask-SQLAlchemy `db`). Tables (`__tablename__`):

`users`, `restaurants`, `restaurant_admins`, `restaurant_reviews`, `restaurant_cuisines`,
`cuisine_types`, `price_ranges`, `countries`, `provinces`, `cities`, `neighbourhoods`,
`tables`, `business_hours`, `menus`, `menu_categories`, `menu_items`, `orders`, `order_items`,
`reservations`, `reservation_tables`, `promotions`, `promotion_items`, `notification_preferences`,
`notification_events`, `analytics_snapshots`. (25 tables.)

Geo lookups (`countries`/`provinces`/`cities`/`neighbourhoods`) are all defined in
`app/models/location.py` (`CountryModel`/`ProvinceModel`/`CityModel`/`NeighbourhoodModel`); there is
no separate `locations` table.

- `analytics_snapshots`: composite PK `(restaurant_id, period_date)` — the checkpoint table.
- `users`: carries Cognito link + per-user SNS fields (`cognito_sub`, `sns_topic_arn`,
  `sns_subscription_arn`, `sns_subscription_status`; see `app/models/enums.py UserSnsSubscriptionStatus`).
- Enums (`UserRole`, order/reservation/promotion statuses, SNS sub status) in `app/models/enums.py`.

**Migrations:** Alembic via Flask-Migrate in `migrations/` (versions in `migrations/versions/`,
timestamp-named). Applied in deployment by the **`db_migrate` Lambda** (`lambdas/db_migrate/handler.py`,
`action=upgrade` to `head`; `action=validate` dumps current revision + tables). Do not hand-edit the DB.

## Tests

- Pytest. `pyproject.toml` sets `pythonpath = ["."]`; run from the repo virtualenv:
  ```bash
  source .venv/bin/activate && pytest        # or: .venv/bin/pytest
  ```
- Tests live in `tests/` (e.g. `test_order_status_events.py`, `test_promotion_events.py`,
  `test_analytics_worker.py`, `test_analytics_service.py`, photo/menu/error-handling tests).
- Ruff is configured with bandit rules (`extend-select = ["S"]`) in `pyproject.toml`.

## Deploy model (pipeline-driven, greenfield)

- On push, `.github/workflows/deploy.yml` runs: `scripts/package_lambdas.sh` →
  `terraform init/plan` → **block destructive plan** → `terraform apply` → wait for RDS Proxy
  target → **invoke `db_migrate`** (`aws lambda invoke`) → zip + upload artifacts +
  `aws lambda update-function-code` → frontend deploy. `destroy.yml` / `validate.yml` also exist.
- Environments are rebuilt greenfield; there is an "import existing resources" step
  (`scripts/import_existing_terraform_resources.sh`) for idempotency.

## Agent constraints (for Claude working here)

- **Do NOT** `git commit` / `git push` unless explicitly asked.
- **Do NOT** run `terraform`, `aws`, or anything that mutates cloud state. Deploy is the pipeline's job.
- Read-only shell (`grep`/`cat`/`ls`/`git status`) is fine for verification.
- When adding/altering endpoints, change BOTH `infra/locals.tf` and the dispatcher (rule 2).
- Treat `.mcp/` as deprecated; do not cite it. Treat `app/api/**/routes.py` and `app/__init__.py`
  as legacy (read for domain logic clues only — they don't run in production).
