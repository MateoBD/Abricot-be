# Abricot TP3 PASO 1 infra

Terraform root for the Cognito + API Gateway + Lambda smoke test.

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

AWS Academy Lab notes:

- Terraform does not create IAM roles or attach IAM policies.
- Terraform does not look up `LabRole` with `iam:GetRole`; set `lambda_role_arn` instead.
- Terraform does not create explicit CloudWatch log groups or API Gateway access logs.
- Terraform does not add resource tags.

Out of scope for PASO 1: RDS, RDS Proxy, `users.cognito_sub`, orders-service,
SNS, SQS, workers, SES, and any separate callback Lambda.

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
