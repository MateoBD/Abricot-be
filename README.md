# Backend API Template

A clean and modular **Flask-based backend template** for building APIs with database integration, Docker support, and a scalable architecture.

---

## Project Structure

```
project/
│
├── blueprints/              # Contains API routes and models
│   ├── models/
│   │   ├── template_model.py
│   │   └── template_response_model.py
│   └── template_blueprint.py
│
├── error_handlers/          # Centralized error and exception handling
│   └── common_handlers.py
│
├── exceptions/              # Custom exception classes
│   └── template_exception.py
│
├── helpers/                 # Utility and helper functions
│   └── authentication.py
│
├── models/                  # SQLAlchemy models
│   ├── __init__.py
│   └── template_model.py
│
├── repositories/            # Database access and repository pattern
│   └── template_repository.py
│
├── services/                # Business logic layer
│   ├── __init__.py
│   └── logging_config.py
│
├── tests                    # Tests folder. Must start with test_
│   ├── unit/
│   │   └── test_model.py
│   └── conftest.py          # testing configuration and fixtures
├── application.py           # Application entry point
├── logging_config.py        # Logging configuration
├── .env                     # Environment and app configuration
├── requirements.txt         # Python dependencies
├── migrations/              # Alembic migrations
└── docker-compose.yml       # Docker services (database, etc.)
```

---

## Prerequisites

**Python 3.11+**  
We will use _Pyenv_ as a the python version manager. Go to https://github.com/pyenv/pyenv and follow the installation instructions.
NOTE: be careful to install the python build dependencies https://github.com/pyenv/pyenv/wiki#suggested-build-environment before installing any python version.  
Once installed do in the shell:

```sh
pyenv install 3.13
pyenv local 3.13 # in the directory of the project.
```

**Docker** and **Docker Compose**  
https://docs.docker.com/engine/install/ubuntu/#install-using-the-repository

---

## Getting Started

### 1. Clone the Repository

```bash
git clone https://github.com/your-username/template-be.git
cd template-be
```

## Environment Configuration

An example configuration file is provided as `.env.example`. You can use it as a starting point for your own environment variables.

### How it works

- Copy the example file to create your actual environment configuration:
  ```bash
  cp .env.example .env
  ```
- The `.env.example` file includes values that allow the application to run locally with a default setup.
- Before deploying or using the project in production, **you must update these values** (like database credentials, secret keys, and other environment-specific variables) to match your environment.

---

### 2. Start Docker Containers

Start all services (like the database):

```bash
docker compose up -d
```

### 3. Set Up the Python Environment

#### Create Virtual Environment

```bash
python -m venv .venv
```

#### Activate Environment

```bash
source .venv/bin/activate
```

#### Install Dependencies

```bash
pip install -r requirements.txt
```

#### Install pre-commit

```bash
pre-commit install
```

---

### 4. Database Setup

Make sure your Docker database container is running before running these commands.

#### Initialize migrations folder

```bash
flask db init
sed -E -i.bak 's/^[[:space:]]*#?[[:space:]]*file_template[[:space:]]*=.*$/file_template = %%(year)d-%%(month).2d-%%(day).2dT%%(hour).2d-%%(minute).2d-%%(second).2d_%%(slug)s/' migrations/alembic.ini
```

Where `flask db init` will create the migrations folder and the `sed -E -i.bak...` command will replace the `file_template` format.  
After both commands the `file_template` in `alembic.ini` should end like this:

```ini
[alembic]
# template used to generate migration files
file_template = %%(year)d-%%(month).2d-%%(day).2dT%%(hour).2d-%%(minute).2d-%%(second).2d_%%(slug)s
```

And a backup `alembik.ini.bak` should be created with the original configuration.

#### Create an Initial Migration

```bash
flask db migrate -m "initial migration"
```

This is also typically run only once to create the initial migration scripts.

#### Apply Migrations

```bash
flask db upgrade
```

This command should be run every time there is a change in the application's database models (after generating a new migration) to apply the latest changes.

---

### 5. Run the Application

```bash
flask run
```

The API will be available at:

```
http://localhost:5000
```

### 6. Run tests

```bash
python -m pytest
```

---

## Customization Guide

| Folder            | Purpose                                | What You Can Change                    |
| ----------------- | -------------------------------------- | -------------------------------------- |
| `blueprints/`     | API routes and request/response models | Add new endpoints and namespaces       |
| `models/`         | Database models                        | Define SQLAlchemy models               |
| `repositories/`   | Database logic                         | Abstract database queries              |
| `services/`       | Business logic                         | Implement service-layer functionality  |
| `helpers/`        | Utilities                              | Add helper or authentication functions |
| `error_handlers/` | Error handling                         | Customize common exceptions            |
| `exceptions/`     | Custom exceptions                      | Define new exception types             |

---

## Branch naming and coding guidelines

There are two pre-commit hooks that check for:

1.  `.hooks/check-branch-naming.sh`: Branchs should have <type>/<desc> naming convention. Where <type> is one of 'feature', 'bugfix', 'refactor', 'hotfix', 'release', 'chore'.
2.  `.hooks/check-protected-branches.sh`: That you should not push to protected branches [master main dev staging].

This is to enforce cleaner branch naming and to force feature branches that only merge to the protected branches via a Pull Request.  
If you wish to deactivate it comment the corresponding hooks on `.pre-commit-config.yaml`

## Extra configuration

You will find in `.ebextensions/aws.config` the default commands that need the Elastic Beanstalk in order to load the project correctly. This is: activate the virtual environment and run the database migrations.

## Common Commands

| Command                     | Description                  |
| --------------------------- | ---------------------------- |
| `docker compose up -d`      | Start Docker containers      |
| `docker compose stop`       | Stop Docker containers       |
| `flask db init`             | Initialize migrations folder |
| `flask db migrate -m "msg"` | Create migration file        |
| `flask db upgrade`          | Apply migrations             |
| `flask run`                 | Start Flask server           |
| `python -m pytest`          | Run tests                    |
