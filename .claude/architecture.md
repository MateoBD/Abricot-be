# Architecture (deployed, real)

Fully serverless on AWS Academy Learner Lab (`LabRole`). Pivoted from a TP2 EC2 + ALB + RDS
Flask monolith; the monolith code still lives under `app/` but only its service/repository/model
layers run — the Flask HTTP layer does not. IaC: Terraform in `infra/`.

## Front door

- **Cognito** user pool + SPA app client (`infra/main.tf:1`, `:16`) — issues JWTs. OAuth code
  exchange happens in `users_service` (`GET /callback`, `lambdas/users_service/handler.py:93`).
- **API Gateway HTTP API v2** (`infra/main.tf`), with a **JWT authorizer** bound to the Cognito
  pool (`aws_apigatewayv2_authorizer.cognito`, `infra/main.tf:57`). Each route attaches the
  authorizer only when its `api_routes` entry has `jwt = true` (`infra/main.tf:112`).
- The JWT authorizer only validates the token. **Role/ownership authorization is enforced in the
  service layer** (`require_restaurant_admin`, `require_same_user_or_super_admin`), not at the gateway.

## Request path & layering

```
API Gateway (HTTP API v2) + Cognito JWT authorizer
  -> lambdas/<service>/handler.py          # DISPATCHER: match method+path -> branch
    -> app/services/cognito_<x>_service.py  # auth boundary
       - principal_user(cognito_sub)        # resolve local user from Cognito sub
       - require_restaurant_admin(...) / require_same_user_or_super_admin(...)
    -> app/services/<domain>_service.py     # business logic
    -> app/repositories/<x>_repository.py    # SQLAlchemy queries
    -> app/models/<x>.py                     # ORM models
  -> RDS Proxy -> RDS PostgreSQL
```

Auth boundary code: `app/services/cognito_authorization_service.py`
(`require_restaurant_admin` at `:70`, `principal_user` at `:34`). Super-admin shortcut honours both
the local `UserRole.SUPER_ADMIN` and the Cognito `SUPER_ADMIN` group claim.

### Lambda inventory (`infra/locals.tf`)

API service Lambdas (`api_lambda_functions`, `infra/locals.tf:92`), all entrypoint `handler.handler`:

| Lambda | Dispatcher | Cognito service | Timeout | VPC |
|---|---|---|---|---|
| `health` | `lambdas/health/handler.py` | — (static `{"status":"ok"}`) | 5s | no |
| `users_service` | `lambdas/users_service/handler.py` | `CognitoUserService` | 10s | yes |
| `catalog_service` | `lambdas/catalog_service/handler.py` | none — calls `RestaurantService`/`MenuService`/`LookupService` directly (public reads) | 15s | yes |
| `orders_service` | `lambdas/orders_service/handler.py` | `CognitoOrderService` | 15s | yes |
| `restaurants_service` | `lambdas/restaurants_service/handler.py` | `CognitoRestaurantService` | 30s | yes |
| `reservations_service` | `lambdas/reservations_service/handler.py` | `CognitoReservationService` | 15s | yes |
| `promotions_service` | `lambdas/promotions_service/handler.py` | `CognitoPromotionService` | 15s | yes |
| `analytics_service` | `lambdas/analytics_service/handler.py` | `CognitoAnalyticsService` | 15s | yes |

Worker Lambdas (`event_worker_lambda_functions`, `infra/locals.tf:179`):

| Lambda | Dispatcher | Trigger | VPC |
|---|---|---|---|
| `email_worker` | `lambdas/email_worker/handler.py` | SQS `email_events` | no |
| `analytics_worker` | `lambdas/analytics_worker/handler.py` | SQS `analytics_events` | yes (needs DB) |

Utility (`private_lambda_functions`, `infra/locals.tf:167`):

| Lambda | Dispatcher | Trigger | VPC |
|---|---|---|---|
| `db_migrate` | `lambdas/db_migrate/handler.py` | manual/pipeline invoke (`action`: `upgrade`/`validate`) | yes |

> `menus`: **admin** menu/category/item CRUD is served by `restaurants_service` /
> `CognitoRestaurantService` (JWT-protected). The **public** "digital menu" read is served by
> `catalog_service` via `MenuService.get_active_menu` — and only on
> `GET /restaurants/{id}/menus?isActive=true` (any other shape 404s,
> `lambdas/catalog_service/handler.py:272`).

### Body parsing — `lambdas/common/api.py`

- `json_body(event)` — JSON body, base64-decodes when `isBase64Encoded` (`:60`).
- `multipart_file(event, "file")` — multipart upload: base64-decode then werkzeug
  `parse_form_data`, returns a `FileStorage` (`:76`). Used by `restaurants_service` photo upload.
- Also: `authorizer_claims`, `claim_sub`, `is_cognito_super_admin`, `with_backend` (the
  try/except wrapper that maps `AppError`/`RuntimeError` to responses).
- Note: `users_service` and `orders_service` predate `common/api.py` and carry **private copies**
  of these helpers (e.g. their `_json_body` does NOT base64-decode). `restaurants_service`,
  `reservations_service`, `promotions_service`, `analytics_service`, `catalog_service` use the shared module.

## Data store

- **One RDS Proxy** (`aws_db_proxy.users`, `infra/private_database.tf:281`) shared by all
  VPC-attached API Lambdas + `analytics_worker` + `db_migrate`. Provides connection pooling for
  Lambda. Driver: `postgresql+pg8000` (`lambdas/common/flask_db.py:37`).
- **RDS PostgreSQL**, `db.t3.micro`, **`multi_az = true`** (`infra/private_database.tf:243`).
  Multi-AZ here is a synchronous **standby for failover**, not a readable secondary replica
  (there is no `replicate_source_db`). [Correction to the "Primary+Secondary you query" framing.]
- **Secrets Manager** holds the DB creds (`aws_secretsmanager_secret.db`,
  `infra/private_database.tf:260`); the **RDS Proxy** consumes them via its `auth { secret_arn }`
  block (`:292`). Lambdas themselves get host/user/password through env vars (see below), not the secret.
- Required DB env (validated in `flask_db._validate_db_env`, `lambdas/common/flask_db.py:27`):
  `DB_TARGET=RDS_PROXY`, `POSTGRES_HOST` (= proxy endpoint), `POSTGRES_PORT`, `POSTGRES_DB`,
  `POSTGRES_USER`, `POSTGRES_PASSWORD`. Wired in `infra/locals.tf:55` (`users_service_db_environment`).
- **Session lifecycle** (`backend_app_context`, `lambdas/common/flask_db.py:87`): `yield`; on
  exception `db.session.rollback()` + re-raise; always `db.session.remove()`.

### Anti-overbooking (a key reason for RDS over DynamoDB)

Availability/booking takes a **row-level lock** with `SELECT ... FOR UPDATE` on the restaurant's
active table rows: `TableRepository.get_active_for_update` (`app/repositories/table_repository.py:67`,
`.with_for_update()` at `:76`), called by `availability_service.py:85` and `reservation_service.py:584`.
The lock is on the **`tables` rows** (capacity), inside the booking transaction — not a single
"capacity counter" row.

## Networking (`infra/private_database.tf`, gated by `enable_full_private_stack`)

- VPC `10.0.0.0/16`, 2 AZs `us-east-1a/b` (`infra/locals.tf:34`).
- 6 subnets: 2 public, 2 private-app (Lambda), 2 private-db (`infra/locals.tf:36`).
- **2 NAT gateways** — one per public subnet/AZ (`aws_nat_gateway.this`,
  count = `length(public_subnet_cidrs)`, `infra/private_database.tf:69`). IGW for public subnets.
- **S3 Gateway VPC endpoint** (`aws_vpc_endpoint.s3`, `infra/private_database.tf:112`) — S3 only.
  SQS/SNS egress goes via NAT.
- SG chain: `${prefix}-lambda-sg` -> `${prefix}-rds-proxy-sg` -> `${prefix}-rds-sg:5432`
  (`infra/private_database.tf:121`, `:135`, `:149`).
- Most API routes are gated on `lambda_private_attachment_enabled` (`infra/locals.tf:71-76`). With
  the private stack off, only `health`, `callback`, `auth-test` exist.

## S3 buckets

- **SPA / frontend** bucket (`infra/frontend_storage.tf`) — static site hosting.
- **Lambda artifacts** bucket (`${prefix}-<acct>-lambda-artifacts`) — deploy zips.
- **Images** bucket (`${prefix}-<acct>-images`, `infra/images.tf`) — **PRIVATE**, all public
  access blocked (`infra/images.tf:38`). Restaurant/menu photos are uploaded multipart and the
  **object KEY is stored** (not a URL); the read path **presigns a GET on demand**
  (`app/integrations/s3.py`: `generate_presigned_get_url` `:36`, `upload_restaurant_photo` returns
  the key `:53`). `AWS_S3_BUCKET` env is set only for `restaurants_service` (`infra/locals.tf:83`).

## IaC layout

- `infra/main.tf` — API Gateway, Cognito, SNS/SQS, Lambda permissions/event-source-mappings.
- `infra/locals.tf` — Lambda definitions, env vars, and the `api_routes` map (route source of truth).
- `infra/private_database.tf` — VPC, subnets, NAT, SGs, RDS, RDS Proxy, Secrets Manager, S3 VPC endpoint.
- `infra/images.tf`, `infra/frontend_storage.tf` — S3 buckets.
- Lambda packaging via custom local module `infra/modules/lambda_function` (`for_each` over
  `lambda_functions`). External pinned module: `terraform-aws-modules/s3-bucket` (cached under
  `infra/.terraform/modules/lambda_artifacts_bucket`).

## Key decisions ("why", for the defense)

- **Monolith -> serverless**: decoupling + elasticity for nocturnal/bursty restaurant traffic.
- **Lambda over ECS/EKS**: scale-to-zero, no idle cost.
- **RDS Postgres over Aurora**: lower write cost for small-business volume.
- **RDS over DynamoDB**: relational model + transactional `SELECT ... FOR UPDATE` anti-overbooking lock.
- **Multi-AZ**: HA standby/failover.
- **RDS Proxy**: connection pooling so bursts of Lambda invocations don't exhaust Postgres connections.
- **SNS + SQS**: decouple email/analytics side effects from the request transaction; per-queue DLQ.
- **Per-user SNS topics**: SES is unavailable in AWS Academy Learner Lab, so each user gets an SNS
  email topic at signup as the customer email channel.
- **Analytics snapshot checkpoint**: seal past days into `analytics_snapshots` so dashboard reads
  are cheap (no full re-scan of operational tables for history).
