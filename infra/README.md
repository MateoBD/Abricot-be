# Abricot TP3 PASO 1/PASO 2 infra

Terraform root for the Cognito + API Gateway + Lambda smoke test and PASO 2
users-service profile mapping routes.

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
- PASO 2 protected users routes:
  - `POST /users`
  - `GET /users/{userId}`
  - `PUT /users/{userId}`

AWS Academy Lab notes:

- Terraform does not create IAM roles or attach IAM policies.
- Terraform does not look up `LabRole` with `iam:GetRole`; set `lambda_role_arn` instead.
- Terraform does not create explicit CloudWatch log groups or API Gateway access logs.
- Terraform does not add resource tags.
- Terraform does not create RDS/RDS Proxy in this AWS Lab step; set `existing_db_*` variables.

Still out of scope here: creating RDS/RDS Proxy, orders-service, SNS, SQS,
workers, SES, and any separate callback Lambda.

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
Set `existing_db_host`, `existing_db_name`, `existing_db_username`, and
`existing_db_password` before deploying PASO 2.
Set `users_service_layer_arns` to a Lambda layer that contains `psycopg2-binary`,
or package that dependency into `lambdas/users_service` before apply.
