# Abricot Backend API

A modular **Flask-based REST API** with JWT authentication, PostgreSQL, Docker support, and Swagger documentation.

---

## Project Structure

```
project/
│
├── blueprints/              # API routes and Swagger models
│   ├── models/
│   │   ├── auth_models.py
│   │   └── restaurant_models.py
│   ├── auth_blueprint.py
│   └── restaurant_blueprint.py
│
├── error_handlers/          # Centralized error and exception handling
│   └── common_handlers.py
│
├── exceptions/              # Custom exception classes
│   ├── auth_exception.py
│   └── restaurant_exception.py
│
├── helpers/                 # Utility and helper functions
│   └── authentication.py
│
├── models/                  # SQLAlchemy ORM models
│   ├── __init__.py
│   ├── user_model.py
│   └── restaurant_model.py
│
├── repositories/            # Database access layer (repository pattern)
│   ├── user_repository.py
│   └── restaurant_repository.py
│
├── tests/                   # Test folder (files must start with test_)
│   ├── unit/
│   └── conftest.py
│
├── __init__.py              # Application factory
├── logging_config.py        # Logging configuration
│
application.py               # Application entry point
.env                         # Environment variables (not committed)
.env.example                 # Environment variables template
requirements.txt             # Python dependencies
migrations/                  # Alembic migrations
docker-compose.yml           # Docker services (PostgreSQL)
```

---

## Prerequisites

**Python 3.11+**  
We use _Pyenv_ as the Python version manager. See https://github.com/pyenv/pyenv for installation instructions.  
Make sure to install the build dependencies first: https://github.com/pyenv/pyenv/wiki#suggested-build-environment

```sh
pyenv install 3.13
pyenv local 3.13
```

**Docker and Docker Compose**  
https://docs.docker.com/engine/install/ubuntu/#install-using-the-repository

---

## Getting Started

### 1. Clone the repository

```bash
git clone https://github.com/your-username/abricot-be.git
cd abricot-be
```

### 2. Configure environment variables

```bash
cp .env.example .env
```

Edit `.env` with your values. At minimum set a strong `JWT_SECRET_KEY` before running in production.

---

### 3. Start Docker containers

```bash
docker compose up -d
```

This starts **PostgreSQL 16** (`abricot-db`) on port `5432` and **LocalStack** (`abricot-localstack`) on `4566`. Run this before `flask db upgrade` or `flask run` so `POSTGRES_HOST=localhost` can connect.

---

### 4. Set up the Python environment

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
pre-commit install
```

---

### 5. Database setup

Make sure the PostgreSQL container is running before running these commands.

#### Initialize migrations (first time only)

```bash
flask db init
sed -E -i.bak 's/^[[:space:]]*#?[[:space:]]*file_template[[:space:]]*=.*$/file_template = %%(year)d-%%(month).2d-%%(day).2dT%%(hour).2d-%%(minute).2d-%%(second).2d_%%(slug)s/' migrations/alembic.ini
```

The `file_template` in `alembic.ini` should end up as:

```ini
file_template = %%(year)d-%%(month).2d-%%(day).2dT%%(hour).2d-%%(minute).2d-%%(second).2d_%%(slug)s
```

#### Create and apply the initial migration

```bash
flask db migrate -m "initial migration"
flask db upgrade
```

Run `flask db migrate` + `flask db upgrade` every time you change a model.

---

### 6. Run the application

```bash
flask run
```

The API will be available at `http://localhost:5000`.  
Swagger UI is available at `http://localhost:5000/`.

---

### 7. Run tests

```bash
python -m pytest
```

---

## API Endpoints

The API uses canonical REST resources. The complete frontend-oriented endpoint
guide lives in [`docs/rest-api-endpoints.md`](docs/rest-api-endpoints.md).

High-level entry points:

| Method | Endpoint | Description | Auth required |
|--------|----------|-------------|---------------|
| POST | `/users` | Register a new user | No |
| POST | `/sessions` | Login and get JWT tokens | No |
| POST | `/access-tokens` | Refresh an access token | Refresh token |
| GET | `/lookups` | Read location/metadata lookups | Yes |
| GET/POST | `/restaurants/` | Search or create restaurants | Create requires admin |
| GET/PUT/DELETE | `/restaurants/<id>` | Restaurant detail lifecycle | Write/delete require admin |
| GET/PATCH | `/reservations/<id>` | Reservation detail and status lifecycle | Yes |

Protected endpoints require `Authorization: Bearer <accessToken>` in the request
header, except `POST /access-tokens`, which requires the refresh token.

---

## Branch naming and coding guidelines

Two pre-commit hooks enforce:

1. `.hooks/check-branch-naming.sh` — Branch names must follow `<type>/<desc>` where `<type>` is one of: `feature`, `bugfix`, `refactor`, `hotfix`, `release`, `chore`.
2. `.hooks/check-protected-branches.sh` — Direct commits to `main`, `master`, `dev`, and `staging` are blocked.

To disable a hook, comment it out in `.pre-commit-config.yaml`.

---

## GitHub Actions Deployment Settings

The CI/CD workflows in `.github/workflows/` use temporary AWS Academy
credentials, run Terraform, publish Lambda artifacts, and deploy the Vue
frontend from the separate `Abricot-few` repository. They run on pushes to
`main` or `dev`, pull requests targeting `main` or `dev`, and manual dispatch.

Configure these GitHub repository secrets before the first run:

| Secret | Required | Description |
|--------|----------|-------------|
| `AWS_ACCESS_KEY_ID` | Yes | Temporary access key copied from AWS Academy Learner Lab -> AWS Details -> AWS CLI. |
| `AWS_SECRET_ACCESS_KEY` | Yes | Temporary secret key copied from AWS Academy Learner Lab -> AWS Details -> AWS CLI. |
| `AWS_SESSION_TOKEN` | Yes | Temporary session token copied from AWS Academy Learner Lab -> AWS Details -> AWS CLI. |
| `TF_VAR_POSTGRES_PASSWORD` | Yes | Production PostgreSQL password passed to Terraform as `var.postgres_password`. |
| `FRONTEND_REPO_TOKEN` | No | Token for checking out the frontend repo if the default `GITHUB_TOKEN` cannot access it. |

Configure these GitHub repository variables:

| Variable | Required | Description |
|----------|----------|-------------|
| `FRONTEND_REPOSITORY` | No | Frontend repository to checkout. Defaults to `NaPrado/Abricot-few`. |
| `CLOUDFRONT_DISTRIBUTION_ID` | No | CloudFront distribution to invalidate after frontend deploy. Leave unset when using direct S3 hosting. |

AWS prerequisites expected by the workflows:

- S3 Terraform backend bucket: `abricot-terraform-state`
- DynamoDB Terraform lock table: `abricot-terraform-lock`
- Active AWS Academy lab credentials with Terraform, Lambda, S3, DynamoDB,
  API Gateway, Cognito, VPC, RDS, and CloudWatch deployment permissions

Terraform creates the frontend hosting bucket and Lambda artifact bucket, then
the deployment workflow reads their names from `terraform output`.

### AWS Academy Credentials

AWS Academy usually blocks creating GitHub OIDC providers from the lab role. Use
temporary lab credentials instead:

1. Start the AWS Academy Learner Lab.
2. Open AWS Details -> AWS CLI.
3. Copy `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`, and
   `AWS_SESSION_TOKEN`.
4. Save those three values as GitHub Actions repository secrets.
5. Refresh these secrets every time the lab restarts or the credentials expire.

If a workflow fails with `ExpiredToken`, `InvalidClientTokenId`, or
`The security token included in the request is expired`, copy a fresh set of
AWS CLI credentials from the lab and rerun the workflow.

---

## Common Commands

| Command                     | Description                   |
|-----------------------------|-------------------------------|
| `docker compose up -d`      | Start `abricot-db` and LocalStack |
| `docker compose stop`       | Stop containers               |
| `flask db init`             | Initialize migrations folder  |
| `flask db migrate -m "msg"` | Generate migration file       |
| `flask db upgrade`          | Apply migrations              |
| `flask run`                 | Start Flask server            |
| `python -m pytest`          | Run tests                     |
