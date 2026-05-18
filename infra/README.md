# Abricot TP3 PASO 1/PASO 2.2B infra

Terraform root for the Cognito + API Gateway + Lambda smoke test and the
optional PASO 2.2B private database infrastructure.

## Scope

This step creates only:

- Cognito User Pool, App Client, and Hosted UI domain.
- HTTP API Gateway with:
  - public `GET /health`
  - public `GET /callback`
  - protected `GET /auth-test`
- Python Lambdas:
  - `health-lambda`
  - `users-service-lambda`
- Required outputs.
- PASO 2.1 protected users routes, only when RDS Proxy is enabled:
  - `POST /users`
  - `GET /users/{userId}`
  - `PUT /users/{userId}`
- Optional PASO 2.2B private infra when `enable_private_database_infra=true`:
  - private app subnets
  - private DB subnets
  - NAT Gateway for Cognito `/oauth2/token`
  - `lambda-sg`, `rds-proxy-sg`, `rds-sg`
  - private RDS PostgreSQL
  - RDS Proxy if AWS Lab permits/provides IAM role and secret support

AWS Academy Lab notes:

- Terraform does not create Lambda IAM roles or attach IAM policies.
- Terraform does not look up `LabRole` with `iam:GetRole`; set `lambda_role_arn` instead.
- Terraform does not create explicit CloudWatch log groups or API Gateway access logs.
- Terraform does not add resource tags.
- `enable_private_database_infra=false` by default keeps PASO 1 plans isolated
  from VPC/RDS/RDS Proxy variables and DB-backed `/users` routes.
- RDS Proxy for PostgreSQL requires Secrets Manager credentials and an IAM role
  that RDS Proxy can assume. This Terraform accepts `rds_proxy_role_arn` as a
  variable and never uses `data.aws_iam_role`.

Still out of scope here: creating orders-service, SNS, SQS, workers, SES, and
any separate callback Lambda.

## PASO 2.2B feature flag

Keep this value for PASO 1-only validation and plans:

```hcl
enable_private_database_infra = false
```

When false:

- no RDS, RDS Proxy, NAT, subnet, or SG resources are created
- private DB variables are not required
- `users-service-lambda` stays in the PASO 1 working shape, outside VPC

When true:

- Terraform attempts to add the private network/RDS/RDS Proxy stack
- `users-service-lambda` is placed in private app subnets
- DB access goes only through RDS Proxy

## Networking contract

`users-service-lambda` handles both `/callback` and `/users/*`. Because it is
configured inside private app subnets for database access, those subnets must
also have outbound internet through NAT so `/callback` can exchange the Cognito
authorization code at `/oauth2/token`.

Required existing AWS pieces:

- NAT egress from private app subnets.
- `lambda-sg` outbound TCP 5432 to `rds-proxy-sg`.
- `rds-proxy-sg` inbound TCP 5432 from `lambda-sg`.
- `rds-proxy-sg` outbound TCP 5432 to `rds-sg`.
- `rds-sg` inbound TCP 5432 from `rds-proxy-sg`.

Do not configure Lambda to use a direct RDS instance endpoint.

## Usage

```bash
cd infra
terraform init
terraform fmt
terraform validate
terraform plan -var-file=terraform.tfvars
```

Start from `terraform.tfvars.example` and set a globally unique
`cognito_domain_prefix` if the default is already taken in the AWS account.
Set `lambda_role_arn` to the AWS Lab role ARN, for example
`arn:aws:iam::<account-id>:role/LabRole`.
Set `enable_private_database_infra=true` only when intentionally planning PASO
2.2B. Then set `postgres_db`, `postgres_user`, `postgres_password`, and
`rds_proxy_role_arn`. If `create_db_secret=false`, also set `db_secret_arn`.
Set `users_service_layer_arns` to a Lambda layer that contains `psycopg2-binary`,
or package that dependency into `lambdas/users_service` before apply.
