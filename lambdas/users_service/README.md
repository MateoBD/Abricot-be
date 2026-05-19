# users-service-lambda placeholder

Estructura preparada en PASO 0.6 e implementada desde PASO 1.

`handler.py` mantiene el smoke test inicial y agrega mapping Cognito a usuario
local desde PASO 2 usando PostgreSQL via RDS Proxy privado.

Responsabilidades:

- PASO 1: `GET /callback` publico y `GET /auth-test` protegido.
- PASO 2: `POST /users`, `GET /users/{userId}` y `PUT /users/{userId}`.

PASO 2 requiere empaquetar `pg8000` para que los endpoints con DB funcionen en
Lambda sin dependencias nativas. No instalar dependencias directamente en esta carpeta: el
camino normal es ejecutar `scripts/package_lambdas.sh`, que copia el source a
`build/lambdas/users_service` e instala ahi las dependencias. `GET /callback`
no depende de esa libreria, pero la Lambda completa vive en subnets privadas en
PASO 2.1, por lo que esas subnets necesitan NAT para llamar a Cognito
`/oauth2/token`.

Configuracion esperada de DB:

- `DB_TARGET=RDS_PROXY`
- `POSTGRES_HOST=<rds-proxy-endpoint>`
- `POSTGRES_SSLMODE=require`

No configurar `POSTGRES_HOST` con el endpoint directo de una RDS privada o publica.
