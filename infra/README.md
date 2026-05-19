# Abricot TP3 Infrastructure

Terraform root for the Abricot TP3 AWS architecture.

## What This Creates

- Cognito User Pool, App Client, and Hosted UI domain.
- API Gateway HTTP API with:
  - public `GET /health`
  - public `GET /callback`
  - protected `GET /auth-test`
  - protected `POST /users`
  - protected `GET /users/{userId}`
  - protected `PUT /users/{userId}`
- Python Lambdas:
  - `health-lambda`
  - `users-service-lambda`
- A dedicated VPC with:
  - 2 public subnets for NAT
  - 2 private app subnets for Lambda
  - 2 private DB subnets for RDS and RDS Proxy
  - NAT Gateway for private Lambda egress
- Private PostgreSQL RDS.
- RDS Proxy in private DB subnets.
- Secrets Manager secret for RDS Proxy credentials.
- Three explicit security groups: `lambda-sg`, `rds-proxy-sg`, `rds-sg`.

Terraform does not create IAM roles and does not use `data.aws_iam_role`.
Both Lambda and RDS Proxy receive the AWS Academy `LabRole` ARN through
variables.

## Architecture

1. User opens the frontend from S3 website hosting or local dev.
2. Frontend redirects to Cognito Hosted UI.
3. Cognito redirects to API Gateway `GET /callback`.
4. `GET /callback` is public and invokes `users-service-lambda`.
5. `users-service-lambda` exchanges the authorization code with Cognito and
   redirects to frontend `/auth/callback#access_token=...`.
6. Protected frontend calls use `Authorization: Bearer <access_token>`.
7. API Gateway validates JWTs with the Cognito authorizer.
8. DB-backed users routes invoke `users-service-lambda` in private app subnets.
9. `users-service-lambda` reaches PostgreSQL only through RDS Proxy.

## Why RDS Is Private

The RDS instance is created with `publicly_accessible = false`, placed only in
private DB subnets, and attached only to `rds-sg`. There is no public inbound
rule and no direct Lambda-to-RDS rule.

## Why RDS Proxy Exists

RDS Proxy is the only database endpoint exposed to `users-service-lambda`. This
keeps Lambda from connecting directly to RDS and gives a controlled connection
layer between Lambda and PostgreSQL.

RDS Proxy requires a Secrets Manager secret and an IAM role it can assume. In
AWS Academy Lab, the only allowed role input is:

```hcl
rds_proxy_role_arn = "arn:aws:iam::<account-id>:role/LabRole"
```

If LabRole cannot be used by RDS Proxy in the lab account, stop and report the
blocker. Do not use public RDS or direct DB access as a fallback.

## Why Lambda Needs NAT

`users-service-lambda` runs in private app subnets. It still handles
`GET /callback`, so it must call Cognito `/oauth2/token` over the internet.
The private app subnets route outbound internet traffic through NAT Gateway.

## Security Groups

| Component | Security Group | Rules |
|---|---|---|
| `users-service-lambda` | `lambda-sg` | Outbound TCP 5432 to `rds-proxy-sg`; outbound TCP 443 to internet through NAT. |
| RDS Proxy | `rds-proxy-sg` | Inbound TCP 5432 from `lambda-sg`; outbound TCP 5432 to `rds-sg`. |
| RDS PostgreSQL | `rds-sg` | Inbound TCP 5432 only from `rds-proxy-sg`. |

No Lambda direct access to RDS is configured. No public access to RDS is
configured.

## Variables

The normal deliverable path only needs these values in `terraform.tfvars`:

```hcl
project_name = "abricot-tp3"
aws_region   = "us-east-1"

lambda_role_arn    = "arn:aws:iam::<account-id>:role/LabRole"
rds_proxy_role_arn = "arn:aws:iam::<account-id>:role/LabRole"

frontend_callback_url = "http://localhost:5173/auth/callback"

postgres_db       = "abricot"
postgres_user     = "abricot_app"
postgres_password = "CHANGE_ME_STRONG_PASSWORD"

enable_full_private_stack = true
users_service_layer_arns  = []
```

Internal network and database defaults live in `locals.tf`: CIDRs, AZs, RDS
size, PostgreSQL port, SSL mode, Cognito scopes, and Lambda runtime.

## Deploy From Zero

```bash
cp terraform.tfvars.example terraform.tfvars
```

Edit `terraform.tfvars`:

- Replace `<account-id>` in both LabRole ARNs.
- Replace `postgres_password` with a strong password.
- Replace `frontend_callback_url` with the S3 website callback URL for deployed
  frontend, or keep localhost for local smoke tests.
- Set `users_service_layer_arns` only if `psycopg2` is supplied through a
  Lambda Layer. Otherwise package the dependency into `lambdas/users_service`
  before applying.

Then run:

```bash
terraform init
terraform fmt
terraform validate
terraform plan
terraform apply
```

## Destroy And Recreate

The stack is designed to be destroyable and recreateable:

```bash
terraform destroy
terraform apply
```

If the Cognito User Pool contains users, AWS may block deletion unless the pool
is cleaned first. Do not manually delete random resources outside Terraform
unless state recovery is planned.

## Optional Two-Phase Recovery

The normal path is one full stack apply with:

```hcl
enable_full_private_stack = true
```

If AWS provider behavior rejects changing `users-service-lambda` from no
`vpc_config` to `vpc_config` in the same apply, use this emergency sequence:

Phase 1:

```hcl
enable_full_private_stack = true
recovery_skip_lambda_private_attachment = true
```

Apply only if the plan creates or repairs VPC, NAT, private RDS, RDS Proxy, and
RDS Proxy target without destroying PASO 1.

Phase 2:

```hcl
enable_full_private_stack = true
recovery_skip_lambda_private_attachment = false
```

Then plan/apply the Lambda private subnet attachment and `/users` routes.

This is only a recovery path. Do not present public RDS, direct DB access, or
removing RDS Proxy as alternatives.
