# Infrastructure Audit — Abricot TP3

**Date:** 2026-05-19  
**Scope:** `infra/` (Terraform) + `lambdas/` (Lambda source)  
**Auditor:** Claude Sonnet 4.6  
**Context:** AWS Academy Lab environment (LabRole-constrained)

---

## Table of Contents

1. [Executive Summary](#1-executive-summary)
2. [Architecture Overview](#2-architecture-overview)
3. [Security Findings](#3-security-findings)
4. [Terraform Code Quality](#4-terraform-code-quality)
5. [AWS Architecture Best Practices](#5-aws-architecture-best-practices)
6. [Lambda Code Review](#6-lambda-code-review)
7. [File Organization](#7-file-organization)
8. [Pre-commit & CI/CD Hygiene](#8-pre-commit--cicd-hygiene)
9. [Recommended Restructure](#9-recommended-restructure)
10. [Issue Summary Table](#10-issue-summary-table)

---

## 1. Executive Summary

The infrastructure is **architecturally sound for a lab/academic environment**. The private VPC → NAT → Lambda → RDS Proxy → RDS chain is correct and follows AWS best practices. Security groups are correctly scoped (no direct Lambda→RDS, no public RDS). Documentation (README, inline comments) is above average.

However, there are **one critical runtime failure** (`psycopg2-binary` is incompatible with Lambda), **several medium-severity design issues**, and **a pattern that needs fixing before any production-like use**.

| Severity | Count |
|----------|-------|
| 🔴 CRITICAL | 2 |
| 🟠 HIGH | 5 |
| 🟡 MEDIUM | 11 |
| 🟢 LOW / SUGGESTION | 15 |

---

## 2. Architecture Overview

```
[Frontend / Local Dev]
        │
        ▼
[Cognito Hosted UI] ──── OAuth2 Code Flow ────►
        │
        ▼
[API Gateway HTTP API]
   ├── GET /health            → health-lambda (public, no VPC)
   ├── GET /callback          → users-service-lambda (public, VPC)
   ├── GET /auth-test         → users-service-lambda (JWT required)
   ├── POST /users            → users-service-lambda (JWT required)
   ├── GET /users/{userId}    → users-service-lambda (JWT required)
   └── PUT /users/{userId}    → users-service-lambda (JWT required)
                                      │
                             [lambda-sg] in private-app-subnets
                                      │
                       ┌──────────────┴────────────────┐
                       │ NAT Gateway (internet egress)  │ RDS Proxy [rds-proxy-sg]
                       │ for Cognito token exchange     │      │
                       └────────────────────────────────┘      ▼
                                                      [RDS PostgreSQL Multi-AZ]
                                                      primary (AZ-a) + standby (AZ-b)
                                                      [rds-sg] in private-db-subnets
```

**Terraform files:**

| File | Purpose |
|------|---------|
| `versions.tf` | Provider version constraints |
| `providers.tf` | AWS provider config |
| `variables.tf` | Input variables |
| `locals.tf` | Computed locals + Lambda function map |
| `main.tf` | Cognito, API Gateway, Lambda, routes, permissions |
| `private_database.tf` | VPC, subnets, NAT, SGs, RDS, RDS Proxy, Secrets Manager |
| `outputs.tf` | All outputs |
| `.gitignore` | Blocks `.terraform/`, `*.zip`, `*.tfstate`, `*.tfvars` |

---

## 3. Security Findings

### 🔴 CRITICAL-1: `psycopg2-binary` Will Fail at Lambda Runtime

**File:** `lambdas/users_service/requirements.txt:1`, `infra/locals.tf:18`

`psycopg2-binary` bundles pre-compiled C extensions linked against system glibc. Lambda runs on Amazon Linux 2 (aarch64 or x86_64). The `psycopg2-binary` wheel downloaded by pip on a Mac/Windows/Ubuntu dev machine targets a different platform → Lambda will import `psycopg2` and immediately raise `ImportError` or `OSError`.

**Impact:** Every DB-backed route (`POST /users`, `GET /users/{userId}`, `PUT /users/{userId}`) returns 500 in production. This is a silent total failure.

**Fix options (pick one):**

```text
Option A — Lambda Layer (recommended for lab):
  Build psycopg2 compiled for Amazon Linux 2 and supply the ARN via
  var.users_service_layer_arns. The requirements.txt is then only for
  local dev, not for Lambda packaging.

Option B — Use aws-psycopg2 package:
  Replace psycopg2-binary with the aws-psycopg2 package in requirements.txt,
  which ships binaries compiled for Lambda.

Option C — Docker-based build:
  docker run --rm -v $(pwd):/var/task public.ecr.aws/lambda/python:3.12 \
    pip install psycopg2-binary -t /var/task/lambdas/users_service/

Option D — Switch to asyncpg or psycopg3:
  psycopg3 (psycopg) has better binary portability.
```

---

### 🔴 CRITICAL-2: DB Password Injected as Lambda Environment Variable

**File:** `infra/locals.tf:53`, `infra/private_database.tf:235-253`

`POSTGRES_PASSWORD = var.postgres_password` is stored as a **plaintext Lambda environment variable**. Lambda env vars are visible in the AWS Console, in CloudTrail, and to any IAM principal with `lambda:GetFunctionConfiguration`.

You already create an `aws_secretsmanager_secret` with the password. The Lambda should retrieve that secret **at runtime**, not receive it as an env var.

```python
# Instead of reading os.environ["POSTGRES_PASSWORD"], do:
import boto3, json
sm = boto3.client("secretsmanager")
secret = json.loads(sm.get_secret_value(SecretId=os.environ["DB_SECRET_ARN"])["SecretString"])
password = secret["password"]
```

Pass only `DB_SECRET_ARN` as the env var. This requires LabRole to have `secretsmanager:GetSecretValue` permission (it typically does in Academy).

Additionally, consider enabling IAM auth on the RDS Proxy:

```hcl
auth {
  auth_scheme = "SECRETS"
  iam_auth    = "REQUIRED"   # <-- upgrade from DISABLED
  secret_arn  = aws_secretsmanager_secret.db[0].arn
}
```

With IAM auth enabled, Lambda authenticates to RDS Proxy using a signed token (no password required at all).

---

### 🟠 HIGH-1: No Remote State Backend

**File:** `infra/versions.tf`

There is no `backend` block. State is stored in a local `terraform.tfstate` file. This means:

- State is lost if the local machine is wiped.
- Multiple team members cannot apply concurrently (no locking).
- No audit trail of who applied what.

**Fix:**

```hcl
# versions.tf
terraform {
  backend "s3" {
    bucket         = "abricot-tp3-tfstate"
    key            = "infra/terraform.tfstate"
    region         = "us-east-1"
    dynamodb_table = "abricot-tp3-tfstate-lock"
    encrypt        = true
  }
}
```

For AWS Academy, the S3 bucket and DynamoDB table must be created manually first (or with a bootstrap script), since LabRole may not allow creating them via Terraform itself.

---

### 🟠 HIGH-2: No State Locking

Follows directly from HIGH-1. Without a DynamoDB lock table, concurrent `terraform apply` runs will corrupt state. For a team project this is high risk.

---

### 🟠 HIGH-3: Pre-commit Hooks Disabled

**File:** `.pre-commit-config.yaml:2`

```yaml
repos: []
```

All hooks are disabled. The repo has hook scripts in `.hooks/` and a `.pre-commit-config.yaml`, but it does nothing. This means:

- No `terraform fmt` check on commit.
- No `terraform validate` check on commit.
- No secret scanning (e.g., `detect-secrets` or `gitleaks`).
- Branch protection hooks exist as files but are never run.

Minimum recommended hooks for a Terraform project:

```yaml
repos:
  - repo: https://github.com/antonbabenko/pre-commit-terraform
    rev: v1.88.0
    hooks:
      - id: terraform_fmt
      - id: terraform_validate
      - id: terraform_docs
  - repo: https://github.com/gitleaks/gitleaks
    rev: v8.18.1
    hooks:
      - id: gitleaks
```

---

### 🟠 HIGH-4: `aws_lambda_permission` Source ARN Too Permissive

**File:** `infra/main.tf:165-172`

```hcl
source_arn = "${aws_apigatewayv2_api.http.execution_arn}/*/*"
```

This grants API Gateway permission to invoke each Lambda for **any method on any route**. Best practice is to scope per-route:

```hcl
# For a route "GET /health" on the health lambda:
source_arn = "${aws_apigatewayv2_api.http.execution_arn}/*/GET/health"
```

In the current `for_each` structure, this requires generating per-route permissions rather than per-function permissions. At minimum, health-lambda should not be invocable from users routes and vice versa.

---

### 🟠 HIGH-5: `infra/.gitignore` Has Redundant and Confusing Entries

**File:** `infra/.gitignore`

```text
*.tfvars          ← line 5
!terraform.tfvars.example
crash.log
crash.*.log
terraform.tfvars  ← line 9 — DUPLICATE of *.tfvars
*.tfvars          ← line 10 — TRIPLICATE
```

`terraform.tfvars` appears on line 5 (via `*.tfvars`) AND explicitly on line 9. `*.tfvars` appears on both line 5 and line 10. While functionally correct (tfvars is blocked), the duplication is a maintenance smell and could mislead a team member into thinking the file would be tracked.

**Also missing from gitignore:**
- `.terraform.tfstate.lock.info` (lock files created during operations)
- `override.tf` and `override.tf.json` (common accidental files)
- `.terraformrc` / `terraform.rc`

---

## 4. Terraform Code Quality

### 🟡 MEDIUM-1: `private_database.tf` Filename Is Misleading

**File:** `infra/private_database.tf`

This file contains **293 lines** covering:
- VPC + Internet Gateway
- Public and private subnets (3 tiers)
- Route tables and associations
- EIP + NAT Gateway
- 3 security groups + 6 security group rules
- DB subnet group
- RDS instance
- Secrets Manager secret + version
- RDS Proxy + target group + target

That is an entire network stack, not "a private database". The filename misled even the person writing this audit (and you, the author, questioning whether it's good practice).

**Recommended split:**

```
infra/
├── network.tf          # VPC, IGW, subnets, route tables, NAT, EIP
├── security_groups.tf  # All SG resources and SG rules
├── database.tf         # RDS instance, subnet group
├── rds_proxy.tf        # RDS Proxy, target group, target, Secrets Manager
```

This is standard Terraform organization and makes each file's purpose immediately clear. The `count = local.full_private_stack_enabled ? 1 : 0` toggle works identically across split files.

---

### 🟡 MEDIUM-2: Network Configuration Hard-Coded in `locals.tf`

**File:** `infra/locals.tf:29-33`

```hcl
vpc_cidr                 = "10.42.0.0/16"
availability_zones       = ["us-east-1a", "us-east-1b"]
public_subnet_cidrs      = ["10.42.0.0/24", "10.42.1.0/24"]
private_app_subnet_cidrs = ["10.42.10.0/24", "10.42.11.0/24"]
private_db_subnet_cidrs  = ["10.42.20.0/24", "10.42.21.0/24"]
```

These are embedded as immutable constants. Issues:

1. `availability_zones` is region-specific but the region is a variable. Deploying to `eu-west-1` will fail because `us-east-1a` does not exist there.
2. CIDRs cannot be changed without destroying and recreating the entire VPC stack (subnet CIDR changes require destroy/create).
3. No CIDR validation — a typo produces a valid-looking but broken network.

**Fix:** Move to variables with proper defaults and validation:

```hcl
variable "vpc_cidr" {
  type    = string
  default = "10.42.0.0/16"
  validation {
    condition     = can(cidrhost(var.vpc_cidr, 0))
    error_message = "Must be valid CIDR."
  }
}

# Derive AZs from data source instead of hardcoding:
data "aws_availability_zones" "available" {
  state = "available"
}
locals {
  availability_zones = slice(data.aws_availability_zones.available.names, 0, 2)
}
```

---

### 🟡 MEDIUM-3: RDS Configuration Hard-Coded in `locals.tf`

**File:** `infra/locals.tf:35-38`

```hcl
rds_instance_class    = "db.t3.micro"
rds_allocated_storage = 20
```

These should be variables to allow sizing per environment. `db.t3.micro` + `multi_az = true` is a contradictory combination (see MEDIUM-8).

---

### 🟡 MEDIUM-4: `count` Used for All Conditional Resources

**File:** `infra/private_database.tf` (every resource)

Every conditional resource uses `count = local.full_private_stack_enabled ? 1 : 0`, leading to index-based references everywhere:

```hcl
aws_vpc.private[0].id
aws_subnet.public[0].id
aws_nat_gateway.this[0].id
```

The modern Terraform pattern for conditional singleton resources is `for_each` with a set:

```hcl
resource "aws_vpc" "private" {
  for_each = local.full_private_stack_enabled ? toset(["this"]) : toset([])
  ...
}
# Reference: aws_vpc.private["this"].id
```

This avoids `[0]` indexing throughout, makes intent explicit, and avoids issues when `count` changes destroy/recreate ordering. For subnets that already use count-based loops (e.g., iterating over CIDRs), a combined approach is needed.

For this codebase, switching entirely is a significant refactor with state migration requirements (`terraform state mv`). It is a suggestion, not an urgent fix — but new resources should use `for_each`.

---

### 🟡 MEDIUM-5: `locals.tf` Mixed Concerns (Compute + Config)

**File:** `infra/locals.tf`

`locals.tf` currently contains:
- URL manipulation logic (lines 7-16)
- Cognito configuration (lines 14-16)
- Network CIDR constants (lines 29-33)
- RDS configuration constants (lines 35-38)
- Lambda environment variable construction (lines 40-59)
- Lambda function definition map (lines 62-81)

The Lambda function map (`lambda_functions`) is particularly out of place in `locals.tf`. It's a large configuration block that belongs either in `main.tf` alongside the Lambda resources or in a dedicated `lambda_config.tf` / `locals_lambda.tf`.

---

### 🟡 MEDIUM-6: `outputs.tf` Contains Internal Academic References

**File:** `infra/outputs.tf:78,81,83,88,92,97`

Several output descriptions reference internal task phases:

```hcl
description = "Private app subnet IDs for DB-backed Lambdas when PASO 2.2B is enabled."
description = "Private DB subnet IDs across two AZs for Multi-AZ private RDS and RDS Proxy."
description = "Whether users-service-lambda is attached to private app subnets."
```

Outputs are the public interface of a Terraform module. References to "PASO 2.2B" are academic task markers that do not belong in infrastructure output descriptions. They will confuse anyone reusing or maintaining this after the course.

---

### 🟡 MEDIUM-7: `frontend_base_url` String Extraction Is Fragile

**File:** `infra/locals.tf:8`

```hcl
frontend_base_url = trimsuffix(trimsuffix(local.frontend_callback_url, "/auth/callback"), "/")
```

This attempts to strip `/auth/callback` from the callback URL to get the base URL. If the callback URL changes (e.g., to `/oauth/callback`, or gains a query param), this silently produces a wrong value. Two independent `trimsuffix` calls to parse a URL is fragile.

The correct fix is to require `frontend_base_url` as a separate variable instead of deriving it from the callback URL:

```hcl
variable "frontend_base_url" {
  description = "Frontend SPA base URL (e.g. https://app.example.com)"
  type        = string
  default     = "http://localhost:5173"
}
```

---

### 🟡 MEDIUM-8: CORS Bakes `localhost:5173` Into Infrastructure

**File:** `infra/main.tf:47`

```hcl
allow_origins = distinct([local.frontend_base_url, "http://localhost:5173"])
```

`http://localhost:5173` is hardcoded as an always-allowed CORS origin. A production deployment would permanently allow CORS from localhost. This should be variable-driven:

```hcl
variable "extra_cors_origins" {
  type    = list(string)
  default = ["http://localhost:5173"]
}

allow_origins = distinct(concat([local.frontend_base_url], var.extra_cors_origins))
```

---

### 🟡 MEDIUM-9: No CloudWatch Log Groups with Retention

**File:** `infra/main.tf` (Lambda resources)

No `aws_cloudwatch_log_group` resources are created. Lambda auto-creates `/aws/lambda/<function-name>` log groups on first invocation with **infinite retention** by default. This leaks logs indefinitely and incurs ongoing CloudWatch storage costs.

```hcl
resource "aws_cloudwatch_log_group" "lambda" {
  for_each = local.lambda_functions

  name              = "/aws/lambda/${local.name_prefix}-${replace(each.key, "_", "-")}"
  retention_in_days = 14
}
```

---

### 🟡 MEDIUM-10: No Explicit Lambda Memory Size

**File:** `infra/locals.tf:62-81`

Lambda `memory_size` defaults to 128 MB when unspecified. `users-service-lambda` establishes a DB connection through RDS Proxy and processes JWT claims — 128 MB is often insufficient for psycopg2 + connection overhead, causing cold-start failures or OOM errors. Should be explicit:

```hcl
users_service = {
  ...
  memory_size = 256  # explicit, reviewable
}
```

---

### 🟡 MEDIUM-11: `aws_secretsmanager_secret` Name Collision on Destroy/Recreate

**File:** `infra/private_database.tf:235-239`

```hcl
resource "aws_secretsmanager_secret" "db" {
  name = "${local.name_prefix}/postgres"
}
```

Secrets Manager enforces a **7-day deletion grace period** after a secret is deleted. If you run `terraform destroy` and then `terraform apply`, the apply will fail because the secret name is still reserved. For lab use, add:

```hcl
resource "aws_secretsmanager_secret" "db" {
  name                    = "${local.name_prefix}/postgres"
  recovery_window_in_days = 0   # immediate deletion, OK for lab
}
```

---

## 5. AWS Architecture Best Practices

### 🟡 MEDIUM: Single NAT Gateway — Single Point of Failure

**File:** `infra/private_database.tf:63-76`

One NAT Gateway is deployed in `public[0]` (AZ-a). All private app subnets (AZ-a and AZ-b) route through it. If AZ-a fails, Lambda in AZ-b loses internet egress (cannot reach Cognito `/oauth2/token`).

- **For production:** One NAT GW per AZ.
- **For this lab:** Acceptable cost trade-off. Document the SPOF explicitly.

```hcl
# Production pattern (one per AZ):
resource "aws_nat_gateway" "this" {
  count         = local.full_private_stack_enabled ? length(local.public_subnet_cidrs) : 0
  allocation_id = aws_eip.nat[count.index].id
  subnet_id     = aws_subnet.public[count.index].id
}
```

---

### 🟢 LOW: `multi_az = true` on `db.t3.micro` Is Contradictory

**File:** `infra/private_database.tf:218`

`multi_az = true` doubles the RDS cost and makes sense for production workloads requiring < 30s failover. Using it on `db.t3.micro` (smallest instance, ~$13/month) is unusual — you wouldn't run production traffic requiring HA on `t3.micro`. For a lab where the goal is to demonstrate the architecture pattern, this is fine. But know that it costs ~2× the single-AZ equivalent.

---

### 🟢 LOW: `deletion_protection = false` and `skip_final_snapshot = true`

**File:** `infra/private_database.tf:219-220`

Acceptable for lab. Document explicitly. For any data-bearing environment:

```hcl
deletion_protection  = true
skip_final_snapshot  = false
final_snapshot_identifier = "${local.name_prefix}-final-snapshot"
```

---

### 🟢 LOW: RDS Engine Version Not Pinned

**File:** `infra/private_database.tf:207`

```hcl
engine = "postgres"
# engine_version not specified
```

AWS will use the current default minor version. If the default changes, `terraform plan` will show a diff and may trigger recreation. Pin it:

```hcl
engine         = "postgres"
engine_version = "16.3"
```

---

### 🟢 LOW: No X-Ray Tracing on Lambda

**File:** `infra/main.tf:78-104`

No `tracing_config` block on `aws_lambda_function`. X-Ray provides distributed tracing from API Gateway through Lambda to RDS Proxy. Worth enabling for debugging:

```hcl
tracing_config {
  mode = "Active"
}
```

---

### 🟢 LOW: API Gateway `auto_deploy = true`

**File:** `infra/main.tf:52-56`

```hcl
resource "aws_apigatewayv2_stage" "default" {
  auto_deploy = true
}
```

`auto_deploy = true` on the `$default` stage redeploys every time any integration changes. For a lab this is convenient. For production, this means route changes deploy immediately without a promotion gate. Consider explicit deployment management in production.

---

### 🟢 LOW: No VPC Endpoints for AWS Services

**File:** `infra/private_database.tf`

Lambda in private subnets currently uses NAT Gateway to reach:
- Cognito `/oauth2/token` (external HTTPS — NAT required, no VPC endpoint available)
- Secrets Manager (if migrated to runtime secret fetching — VPC endpoint available)
- CloudWatch Logs (VPC endpoint available)

For Secrets Manager and CloudWatch Logs, VPC endpoints eliminate NAT GW traffic charges and improve security (traffic stays within AWS). For this lab, NAT is fine. Note for future reference:

```hcl
resource "aws_vpc_endpoint" "secretsmanager" {
  vpc_id              = local.private_vpc_id
  service_name        = "com.amazonaws.${var.aws_region}.secretsmanager"
  vpc_endpoint_type   = "Interface"
  subnet_ids          = local.private_app_subnet_ids
  security_group_ids  = [aws_security_group.lambda[0].id]
  private_dns_enabled = true
}
```

---

### 🟢 LOW: Missing HTTP Methods in CORS Configuration

**File:** `infra/main.tf:45`

```hcl
allow_methods = ["GET", "POST", "PUT", "OPTIONS"]
```

`DELETE` and `PATCH` are absent. If future routes use these methods, CORS will block browser requests silently. Add proactively or document as intentional constraint.

---

### 🟢 LOW: No Resource Tags

**File:** `infra/providers.tf:2-5`

```hcl
# default_tags removed to avoid AccessDeniedException on apply.
```

The comment correctly explains the Lab constraint (Academy voc-cancel-cred policy blocks tagging on API GW and CloudWatch). However, VPC, subnets, security groups, RDS, Lambda, and Cognito resources **can** be tagged. Only API GW and CloudWatch fail. At minimum, tag the VPC-family and RDS resources for cost attribution and searchability:

```hcl
resource "aws_vpc" "private" {
  ...
  tags = {
    Name        = "${local.name_prefix}-vpc"
    Environment = "lab"
    Project     = var.project_name
  }
}
```

---

## 6. Lambda Code Review

### 🔴 CRITICAL: `psycopg2-binary` — See Section 3

Already covered. This is the most impactful bug in the entire codebase.

---

### 🟢 LOW: `__pycache__` Packaged Into Lambda ZIP

**File:** `infra/locals.tf:65,72`

```hcl
source_dir = "${path.module}/../lambdas/health"
```

`archive_file` zips the entire directory, including `__pycache__/*.pyc` files. These are platform-specific bytecode and bloat the package. The `archive_file` resource supports exclusions:

```hcl
data "archive_file" "lambda" {
  for_each = local.lambda_functions
  type        = "zip"
  source_dir  = each.value.source_dir
  output_path = "${path.module}/${each.key}.zip"
  excludes    = ["__pycache__", "*.pyc", "*.pyo", "*.pytest_cache", "*.dist-info"]
}
```

---

### 🟢 LOW: Lambda Uses Inline Router — Routes Should Match API Gateway Routes Exactly

**File:** `lambdas/users_service/handler.py:505-524`

```python
if method == "GET" and path.endswith("/callback"):
    ...
if method == "GET" and "/users/" in path:
    ...
```

The routing logic uses `endswith` and `in` string checks. This is fragile:
- A path like `/evil/callback` would match the callback handler.
- A path like `/admins/users/123` would match the users handler.

With API Gateway HTTP API v2 (payload 2.0), the `rawPath` is exactly what was configured in the route key. Prefer exact-match routing:

```python
ROUTES = {
    ("GET", "/callback"):       _handle_callback,
    ("GET", "/auth-test"):      _handle_auth_test,
    ("POST", "/users"):         _handle_post_users,
}

def handler(event, context):
    path = _route_path(event)
    method = _method(event)
    route_fn = ROUTES.get((method, path))
    if route_fn:
        return route_fn(event)
    # parameterized routes
    if method == "GET" and re.fullmatch(r"/users/[^/]+", path):
        return _handle_get_user(event)
    ...
```

---

### 🟢 LOW: DB Connection Created Per Request — No Connection Reuse

**File:** `lambdas/users_service/handler.py:180-203`

```python
def _db_connect():
    return psycopg2.connect(...)
```

Each Lambda invocation opens a new database connection. RDS Proxy mitigates this at the infrastructure level (connection pooling), but within a single warm Lambda instance, connections are not reused across requests. For a Lambda that handles multiple routes, a module-level connection with reconnect-on-failure would reduce latency and RDS Proxy overhead. This is a cold-start optimization, not a correctness issue.

---

### 🟢 LOW: `users_service` Lambda Timeout Too Short for VPC Cold Start

**File:** `infra/locals.tf:74`

```hcl
timeout = 10
```

VPC-attached Lambda cold starts take 5–15 seconds just for ENI attachment, before any application code runs. A 10s timeout risks cold-start timeouts under certain conditions. Recommend 30s for VPC Lambdas in general:

```hcl
timeout = 30
```

---

### 🟢 LOW: No Input Validation on `POST /users` Body Fields

**File:** `lambdas/users_service/handler.py:401-403`

```python
name    = str(claims.get("given_name") or email.split("@", 1)[0]).strip() or "Cognito"
surname = str(claims.get("family_name") or "User").strip() or "User"
```

`name` and `surname` are derived from JWT claims with fallbacks. No length validation — a very long `given_name` claim could produce an over-length name. This is low-risk for Cognito-issued tokens but worth noting for compliance.

---

## 7. File Organization

### Current Structure

```
infra/
├── .gitignore           ✓ correct, minor redundancy
├── .terraform.lock.hcl  ✓ committed (correct per Terraform best practices)
├── locals.tf            ⚠ oversized, mixed concerns
├── main.tf              ✓ Cognito + API GW + Lambda
├── outputs.tf           ⚠ academic references in descriptions
├── private_database.tf  ⚠ misleading name, contains entire network stack
├── providers.tf         ✓ minimal, correctly constrained for Lab
├── README.md            ✓ excellent documentation
├── terraform.tfvars     ✗ not tracked (gitignored correctly)
├── terraform.tfvars.example ✓ committed safely
├── variables.tf         ✓ good variable definitions with validation
└── versions.tf          ⚠ missing backend block
lambdas/
├── health/
│   ├── handler.py       ✓ minimal, correct
│   └── README.md        ✓
└── users_service/
    ├── handler.py       ✓ well-structured, single critical bug
    ├── requirements.txt ⚠ psycopg2-binary wrong for Lambda
    └── README.md
```

### Recommended Structure

```
infra/
├── .gitignore
├── .terraform.lock.hcl
├── backend.tf           NEW — remote S3 backend
├── versions.tf
├── providers.tf
├── variables.tf
├── locals.tf            REDUCED — only URL/scope/feature-flag logic
├── locals_lambda.tf     NEW — lambda function map + environments
├── network.tf           RENAMED/SPLIT from private_database.tf
├── security_groups.tf   NEW — split from private_database.tf
├── database.tf          NEW — RDS + subnet group, split from private_database.tf
├── rds_proxy.tf         NEW — RDS Proxy resources, split from private_database.tf
├── cognito.tf           NEW — split from main.tf
├── api_gateway.tf       NEW — split from main.tf
├── lambda.tf            RENAMED — Lambda functions, permissions, log groups
├── outputs.tf
├── README.md
└── terraform.tfvars.example
lambdas/
├── health/
│   ├── handler.py
│   └── requirements.txt (empty — no deps)
└── users_service/
    ├── handler.py
    └── requirements.txt   FIX — use aws-psycopg2 or remove for Layer approach
```

---

## 8. Pre-commit & CI/CD Hygiene

### Pre-commit: Completely Disabled

`.pre-commit-config.yaml` has `repos: []`. No checks run on commit.

**Minimum viable hooks to add:**

```yaml
repos:
  - repo: https://github.com/antonbabenko/pre-commit-terraform
    rev: v1.88.0
    hooks:
      - id: terraform_fmt
        args: [--args=-recursive]
      - id: terraform_validate
      - id: terraform_docs
        args:
          - --hook-config=--path-to-file=infra/README.md
          - --hook-config=--add-to-existing-file=true
  - repo: https://github.com/gitleaks/gitleaks
    rev: v8.18.1
    hooks:
      - id: gitleaks
```

### No CI/CD Pipeline for Terraform

There is no GitHub Actions workflow that runs `terraform plan` on pull requests. This means:
- No plan output visible in PR review.
- Infrastructure changes can be merged without plan verification.
- No enforcement of `terraform fmt` on CI.

**Recommended GitHub Actions workflow:**

```yaml
# .github/workflows/terraform.yml
name: Terraform Plan

on:
  pull_request:
    paths:
      - 'infra/**'

jobs:
  plan:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: hashicorp/setup-terraform@v3
        with:
          terraform_version: "~> 1.6"
      - run: terraform -chdir=infra init -backend=false
      - run: terraform -chdir=infra fmt -check -recursive
      - run: terraform -chdir=infra validate
```

---

## 9. Recommended Restructure

This section answers your specific question: **"Is having a `private_database.tf` file even good practice?"**

**No — the filename is misleading and the file is overloaded.**

The file name implies database configuration but it actually contains the complete private networking stack (VPC, subnets, routing, NAT, security groups) plus the database (RDS, RDS Proxy, Secrets Manager). This violates the principle of least surprise for anyone reading the codebase.

**The `count`-based feature flag pattern itself is fine** — using `count = local.full_private_stack_enabled ? 1 : 0` to make an entire stack optional is a well-established Terraform pattern. The problem is not the pattern, it is what is packed into a single file under that pattern.

**Recommended rename/split priority:**

| Priority | Action | Effort |
|----------|--------|--------|
| 1 | Fix psycopg2-binary (CRITICAL) | Low |
| 2 | Add remote backend | Medium |
| 3 | Move password to Secrets Manager at runtime | Medium |
| 4 | Split `private_database.tf` → `network.tf` + `security_groups.tf` + `database.tf` + `rds_proxy.tf` | Low (rename + refactor) |
| 5 | Extract AZs via data source | Low |
| 6 | Add CloudWatch log groups with retention | Low |
| 7 | Fix `infra/.gitignore` redundancy | Trivial |
| 8 | Re-enable pre-commit hooks | Low |
| 9 | Set explicit `memory_size` and `timeout = 30` on VPC Lambda | Trivial |
| 10 | Remove academic references from output descriptions | Trivial |

---

## 10. Issue Summary Table

| # | Severity | File | Issue | Fix |
|---|----------|------|-------|-----|
| 1 | 🔴 CRITICAL | `lambdas/users_service/requirements.txt` | `psycopg2-binary` incompatible with Lambda runtime | Use `aws-psycopg2`, Lambda Layer, or Docker build |
| 2 | 🔴 CRITICAL | `locals.tf:53`, `private_database.tf:248-254` | DB password as Lambda env var (plaintext) | Fetch from Secrets Manager at runtime |
| 3 | 🟠 HIGH | `versions.tf` | No remote backend, local state only | Add S3 backend + DynamoDB lock table |
| 4 | 🟠 HIGH | `versions.tf` | No state locking | Add DynamoDB lock table |
| 5 | 🟠 HIGH | `.pre-commit-config.yaml` | All hooks disabled | Re-enable with terraform + gitleaks hooks |
| 6 | 🟠 HIGH | `main.tf:171` | Lambda permissions too broad (`*/*/*`) | Scope per route |
| 7 | 🟠 HIGH | `infra/.gitignore` | Redundant entries (3× `*.tfvars`) | Deduplicate |
| 8 | 🟡 MEDIUM | `private_database.tf` | Filename misleading, file overloaded (VPC+network+SG+RDS+proxy) | Split into 4 files |
| 9 | 🟡 MEDIUM | `locals.tf:29-33` | AZs hardcoded for `us-east-1`, breaks other regions | Use `data.aws_availability_zones` |
| 10 | 🟡 MEDIUM | `locals.tf:35-38` | RDS instance class and storage hardcoded | Move to variables |
| 11 | 🟡 MEDIUM | `locals.tf:8` | Fragile URL string manipulation for base URL | Add separate `frontend_base_url` variable |
| 12 | 🟡 MEDIUM | `main.tf:47` | `localhost:5173` hardcoded in CORS | Move to variable `extra_cors_origins` |
| 13 | 🟡 MEDIUM | `main.tf` | No CloudWatch log groups → infinite log retention | Add `aws_cloudwatch_log_group` per function |
| 14 | 🟡 MEDIUM | `locals.tf:74` | No explicit Lambda `memory_size` | Set `memory_size = 256` for users_service |
| 15 | 🟡 MEDIUM | `private_database.tf:235` | Secrets Manager name collision on destroy/recreate | Add `recovery_window_in_days = 0` |
| 16 | 🟡 MEDIUM | `outputs.tf` | Academic task refs ("PASO 2.2B") in descriptions | Remove / rewrite descriptions |
| 17 | 🟡 MEDIUM | `locals.tf:62-81` | Lambda function map in `locals.tf` (wrong file) | Move to `locals_lambda.tf` or `lambda.tf` |
| 18 | 🟢 LOW | `private_database.tf:69` | Single NAT GW = SPOF for cross-AZ Lambda egress | Document; one NAT per AZ in production |
| 19 | 🟢 LOW | `private_database.tf:218` | `multi_az=true` on `db.t3.micro` (cost/sense mismatch) | Acceptable for lab, document |
| 20 | 🟢 LOW | `private_database.tf:219-220` | `deletion_protection=false`, `skip_final_snapshot=true` | Acceptable for lab, document |
| 21 | 🟢 LOW | `private_database.tf:207` | RDS engine version not pinned | Pin `engine_version = "16.3"` |
| 22 | 🟢 LOW | `main.tf:78-104` | No X-Ray tracing on Lambda | Add `tracing_config { mode = "Active" }` |
| 23 | 🟢 LOW | `main.tf:52-56` | `auto_deploy = true` on API GW stage | Acceptable for lab |
| 24 | 🟢 LOW | `main.tf:45` | CORS missing DELETE, PATCH methods | Add or document as intentional |
| 25 | 🟢 LOW | `main.tf`, `private_database.tf` | No resource tags on any resource | Tag VPC, RDS, Lambda resources |
| 26 | 🟢 LOW | `locals.tf:65,72` | `__pycache__` packaged into Lambda ZIP | Add `excludes` to `archive_file` |
| 27 | 🟢 LOW | `locals.tf:74` | Lambda timeout 10s too short for VPC cold start | Set `timeout = 30` |
| 28 | 🟢 LOW | `handler.py:505-524` | Lambda router uses fragile string matching | Use exact-match route table |
| 29 | 🟢 LOW | `handler.py:180-203` | New DB connection per invocation | Module-level connection with reconnect |
| 30 | 🟢 LOW | *(missing)* | No GitHub Actions workflow for Terraform | Add plan-on-PR workflow |

---

*End of audit. No code was modified during this review.*
