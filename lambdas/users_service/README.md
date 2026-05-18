# users-service-lambda placeholder

Estructura preparada en PASO 0.6 e implementada desde PASO 1.

`handler.py` mantiene el smoke test inicial y agrega mapping Cognito a usuario local
en PASO 2 usando una DB PostgreSQL existente configurada por variables.

Responsabilidades:

- PASO 1: `GET /callback` publico y `GET /auth-test` protegido.
- PASO 2: `POST /users`, `GET /users/{userId}` y `PUT /users/{userId}`.

PASO 2 requiere empaquetar `psycopg2-binary` para que los endpoints con DB
funcionen en Lambda. `GET /callback` no depende de esa libreria.
