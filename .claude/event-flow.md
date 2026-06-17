# Event flow (async / decoupling)

Two separate async mechanisms. Don't confuse them:

1. **Domain-event pipeline** (SNS → 2× SQS → worker Lambdas) for orders/promotions side effects + analytics.
2. **Per-user SNS email topics** for customer email (because SES is unavailable in Learner Lab).
   Reservation confirmation uses this **synchronously**, NOT the queue pipeline.

> Dead/legacy: `app/services/async_queue.py` (`AsyncNotificationWorker`, an in-process
> threading+Queue retry worker) is wired only into the Flask `create_app`
> (`app/__init__.py:51`). It does NOT run in any deployed Lambda. Ignore it for production behavior.

## 1. Domain-event pipeline

```
publisher (app/services/domain_event_publisher.py: publish_domain_event)
  -> SNS topic  domain_events            (infra/main.tf:124  ${prefix}-domain-events)
       ├─ subscription -> SQS email_events      (infra/main.tf:216 / queue :145, DLQ :140)
       │     -> Lambda email_worker             (event_source_mapping infra/main.tf:232)
       └─ subscription -> SQS analytics_events   (infra/main.tf:224 / queue :161, DLQ :156)
             -> Lambda analytics_worker          (event_source_mapping infra/main.tf:239)
```

- The SNS topic fans out to **both** queues with **no filter policy** — every event lands in both
  queues; **each worker filters by `eventType` itself**.
- Each SQS queue has a **DLQ** with `maxReceiveCount = 3` (`redrive_policy`, `infra/main.tf:150`, `:166`).
- Workers return `{"batchItemFailures": [...]}` (`ReportBatchItemFailures`, `infra/main.tf:236`)
  so only failed records redrive.

### Event envelope (`domain_event_publisher.py:96`)

```json
{ "eventType","eventVersion":"1.0","occurredAt","source":"backend",
  "userId","restaurantId","userTopicArn","data": { ... } }
```

`publish_domain_event` is **best-effort and never raises into the caller** (`:121`) — a messaging
failure must not break the business transaction. It reads the topic ARN from
`DOMAIN_EVENTS_TOPIC_ARN`; if unset it logs and skips (`:89`).

**`userTopicArn` is resolved on the publish side** (`_resolve_user_topic_arn`, `:54`): the worker
Lambdas are packaged WITHOUT the app/DB layer, so the recipient's confirmed per-user SNS topic is
looked up here (where DB context exists) and embedded in the event. Returns `None` unless the user
exists, has a topic, and `sns_subscription_status == CONFIRMED`.

### Events actually published

| eventType | publisher | file:line |
|---|---|---|
| `order.created` | `publish_order_created` → `publish_domain_event` | `app/services/order_event_publisher.py:39` (called from `cognito_order_service.py:46`) |
| `order.status_changed` | `publish_domain_event` | `app/services/order_service.py:235` |
| `promotion.notify` | `publish_domain_event` (one per subscribed recipient) | `app/services/notification_service.py:407` |

### Consumers

**`email_worker`** (`lambdas/email_worker/handler.py`) — turns events into customer emails.
- Handles `{order.created, order.status_changed, promotion.notify}` (`_HANDLED_EVENT_TYPES :13`).
- Skips records with no `userTopicArn` (no confirmed recipient → nothing to deliver, `:95`).
- Publishes the formatted message to the recipient's **per-user SNS topic** (`:106`).
- Env: `EMAIL_TOPIC_ARN` (`infra/locals.tf:87`) — note this is the shared `email_topic`, but the
  worker actually publishes to the **per-user** topic carried in `userTopicArn`.

**`analytics_worker`** (`lambdas/analytics_worker/handler.py`) — recomputes daily snapshots.
- Reacts to `{order.created, order.status_changed, reservation.created}` (`_RECOMPUTE_EVENTS :12`).
- Resolves `(restaurant_id, day)` from the operational record
  (`AnalyticsRepository.resolve_recompute_target`) and UPSERTs the day snapshot
  (`recompute_day_snapshot`) — see "Analytics" below.
- Needs the DB, so it runs in-VPC and uses the RDS Proxy env (`infra/locals.tf:88`).

> **⚠ Correction to the narrative: `reservation.created` is declared but NEVER published.**
> No code calls `publish_domain_event("reservation.created", ...)` (grep-verified across
> `app/` and `lambdas/`). The `analytics_worker` and `AnalyticsRepository.resolve_recompute_target`
> (`app/repositories/analytics_repository.py:366`) handle it, but no producer emits it. Net effect:
> **analytics snapshots are only recomputed from order events.** Reservation counts in a sealed
> snapshot therefore only update if an *order* event for that restaurant/day re-triggers a
> recompute (which re-reads reservations for that day). `report=metrics`/`dashboard` "today" reads
> are live SQL and unaffected. If you want event-driven reservation snapshots, publish
> `reservation.created` from the reservation create paths.
>
> Also: `analytics_worker` ignores `promotion.notify`; `email_worker` ignores `reservation.created`.
> So the queues receive all 3 published event types, but each worker acts on its own subset.

## 2. Per-user SNS email topics (customer email channel)

SES is unavailable in AWS Academy Learner Lab, so each customer gets a dedicated **SNS topic with
an email subscription**, provisioned at signup. Service:
`app/services/sns_user_notification_service.py`.

- `ensure_subscription(user)` (`:59`) — `create_topic(Name=…-{user_id}-notifications)` then
  `subscribe(Protocol="email", Endpoint=user.email)`; stores `sns_topic_arn`, `sns_subscription_arn`,
  `sns_subscription_status` on the user. Topic name prefix from `SNS_USER_TOPIC_PREFIX`
  (`infra/locals.tf:52`, `:84`).
- A new email subscription starts `PENDING_CONFIRMATION` until the user clicks the AWS confirmation
  link; only then `CONFIRMED`.
- `refresh_subscription_status(user)` (`:104`) re-checks via `list_subscriptions_by_topic`.

### Reservation confirmation = SYNCHRONOUS per-user publish (not the queue)

`CognitoReservationService.create` (ONLINE source, `app/services/cognito_reservation_service.py:108`):
1. `refresh_subscription_status(principal)`; **if not `CONFIRMED` → `ForbiddenError`** ("confirm
   your email subscription before reserving", `:109`). A reservation requires a confirmed sub first.
2. Create the reservation (`ReservationService.create`).
3. **Synchronously** `SnsUserNotificationService.publish_reservation_confirmation(reservation_id)`
   (`:125`) → publishes confirmation directly to the user's topic
   (`sns_user_notification_service.py:151`). Wrapped in try/except so a publish failure does not
   roll back the reservation.

`POST …/public-reservations` (guest) → `create_public` → `create_guest_online`: no auth, no email.

## Env-var wiring (topics/queues → Lambdas), from `infra/locals.tf:78`

| Lambda | relevant env |
|---|---|
| `orders_service` | `DOMAIN_EVENTS_TOPIC_ARN = aws_sns_topic.domain_events.arn` |
| `promotions_service` | `DOMAIN_EVENTS_TOPIC_ARN = aws_sns_topic.domain_events.arn` |
| `reservations_service` | `SNS_USER_TOPIC_PREFIX = ${prefix}-user` |
| `users_service` | `SNS_USER_TOPIC_PREFIX = ${prefix}-user` (provision sub at signup) |
| `email_worker` | `EMAIL_TOPIC_ARN = aws_sns_topic.email_topic.arn` |
| `analytics_worker` | DB env (RDS Proxy) |

Note: `order.status_changed` is emitted from `order_service.py`, but only `orders_service` (and
`promotions_service`) get `DOMAIN_EVENTS_TOPIC_ARN`. The order status change runs inside
`orders_service`, so the env is present there.

## 3. Analytics snapshot checkpoint

Table `analytics_snapshots`, **composite PK `(restaurant_id, period_date)`**
(`app/models/analytics_snapshot.py:21`). One row per restaurant per day.

- **Seal a past day:** `analytics_worker` → `AnalyticsRepository.recompute_day_snapshot`
  (`app/repositories/analytics_repository.py:417`). It **recomputes from scratch** (not increment)
  via `compute_day_aggregate` (`:382`) and UPSERTs → **idempotent under SQS redelivery**.
- **Read (`report=dashboard`):** `AnalyticsService.get_snapshot_dashboard`
  (`app/services/analytics_service.py:232`): `period_date < today` from `analytics_snapshots`;
  `period_date == today` computed live via the same `compute_day_aggregate`. Crisp boundary avoids
  double counting; each `byDay` row is tagged `source: "snapshot" | "live"`.
