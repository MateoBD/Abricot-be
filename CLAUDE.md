# Abricot — Backend (Abricot-be)

Claude context entrypoint. Read this first. Deeper docs live in `.claude/`.

> **`.mcp/` IS DEPRECATED — DO NOT TRUST IT FOR CONTRACTS.**
> `.mcp/abricot_proposal.md`, `.mcp/abricot_frontend_guide.md`, `.mcp/abricot_checklist.md`
> and `.mcp/BEST_PRACTICES.md` call themselves the "fuente de verdad" but describe an
> **aspirational** design and the **legacy TP2 Flask monolith** (Spring-Boot mental model).
> They DO NOT match the deployed serverless system and have caused real routing bugs.
> The route source of truth is `infra/locals.tf` (`api_routes`) cross-checked against the
> dispatcher in each `lambdas/<service>/handler.py`. Remove `.mcp/` — see bottom of this file.

## What Abricot is

B2B SaaS for restaurants (reservations + orders). Five product features:
1. Real-time availability / anti-overbooking (row-lock on tables).
2. Self-service reservations + async email confirmation (per-user SNS).
3. Order tracking + status notifications + digital menu.
4. Ad-hoc promotions + optional email notify.
5. Predictive demand analytics (snapshot-based daily reports).

## #1 thing to know: the deployed Lambdas DO NOT run Flask

Each API service Lambda is a **custom path dispatcher** at `lambdas/<service>/handler.py`.
`handler(event, context)` matches `method + path` and calls a `Cognito<X>Service` method, which
enforces auth and delegates down the layers:

```
API Gateway (HTTP API v2) + Cognito JWT authorizer
  -> lambdas/<service>/handler.py        # dispatcher: match method+path
    -> app/services/cognito_*_service.py  # auth: principal_user + require_restaurant_admin
      -> app/services/<domain>_service.py # business logic
        -> app/repositories/*_repository.py
          -> app/models/*  (SQLAlchemy) -> RDS Proxy -> PostgreSQL
```

The Flask app (`app/__init__.py`, `app/api/**/routes.py`, `application.py`) is the **legacy TP2
monolith and is DEAD in deployment**. The ONLY thing the Lambdas borrow from Flask is
`common.flask_db.backend_app_context` (`lambdas/common/flask_db.py`) — a minimal app context that
provides a SQLAlchemy session. Do not assume a Flask route, blueprint, decorator, or
`AsyncNotificationWorker` thread runs in production.

**To add or change an endpoint you must wire it in the DISPATCHER**, register the route in
`infra/locals.tf`, and (usually) add a `Cognito<X>Service` method. Editing `app/api/**/routes.py`
alone does NOTHING in deployment. This mismatch is the #1 source of bugs in this repo.

## Where to read next (`.claude/`)

- `.claude/architecture.md` — serverless topology, layering, AWS resources, data store, the "why" decisions.
- `.claude/api-routes.md` — the full route map from `infra/locals.tf`, each cross-checked to its dispatcher branch.
- `.claude/event-flow.md` — SNS/SQS domain-event pipeline, per-user email SNS, analytics snapshots, real publisher/consumer files + env vars.
- `.claude/working-in-this-repo.md` — rules for changes, tests, deploy model, agent constraints, `.mcp` warning.

## Quick facts

- API Lambdas: `health`, `users_service`, `catalog_service`, `orders_service`,
  `restaurants_service`, `reservations_service`, `promotions_service`, `analytics_service`.
- Worker Lambdas: `email_worker`, `analytics_worker`. Utility: `db_migrate`. All `handler.handler`.
- Body parsing: `lambdas/common/api.py` (`json_body`, `multipart_file`). Some handlers
  (`users_service`, `orders_service`) keep private copies of these helpers.
- DB session lifecycle: `backend_app_context` rolls back on exception, `db.session.remove()` on exit.
- Tests: pytest, run from the repo `.venv` (`pythonpath = ["."]`, see `pyproject.toml`). Tests live in `tests/`.
- Deploy is pipeline-driven on push (`.github/workflows/deploy.yml`): `terraform apply` + invoke `db_migrate`
  + `update-function-code`. Environments are rebuilt greenfield. **Agents must not run terraform/aws or commit/push.**

## Remove the deprecated `.mcp/` docs

```bash
git rm -r .mcp
```
