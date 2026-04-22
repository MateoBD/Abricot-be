# Flask REST API — Best Practices

This document is the authoritative guide for this codebase. It describes the architecture, the contract of every layer, the rules that govern how code is written, and how every concept maps to its Spring Boot equivalent for developers coming from that ecosystem.

Teammates and AI agents must read this before making any changes.

---

## 0. Mental Model: How This Maps to Spring Boot

If you have Spring Boot experience, here is the full conceptual mapping before diving into details:

| This project | Spring Boot equivalent | Notes |
|---|---|---|
| `app/__init__.py` → `create_app()` | `@SpringBootApplication` + `main()` | The factory assembles the whole application |
| `app/config.py` | `application.properties` / `@Configuration` classes | Env-specific config objects |
| `app/extensions.py` | `@Bean` declarations in a `@Configuration` class | Extension instances are "beans" |
| `app/api/*/routes.py` | `@RestController` + `@RequestMapping` | HTTP layer, thin wrappers |
| `app/api/*/schemas.py` | Request/Response DTOs (`record` or `@Data` POJO) | Swagger model definitions |
| `app/services/` | `@Service` classes | Business logic, pure Java/Python |
| `app/repositories/` | `@Repository` (Spring Data JPA) | Data access, all queries here |
| `app/models/` | `@Entity` (JPA) | ORM schema definition |
| `app/exceptions/errors.py` | `@ResponseStatus` custom exceptions + `RuntimeException` hierarchy | All exceptions in one file |
| `app/error_handlers.py` | `@ControllerAdvice` + `@ExceptionHandler` | Global exception mapper |
| `app/middleware/auth.py` | Spring Security filter chain | JWT verification |
| `app/integrations/s3.py` | `@Service` wrapping an AWS SDK client | Third-party clients |
| `flask_jwt_extended` | `spring-security-oauth2-resource-server` | JWT library |
| `Flask-SQLAlchemy` + Alembic | Spring Data JPA + Flyway/Liquibase | ORM + migrations |
| `Flask-RESTX` | SpringDoc/Springfox (Swagger) | Auto-generates OpenAPI docs |
| `docker-compose.yml` | `docker-compose.yml` | Local PostgreSQL + LocalStack |

The biggest conceptual difference from Spring Boot: **Flask has no dependency injection container**. There is no `@Autowired`, no IoC container scanning for `@Component`. Instead:
- Extension objects (db, bcrypt, jwt) are module-level singletons imported directly.
- Services call repositories by importing the class directly.
- The application factory (`create_app`) wires everything together by calling explicit `init_app()` methods.

Think of it as "manual wiring" vs Spring's "auto-wiring".

---

## 1. Project Structure

```
app/                            # All application source code — equivalent to src/main/java/
├── __init__.py                 # Application factory (create_app) — equivalent to main()
├── config.py                   # Config classes — equivalent to application.properties + @Configuration
├── extensions.py               # Extension/bean instances — equivalent to @Bean declarations
├── error_handlers.py           # Flask-level error handlers — equivalent to @ControllerAdvice
├── logging_config.py           # Logging dict config — equivalent to logback.xml
│
├── api/                        # HTTP layer — equivalent to your controllers package
│   ├── __init__.py             # Flask-RESTX Api object + namespace wiring + API-level error handlers
│   ├── auth/
│   │   ├── routes.py           # Auth endpoints — equivalent to AuthController.java
│   │   └── schemas.py          # Swagger model definitions — equivalent to AuthRequestDto.java / AuthResponseDto.java
│   └── restaurants/
│       ├── routes.py           # Restaurant endpoints — equivalent to RestaurantController.java
│       └── schemas.py          # Swagger model definitions
│
├── services/                   # Business logic — equivalent to your services package
│   ├── auth_service.py         # AuthService — equivalent to AuthService.java (@Service)
│   └── restaurant_service.py   # RestaurantService — equivalent to RestaurantService.java (@Service)
│
├── repositories/               # Data access — equivalent to your repositories package
│   ├── user_repository.py      # UserRepository — equivalent to UserRepository.java (@Repository)
│   └── restaurant_repository.py
│
├── models/                     # ORM entities — equivalent to your entities/domain package
│   ├── __init__.py             # Imports all models so Flask-Migrate detects them
│   ├── user.py                 # UserModel — equivalent to User.java (@Entity)
│   └── restaurant.py           # RestaurantModel — equivalent to Restaurant.java (@Entity)
│
├── exceptions/
│   └── errors.py               # Exception hierarchy — equivalent to your exceptions package
│
├── middleware/
│   └── auth.py                 # JWT decorators — equivalent to JwtAuthFilter.java (OncePerRequestFilter)
│
└── integrations/
    └── s3.py                   # S3 client — equivalent to S3Service.java wrapping the AWS SDK

migrations/                     # Alembic migrations — equivalent to Flyway sql/V1__*.sql files
tests/                          # (to be added) unit/ and integration/
application.py                  # Entry point — equivalent to the @SpringBootApplication main class
docker-compose.yml              # PostgreSQL + LocalStack for local dev
.env.example                    # All required env vars documented
```

---

## 2. Layer-by-Layer Contracts

Each layer has an explicit contract. Breaking these contracts is a bug.

---

### 2.1 `app/__init__.py` — Application Factory

**Spring Boot equivalent:** The `main()` method in your `@SpringBootApplication` class, plus all the auto-configuration that Spring Boot does invisibly.

In Spring Boot, you call `SpringApplication.run(App.class, args)` and the framework scans for `@Component`, `@Service`, `@Repository`, `@Bean` etc. and wires everything automatically.

In Flask, there is no auto-scanning. `create_app()` is the explicit replacement: it loads config, initialises extensions (the "beans"), registers routes (the "controllers"), and registers error handlers (the `@ControllerAdvice`). You see every wire-up call in one place.

**What `create_app()` does, in order:**
1. Resolves the config class (`TestingConfig` or `ProductionConfig`) from the `ENV` environment variable.
2. Calls `ProductionConfig.validate()` — fails fast if any required env var is missing.
3. Calls `app.config.from_object(cfg_class)` — pushes all config values into Flask's config dict.
4. Sets up logging.
5. Calls `init_extensions(app)` — binds db, jwt, bcrypt, cors, migrate to this app instance.
6. Calls `register_blueprints(app)` — creates the RESTX Api and registers all namespaces.
7. Calls `register_error_handlers(app)` — registers `@app.errorhandler` functions.

**Rules:**
- This file contains only `create_app()` and `_setup_logging()`. Zero business logic.
- All imports from `app.*` are deferred inside functions to prevent circular imports at module load time.
- Never call `create_app()` more than once per process. In tests, one `scope="session"` app fixture is the correct pattern.

```python
def create_app(config_name: str | None = None) -> Flask:
    app = Flask(__name__)
    cfg_class = config[config_name or get_config_name()]
    if hasattr(cfg_class, "validate"):
        cfg_class.validate()
    app.config.from_object(cfg_class)
    _setup_logging(app)
    from app.extensions import init_extensions
    init_extensions(app)
    from app.api import register_blueprints
    register_blueprints(app)
    from app.error_handlers import register_error_handlers
    register_error_handlers(app)
    return app
```

---

### 2.2 `app/config.py` — Configuration

**Spring Boot equivalent:** `application.properties` / `application-prod.properties` / `application-test.properties`, or `@ConfigurationProperties` classes.

Spring Boot auto-selects the right profile properties file via `spring.profiles.active`. Here, `get_config_name()` reads the `ENV` env var and returns `"testing"` or `"production"`, which selects the correct config class.

**Config classes:**

| Class | Environment | Database | JWT secret |
|---|---|---|---|
| `TestingConfig` | `ENV=testing` (e.g. pytest) | SQLite in-memory | Hard-coded test value |
| `ProductionConfig` | `ENV=production` (default) | PostgreSQL from env vars | Read from `JWT_SECRET_KEY` env var |

**JWT configuration on `BaseConfig`:**

```python
JWT_ACCESS_TOKEN_EXPIRES  = timedelta(minutes=15)   # Short-lived — stolen tokens expire fast
JWT_REFRESH_TOKEN_EXPIRES = timedelta(days=30)       # Long-lived — user re-auth interval
JWT_TOKEN_LOCATION        = ["headers"]              # Only accept tokens from HTTP headers
JWT_HEADER_NAME           = "Authorization"          # The header name
JWT_HEADER_TYPE           = "Bearer"                 # The prefix before the token
```

`JWT_TOKEN_LOCATION = ["headers"]` is the most important security setting. Without it, Flask-JWT-Extended would also accept tokens in query strings (`?jwt=...`) and cookies, which are attack surfaces. This forces the header-only contract.

**`ProductionConfig.validate()`** is called before `app.config.from_object()`. It lists every required env var and raises `EnvironmentError` immediately if any are missing — equivalent to Spring Boot's `@ConfigurationProperties(prefix="...")` validation with `@NotNull` constraints. You see the missing variable at startup, not at the first request.

**Rules:**
- All env var reads happen here — `os.environ.get()` appears only in `config.py`.
- `TestingConfig` has hard-coded values so tests run with zero env var setup.
- `ALLOWED_ORIGINS` is read from a comma-separated env var. Never `"*"` in production.
- Never call `load_dotenv()` here — that is `application.py`'s single job.

---

### 2.3 `app/extensions.py` — Extension Instances

**Spring Boot equivalent:** A `@Configuration` class full of `@Bean` methods.

In Spring Boot:
```java
@Configuration
public class AppConfig {
    @Bean
    public PasswordEncoder passwordEncoder() {
        return new BCryptPasswordEncoder(12);
    }
    @Bean
    public JwtDecoder jwtDecoder() { ... }
}
```

In Flask, extensions are module-level singletons. There is no IoC container to inject them — you simply `import` them. The `init_app(app)` pattern is Flask's two-phase initialisation: create the object once, bind it to the app later. This is what allows the same extension instance to be shared by multiple apps in tests.

```python
# Declare once — equivalent to @Bean definition
db = SQLAlchemy()
jwt = JWTManager()
bcrypt = Bcrypt()

# Bind to app — equivalent to @Autowired wiring
def init_extensions(app: Flask) -> None:
    db.init_app(app)
    jwt.init_app(app)
    bcrypt.init_app(app)
    ...
```

**CORS configuration:** Production restricts origins to the `ALLOWED_ORIGINS` list from config. `"*"` is only acceptable in `TestingConfig`. The CORS preflight (`OPTIONS`) response is handled automatically.

**Model auto-detection for migrations:** Flask-Migrate (Alembic) needs to know about all models to generate migrations. SQLAlchemy 2.0 does NOT auto-scan packages — you must import every model class explicitly. This is done inside `with app.app_context()` at the end of `init_extensions`:

```python
with app.app_context():
    from app.models import restaurant, user  # noqa: F401
```

**Rule:** When you add a new model, add its import here AND in `app/models/__init__.py`.

---

### 2.4 `app/api/` — HTTP Layer

**Spring Boot equivalent:** `@RestController` classes with `@GetMapping`, `@PostMapping`, etc.

Flask-RESTX `Resource` classes are the direct equivalent of `@RestController` classes. Each public method (`get`, `post`, `put`, `delete`) maps to an HTTP verb, exactly like `@GetMapping` / `@PostMapping`.

**Spring Boot:**
```java
@RestController
@RequestMapping("/restaurants")
public class RestaurantController {
    @PostMapping
    @ResponseStatus(HttpStatus.CREATED)
    public RestaurantResponse create(@Valid @RequestBody RestaurantCreateRequest req) {
        return restaurantService.create(req.name(), req.address(), ...);
    }
}
```

**Flask-RESTX equivalent:**
```python
@namespace.route("/")
class RestaurantList(Resource):
    @namespace.expect(restaurant_create_model, validate=True)
    @namespace.response(201, "Created.", restaurant_response_model)
    def post(self):
        data = request.json
        return RestaurantService.create(
            name=data.get("name", ""),
            ...
        ), 201
```

The `@namespace.expect(model, validate=True)` decorator is equivalent to `@Valid @RequestBody` — it validates the incoming JSON against the schema and returns a 400 automatically if validation fails.

**`app/api/__init__.py`** creates the single Flask-RESTX `Api` object. It also registers API-level error handlers (`_register_api_error_handlers`). Flask-RESTX catches exceptions raised inside `Resource` methods before Flask sees them, so handlers registered on the `Api` object fire first. The Flask-level handlers in `error_handlers.py` serve as the fallback.

**`schemas.py`** files are the DTO layer. In Spring Boot you would write `record RestaurantCreateRequest(String name, String address, ...)` with Bean Validation annotations (`@NotBlank`, `@Email`, `@Size`, `@Pattern`). Here you write a Flask-RESTX `Model` with equivalent field constraints. They serve the same two purposes: input validation contract and Swagger documentation generation.

#### Schema Field Constraints

Flask-RESTX `fields.String` supports `pattern` (regex), `min_length`, and `max_length` — direct equivalents of Spring's `@Pattern`, `@Size(min=)`, and `@Size(max=)`.

**Spring Boot:**
```java
public record RegisterRequest(
    @NotBlank @Email @Size(max = 255)
    String email,

    @NotBlank @Size(min = 8, max = 128)
    String password,

    @NotBlank @Pattern(regexp = "^[a-zA-ZáéíóúüñÁÉÍÓÚÜÑ'\\- ]{1,100}$")
    String name
) {}
```

**Flask-RESTX equivalent:**
```python
Model("RegisterRequest", {
    "email": fields.String(
        required=True,
        pattern=r"^[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}$",
        max_length=255,
    ),
    "password": fields.String(required=True, min_length=8, max_length=128),
    "name": fields.String(
        required=True,
        pattern=r"^[a-zA-ZáéíóúüñÁÉÍÓÚÜÑ'\- ]{1,100}$",
    ),
})
```

When `@namespace.expect(model, validate=True)` is active, Flask-RESTX converts the `Model` to a JSON Schema and runs `jsonschema` validation. Constraint violations return a 400 automatically — equivalent to `@Valid` + `MethodArgumentNotValidException` in Spring.

**Constraints used in this project:**

| Field | Constraint | Pattern / limit |
|---|---|---|
| email (any) | Format regex + max length | `^[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}$`, max 255 |
| password | Length only | min 8, max 128 |
| name / surname | Letters (ES), hyphens, spaces | `^[a-zA-ZáéíóúüñÁÉÍÓÚÜÑ'\- ]{1,100}$` |
| phone | International format | `^\+?[\d\s\(\)\-\.]{7,30}$` |
| restaurant name | Length only | min 1, max 150 |
| address | Length only | min 1, max 255 |
| description | Length only | max 2000 |

**Shared field definitions (`_RESTAURANT_WRITABLE_FIELDS`):** Create and Update models for the same resource share field definitions via a dict. When you change a field constraint, you change it in one place:

```python
_RESTAURANT_WRITABLE_FIELDS = { "name": fields.String(...), ... }
restaurant_create_model = Model("RestaurantCreateRequest", {**_RESTAURANT_WRITABLE_FIELDS})
restaurant_update_model = Model("RestaurantUpdateRequest", {**_RESTAURANT_WRITABLE_FIELDS})
```

**Examples must use generic Spanish values** — no English placeholder names in examples. Use `"usuario@ejemplo.com"`, `"Juan"`, `"García"`, `"El Gaucho Rojo"`, etc.

**Rules:**
- Route methods must be 5–15 lines. Any longer means business logic has leaked in — move it to the service.
- Never import `db`, `bcrypt`, or `jwt` in a route file.
- Never raise `AppError` subclasses from a route. The service raises them.
- Pass only primitive Python types to services — never pass `request`, a Flask context object, or a RESTX model instance.
- The route returns `(service_result, http_status_code)`. That is the entire job.
- Every input field that has a known format must have a `pattern`, `min_length`, or `max_length` constraint. Unconstrained fields are a security and data quality risk.

---

### 2.5 `app/services/` — Business Logic Layer

**Spring Boot equivalent:** `@Service` classes.

This is the most important layer and the one most often skipped by beginners. Every use case, every business rule, every validation that is NOT just "is this field present?" lives here.

In Spring Boot, a service is `@Service` and gets `@Autowired` dependencies. Here, a service is a plain class with `@staticmethod` methods that import their dependencies directly.

**Spring Boot:**
```java
@Service
public class AuthService {
    private final UserRepository userRepository;
    private final PasswordEncoder passwordEncoder;

    public AuthResponse register(RegisterRequest req) {
        if (userRepository.findByEmail(req.email()).isPresent())
            throw new ConflictException("Email already in use");
        ...
    }
}
```

**Flask equivalent:**
```python
class AuthService:
    @staticmethod
    def register(email: str, password: str, ...) -> dict:
        if UserRepository.get_by_email(email):
            raise ConflictError("An account with this email already exists.")
        ...
```

**What belongs in a service:**
- Input normalisation (strip, lowercase, null-coalesce)
- Business rule validation (password length, email uniqueness)
- Orchestration of multiple repository calls
- Password hashing / token generation
- Calling integrations (S3, email)
- Logging of business events

**What does NOT belong in a service:**
- Any Flask import (`request`, `jsonify`, etc.)
- HTTP status codes
- Direct `db.session` calls — that is the repository's job

**Rules:**
- No Flask imports. If you find yourself writing `from flask import ...` in a service, stop — you have leaked HTTP concerns.
- Return plain `dict` objects (via `model.to_dict()`). Routes must never need to call `.to_dict()`.
- Raise `AppError` subclasses for expected failures. Never return `{"error": ...}` dicts.
- Log at `INFO` on success. Never log passwords, tokens, or full email addresses.

---

### 2.6 `app/repositories/` — Data Access Layer

**Spring Boot equivalent:** `@Repository` interfaces extending `JpaRepository<Entity, Long>`.

Spring Data JPA auto-generates SQL for `findByEmail(String email)`. Here you write it explicitly using SQLAlchemy 2.0's `select()` API. It is more verbose but also more transparent — there is no "magic" query generation.

**Spring Boot:**
```java
@Repository
public interface UserRepository extends JpaRepository<User, Long> {
    Optional<User> findByEmail(String email);
}
// Spring generates the SQL automatically.
```

**Flask equivalent:**
```python
class UserRepository:
    @staticmethod
    def get_by_email(email: str) -> UserModel | None:
        return db.session.execute(
            db.select(UserModel).where(UserModel.email == email)
        ).scalar_one_or_none()
```

**SQLAlchemy 2.0 API — mandatory:**

```python
# CORRECT — SQLAlchemy 2.0 style
db.session.execute(db.select(Model).where(...)).scalar_one_or_none()
db.session.get(Model, primary_key)
list(db.session.execute(db.select(Model).order_by(Model.name)).scalars())

# WRONG — deprecated SQLAlchemy 1.x style, removed in 2.0, do NOT use
Model.query.filter_by(email=email).first()
Model.query.get(primary_key)
```

**Rules:**
- Every `db.session.add()`, `db.session.commit()`, `db.session.delete()` call lives in a repository. Zero exceptions.
- Returns ORM model instances or `None`. Never raises "not found" exceptions — that is the service's responsibility.
- Never applies business rules. A repository's job is purely data access.
- Static methods only — no instance state.

---

### 2.7 `app/models/` — ORM Models

**Spring Boot equivalent:** JPA `@Entity` classes.

**Spring Boot:**
```java
@Entity
@Table(name = "users")
public class User {
    @Id @GeneratedValue
    private Long id;

    @Column(unique = true, nullable = false, length = 255)
    private String email;

    @CreationTimestamp
    private Instant createdAt;
}
```

**Flask equivalent — uses SQLAlchemy 2.0 `Mapped[]` syntax:**
```python
class UserModel(db.Model):
    __tablename__ = "users"
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    email: Mapped[str] = mapped_column(String(255), nullable=False, unique=True, index=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(UTC)
    )
```

`Mapped[str]` is the Python equivalent of `@Column(nullable = false)`. `Mapped[str | None]` is the equivalent of `@Column(nullable = true)`. The types are enforced by mypy statically, the same way Spring's type system catches nullability at compile time.

**Rules:**
- Always use `Mapped[]` + `mapped_column()` (SQLAlchemy 2.0). Never use the legacy `Column()` API.
- `DateTime(timezone=True)` on every timestamp column. Always default to `datetime.now(UTC)`.
- Add `index=True` to every column that appears in a `WHERE` clause or `JOIN`.
- One `to_dict()` method for serialisation. No other methods — no business logic, no queries.
- All models must be imported in both `app/models/__init__.py` AND inside `init_extensions()`.

---

### 2.8 `app/exceptions/errors.py` — Exception Hierarchy

**Spring Boot equivalent:** Custom `RuntimeException` subclasses annotated with `@ResponseStatus`, all living in an `exceptions` package.

**Spring Boot:**
```java
@ResponseStatus(HttpStatus.NOT_FOUND)
public class NotFoundException extends RuntimeException {
    public NotFoundException(String message) { super(message); }
}
```

Here everything lives in ONE file:

```python
class AppError(Exception):       # Root — like RuntimeException
    status_code: int = 500
    code: str = "INTERNAL_ERROR"
    def __init__(self, message: str, payload: dict | None = None): ...

class NotFoundError(AppError):   status_code = 404;  code = "NOT_FOUND"
class ConflictError(AppError):   status_code = 409;  code = "CONFLICT"
class ValidationError(AppError): status_code = 400;  code = "VALIDATION_ERROR"
class UnauthorizedError(AppError): status_code = 401; code = "UNAUTHORIZED"
class ForbiddenError(AppError):  status_code = 403;  code = "FORBIDDEN"
```

The `status_code` and `code` are baked into the exception class itself — the error handler does not need a mapping table. The `payload` dict is for field-level details (e.g. `{"email": "Already in use"}`), equivalent to Spring's `BindingResult` / `FieldError` collection.

**Rule:** Never create new exception files. Add new exception classes to `errors.py` only.

---

### 2.9 `app/error_handlers.py` — Centralised Error Handling

**Spring Boot equivalent:** `@ControllerAdvice` class with `@ExceptionHandler` methods.

**Spring Boot:**
```java
@ControllerAdvice
public class GlobalExceptionHandler {
    @ExceptionHandler(NotFoundException.class)
    public ResponseEntity<ErrorResponse> handleNotFound(NotFoundException ex) {
        return ResponseEntity.status(404).body(new ErrorResponse(ex.getMessage(), "NOT_FOUND"));
    }
}
```

**Flask equivalent:**
```python
@app.errorhandler(AppError)
def handle_app_error(e: AppError):
    return jsonify({"message": e.message, "code": e.code, "errors": e.payload}), e.status_code
```

Because `AppError` is the base class, this single handler catches ALL custom exceptions (`NotFoundError`, `ConflictError`, etc.) — exactly like catching `AppError` in a Spring `@ExceptionHandler`.

**Two-layer error handling:**

1. **`app/api/__init__.py`** — registers handlers on the Flask-RESTX `Api` object. These catch exceptions thrown inside `Resource` methods before Flask sees them. Returns `dict` (RESTX serialises it to JSON).

2. **`app/error_handlers.py`** — registers handlers on the Flask `app`. These are the authoritative fallback for anything the RESTX layer misses (e.g. errors in middleware, before-request hooks). Returns `jsonify(...)`.

This dual layer is necessary because Flask-RESTX has its own exception handling middleware that intercepts exceptions before they reach Flask's handler. Both layers use the same response envelope.

**Every error response must use this exact shape:**
```json
{
    "message": "Human-readable description for the user.",
    "code":    "MACHINE_READABLE_CODE",
    "errors":  { "fieldName": "Field-specific message" }
}
```
`errors` is `{}` when there are no field-level details. Clients can rely on all three keys always being present.

**Standard `code` values:** `NOT_FOUND`, `CONFLICT`, `VALIDATION_ERROR`, `UNAUTHORIZED`, `FORBIDDEN`, `INTERNAL_ERROR`, `VALUE_ERROR`.

---

### 2.10 JWT Authentication — Access Tokens and Refresh Tokens

**Spring Boot equivalent:** `JwtAuthenticationFilter` (extends `OncePerRequestFilter`) + `spring-security-oauth2-resource-server`.

#### Token Types

| Token | Header | Expiry | Purpose |
|---|---|---|---|
| Access token | `Authorization: Bearer <accessToken>` | 15 minutes | Sent on every protected request |
| Refresh token | `Authorization: Bearer <refreshToken>` | 30 days | Sent ONLY to `POST /auth/refresh` |

Both tokens are JWTs signed with the same `JWT_SECRET_KEY`. Flask-JWT-Extended distinguishes them via a `type` claim inside the JWT payload (`"access"` vs `"refresh"`). If you send a refresh token to a protected endpoint, it returns 401. If you send an access token to `/auth/refresh`, it returns 401. The types are not interchangeable.

User profile endpoints are **`GET/PUT /users/<uuid:user_id>`** and **`PUT /users/<uuid:user_id>/password`**, not `/users/me`. **`require_path_user_matches_jwt`** rejects requests where `user_id` ≠ JWT subject (`403 FORBIDDEN`).

#### Token Flow

```
1. POST /auth/login   → response body: { accessToken, refreshToken, user }
2. Client stores both tokens (e.g. in memory / secure storage)
3. Every API call:    → request header: Authorization: Bearer <accessToken>
4. Access token expires (15 min later):
5. POST /auth/refresh → request header: Authorization: Bearer <refreshToken>
                      → response body: { accessToken }   (new 15-min token)
6. Client replaces stored accessToken and retries
7. Refresh token expires (30 days):
8. User must log in again (POST /auth/login)
```

#### Why short-lived access tokens?

A stolen access token is only valid for 15 minutes. In Spring Security with stateless JWT, there is no session to invalidate — once a token is issued you cannot revoke it (without a blocklist). Short expiry is the mitigation. The refresh token pattern lets users stay "logged in" for 30 days without needing a long-lived access token.

#### JWT Config (`app/config.py` — `BaseConfig`)

```python
JWT_TOKEN_LOCATION = ["headers"]   # Critical: only accept tokens from Authorization header
JWT_HEADER_NAME    = "Authorization"
JWT_HEADER_TYPE    = "Bearer"
```

`JWT_TOKEN_LOCATION = ["headers"]` is the most important setting. Without it, Flask-JWT-Extended would also accept tokens from query strings (`?jwt=...`) and cookies, which are additional attack surfaces. This enforces that tokens travel exclusively through the `Authorization` header.

#### `app/middleware/auth.py`

Two decorators — use the right one:

```python
# Protects normal endpoints — verifies an ACCESS token
@require_authentication()
def get(self): ...

# Protects ONLY the refresh endpoint — verifies a REFRESH token
@require_refresh_token()
def post(self): ...  # POST /auth/refresh
```

`get_current_user_id()` returns the authenticated user's ID as `int`. Call it inside any protected route that needs to know who is making the request.

**Spring Boot equivalent:**
```java
// Spring Security extracts the user from the JWT automatically
// and puts it in SecurityContextHolder
Authentication auth = SecurityContextHolder.getContext().getAuthentication();
String userId = auth.getName();

// Flask equivalent:
user_id = get_current_user_id()  # calls get_jwt_identity() under the hood
```

---

### 2.11 `app/integrations/s3.py` — AWS S3

**Spring Boot equivalent:** A `@Service` class that wraps the AWS SDK `S3Client`.

`S3Client` is a singleton accessed via `S3Client.get()`. The boto3 client is lazily initialised on first use (not at import time) so that tests that never touch S3 are not affected by missing credentials.

**Two modes:**

| Env var | Mode | Credentials |
|---|---|---|
| `USE_LOCALSTACK=true` | Local dev | Dummy (`test`/`test`), connects to `LOCALSTACK_ENDPOINT` |
| (default) | AWS | Uses ambient IAM role (EC2) or explicit `AWS_ACCESS_KEY_ID`/`AWS_SECRET_ACCESS_KEY` |

---

## 3. Database Rules

### Migrations (Alembic = Flask's Flyway)

**Spring Boot equivalent:** Flyway `sql/V1__create_users_table.sql` files.

| Flask command | Flyway equivalent |
|---|---|
| `flask db migrate -m "add_orders_table"` | Write a new `V*__*.sql` file |
| `flask db upgrade` | `mvn flyway:migrate` |
| `flask db downgrade` | `mvn flyway:undo` |

**Rules:**
- Every schema change needs a migration. Never use `db.create_all()` in production — it does not track state.
- Always review the auto-generated migration file before committing. Alembic misses some changes (e.g. constraint name changes, index renames).
- Never edit a migration that has been applied to any environment. Create a new one.

### SQLAlchemy 2.0 Query API

Always use the 2.0 API. The 1.x `Model.query` API is deprecated and removed:

```python
# CORRECT — 2.0 style
db.session.execute(db.select(Model).where(Model.field == value)).scalar_one_or_none()
db.session.get(Model, pk)
list(db.session.execute(db.select(Model).order_by(Model.name)).scalars())

# WRONG — 1.x style, do not use
Model.query.filter_by(field=value).first()
Model.query.get(pk)
```

---

## 4. API Design Conventions

### URL Structure

```
GET    /auth/register          ← No, this is a POST
POST   /auth/register          ✓
POST   /auth/login             ✓
POST   /auth/refresh           ✓ — token refresh is a POST action on the auth resource

GET    /restaurants/           ✓ — list
POST   /restaurants/           ✓ — create
GET    /restaurants/{id}       ✓ — read one
PUT    /restaurants/{id}       ✓ — full replace (all fields required)
PATCH  /restaurants/{id}       — partial update (add when needed)
DELETE /restaurants/{id}       ✓ — delete
POST   /restaurants/{id}/photo ✓ — sub-resource action
```

`PUT` = full replacement. All editable fields are required. Omitting an optional field CLEARS it in the database. Use `PATCH` when you want partial updates.

### HTTP Status Codes

| Situation | Code | Spring equivalent |
|---|---|---|
| Successful GET / PUT | 200 | `HttpStatus.OK` |
| Successful POST (created) | 201 | `HttpStatus.CREATED` |
| Successful DELETE (no body) | 204 | `HttpStatus.NO_CONTENT` |
| Validation error / bad input | 400 | `HttpStatus.BAD_REQUEST` |
| Unauthenticated | 401 | `HttpStatus.UNAUTHORIZED` |
| Authenticated but forbidden | 403 | `HttpStatus.FORBIDDEN` |
| Resource not found | 404 | `HttpStatus.NOT_FOUND` |
| Duplicate resource / unique constraint | 409 | `HttpStatus.CONFLICT` |
| Server error | 500 | `HttpStatus.INTERNAL_SERVER_ERROR` |

### Response Envelope

All successful list responses:
```json
{ "data": [...], "total": 42, "page": 1, "perPage": 20 }
```
(Pagination not yet implemented — when added, use this shape.)

All successful single-resource responses: return the object directly, no wrapper.

All error responses: always use the standard envelope (see Section 2.9).

All datetime fields: ISO 8601 with UTC offset — `"2026-04-07T19:00:00+00:00"`.

---

## 5. Security Rules

- **CORS:** `ALLOWED_ORIGINS` must be an explicit list in production. Never `"*"`. Configure at the nginx/load-balancer level too.
- **Passwords:** Always hashed with bcrypt (work factor 12). Never logged, never returned in any response.
- **JWT location:** Tokens travel ONLY through `Authorization: Bearer` header. `JWT_TOKEN_LOCATION = ["headers"]` enforces this. Never accept tokens in query strings.
- **JWT secret:** Must be at least 32 random bytes. Generate with `openssl rand -hex 32`. Rotate without downtime using a secret rotation strategy.
- **SQL injection:** Prevented by the SQLAlchemy ORM. If raw SQL is ever needed, use `text()` with bound parameters — never f-strings or string concatenation.
- **File uploads:** Set `MAX_CONTENT_LENGTH = 5 * 1024 * 1024` (5 MB). Validate MIME type, not just file extension.

---

## 6. Adding a New Resource (Step-by-Step)

When adding a new resource (e.g. "Orders"), follow these steps in order:

1. **Model** — `app/models/order.py` using `Mapped[]` + `mapped_column()`. Add `to_dict()`.
2. **Register model** — add `from app.models import order  # noqa: F401` to both `app/models/__init__.py` and `app/extensions.init_extensions()`.
3. **Migration** — `flask db migrate -m "add_orders_table"`, review the generated file, then `flask db upgrade`.
4. **Repository** — `app/repositories/order_repository.py` with static methods. SQLAlchemy 2.0 API only.
5. **Exceptions** — Add any new exception types to `app/exceptions/errors.py`.
6. **Service** — `app/services/order_service.py` with all business logic. No Flask imports. Raises `AppError` subclasses.
7. **Schemas** — `app/api/orders/schemas.py` with Flask-RESTX `Model` definitions for requests and responses.
8. **Routes** — `app/api/orders/routes.py` with thin `Resource` classes calling the service.
9. **Register namespace** — add the namespace in `app/api/__init__.py`.

---

## 7. Testing

Tests live in `tests/`. Pass `"testing"` to `create_app` — this selects `TestingConfig` which uses SQLite in-memory and a dummy JWT secret, requiring zero env var setup.

```
tests/
├── conftest.py               # Session-scoped app, per-test rollback, auth helpers
├── unit/                     # Test services in isolation by mocking repositories
│   ├── test_auth_service.py
│   └── test_restaurant_service.py
└── integration/              # Full HTTP tests via Flask test client
    ├── test_auth_routes.py
    └── test_restaurant_routes.py
```

### Recommended `conftest.py`

```python
import pytest
from app import create_app
from app.extensions import db as _db

@pytest.fixture(scope="session")
def app():
    """Create one app for the whole test session — equivalent to Spring's @SpringBootTest."""
    app = create_app("testing")
    with app.app_context():
        _db.create_all()
        yield app
        _db.drop_all()

@pytest.fixture
def client(app):
    return app.test_client()

@pytest.fixture(autouse=True)
def rollback(app):
    """Roll back every test's DB changes — equivalent to @Transactional on a Spring test."""
    with app.app_context():
        yield
        _db.session.rollback()

@pytest.fixture
def auth_headers(client):
    """Returns Authorization headers for a registered test user."""
    resp = client.post("/auth/register", json={
        "email": "test@example.com", "password": "password123",
        "name": "Test", "surname": "User"
    })
    token = resp.json["accessToken"]
    return {"Authorization": f"Bearer {token}"}
```

**Spring Boot comparison:**
- `scope="session"` app fixture = `@SpringBootTest` context reuse
- `autouse=True` rollback fixture = `@Transactional` on test methods (rolls back after each test)
- `auth_headers` fixture = Spring Security `@WithMockUser` / `mockMvc.with(user(...))`

---

## 8. Code Quality

### Type Hints

Every function signature must have full type annotations. Use Python 3.10+ union syntax:

```python
def get_by_id(restaurant_id: int) -> RestaurantModel | None: ...  # Correct
def get_by_id(restaurant_id: int) -> Optional[RestaurantModel]: ...  # Wrong, use | None
```

### Linting (`pyproject.toml`)

`ruff` handles both linting and formatting — it replaces `flake8` + `black`:

```toml
[tool.ruff]
line-length = 100
[tool.ruff.lint]
select = ["E", "F", "I", "S", "UP", "B"]
ignore = ["S101"]  # allow assert in tests
```

### Comments

Write no comments by default. Only add a comment when the **why** is non-obvious: a hidden constraint, a workaround for a specific bug, a subtle invariant. Never explain what the code does — well-named identifiers do that. Never write comments referencing the current task or PR.

### Logging

```python
logger = logging.getLogger(__name__)  # Module-level, one per file
```

| Situation | Level |
|---|---|
| Successful business operation | `INFO` |
| Expected failure (wrong password, not found) | `WARNING` |
| Unexpected exception | `ERROR` / `EXCEPTION` |

Never log PII: no email addresses, passwords, tokens, or phone numbers.
