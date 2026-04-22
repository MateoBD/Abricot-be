# Abricot — Guía Completa de API para el Frontend

Este documento es la **fuente de verdad** para el equipo de frontend. Describe cada endpoint, cada campo de cada request y response, cada flujo de usuario de punta a punta, y todas las reglas de negocio que el frontend debe respetar.

---

## Tabla de Contenidos

1. [Fundamentos](#1-fundamentos)
2. [Referencia de Endpoints — Auth](#2-auth)
3. [Referencia de Endpoints — Datos de Referencia (Lookup)](#3-datos-de-referencia-lookup)
4. [Referencia de Endpoints — Restaurantes](#4-restaurantes)
5. [Referencia de Endpoints — Mesas](#5-mesas)
6. [Referencia de Endpoints — Horarios de Negocio](#6-horarios-de-negocio)
7. [Referencia de Endpoints — Disponibilidad](#7-disponibilidad)
8. [Referencia de Endpoints — Reservas](#8-reservas)
9. [Referencia de Endpoints — Menús](#9-menús)
10. [Referencia de Endpoints — Categorías de Menú](#10-categorías-de-menú)
11. [Referencia de Endpoints — Ítems de Menú](#11-ítems-de-menú)
12. [Referencia de Endpoints — Pedidos](#12-pedidos)
13. [Referencia de Endpoints — Promociones](#13-promociones)
14. [Referencia de Endpoints — Perfil de Usuario](#14-perfil-de-usuario)
15. [Referencia de Endpoints — Preferencias de Notificación](#15-preferencias-de-notificación)
16. [Referencia de Endpoints — Analytics](#16-analytics)
17. [Flujos de Usuario Completos](#17-flujos-de-usuario-completos)

---

## 1. Fundamentos

### 1.1 Base URL

```
https://<dominio>/
```

Todos los paths en este documento son relativos a la base URL. Ejemplo: `POST /auth/login` → `POST https://<dominio>/auth/login`.

---

### 1.2 Autenticación

El sistema usa **dos tokens JWT** distintos, ambos enviados exclusivamente en el header `Authorization`.

| Token | Duración | Para qué se usa |
|---|---|---|
| `accessToken` | 15 minutos | Autenticar cada request protegido |
| `refreshToken` | 30 días | Obtener un nuevo `accessToken` en `POST /auth/refresh` |

**Cómo enviar un access token:**
```
Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
```

**Reglas críticas:**
- El `accessToken` y el `refreshToken` **no son intercambiables**. Enviar un `refreshToken` a un endpoint protegido devuelve `401`. Enviar un `accessToken` a `POST /auth/refresh` devuelve `401`.
- **Nunca** enviar tokens en query params ni en cookies. El servidor solo acepta el header `Authorization: Bearer`.
- **Almacenamiento sugerido:** `accessToken` en memoria (variable de estado / store); `refreshToken` en `localStorage` o `sessionStorage` según la política de seguridad de la app. El `refreshToken` debe sobrevivir recarga de página para que el usuario no tenga que re-loguearse cada 15 minutos.

---

### 1.3 Estrategia de Refresh de Tokens

El `accessToken` expira en 15 minutos. El frontend debe manejar esto automáticamente:

**Flujo recomendado (interceptor de Axios / fetch wrapper):**

1. Cada request protegido se envía con el `accessToken` actual.
2. Si la respuesta es `401` con `code: "UNAUTHORIZED"`, intentar una sola vez:
   a. Llamar a `POST /auth/refresh` con el `refreshToken` en el header.
   b. Si devuelve `200`: guardar el nuevo `accessToken`, reintentar el request original con el nuevo token.
   c. Si devuelve `401`: el `refreshToken` expiró o es inválido → redirigir al usuario a la pantalla de login y limpiar todos los tokens almacenados.
3. Si el reintento también falla con `401`, redirigir a login sin reintentar nuevamente (evitar bucle infinito).

---

### 1.4 Formato de Respuestas de Error

**Todos** los errores siguen exactamente este formato JSON:

```json
{
  "message": "Descripción legible del error.",
  "code": "CODIGO_DE_ERROR",
  "errors": {}
}
```

El campo `errors` puede contener detalles adicionales (por ejemplo, qué campo falló validación). Puede ser un objeto vacío `{}`.

**Tabla de códigos de error por HTTP status:**

| HTTP Status | `code` posibles | Cuándo ocurre |
|---|---|---|
| `400` | `VALIDATION_ERROR`, `VALUE_ERROR` | Campo inválido, formato incorrecto, constraint violado |
| `401` | `UNAUTHORIZED` | Token ausente, expirado, inválido o tipo incorrecto |
| `403` | `FORBIDDEN` | Autenticado pero sin permisos (ej: no es admin del restaurante) |
| `404` | `NOT_FOUND` | El recurso no existe |
| `409` | `CONFLICT` | Email ya registrado, mesa ya ocupada, recurso duplicado |
| `500` | `INTERNAL_ERROR` | Error inesperado del servidor |

**Error de validación de Flask-RESTX** (campos del body inválidos según el schema):
```json
{
  "message": "Input payload validation failed",
  "errors": {
    "email": "email is required",
    "password": "'abc' is too short"
  }
}
```
Este formato puede diferir ligeramente del estándar porque lo genera el framework. El campo `errors` contiene un objeto con los nombres de campo como claves.

---

### 1.5 Paginación

Los endpoints de listado que devuelven muchos resultados usan este envelope de paginación:

```json
{
  "data": [ ... ],
  "total": 150,
  "page": 1,
  "perPage": 20
}
```

**Query params de paginación (todos opcionales):**
- `page` — número de página, base 1 (default: `1`)
- `perPage` — resultados por página (default: `20`, máximo: `100` en endpoints que lo aplican; ver cada sección)

> En el backend actual, el listado de restaurantes (`GET /restaurants/`) usa explícitamente **`perPage`** (camelCase), no `per_page`.

---

### 1.6 Convenciones

- **Todos los campos JSON** usan `camelCase` tanto en requests como en responses.
- **Fechas y horas** usan ISO 8601: `"2026-04-19T14:30:00+00:00"` (siempre UTC con timezone explícito).
- **Fechas sin hora** usan formato `YYYY-MM-DD`: `"2026-05-10"`.
- **Horas** usan formato `HH:MM`: `"20:30"`.
- **Precios** son strings decimales con 2 cifras: `"1250.00"`. No son números flotantes para evitar pérdida de precisión.
- **IDs** son strings en formato **UUID v7** (ej: `"01960e4e-5c5e-7abc-8def-000000000001"`). Nunca enteros. Almacenar y comparar siempre como strings.

---

### 1.7 Autenticación en rutas de restaurantes

En la implementación actual, el blueprint **Restaurants** declara `require_authentication()` a nivel de namespace. Eso implica:

- **`GET /restaurants/`** (búsqueda/listado) y **`GET /restaurants/{restaurantId}`** (detalle) **requieren** `Authorization: Bearer <accessToken>` para cualquier rol autenticado.
- **`POST /restaurants/`** exige además rol **`RESTAURANT_ADMIN`** o **`SUPER_ADMIN`**.
- Operaciones de administración sobre un restaurante (PUT, DELETE, foto, admins, analytics) exigen ser **admin de ese restaurante** (o `SUPER_ADMIN`), según el endpoint.

Si el frontend necesita listados o fichas **públicas sin login**, habrá que acordar un cambio de permisos en backend; hasta entonces, el flujo “visitante” debe obtener un token (p. ej. usuario de solo lectura) o estas pantallas solo estarán disponibles tras login.

---

## 2. Auth

### `POST /auth/register`

Crea una cuenta nueva. Devuelve ambos tokens y el perfil del usuario.

**Auth requerida:** Ninguna (🔓 público)

**Request body:**
```json
{
  "email": "juan.garcia@ejemplo.com",
  "password": "ContraseñaSegura1",
  "name": "Juan",
  "surname": "García"
}
```

| Campo | Tipo | Requerido | Validación |
|---|---|---|---|
| `email` | string | ✅ | Formato email válido. Máx 255 caracteres. |
| `password` | string | ✅ | Mín 8, máx 128 caracteres. |
| `name` | string | ✅ | Solo letras (incluye acentos y ñ), guiones y espacios. Máx 100 caracteres. |
| `surname` | string | ✅ | Mismas reglas que `name`. |

**Response `201`:**
```json
{
  "accessToken": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "refreshToken": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "user": {
    "id": "01960e4e-5c5e-7abc-8def-000000000001",
    "email": "juan.garcia@ejemplo.com",
    "name": "Juan",
    "surname": "García",
    "role": "CUSTOMER",
    "createdAt": "2026-04-19T14:30:00+00:00"
  }
}
```

**Errores:**
| Status | `code` | Cuándo |
|---|---|---|
| `400` | `VALIDATION_ERROR` | Campo ausente o formato inválido |
| `409` | `CONFLICT` | El email ya está registrado |

---

### `POST /auth/login`

Autentica un usuario existente. Devuelve ambos tokens y el perfil.

**Auth requerida:** Ninguna (🔓 público)

**Request body:**
```json
{
  "email": "juan.garcia@ejemplo.com",
  "password": "ContraseñaSegura1"
}
```

| Campo | Tipo | Requerido | Validación |
|---|---|---|---|
| `email` | string | ✅ | Formato email. Máx 255 caracteres. |
| `password` | string | ✅ | Mín 8, máx 128 caracteres. |

**Response `200`:**
```json
{
  "accessToken": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "refreshToken": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "user": {
    "id": "01960e4e-5c5e-7abc-8def-000000000001",
    "email": "juan.garcia@ejemplo.com",
    "name": "Juan",
    "surname": "García",
    "role": "CUSTOMER",
    "createdAt": "2026-04-19T14:30:00+00:00"
  }
}
```

**Errores:**
| Status | `code` | Cuándo |
|---|---|---|
| `400` | `VALIDATION_ERROR` | Campo ausente o formato inválido |
| `401` | `UNAUTHORIZED` | Email no registrado o contraseña incorrecta |

> El servidor **no indica** si el email existe o no. Siempre devuelve el mismo `401` para ambos casos (seguridad por diseño).

---

### `POST /auth/refresh`

Obtiene un nuevo `accessToken` usando el `refreshToken`. El `refreshToken` no cambia.

**Auth requerida:** `Authorization: Bearer <refreshToken>` (⚠️ debe ser el refresh token, NO el access token)

**Request body:** Vacío.

**Response `200`:**
```json
{
  "accessToken": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
}
```

**Errores:**
| Status | `code` | Cuándo |
|---|---|---|
| `401` | `UNAUTHORIZED` | Refresh token ausente, expirado, inválido o se envió un access token en su lugar |

---

## 3. Datos de Referencia (Lookup)

Estos endpoints devuelven listas estáticas para poblar dropdowns y filtros. En la **propuesta de producto** suelen ser públicos y raramente cambian.

> **Backend actual:** las rutas HTTP descritas en esta sección (`GET /cuisines/`, `GET /price-ranges/`, jerarquía país → provincia → ciudad → barrio) **pueden no estar registradas aún** en el servidor. El repositorio de datos (`LookupRepository`) existe en capa de dominio; cuando los endpoints estén disponibles, el contrato debe coincidir con lo documentado aquí. Hasta entonces, el frontend puede usar datos embebidos, fixtures o pantallas que no dependan de lookup en vivo.

---

### `GET /cuisines/`

**Auth:** Ninguna (🔓)

**Response `200`:**
```json
[
  { "id": "01960e4e-5c5e-7abc-8def-000000000001", "slug": "ARGENTINA", "label": "Parrilla y Criolla" },
  { "id": "01960e4e-5c5e-7abc-8def-000000000002", "slug": "ITALIANA",  "label": "Pasta y Pizza" },
  { "id": "01960e4e-5c5e-7abc-8def-000000000003", "slug": "JAPONESA",  "label": "Sushi y Ramen" },
  { "id": "01960e4e-5c5e-7abc-8def-000000000004", "slug": "MEDITERRANEA", "label": "Griega, Española y Árabe" },
  { "id": "01960e4e-5c5e-7abc-8def-000000000005", "slug": "MEXICANA",  "label": "Tacos y Burritos" },
  { "id": "01960e4e-5c5e-7abc-8def-000000000006", "slug": "PERUANA",   "label": "Ceviche y Lomo Saltado" },
  { "id": "01960e4e-5c5e-7abc-8def-000000000007", "slug": "AMERICANA", "label": "Hamburguesas y BBQ" },
  { "id": "01960e4e-5c5e-7abc-8def-000000000008", "slug": "CHINA",     "label": "Dim Sum y Wok" },
  { "id": "01960e4e-5c5e-7abc-8def-000000000009", "slug": "FRANCESA",  "label": "Bistró y Haute Cuisine" },
  { "id": "01960e4e-5c5e-7abc-8def-00000000000a", "slug": "CAFE_BAR", "label": "Cafetería y Brunch" },
  { "id": "01960e4e-5c5e-7abc-8def-00000000000b", "slug": "VEGANA_VEGETARIANA", "label": "Plant-Based" },
  { "id": "01960e4e-5c5e-7abc-8def-00000000000c", "slug": "MARISCOS", "label": "Pescadería y Mariscos" },
  { "id": "01960e4e-5c5e-7abc-8def-00000000000d", "slug": "FUSION",   "label": "Fusión" },
  { "id": "01960e4e-5c5e-7abc-8def-00000000000e", "slug": "OTRA",     "label": "Otra" }
]
```

---

### `GET /price-ranges/`

**Auth:** Ninguna (🔓)

**Response `200`:**
```json
[
  { "id": "01960e4e-5c5e-7abc-8def-000000000011", "slug": "ECONOMICO",  "label": "$",    "description": "Menos de $5.000 por persona",  "sortOrder": 1 },
  { "id": "01960e4e-5c5e-7abc-8def-000000000012", "slug": "MODERADO",   "label": "$$",   "description": "$5.000 – $15.000 por persona", "sortOrder": 2 },
  { "id": "01960e4e-5c5e-7abc-8def-000000000013", "slug": "ELEGANTE",   "label": "$$$",  "description": "$15.000 – $40.000 por persona","sortOrder": 3 },
  { "id": "01960e4e-5c5e-7abc-8def-000000000014", "slug": "EXCLUSIVO",  "label": "$$$$", "description": "Más de $40.000 por persona",   "sortOrder": 4 }
]
```

---

### `GET /countries/`

**Auth:** Ninguna (🔓)

**Response `200`:**
```json
[
  { "id": "01960e4e-5c5e-7abc-8def-000000000021", "name": "Argentina", "isoCode": "AR" },
  { "id": "01960e4e-5c5e-7abc-8def-000000000022", "name": "Uruguay",   "isoCode": "UY" }
]
```

---

### `GET /countries/{countryId}/provinces/`

**Auth:** Ninguna (🔓)

**Path param:** `countryId` — UUID v7 del país

**Response `200`:**
```json
[
  { "id": "01960e4e-5c5e-7abc-8def-000000000031", "name": "Buenos Aires", "countryId": "01960e4e-5c5e-7abc-8def-000000000021" },
  { "id": "01960e4e-5c5e-7abc-8def-000000000032", "name": "CABA",         "countryId": "01960e4e-5c5e-7abc-8def-000000000021" },
  { "id": "01960e4e-5c5e-7abc-8def-000000000033", "name": "Córdoba",      "countryId": "01960e4e-5c5e-7abc-8def-000000000021" }
]
```

**Errores:**
| Status | `code` | Cuándo |
|---|---|---|
| `404` | `NOT_FOUND` | El país no existe |

---

### `GET /provinces/{provinceId}/cities/`

**Auth:** Ninguna (🔓)

**Response `200`:**
```json
[
  { "id": "01960e4e-5c5e-7abc-8def-000000000041", "name": "Buenos Aires", "provinceId": "01960e4e-5c5e-7abc-8def-000000000031" },
  { "id": "01960e4e-5c5e-7abc-8def-000000000042", "name": "Mar del Plata","provinceId": "01960e4e-5c5e-7abc-8def-000000000031" }
]
```

---

### `GET /cities/{cityId}/neighbourhoods/`

**Auth:** Ninguna (🔓)

**Response `200`:**
```json
[
  { "id": "01960e4e-5c5e-7abc-8def-000000000051", "name": "Palermo",   "cityId": "01960e4e-5c5e-7abc-8def-000000000041" },
  { "id": "01960e4e-5c5e-7abc-8def-000000000052", "name": "Recoleta",  "cityId": "01960e4e-5c5e-7abc-8def-000000000041" },
  { "id": "01960e4e-5c5e-7abc-8def-000000000053", "name": "San Telmo", "cityId": "01960e4e-5c5e-7abc-8def-000000000041" }
]
```

---

## 4. Restaurantes

Contrato alineado con `app/api/restaurants/` (Flask-RESTX). Path param: **`restaurantId`** es un **UUID** (el router usa `<uuid:restaurant_id>`).

### Forma de `RestaurantResponse` (listado y detalle)

El backend devuelve un objeto **plano** (sin anidar `city`, `province`, `priceRange` ni objetos `cuisineTypes`). Para mostrar nombres legibles, combiná estos UUID con los datos de lookup (§3) cuando estén disponibles.

Campos típicos:

| Campo | Tipo | Notas |
|---|---|---|
| `id` | string (UUID) | |
| `name`, `address`, `phone` | string | |
| `cityId` | string (UUID) | Obligatorio en entidad |
| `neighbourhoodId` | string (UUID) \| null | |
| `priceRangeId` | string (UUID) \| null | |
| `email`, `description`, `photoUrl` | string \| null | |
| `allowTableJoining` | bool | Configuración del local |
| `defaultSlotDurationMinutes` | int | P. ej. `90` |
| `cuisineTypeIds` | string[] (UUID[]) | Tipos de cocina asociados (tabla `restaurant_cuisines`) |
| `createdAt` | string (ISO 8601) | |

---

### `GET /restaurants/`

Búsqueda y listado paginado con filtros opcionales.

**Auth:** Access token (🔑) — **cualquier usuario autenticado** (el namespace exige JWT).

**Query params (todos opcionales, nombres en camelCase):**

| Parámetro | Tipo | Descripción |
|---|---|---|
| `name` | string | Búsqueda parcial por nombre (**case-insensitive** / `ILIKE`). |
| `countryId` | string (UUID) | Restaurantes cuya ciudad pertenece a un país (vía provincia). |
| `provinceId` | string (UUID) | Ciudad cuya provincia coincide. |
| `cityId` | string (UUID) | Coincide con `cityId` del restaurante. |
| `neighbourhoodId` | string (UUID) | Coincide con `neighbourhoodId` del restaurante. |
| `priceRangeId` | string (UUID) | Coincide con `priceRangeId` del restaurante. |
| `cuisineTypeIds` | string (UUID), **repetible** | Restaurantes que tengan **al menos uno** de los tipos listados en `restaurant_cuisines`. Podés repetir el query param (`?cuisineTypeIds=a&cuisineTypeIds=b`) o enviar varios UUID separados por coma en un solo valor. |
| `page` | int | Default: `1`. |
| `perPage` | int | Default: `20`, máximo `100`. |

**Ejemplo:**  
`GET /restaurants/?name=gaucho&cityId=018f1234-5678-7abc-8def-123456789041&cuisineTypeIds=018f…001&cuisineTypeIds=018f…002&page=1&perPage=20`

**Response `200`:**
```json
{
  "data": [
    {
      "id": "01960e4e-5c5e-7abc-8def-000000000061",
      "name": "El Gaucho Rojo",
      "address": "Av. Corrientes 1234",
      "cityId": "01960e4e-5c5e-7abc-8def-000000000041",
      "neighbourhoodId": "01960e4e-5c5e-7abc-8def-000000000051",
      "priceRangeId": "01960e4e-5c5e-7abc-8def-000000000012",
      "phone": "+54 11 4444-5555",
      "email": "contacto@elgauchorojo.com",
      "description": "Parrilla tradicional argentina.",
      "photoUrl": "https://bucket.s3.amazonaws.com/restaurants/01960e4e-5c5e-7abc-8def-000000000061/foto.jpg",
      "allowTableJoining": true,
      "defaultSlotDurationMinutes": 90,
      "cuisineTypeIds": [
        "01960e4e-5c5e-7abc-8def-000000000001"
      ],
      "createdAt": "2026-04-07T19:00:00+00:00"
    }
  ],
  "total": 45,
  "page": 1,
  "perPage": 20
}
```

**Errores:** `401` si falta o vence el token.

---

### `POST /restaurants/`

Crea un restaurante. El usuario creador queda asociado como administrador del restaurante; el rol del usuario puede actualizarse según la lógica del backend.

**Auth:** Access token (🔑) + rol **`RESTAURANT_ADMIN`** o **`SUPER_ADMIN`**.

**Request body (JSON, camelCase):**
```json
{
  "name": "El Gaucho Rojo",
  "address": "Av. Corrientes 1234, CABA",
  "cityId": "01960e4e-5c5e-7abc-8def-000000000041",
  "neighbourhoodId": "01960e4e-5c5e-7abc-8def-000000000051",
  "priceRangeId": "01960e4e-5c5e-7abc-8def-000000000012",
  "cuisineTypeIds": [
    "01960e4e-5c5e-7abc-8def-000000000001",
    "01960e4e-5c5e-7abc-8def-000000000002"
  ],
  "phone": "+54 11 4444-5555",
  "email": "contacto@elgauchorojo.com",
  "description": "Parrilla tradicional argentina en el corazón de Buenos Aires."
}
```

| Campo | Tipo | Requerido | Validación |
|---|---|---|---|
| `name` | string | ✅ | Mín 1, máx 150 caracteres |
| `address` | string | ✅ | Mín 1, máx 255 caracteres |
| `cityId` | string (UUID) | ✅ | UUID válido; debe existir fila en `cities` |
| `neighbourhoodId` | string (UUID) | ❌ | Si se envía, debe existir y corresponder a la ciudad (regla de negocio / FK) |
| `priceRangeId` | string (UUID) | ❌ | Debe existir en `price_ranges` |
| `cuisineTypeIds` | string[] (UUID) | ❌ | Cada ID en `cuisine_types`. Omitir o `[]` = sin tipos asociados |
| `phone` | string | ✅ | Patrón teléfono internacional (ver OpenAPI) |
| `email` | string | ❌ | Email válido, máx 255 |
| `description` | string | ❌ | Máx 2000 caracteres |

> **`allowTableJoining`** y **`defaultSlotDurationMinutes`** no se envían en create/update actuales: se definen a nivel de modelo/BD (defaults). Si en el futuro se exponen en API, se documentarán aquí.

**Response `201`:** Objeto `RestaurantResponse` (misma forma que un ítem de `data` en el GET list).

**Errores:**
| Status | `code` | Cuándo |
|---|---|---|
| `400` | `VALIDATION_ERROR` | Payload inválido (Flask-RESTX / servicio) |
| `401` | `UNAUTHORIZED` | Sin token o token inválido |
| `403` | `FORBIDDEN` | Rol distinto de `RESTAURANT_ADMIN` / `SUPER_ADMIN` |

---

### `GET /restaurants/{restaurantId}`

Detalle de un restaurante.

**Auth:** Access token (🔑) — cualquier usuario autenticado.

**Response `200`:** Un solo objeto `RestaurantResponse` (mismos campos que en el listado, incluido `cuisineTypeIds`).

**Errores:**
| Status | `code` | Cuándo |
|---|---|---|
| `401` | `UNAUTHORIZED` | Sin token |
| `404` | `NOT_FOUND` | El restaurante no existe |

---

### `PUT /restaurants/{restaurantId}`

Reemplaza los campos del cuerpo según el schema de actualización. Comportamiento de opcionales:

- **`neighbourhoodId` / `priceRangeId`:** si la clave **no** está en el JSON, el backend **no** modifica el valor actual (`FIELD_UNSET`). Si la clave **está** (incluso con `null`), se aplica limpieza o nuevo UUID según validación.
- **`cuisineTypeIds`:** si la clave **no** está, no se tocan las filas de `restaurant_cuisines`. Si está presente (puede ser `[]`), se **reemplaza** el conjunto de tipos de cocina.

**Auth:** Access token + **admin del restaurante** (o `SUPER_ADMIN`) 🔐

**Request body:** Mismos campos que `POST` (todos los requeridos por el schema de update: `name`, `address`, `phone`, `cityId`, etc.).

**Response `200`:** `RestaurantResponse` actualizado.

**Errores:**
| Status | `code` | Cuándo |
|---|---|---|
| `400` | `VALIDATION_ERROR` | Campo inválido |
| `401` | `UNAUTHORIZED` | Sin token |
| `403` | `FORBIDDEN` | No es admin del restaurante |
| `404` | `NOT_FOUND` | Restaurante inexistente |

---

### `DELETE /restaurants/{restaurantId}`

Elimina el restaurante.

**Auth:** Access token + admin del restaurante (🔐)

**Response `204`:** Sin cuerpo.

**Errores:**
| Status | `code` | Cuándo |
|---|---|---|
| `401` | `UNAUTHORIZED` | Sin token |
| `403` | `FORBIDDEN` | No es admin del restaurante |
| `404` | `NOT_FOUND` | No existe |

---

### `POST /restaurants/{restaurantId}/photo`

Sube o reemplaza la foto del restaurante (S3).

**Auth:** Access token + admin del restaurante (🔐)

**Request:** `multipart/form-data` con el campo **`file`** (no `photo`) conteniendo la imagen.

```
Content-Type: multipart/form-data
file: <archivo binario>
```

Formatos aceptados: `image/jpeg`, `image/png`, `image/webp`.

**Response `200`:** Objeto **`RestaurantResponse` completo** (incluye `photoUrl` actualizado), no solo la URL.

**Errores:**
| Status | `code` | Cuándo |
|---|---|---|
| `400` | `VALIDATION_ERROR` | Sin archivo o MIME no permitido |
| `401` | `UNAUTHORIZED` | Sin token |
| `403` | `FORBIDDEN` | No es admin |
| `404` | `NOT_FOUND` | El restaurante no existe |

---

### Administradores del restaurante (implementado)

**Auth:** JWT + ser admin del restaurante (o `SUPER_ADMIN`), salvo anotación contraria.

#### `GET /restaurants/{restaurantId}/admins/`

Lista paginada de administradores (mismo envelope `data`, `total`, `page`, `perPage` que otros listados del API). Cada elemento incluye `id` (UUID del **usuario**), `email`, `name`, `surname`, `role`, `createdAt`.

#### `POST /restaurants/{restaurantId}/admins/`

**Body:** `{ "userId": "<uuid del usuario a promover>" }`  
**Éxitos / errores:** `201`, `404`, `409` si ya es admin.

#### `DELETE /restaurants/{restaurantId}/admins/{userId}`

Quita a `userId` (UUID) como admin del restaurante. **`userId` en la URL es UUID**, no entero.

---

## 5. Mesas

> **Nota:** Los endpoints de esta sección forman parte de la especificación; comprobar en el backend si ya están registrados antes de integrar.

Todos los endpoints de mesas requieren ser admin del restaurante (🔐).

---

### `GET /restaurants/{restaurantId}/tables/`

Lista todas las mesas del restaurante.

**Response `200`:**
```json
[
  {
    "id": "01960e4e-5c5e-7abc-8def-000000000071",
    "restaurantId": "01960e4e-5c5e-7abc-8def-000000000061",
    "number": 1,
    "capacity": 2,
    "name": null,
    "isJoinable": true,
    "isActive": true
  },
  {
    "id": "01960e4e-5c5e-7abc-8def-000000000085",
    "restaurantId": "01960e4e-5c5e-7abc-8def-000000000061",
    "number": 21,
    "capacity": 4,
    "name": "Mesa VIP",
    "isJoinable": false,
    "isActive": true
  }
]
```

---

### `POST /restaurants/{restaurantId}/tables/`

Crea una sola mesa.

**Request body:**
```json
{
  "number": 31,
  "capacity": 6,
  "name": "Terraza Norte",
  "isJoinable": true,
  "isActive": true
}
```

| Campo | Tipo | Requerido | Notas |
|---|---|---|---|
| `number` | int | ✅ | Número de mesa. Debe ser único dentro del restaurante. |
| `capacity` | int | ✅ | Cantidad de personas que caben en la mesa. |
| `name` | string | ❌ | Nombre descriptivo. Máx 50 caracteres. |
| `isJoinable` | bool | ❌ | Default: `true`. Si puede unirse con otras mesas. |
| `isActive` | bool | ❌ | Default: `true`. |

**Response `201`:** Objeto `TableResponse` (igual a un elemento del listado).

**Errores:**
| Status | `code` | Cuándo |
|---|---|---|
| `409` | `CONFLICT` | Ya existe una mesa con ese `number` en este restaurante |

---

### `POST /restaurants/{restaurantId}/tables/bulk`

Crea múltiples mesas en una sola operación. Los números de mesa se asignan automáticamente en secuencia desde el más alto existente + 1.

**Request body:**
```json
{
  "groups": [
    { "quantity": 20, "capacity": 2 },
    { "quantity": 10, "capacity": 4, "isJoinable": false }
  ]

}
```

| Campo | Tipo | Requerido | Notas |
|---|---|---|---|
| `groups` | array | ✅ | Al menos 1 grupo. |
| `groups[].quantity` | int | ✅ | Cantidad de mesas a crear en este grupo. Mín 1. |
| `groups[].capacity` | int | ✅ | Capacidad de cada mesa del grupo. |
| `groups[].isJoinable` | bool | ❌ | Default: `true` |

**Ejemplo:** Si el restaurante ya tiene 5 mesas (números 1–5), este body creará mesas 6–25 con capacidad 2 (`isJoinable: true`) y mesas 26–35 con capacidad 4 (`isJoinable: false`).

**Response `201`:**
```json
{
  "created": 30,
  "tables": [
    { "id": "01960e4e-5c5e-7abc-8def-000000000076", "restaurantId": "01960e4e-5c5e-7abc-8def-000000000061", "number": 6, "capacity": 2, "name": null, "isJoinable": true, "isActive": true },
    ...
  ]
}
```

---

### `GET /restaurants/{restaurantId}/tables/{tableId}`

**Response `200`:** Objeto `TableResponse`.

**Errores:**
| Status | `code` | Cuándo |
|---|---|---|
| `404` | `NOT_FOUND` | Mesa no existe o no pertenece al restaurante |

---

### `PUT /restaurants/{restaurantId}/tables/{tableId}`

**Request body:**
```json
{
  "number": 31,
  "capacity": 6,
  "name": "Terraza Norte",
  "isJoinable": true,
  "isActive": false
}
```

Todos los campos son requeridos en un PUT. `isActive: false` desactiva la mesa (no aparecerá en disponibilidad ni en nuevas reservas).

**Response `200`:** Objeto `TableResponse` actualizado.

---

### `DELETE /restaurants/{restaurantId}/tables/{tableId}`

**Response `204`:** Sin cuerpo.

**Errores:**
| Status | `code` | Cuándo |
|---|---|---|
| `409` | `CONFLICT` | La mesa tiene reservas futuras confirmadas. Primero cancelarlas o desactivar la mesa en lugar de eliminarla. |

---

## 6. Horarios de Negocio

### `GET /restaurants/{restaurantId}/business-hours/`

Obtiene los 7 días de horarios.

**Auth:** Ninguna (🔓)

**Response `200`:**
```json
[
  { "id": "01960e4e-5c5e-7abc-8def-000000000091", "dayOfWeek": 0, "dayName": "Lunes",    "opensAt": "12:00", "closesAt": "00:00", "isClosed": false },
  { "id": "01960e4e-5c5e-7abc-8def-000000000092", "dayOfWeek": 1, "dayName": "Martes",   "opensAt": "12:00", "closesAt": "00:00", "isClosed": false },
  { "id": "01960e4e-5c5e-7abc-8def-000000000093", "dayOfWeek": 2, "dayName": "Miércoles","opensAt": "12:00", "closesAt": "00:00", "isClosed": false },
  { "id": "01960e4e-5c5e-7abc-8def-000000000094", "dayOfWeek": 3, "dayName": "Jueves",   "opensAt": "12:00", "closesAt": "00:00", "isClosed": false },
  { "id": "01960e4e-5c5e-7abc-8def-000000000095", "dayOfWeek": 4, "dayName": "Viernes",  "opensAt": "20:00", "closesAt": "01:00", "isClosed": false },
  { "id": "01960e4e-5c5e-7abc-8def-000000000096", "dayOfWeek": 5, "dayName": "Sábado",   "opensAt": "20:00", "closesAt": "02:00", "isClosed": false },
  { "id": "01960e4e-5c5e-7abc-8def-000000000097", "dayOfWeek": 6, "dayName": "Domingo",  "opensAt": null,    "closesAt": null,    "isClosed": true }
]
```

> `dayOfWeek`: 0 = Lunes, 1 = Martes, ..., 6 = Domingo.
> Cuando `isClosed: true`, `opensAt` y `closesAt` son `null`.
> `closesAt` puede ser menor que `opensAt` para indicar que cierra pasada la medianoche (ej: abre 20:00, cierra 02:00 del día siguiente).

---

### `PUT /restaurants/{restaurantId}/business-hours/`

Reemplaza los horarios de toda la semana. Enviar los 7 días siempre.

**Auth:** Access token + ser admin (🔐)

**Request body:**
```json
[
  { "dayOfWeek": 0, "opensAt": "12:00", "closesAt": "00:00", "isClosed": false },
  { "dayOfWeek": 1, "opensAt": "12:00", "closesAt": "00:00", "isClosed": false },
  { "dayOfWeek": 2, "opensAt": "12:00", "closesAt": "00:00", "isClosed": false },
  { "dayOfWeek": 3, "opensAt": "12:00", "closesAt": "00:00", "isClosed": false },
  { "dayOfWeek": 4, "opensAt": "20:00", "closesAt": "01:00", "isClosed": false },
  { "dayOfWeek": 5, "opensAt": "20:00", "closesAt": "02:00", "isClosed": false },
  { "dayOfWeek": 6, "opensAt": null,    "closesAt": null,    "isClosed": true }
]
```

| Campo | Tipo | Requerido | Notas |
|---|---|---|---|
| `dayOfWeek` | int | ✅ | 0–6. El array puede enviarse en cualquier orden. |
| `opensAt` | string | ❌ | Formato `HH:MM`. Requerido si `isClosed: false`. |
| `closesAt` | string | ❌ | Formato `HH:MM`. Requerido si `isClosed: false`. |
| `isClosed` | bool | ✅ | Si es `true`, `opensAt` y `closesAt` deben ser `null`. |

**Response `200`:** Array de 7 objetos igual al de GET.

---

## 7. Disponibilidad

### `GET /restaurants/{restaurantId}/availability/`

Devuelve todos los turnos del día para un grupo de N personas, indicando cuáles están disponibles y qué mesas se asignarían.

**Auth:** Ninguna (🔓)

**Query params:**

| Parámetro | Tipo | Requerido | Descripción |
|---|---|---|---|
| `date` | string | ✅ | Formato `YYYY-MM-DD`. Debe ser hoy o una fecha futura. |
| `party_size` | int | ✅ | Número de personas. Mín 1. |

**Response `200`:**
```json
{
  "date": "2026-05-10",
  "partySize": 6,
  "allowTableJoining": true,
  "slots": [
    {
      "timeSlot": "20:00",
      "isAvailable": true,
      "tableAssignment": {
        "tableIds": ["01960e4e-5c5e-7abc-8def-000000000072", "01960e4e-5c5e-7abc-8def-000000000073", "01960e4e-5c5e-7abc-8def-000000000075"],
        "tableNumbers": [2, 3, 5],
        "totalCapacity": 6,
        "isJoined": true
      }
    },
    {
      "timeSlot": "21:30",
      "isAvailable": false,
      "tableAssignment": null
    },
    {
      "timeSlot": "23:00",
      "isAvailable": true,
      "tableAssignment": {
        "tableIds": ["01960e4e-5c5e-7abc-8def-000000000077"],
        "tableNumbers": [7],
        "totalCapacity": 8,
        "isJoined": false
      }
    }
  ]
}
```

> Los slots no disponibles (`isAvailable: false`) se incluyen con `tableAssignment: null` para que el frontend pueda mostrar visualmente qué horarios están ocupados.
> El intervalo entre slots lo define `defaultSlotDurationMinutes` del restaurante.

**Errores:**
| Status | `code` | Cuándo |
|---|---|---|
| `400` | `VALIDATION_ERROR` | Fecha inválida, en el pasado o `party_size` menor a 1 |
| `404` | `NOT_FOUND` | El restaurante no existe |

---

## 8. Reservas

### `POST /restaurants/{restaurantId}/reservations/`

El cliente crea una reserva. El sistema verifica disponibilidad y la confirma automáticamente. Si no hay disponibilidad, devuelve `409`.

**Auth:** Access token (🔑)

**Request body:**
```json
{
  "partySize": 4,
  "date": "2026-05-10",
  "timeSlot": "20:00",
  "notes": "Festejo de cumpleaños. Preferimos estar cerca de la ventana."
}
```

| Campo | Tipo | Requerido | Validación |
|---|---|---|---|
| `partySize` | int | ✅ | Mín 1. |
| `date` | string | ✅ | `YYYY-MM-DD`. Debe ser fecha futura. |
| `timeSlot` | string | ✅ | `HH:MM`. Debe ser un slot válido para ese restaurante. |
| `notes` | string | ❌ | Máx 1000 caracteres. |

**Response `201`:**
```json
{
  "id": "01960e4e-5c5e-7abc-8def-00000000002a",
  "restaurantId": "01960e4e-5c5e-7abc-8def-000000000061",
  "restaurantName": "El Gaucho Rojo",
  "userId": "01960e4e-5c5e-7abc-8def-000000000007",
  "guestName": null,
  "guestPhone": null,
  "guestEmail": null,
  "source": "ONLINE",
  "partySize": 4,
  "date": "2026-05-10",
  "timeSlot": "20:00",
  "status": "CONFIRMED",
  "notes": "Festejo de cumpleaños. Preferimos estar cerca de la ventana.",
  "confirmationCode": "ABC12345",
  "createdAt": "2026-04-19T14:30:00+00:00",
  "tables": [
    { "tableId": "01960e4e-5c5e-7abc-8def-000000000077", "tableNumber": 7, "capacity": 4 }
  ]
}
```

**Errores:**
| Status | `code` | Cuándo |
|---|---|---|
| `400` | `VALIDATION_ERROR` | Campo inválido |
| `401` | `UNAUTHORIZED` | Sin token |
| `404` | `NOT_FOUND` | El restaurante no existe |
| `409` | `CONFLICT` | No hay disponibilidad para ese día, hora y cantidad de personas |

---

### `POST /restaurants/{restaurantId}/reservations/admin`

El admin crea una reserva en nombre de un cliente (llamado telefónico, evento, grupo grande). No requiere que el grupo tenga cuenta registrada.

**Auth:** Access token + ser admin del restaurante (🔐)

**Request body:**
```json
{
  "partySize": 20,
  "date": "2026-06-15",
  "timeSlot": "21:00",
  "source": "EVENT",
  "guestName": "Empresa Tech S.A.",
  "guestPhone": "+54 11 5555-0000",
  "guestEmail": "eventos@techsa.com",
  "userId": null,
  "notes": "Cena de fin de año. Requieren proyector."
}
```

| Campo | Tipo | Requerido | Validación |
|---|---|---|---|
| `partySize` | int | ✅ | Mín 1 |
| `date` | string | ✅ | `YYYY-MM-DD`, fecha futura |
| `timeSlot` | string | ✅ | `HH:MM` |
| `source` | string | ✅ | `"PHONE"` o `"EVENT"` (no `"ONLINE"`) |
| `guestName` | string | ✅* | Requerido si `userId` es `null`. Máx 150 caracteres. |
| `guestPhone` | string | ❌ | Teléfono del contacto del grupo |
| `guestEmail` | string | ❌ | Email para enviar la confirmación. Si se envía, recibe email de confirmación. |
| `userId` | string (uuid) | ❌ | ID de usuario registrado. Si se envía, `guestName` puede ser `null`. |
| `notes` | string | ❌ | Notas internas |

> Exactamente uno de `guestName` (cuando `userId` es null) o `userId` debe ser no-nulo.

**Response `201`:** Idéntico a `POST /restaurants/{id}/reservations/` pero con `source: "PHONE"` o `"EVENT"` y los campos de huésped poblados.

---

### `GET /restaurants/{restaurantId}/reservations/`

Lista todas las reservas del restaurante. Solo para admins.

**Auth:** Access token + ser admin (🔐)

**Query params:**

| Parámetro | Tipo | Descripción |
|---|---|---|
| `date_from` | string | `YYYY-MM-DD` — fecha desde (inclusive) |
| `date_to` | string | `YYYY-MM-DD` — fecha hasta (inclusive) |
| `status` | string | Filtrar por estado: `CONFIRMED`, `CANCELLED`, `COMPLETED`, `NO_SHOW` |
| `source` | string | Filtrar por origen: `ONLINE`, `PHONE`, `EVENT` |
| `page` | int | Página (default: 1) |
| `per_page` | int | Por página (default: 20) |

**Response `200`:**
```json
{
  "data": [ /* array de ReservationResponse */ ],
  "total": 87,
  "page": 1,
  "perPage": 20
}
```

---

### `GET /reservations/{reservationId}`

Obtiene una reserva específica.

**Auth:** Access token (🔑). Solo el dueño de la reserva o un admin del restaurante puede verla.

**Response `200`:** Objeto `ReservationResponse` completo.

**Errores:**
| Status | `code` | Cuándo |
|---|---|---|
| `401` | `UNAUTHORIZED` | Sin token |
| `403` | `FORBIDDEN` | No es el dueño ni admin del restaurante |
| `404` | `NOT_FOUND` | No existe |

---

### `GET /reservations/lookup`

Consultar una reserva por código de confirmación. Público — para el link en el email de confirmación.

**Auth:** Ninguna (🔓)

**Query params:**

| Parámetro | Tipo | Requerido |
|---|---|---|
| `code` | string | ✅ |

**Ejemplo:** `GET /reservations/lookup?code=ABC12345`

**Response `200`:** Objeto `ReservationResponse` completo.

**Errores:**
| Status | `code` | Cuándo |
|---|---|---|
| `404` | `NOT_FOUND` | No existe reserva con ese código |

---

### `PATCH /reservations/{reservationId}/cancel`

Cancela una reserva. Puede hacerlo el dueño de la reserva o un admin del restaurante.

**Auth:** Access token (🔑)

**Request body:**
```json
{
  "reason": "El grupo no puede asistir por una emergencia."
}
```

| Campo | Tipo | Requerido |
|---|---|---|
| `reason` | string | ❌ |

**Response `200`:** Objeto `ReservationResponse` con `status: "CANCELLED"` y `tables: []`.

**Errores:**
| Status | `code` | Cuándo |
|---|---|---|
| `403` | `FORBIDDEN` | No es el dueño ni admin |
| `409` | `CONFLICT` | La reserva ya está cancelada, completada o marcada como no-show |

---

### `PATCH /reservations/{reservationId}/reassign-tables`

Admin reasigna manualmente las mesas de una reserva confirmada (para organizar mejor el salón).

**Auth:** Access token + ser admin (🔐)

**Request body:**
```json
{
  "tableIds": ["01960e4e-5c5e-7abc-8def-000000000073", "01960e4e-5c5e-7abc-8def-000000000074"]
}
```

| Campo | Tipo | Requerido | Validación |
|---|---|---|---|
| `tableIds` | string[] (uuid[]) | ✅ | Mín 1 mesa. Las mesas deben estar disponibles en el slot y tener capacidad suficiente para el `partySize` de la reserva. |

**Response `200`:** Objeto `ReservationResponse` actualizado.

---

### `PATCH /reservations/{reservationId}/complete`

Admin marca el turno como completado (el grupo se fue).

**Auth:** Access token + ser admin (🔐)

**Request body:** Vacío.

**Response `200`:** Objeto `ReservationResponse` con `status: "COMPLETED"`.

---

### `PATCH /reservations/{reservationId}/no-show`

Admin marca la reserva como inasistencia (el grupo no se presentó). Libera las mesas.

**Auth:** Access token + ser admin (🔐)

**Request body:** Vacío.

**Response `200`:** Objeto `ReservationResponse` con `status: "NO_SHOW"`.

---

### `GET /users/{userId}/reservations/`

Lista las reservas del usuario autenticado.

**Auth:** Access token (🔑)

**Query params:**

| Parámetro | Tipo | Descripción |
|---|---|---|
| `status` | string | Filtrar: `CONFIRMED`, `CANCELLED`, `COMPLETED`, `NO_SHOW` |
| `page` | int | Default: 1 |
| `per_page` | int | Default: 20 |

**Response `200`:** Envelope paginado con array de `ReservationResponse`.

---

## 9. Menús

### `GET /restaurants/{restaurantId}/menus/`

**Auth:** Ninguna (🔓)

**Response `200`:**
```json
[
  { "id": "01960e4e-5c5e-7abc-8def-0000000000a1", "restaurantId": "01960e4e-5c5e-7abc-8def-000000000061", "name": "Menú Primavera 2026", "isActive": true, "createdAt": "2026-04-07T19:00:00+00:00" }
]
```

---

### `POST /restaurants/{restaurantId}/menus/`

**Auth:** Admin (🔐)

**Request body:**
```json
{ "name": "Menú Primavera 2026" }
```

| Campo | Tipo | Requerido | Validación |
|---|---|---|---|
| `name` | string | ✅ | Máx 150 caracteres |

**Response `201`:** Objeto `MenuResponse`.

---

### `GET /restaurants/{restaurantId}/menus/{menuId}`

Devuelve el menú completo con todas sus categorías e ítems anidados.

**Auth:** Ninguna (🔓)

**Response `200`:**
```json
{
  "id": "01960e4e-5c5e-7abc-8def-0000000000a1",
  "restaurantId": "01960e4e-5c5e-7abc-8def-000000000061",
  "name": "Menú Primavera 2026",
  "isActive": true,
  "createdAt": "2026-04-07T19:00:00+00:00",
  "categories": [
    {
      "id": "01960e4e-5c5e-7abc-8def-0000000000b1",
      "menuId": "01960e4e-5c5e-7abc-8def-0000000000a1",
      "name": "Entradas",
      "displayOrder": 0,
      "isActive": true,
      "items": [
        {
          "id": "01960e4e-5c5e-7abc-8def-0000000000c1",
          "categoryId": "01960e4e-5c5e-7abc-8def-0000000000b1",
          "name": "Provoleta",
          "description": "Queso provolone a la parrilla con oregano.",
          "price": "1500.00",
          "photoUrl": "https://bucket.s3.amazonaws.com/items/01960e4e-5c5e-7abc-8def-0000000000c1/foto.jpg",
          "isAvailable": true,
          "createdAt": "2026-04-07T20:00:00+00:00"
        }
      ]
    }
  ]
}
```

---

### `PUT /restaurants/{restaurantId}/menus/{menuId}`

**Auth:** Admin (🔐)

**Request body:**
```json
{ "name": "Menú Otoño 2026", "isActive": true }
```

**Response `200`:** Objeto `MenuResponse`.

---

### `DELETE /restaurants/{restaurantId}/menus/{menuId}`

**Auth:** Admin (🔐)

**Response `204`:** Sin cuerpo.

---

### `PATCH /restaurants/{restaurantId}/menus/{menuId}/activate`

Activa este menú y desactiva automáticamente el que estaba activo. Solo puede haber un menú activo por restaurante.

**Auth:** Admin (🔐)

**Request body:** Vacío.

**Response `200`:** Objeto `MenuResponse` con `isActive: true`.

---

## 10. Categorías de Menú

### `GET /menus/{menuId}/categories/`

**Auth:** Ninguna (🔓)

**Response `200`:**
```json
[
  { "id": "01960e4e-5c5e-7abc-8def-0000000000b1", "menuId": "01960e4e-5c5e-7abc-8def-0000000000a1", "name": "Entradas",    "displayOrder": 0, "isActive": true },
  { "id": "01960e4e-5c5e-7abc-8def-0000000000b2", "menuId": "01960e4e-5c5e-7abc-8def-0000000000a1", "name": "Principales", "displayOrder": 1, "isActive": true },
  { "id": "01960e4e-5c5e-7abc-8def-0000000000b3", "menuId": "01960e4e-5c5e-7abc-8def-0000000000a1", "name": "Postres",     "displayOrder": 2, "isActive": true }
]
```

---

### `POST /menus/{menuId}/categories/`

**Auth:** Admin del restaurante dueño del menú (🔐)

**Request body:**
```json
{
  "name": "Bebidas",
  "displayOrder": 3,
  "isActive": true
}
```

| Campo | Tipo | Requerido | Notas |
|---|---|---|---|
| `name` | string | ✅ | Máx 100 caracteres |
| `displayOrder` | int | ❌ | Default: 0. Orden de aparición en el menú. |
| `isActive` | bool | ❌ | Default: `true` |

**Response `201`:** Objeto `MenuCategoryResponse`.

---

### `PUT /menus/{menuId}/categories/{categoryId}`

**Auth:** Admin (🔐)

**Request body:**
```json
{ "name": "Bebidas y Tragos", "displayOrder": 3, "isActive": true }
```

**Response `200`:** Objeto `MenuCategoryResponse` actualizado.

---

### `DELETE /menus/{menuId}/categories/{categoryId}`

**Auth:** Admin (🔐)

**Response `204`:** Sin cuerpo.

---

### `PATCH /menus/{menuId}/categories/reorder`

Reordena todas las categorías del menú en una sola operación.

**Auth:** Admin (🔐)

**Request body:**
```json
{
  "orderedIds": [
    "01960e4e-5c5e-7abc-8def-0000000000b3",
    "01960e4e-5c5e-7abc-8def-0000000000b1",
    "01960e4e-5c5e-7abc-8def-0000000000b2"
  ]
}
```

El servidor asigna `displayOrder = índice_en_el_array` (0, 1, 2...). En el ejemplo, la categoría b3 queda primera (displayOrder 0), la b1 queda segunda, la b2 queda tercera.

**Response `200`:** Array de `MenuCategoryResponse` reordenados.

---

## 11. Ítems de Menú

### `GET /categories/{categoryId}/items/`

**Auth:** Ninguna (🔓)

**Response `200`:** Array de `MenuItemResponse`.

---

### `POST /categories/{categoryId}/items/`

**Auth:** Admin (🔐)

**Request body:**
```json
{
  "name": "Provoleta",
  "description": "Queso provolone a la parrilla con oregano y aceitunas.",
  "price": "1500.00",
  "isAvailable": true
}
```

| Campo | Tipo | Requerido | Validación |
|---|---|---|---|
| `name` | string | ✅ | Máx 150 caracteres |
| `description` | string | ❌ | Máx 2000 caracteres |
| `price` | string | ✅ | Decimal positivo con 2 cifras: `"1500.00"` |
| `isAvailable` | bool | ❌ | Default: `true` |

**Response `201`:** Objeto `MenuItemResponse`.

---

### `GET /items/{itemId}`

**Auth:** Ninguna (🔓)

**Response `200`:** Objeto `MenuItemResponse`.

---

### `PUT /items/{itemId}`

**Auth:** Admin (🔐)

**Request body:** Igual a POST pero todos los campos presentes.

**Response `200`:** Objeto `MenuItemResponse` actualizado.

---

### `DELETE /items/{itemId}`

**Auth:** Admin (🔐)

**Response `204`:** Sin cuerpo.

---

### `POST /items/{itemId}/photo`

Sube o reemplaza la foto de un ítem del menú.

**Auth:** Admin (🔐)

**Request:** `multipart/form-data` con campo `photo`.

**Response `200`:**
```json
{ "photoUrl": "https://bucket.s3.amazonaws.com/items/01960e4e-5c5e-7abc-8def-0000000000c5/abc.jpg" }
```

---

### `PATCH /items/{itemId}/availability`

Activa o desactiva un ítem sin editarlo completo. Útil para "agotado temporalmente".

**Auth:** Admin (🔐)

**Request body:**
```json
{ "isAvailable": false }
```

**Response `200`:** Objeto `MenuItemResponse` con `isAvailable` actualizado.

---

## 12. Pedidos

> No existe delivery. Todos los pedidos son para consumir en el local.

---

### `POST /restaurants/{restaurantId}/orders/`

El cliente crea un pedido. Los precios de cada ítem se toman como snapshot del precio actual al momento del pedido.

**Auth:** Access token (🔑)

**Request body:**
```json
{
  "items": [
    { "menuItemId": "01960e4e-5c5e-7abc-8def-0000000000c1", "quantity": 2, "notes": "Sin sal" },
    { "menuItemId": "01960e4e-5c5e-7abc-8def-0000000000c5", "quantity": 1, "notes": null }
  ],
  "notes": "Mesa cerca de la barra."
}
```

| Campo | Tipo | Requerido | Validación |
|---|---|---|---|
| `items` | array | ✅ | Mín 1 elemento |
| `items[].menuItemId` | string (uuid) | ✅ | Debe existir, estar disponible y pertenecer al menú activo del restaurante |
| `items[].quantity` | int | ✅ | Mín 1 |
| `items[].notes` | string | ❌ | Notas del ítem (ej: "sin sal", "bien cocido") |
| `notes` | string | ❌ | Notas generales del pedido |

**Response `201`:**
```json
{
  "id": "01960e4e-5c5e-7abc-8def-000000000063",
  "restaurantId": "01960e4e-5c5e-7abc-8def-000000000061",
  "restaurantName": "El Gaucho Rojo",
  "userId": "01960e4e-5c5e-7abc-8def-000000000007",
  "status": "PENDING",
  "totalAmount": "4500.00",
  "notes": "Mesa cerca de la barra.",
  "estimatedReadyAt": null,
  "createdAt": "2026-04-19T21:00:00+00:00",
  "items": [
    {
      "id": "01960e4e-5c5e-7abc-8def-0000000000d1",
      "menuItemId": "01960e4e-5c5e-7abc-8def-0000000000c1",
      "menuItemName": "Provoleta",
      "quantity": 2,
      "unitPrice": "1500.00",
      "notes": "Sin sal"
    },
    {
      "id": "01960e4e-5c5e-7abc-8def-0000000000d2",
      "menuItemId": "01960e4e-5c5e-7abc-8def-0000000000c5",
      "menuItemName": "Lomo a la parrilla",
      "quantity": 1,
      "unitPrice": "1500.00",
      "notes": null
    }
  ]
}
```

**Errores:**
| Status | `code` | Cuándo |
|---|---|---|
| `400` | `VALIDATION_ERROR` | Item ID inexistente, no disponible o no pertenece al restaurante |
| `404` | `NOT_FOUND` | El restaurante no tiene menú activo |

---

### `GET /restaurants/{restaurantId}/orders/`

Lista todos los pedidos del restaurante.

**Auth:** Admin (🔐)

**Query params:**

| Parámetro | Tipo | Descripción |
|---|---|---|
| `status` | string | `PENDING`, `CONFIRMED`, `IN_PREPARATION`, `READY`, `COMPLETED`, `CANCELLED` |
| `page` | int | Default: 1 |
| `per_page` | int | Default: 20 |

**Response `200`:** Envelope paginado con array de `OrderResponse`.

---

### `GET /orders/{orderId}`

**Auth:** Access token (🔑). Solo el dueño del pedido o admin del restaurante.

**Response `200`:** Objeto `OrderResponse` completo.

---

### `PATCH /orders/{orderId}/status`

Admin avanza el estado del pedido.

**Auth:** Admin (🔐)

**Request body:**
```json
{
  "status": "IN_PREPARATION",
  "estimatedReadyAt": "2026-04-19T21:30:00+00:00"
}
```

| Campo | Tipo | Requerido | Notas |
|---|---|---|---|
| `status` | string | ✅ | Debe ser una transición válida (ver máquina de estados) |
| `estimatedReadyAt` | string | ❌ | ISO 8601. Relevante cuando `status: "READY"` |

**Transiciones válidas:**
```
PENDING       → CONFIRMED
PENDING       → CANCELLED  (solo admin)
CONFIRMED     → IN_PREPARATION
CONFIRMED     → CANCELLED  (solo admin)
IN_PREPARATION → READY
READY         → COMPLETED
```

**Response `200`:** Objeto `OrderResponse` actualizado.

**Errores:**
| Status | `code` | Cuándo |
|---|---|---|
| `409` | `CONFLICT` | La transición de estado es inválida |

---

### `PATCH /orders/{orderId}/cancel`

El cliente cancela su propio pedido. Solo es posible si el estado es `PENDING`.

**Auth:** Access token (🔑)

**Request body:** Vacío.

**Response `200`:** Objeto `OrderResponse` con `status: "CANCELLED"`.

**Errores:**
| Status | `code` | Cuándo |
|---|---|---|
| `403` | `FORBIDDEN` | No es el dueño del pedido |
| `409` | `CONFLICT` | El pedido ya no está en estado `PENDING` |

---

### `GET /users/{userId}/orders/`

Lista los pedidos del usuario autenticado.

**Auth:** Access token (🔑)

**Query params:** `page`, `per_page`, `status` (opcional).

**Response `200`:** Envelope paginado con array de `OrderResponse`.

---

## 13. Promociones

### `GET /restaurants/{restaurantId}/promotions/`

Lista las promociones **activas** del restaurante. Público.

**Auth:** Ninguna (🔓)

**Response `200`:** Array de `PromotionResponse`.

---

### `GET /promotions/feed`

Feed global de todas las promociones activas en toda la plataforma, ordenadas por `startDate` descendente.

**Auth:** Ninguna (🔓)

**Query params:** `page`, `per_page`.

**Response `200`:** Envelope paginado con array de `PromotionResponse`.

---

### `POST /restaurants/{restaurantId}/promotions/`

**Auth:** Admin (🔐)

**Request body:**
```json
{
  "title": "2x1 en entradas — solo viernes",
  "description": "Todos los viernes de mayo, pedí 2 entradas y pagá 1.",
  "discountType": "PERCENTAGE",
  "discountValue": "50.00",
  "startDate": "2026-05-01",
  "endDate": "2026-05-30",
  "notifyUsers": true,
  "menuItemIds": ["01960e4e-5c5e-7abc-8def-0000000000c1", "01960e4e-5c5e-7abc-8def-0000000000c2", "01960e4e-5c5e-7abc-8def-0000000000c3"]
}
```

| Campo | Tipo | Requerido | Notas |
|---|---|---|---|
| `title` | string | ✅ | Máx 200 caracteres |
| `description` | string | ❌ | Máx 2000 caracteres |
| `discountType` | string | ✅ | `"PERCENTAGE"`, `"FIXED_AMOUNT"` o `"FREE_ITEM"` |
| `discountValue` | string | ✅ | Decimal. Para `PERCENTAGE`: 0–100. Para `FIXED_AMOUNT`: monto. |
| `startDate` | string | ✅ | `YYYY-MM-DD` |
| `endDate` | string | ✅ | `YYYY-MM-DD`. Debe ser >= `startDate`. |
| `notifyUsers` | bool | ❌ | Default: `false`. Si `true`, notifica por email a todos los usuarios suscritos. |
| `menuItemIds` | string[] (uuid[]) | ❌ | IDs de ítems a los que aplica la promo. Si es vacío o se omite, aplica a todo el menú. |

**Response `201`:** Objeto `PromotionResponse`.

---

### `GET /restaurants/{restaurantId}/promotions/{promotionId}`

**Auth:** Ninguna (🔓)

**Response `200`:**
```json
{
  "id": "01960e4e-5c5e-7abc-8def-0000000000e5",
  "restaurantId": "01960e4e-5c5e-7abc-8def-000000000061",
  "restaurantName": "El Gaucho Rojo",
  "title": "2x1 en entradas — solo viernes",
  "description": "...",
  "discountType": "PERCENTAGE",
  "discountValue": "50.00",
  "startDate": "2026-05-01",
  "endDate": "2026-05-30",
  "isActive": true,
  "notifyUsers": true,
  "createdAt": "2026-04-19T14:30:00+00:00",
  "items": [
    { "id": "01960e4e-5c5e-7abc-8def-0000000000c1", "categoryId": "01960e4e-5c5e-7abc-8def-0000000000b1", "name": "Provoleta", "price": "1500.00", ... }
  ]
}
```

> `items` es un array vacío si la promoción aplica a todo el menú.

---

### `PUT /restaurants/{restaurantId}/promotions/{promotionId}`

**Auth:** Admin (🔐)

**Request body:** Igual al de POST.

**Response `200`:** Objeto `PromotionResponse` actualizado.

---

### `PATCH /restaurants/{restaurantId}/promotions/{promotionId}/deactivate`

**Auth:** Admin (🔐)

**Request body:** Vacío.

**Response `200`:** `PromotionResponse` con `isActive: false`.

---

### `PATCH /restaurants/{restaurantId}/promotions/{promotionId}/activate`

**Auth:** Admin (🔐)

**Request body:** Vacío.

**Response `200`:** `PromotionResponse` con `isActive: true`.

---

### `DELETE /restaurants/{restaurantId}/promotions/{promotionId}`

**Auth:** Admin (🔐)

**Response `204`:** Sin cuerpo.

---

## 14. Perfil de Usuario

Los recursos de perfil siguen **REST por recurso**: el path incluye el **`userId`** (UUID string), no el alias `/me`.

**Regla de autorización (backend implementado):** el `userId` de la URL debe ser **exactamente el mismo** que el identificador del usuario en el JWT (claim `sub` / el `id` devuelto en login). Si pedís el perfil de **otro** UUID, la API responde **`403 FORBIDDEN`** con `code: "FORBIDDEN"`, aunque el token sea válido.

Tras `POST /auth/login` o `POST /auth/register`, usá `user.id` de la respuesta como segmento de URL en todas las llamadas de esta sección.

---

### `GET /users/{userId}`

**Auth:** Access token (🔑)

**Path:** `userId` — UUID del usuario; **debe coincidir con el JWT**.

**Response `200`:**
```json
{
  "id": "01960e4e-5c5e-7abc-8def-000000000007",
  "email": "juan.garcia@ejemplo.com",
  "name": "Juan",
  "surname": "García",
  "role": "RESTAURANT_ADMIN",
  "createdAt": "2026-04-07T19:00:00+00:00"
}
```

**Errores:**
| Status | `code` | Cuándo |
|---|---|---|
| `403` | `FORBIDDEN` | `userId` de la URL ≠ usuario del JWT |
| `404` | `NOT_FOUND` | Usuario inexistente (mismo `userId` que el JWT) |

---

### `PUT /users/{userId}`

Actualiza nombre y apellido. Misma regla de path que el GET.

**Auth:** Access token (🔑)

**Request body:**
```json
{ "name": "Juan Pablo", "surname": "García" }
```

| Campo | Tipo | Requerido | Validación |
|---|---|---|---|
| `name` | string | ✅ | Máx 100 caracteres, solo letras/acentos/ñ/guiones/espacios |
| `surname` | string | ✅ | Igual que `name` |

**Response `200`:** `UserProfileResponse` actualizado.

**Errores:** `403` si el `userId` no coincide con el JWT.

---

### `PUT /users/{userId}/password`

**Auth:** Access token (🔑)

**Request body:**
```json
{
  "currentPassword": "ContraseñaVieja1",
  "newPassword": "ContraseñaNueva2"
}
```

| Campo | Tipo | Requerido | Validación |
|---|---|---|---|
| `currentPassword` | string | ✅ | Contraseña actual del usuario |
| `newPassword` | string | ✅ | Mín 8, máx 128 caracteres |

**Response `200`:**
```json
{ "message": "Contraseña actualizada correctamente." }
```

**Errores:**
| Status | `code` | Cuándo |
|---|---|---|
| `401` | `UNAUTHORIZED` | `currentPassword` incorrecto |
| `403` | `FORBIDDEN` | `userId` de la URL ≠ usuario del JWT |

---

### `GET /users/{userId}/restaurants/`

Lista todos los restaurantes que administra el usuario.

**Auth:** Access token (🔑). Path `userId` = JWT.

**Response `200`:** Array de `RestaurantResponse` completos (igual al objeto de `GET /restaurants/`).

> **Backend actual:** este endpoint **aún no está expuesto** en el código del API (existen `GET/PUT /users/{userId}` y `PUT /users/{userId}/password`). Hasta que se implemente, el frontend puede derivar la lista desde otros flujos o mantener estado local tras crear restaurantes.

---

## 15. Preferencias de Notificación

Misma convención que §14: **`userId` en el path = usuario del JWT** (cuando estos endpoints existan en backend).

### `GET /users/{userId}/notification-preferences/`

Lista las preferencias de notificación del usuario para cada restaurante que sigue.

**Auth:** Access token (🔑)

**Response `200`:**
```json
[
  {
    "restaurantId": "01960e4e-5c5e-7abc-8def-000000000061",
    "restaurantName": "El Gaucho Rojo",
    "receivePromotions": true,
    "receiveOrderUpdates": true,
    "receiveReservationReminders": true
  }
]
```

---

### `PUT /users/{userId}/notification-preferences/{restaurantId}`

Actualiza las preferencias para un restaurante específico. Si no existía una preferencia, se crea.

**Auth:** Access token (🔑)

**Request body:**
```json
{
  "receivePromotions": false,
  "receiveOrderUpdates": true,
  "receiveReservationReminders": true
}
```

Todos los campos son requeridos.

**Response `200`:** Objeto `NotificationPreferenceResponse` actualizado.

---

## 16. Analytics

Todos los endpoints de analytics requieren ser admin del restaurante (🔐) y aceptan los query params `start` y `end` en formato `YYYY-MM-DD`.

---

### `GET /restaurants/{restaurantId}/analytics/occupancy`

**Query params:** `start` (✅), `end` (✅)

**Response `200`:**
```json
{
  "restaurantId": "01960e4e-5c5e-7abc-8def-000000000061",
  "period": { "start": "2026-04-01", "end": "2026-04-30" },
  "totalReservations": 120,
  "totalCovers": 480,
  "occupancyByDay": [
    { "date": "2026-04-01", "reservations": 4, "covers": 16, "occupancyRate": 0.80 }
  ]
}
```

---

### `GET /restaurants/{restaurantId}/analytics/orders`

**Query params:** `start`, `end`

**Response `200`:**
```json
{
  "restaurantId": "01960e4e-5c5e-7abc-8def-000000000061",
  "period": { "start": "2026-04-01", "end": "2026-04-30" },
  "totalOrders": 340,
  "totalRevenue": "850000.00",
  "averageOrderValue": "2500.00",
  "ordersByStatus": [
    { "status": "COMPLETED", "count": 310 },
    { "status": "CANCELLED", "count": 30 }
  ],
  "revenueByDay": [
    { "date": "2026-04-01", "revenue": "28000.00", "orders": 11 }
  ]
}
```

---

### `GET /restaurants/{restaurantId}/analytics/popular-items`

**Query params:** `start`, `end`, `limit` (default: 10)

**Response `200`:**
```json
{
  "restaurantId": "01960e4e-5c5e-7abc-8def-000000000061",
  "period": { "start": "2026-04-01", "end": "2026-04-30" },
  "items": [
    { "menuItemId": "01960e4e-5c5e-7abc-8def-0000000000c3", "name": "Lomo a la parrilla", "quantitySold": 210, "revenue": "315000.00", "rank": 1 }
  ]
}
```

---

### `GET /restaurants/{restaurantId}/analytics/promotions`

**Query params:** `start`, `end`

**Response `200`:**
```json
{
  "restaurantId": "01960e4e-5c5e-7abc-8def-000000000061",
  "period": { "start": "2026-04-01", "end": "2026-04-30" },
  "promotions": [
    { "promotionId": "01960e4e-5c5e-7abc-8def-0000000000e5", "title": "2x1 en entradas", "ordersWithPromotion": 45, "revenueImpact": "67500.00", "discountGiven": "33750.00" }
  ]
}
```

---

### `GET /restaurants/{restaurantId}/analytics/peak-hours`

**Query params:** `start`, `end`

**Response `200`:**
```json
{
  "restaurantId": "01960e4e-5c5e-7abc-8def-000000000061",
  "period": { "start": "2026-04-01", "end": "2026-04-30" },
  "reservationsByHour": [
    { "hour": 20, "count": 95 },
    { "hour": 21, "count": 72 }
  ],
  "ordersByHour": [
    { "hour": 21, "count": 130 }
  ]
}
```

---

## 17. Flujos de Usuario Completos

Esta sección describe exactamente qué llamadas hace el frontend, en qué orden, con qué datos y cómo reacciona a cada respuesta.

---

### Flujo 1 — Registro de nuevo usuario

**Actor:** Visitante no autenticado  
**Pantalla:** Formulario de registro

**Pasos:**

1. El usuario completa el formulario: email, contraseña, nombre, apellido.
2. El frontend valida localmente:
   - Email con formato válido.
   - Contraseña ≥ 8 caracteres.
   - Nombre y apellido solo letras/acentos/guiones.
3. Al enviar: `POST /auth/register` con los 4 campos.
4. **Si `201`:** Guardar `accessToken` en memoria y `refreshToken` en `localStorage`. Guardar el objeto `user` en el store global. Redirigir al home o dashboard según `user.role`.
5. **Si `409` (`CONFLICT`):** Mostrar error "Este email ya está registrado. ¿Querés iniciar sesión?".
6. **Si `400` (`VALIDATION_ERROR`):** Mostrar el error del campo correspondiente dentro del formulario.

---

### Flujo 2 — Login

**Actor:** Usuario registrado  
**Pantalla:** Formulario de login

**Pasos:**

1. El usuario ingresa email y contraseña.
2. `POST /auth/login`.
3. **Si `200`:** Mismo almacenamiento que en registro. Redirigir según `user.role`:
   - `CUSTOMER` → home / búsqueda de restaurantes
   - `RESTAURANT_ADMIN` → dashboard de sus restaurantes
   - `SUPER_ADMIN` → panel de administración global
4. **Si `401`:** Mostrar "Email o contraseña incorrectos." (no indicar cuál de los dos es incorrecto).
5. **Si `400`:** Mostrar error del campo.

---

### Flujo 3 — Refresh automático de token (interceptor)

**Actor:** Cualquier usuario con sesión activa  
**Cuándo se dispara:** Automáticamente cuando cualquier llamada autenticada devuelve `401`

**Pasos:**

1. El interceptor detecta `401` en cualquier request.
2. Verificar que no estemos ya en proceso de refresh (evitar loops).
3. Leer `refreshToken` de `localStorage`.
4. Si no existe: redirigir a login.
5. `POST /auth/refresh` con `Authorization: Bearer <refreshToken>`.
6. **Si `200`:** Actualizar el `accessToken` en memoria. Reintentar el request original fallido con el nuevo token. Devolver la respuesta al caller como si nada hubiera pasado.
7. **Si `401`:** El refresh token expiró. Limpiar `accessToken`, `refreshToken` y el estado de usuario del store. Redirigir a login con mensaje "Tu sesión expiró. Por favor iniciá sesión nuevamente."

---

### Flujo 4 — Recuperación de sesión al recargar la página

**Actor:** Usuario que tenía sesión activa y recargó la página

**Pasos:**

1. Al inicializar la app, leer `refreshToken` de `localStorage`.
2. Si no existe: el usuario no está logueado, mostrar app en modo público.
3. Si existe: `POST /auth/refresh`.
4. **Si `200`:** Guardar nuevo `accessToken` en memoria. Luego `GET /users/{userId}` con el `userId` del objeto `user` devuelto en login/register (debe coincidir con el JWT) para recuperar el perfil y restaurar el store. Mostrar la app como si el usuario estuviera logueado.
5. **Si `401`:** Limpiar `localStorage`, mostrar app en modo público.

---

### Flujo 5 — Búsqueda y filtrado de restaurantes

**Actor:** Usuario **autenticado** (el backend actual exige JWT para `GET /restaurants/`; ver §1.7 Autenticación en rutas de restaurantes)  
**Pantalla:** Listado/búsqueda de restaurantes

**Pasos:**

1. Asegurar sesión válida (`accessToken`). Si no hay login, redirigir o mostrar mensaje según producto.
2. Cargar datos de filtros cuando existan endpoints de lookup (§3); si aún no están desplegados, usar datos embebidos o fixtures.
   - `GET /cuisines/` → tipos de cocina
   - `GET /price-ranges/` → selector de precio (`label`: $, $$, …)
   - `GET /countries/` → país → `GET /countries/{countryId}/provinces/` → `GET /provinces/{provinceId}/cities/` → `GET /cities/{cityId}/neighbourhoods/`
3. El usuario aplica filtros y/o nombre.
4. Llamar `GET /restaurants/` con query params en **camelCase** y UUIDs como strings:
   - Ejemplo: `GET /restaurants/?name=gaucho&cityId=01960e4e-5c5e-7abc-8def-000000000041&priceRangeId=01960e4e-5c5e-7abc-8def-000000000012&cuisineTypeIds=01960e4e-5c5e-7abc-8def-000000000001&cuisineTypeIds=01960e4e-5c5e-7abc-8def-000000000003&page=1&perPage=20`
5. Mostrar `data[]`. Cada ítem trae `cityId`, `priceRangeId`, `cuisineTypeIds`, etc.; resolver etiquetas con el cache de lookup o mapas locales.
6. Paginación: `total`, `page`, `perPage`.
7. Al limpiar filtros: `GET /restaurants/?page=1&perPage=20` (o sin query).
8. Click en un restaurante: navegar al detalle (`GET /restaurants/{restaurantId}` con el mismo token).

---

### Flujo 6 — Vista detallada de un restaurante

**Actor:** Usuario autenticado (JWT requerido en la implementación actual)  
**Pantalla:** Perfil del restaurante

**Pasos:**

1. `GET /restaurants/{restaurantId}` con `Authorization: Bearer` → mostrar nombre, foto, descripción, `cityId` / `neighbourhoodId` / `priceRangeId`, `cuisineTypeIds` (enlazar con datos de lookup para nombres).
2. En paralelo:
   - `GET /restaurants/{restaurantId}/business-hours/` → mostrar horarios.
   - `GET /restaurants/{restaurantId}/menus/` → si existe menú activo, mostrar botón "Ver menú".
   - `GET /restaurants/{restaurantId}/promotions/` → si hay promociones activas, mostrar sección de promos.
3. Si el usuario quiere ver el menú completo: `GET /restaurants/{restaurantId}/menus/{menuId}` (el menú con `isActive: true`).

---

### Flujo 7 — Crear reserva (cliente)

**Actor:** Usuario autenticado como `CUSTOMER` o `RESTAURANT_ADMIN`  
**Pantalla:** Formulario de reserva dentro del perfil del restaurante

**Pasos:**

1. El usuario selecciona fecha y cantidad de personas.
2. `GET /restaurants/{restaurantId}/availability/?date=YYYY-MM-DD&party_size=N`
3. Mostrar los slots:
   - Los slots con `isAvailable: true` → botón activo mostrando la hora.
   - Los slots con `isAvailable: false` → mostrar la hora pero deshabilitado/tachado.
   - Si `tableAssignment.isJoined: true` → mostrar indicador de que se unirán mesas.
4. El usuario selecciona un slot disponible y opcionalmente escribe una nota.
5. `POST /restaurants/{restaurantId}/reservations/` con `{ partySize, date, timeSlot, notes }`.
6. **Si `201`:** Mostrar pantalla de confirmación con el código `confirmationCode`, las mesas asignadas y los datos del turno. El sistema envía un email de confirmación automáticamente.
7. **Si `409` (`CONFLICT`):** El slot fue tomado mientras el usuario eligió (race condition). Mostrar "Este horario ya no está disponible. Por favor elegí otro." y recargar la disponibilidad.
8. **Si `401`:** Redirigir a login con mensaje "Necesitás iniciar sesión para hacer una reserva."

---

### Flujo 8 — Consultar reserva por código (sin login)

**Actor:** Cualquier persona con el link del email de confirmación  
**URL de ejemplo:** `https://app.abricot.com/reservas?code=ABC12345`

**Pasos:**

1. Al cargar la página, leer `code` del query param de la URL.
2. `GET /reservations/lookup?code=ABC12345`
3. **Si `200`:** Mostrar los detalles de la reserva: restaurante, fecha, hora, personas, mesas, estado.
4. Si `status: "CONFIRMED"`, mostrar opción "Cancelar reserva". Al hacer click:
   - Pedir confirmación al usuario.
   - Si el usuario no está logueado: mostrar formulario para confirmar nombre/email y pedir al backend que verifique identidad (fuera del scope del MVP) o simplemente redirigir a login.
5. **Si `404`:** Mostrar "No encontramos una reserva con ese código."

---

### Flujo 9 — Cancelar reserva (cliente)

**Actor:** Usuario autenticado con una reserva confirmada  
**Pantalla:** Historial de reservas o detalle de una reserva

**Pasos:**

1. `GET /users/{userId}/reservations/` (mismo `userId` que el JWT) → mostrar lista con estado de cada reserva.
2. El usuario hace click en "Cancelar" en una reserva con `status: "CONFIRMED"`.
3. Mostrar diálogo de confirmación con campo de motivo opcional.
4. `PATCH /reservations/{reservationId}/cancel` con `{ reason: "..." }`.
5. **Si `200`:** Actualizar el estado de la reserva en la UI a "CANCELADA". Mostrar mensaje de éxito.
6. **Si `409`:** La reserva ya no está en estado cancelable. Actualizar la UI con el estado actual.

---

### Flujo 10 — Crear restaurante (admin — primer restaurante o nuevo restaurante adicional)

**Actor:** Usuario con rol **`RESTAURANT_ADMIN`** o **`SUPER_ADMIN`** (requisito del `POST /restaurants/` actual)  
**Pantalla:** Formulario "Crear restaurante"

**Pasos:**

1. Cargar datos de lookup cuando existan endpoints (§3); si no, usar listas locales de ciudades / cocinas / rangos con **UUID** coherentes con la BD.
2. Jerarquía ubicación: país → provincias → ciudades → barrios (opcional), igual que en el flujo 5.
3. El usuario completa campos obligatorios (`name`, `address`, `phone`, `cityId`) y opcionales (`neighbourhoodId`, `priceRangeId`, `cuisineTypeIds[]`, `email`, `description`). Todos los IDs como **strings UUID**.
4. `POST /restaurants/` con el JSON en camelCase (sin `allowTableJoining` ni `defaultSlotDurationMinutes` en el body actual).
5. **Si `201`:** actualizar perfil con `GET /users/{userId}` si el rol o los datos cambiaron; redirigir al dashboard del restaurante.
6. **Si `403`:** el usuario no tiene rol permitido para crear restaurantes.
7. **Si validación falla:** revisar mensajes `400` / campos del schema.

---

### Flujo 11 — Configurar mesas del restaurante (admin)

**Actor:** Admin del restaurante  
**Pantalla:** Panel de administración → sección "Mesas"

#### Opción A: Carga masiva inicial

1. El admin elige "Crear mesas en lote".
2. Completa grupos: ej. `20 mesas de 2 personas (unibles)` + `10 mesas de 4 personas (no unibles)`.
3. `POST /restaurants/{restaurantId}/tables/bulk` con `{ groups: [...] }`.
4. **Si `201`:** Mostrar la lista de mesas creadas. La numeración fue asignada automáticamente.

#### Opción B: Mesa individual

1. El admin elige "Agregar mesa".
2. Completa: número, capacidad, nombre descriptivo (opcional), ¿es unible?
3. `POST /restaurants/{restaurantId}/tables/` con los campos.
4. **Si `409`:** "Ya existe una mesa con ese número. Usá uno distinto."

#### Editar mesa existente

1. `GET /restaurants/{restaurantId}/tables/` → mostrar lista.
2. El admin edita una mesa → `PUT /restaurants/{restaurantId}/tables/{tableId}`.
3. Para desactivar temporalmente: `PUT` con `isActive: false`.

#### Eliminar mesa

1. `DELETE /restaurants/{restaurantId}/tables/{tableId}`.
2. **Si `409`:** "Esta mesa tiene reservas futuras confirmadas. Primero cancelalas o desactivá la mesa."

---

### Flujo 12 — Configurar horarios de negocio (admin)

**Actor:** Admin del restaurante  
**Pantalla:** Panel de administración → "Horarios"

**Pasos:**

1. `GET /restaurants/{restaurantId}/business-hours/` → mostrar los 7 días con sus horarios actuales.
2. El admin edita los horarios con un picker de horas para `opensAt` y `closesAt`.
3. Para días cerrados: toggle "Cerrado" activa `isClosed: true` y oculta los pickers.
4. Al guardar: `PUT /restaurants/{restaurantId}/business-hours/` con el array de 7 días.
5. **Si `200`:** Mostrar confirmación "Horarios actualizados".

---

### Flujo 13 — Crear reserva como admin (teléfono o evento)

**Actor:** Admin del restaurante  
**Pantalla:** Panel de administración → "Nueva reserva"

**Pasos:**

1. El admin selecciona fecha y cantidad de personas.
2. `GET /restaurants/{restaurantId}/availability/?date=YYYY-MM-DD&party_size=N` → mostrar slots disponibles.
3. El admin selecciona slot, elige el origen (`PHONE` o `EVENT`).
4. Completa los datos del grupo:
   - Si el grupo tiene cuenta en Abricot: buscar por email y obtener `userId`. Enviar `userId` en el body.
   - Si no tiene cuenta: completar `guestName` (requerido), `guestPhone` y `guestEmail` opcionales.
5. `POST /restaurants/{restaurantId}/reservations/admin` con todos los datos.
6. **Si `201`:** Mostrar confirmación con `confirmationCode`. Si se proveyó `guestEmail`, el sistema envía confirmación por email al huésped automáticamente.
7. **Si `409`:** "No hay disponibilidad para ese horario."

---

### Flujo 14 — Gestionar reservas del día (admin)

**Actor:** Admin del restaurante  
**Pantalla:** Panel de reservas del día

**Pasos:**

1. `GET /restaurants/{restaurantId}/reservations/?date_from=HOY&date_to=HOY&status=CONFIRMED`
2. Mostrar lista de reservas del día con nombre del cliente/huésped, hora, personas, mesas.

#### Completar turno:
1. Al finalizar el turno: `PATCH /reservations/{reservationId}/complete`.
2. Actualizar la UI.

#### Marcar no-show:
1. `PATCH /reservations/{reservationId}/no-show`.
2. Las mesas quedan liberadas para ese slot.

#### Reasignar mesas (reorganizar el salón):
1. Ver la disponibilidad de mesas: `GET /restaurants/{restaurantId}/tables/`.
2. `PATCH /reservations/{reservationId}/reassign-tables` con los nuevos `tableIds`.

---

### Flujo 15 — Crear y gestionar el menú (admin)

**Actor:** Admin del restaurante

#### Crear menú:
1. `POST /restaurants/{restaurantId}/menus/` con `{ name: "Menú Primavera 2026" }`.
2. Agregar categorías: `POST /menus/{menuId}/categories/` para "Entradas", "Principales", "Postres", etc.
3. Agregar ítems a cada categoría: `POST /categories/{categoryId}/items/` con nombre, descripción y precio.
4. Subir foto de cada ítem: `POST /items/{itemId}/photo` con `multipart/form-data`.
5. Activar el menú: `PATCH /restaurants/{restaurantId}/menus/{menuId}/activate`.

#### Reordenar categorías:
1. El admin arrastra las categorías en la UI.
2. Al soltar: `PATCH /menus/{menuId}/categories/reorder` con el array de IDs en el nuevo orden.

#### Marcar ítem como agotado:
1. `PATCH /items/{itemId}/availability` con `{ isAvailable: false }`.

---

### Flujo 16 — Crear y seguir un pedido (cliente)

**Actor:** Usuario autenticado  
**Pantalla:** Menú del restaurante

**Pasos:**

1. `GET /restaurants/{restaurantId}/menus/` → obtener el menú con `isActive: true`.
2. `GET /restaurants/{restaurantId}/menus/{menuId}` → mostrar el menú completo con categorías e ítems.
3. El usuario agrega ítems al carrito (gestión local en el frontend, sin llamadas al backend).
4. Al confirmar el pedido: `POST /restaurants/{restaurantId}/orders/` con el array de ítems.
5. **Si `201`:** Mostrar confirmación con número de pedido. Status inicial: `PENDING`.
6. El frontend puede sondear el estado del pedido periódicamente: `GET /orders/{orderId}`.
   - O usar WebSocket/SSE si el backend los soporta en el futuro.

**Pantalla de seguimiento:**
- `PENDING` → "Tu pedido fue recibido. Esperando confirmación del restaurante."
- `CONFIRMED` → "El restaurante confirmó tu pedido."
- `IN_PREPARATION` → "Tu pedido está en preparación."
- `READY` → "¡Tu pedido está listo para retirar!"
- `COMPLETED` → "Pedido entregado. ¡Buen provecho!"
- `CANCELLED` → "El pedido fue cancelado."

#### El cliente cancela (solo si PENDING):
1. `PATCH /orders/{orderId}/cancel`.
2. **Si `409`:** "Tu pedido ya entró en preparación y no puede cancelarse."

---

### Flujo 17 — Gestionar pedidos del día (admin)

**Actor:** Admin del restaurante  
**Pantalla:** Panel de pedidos (tiempo real / lista)

**Pasos:**

1. `GET /restaurants/{restaurantId}/orders/?status=PENDING` → mostrar nuevos pedidos.
2. Para cada pedido nuevo, el admin puede:
   - Confirmar: `PATCH /orders/{orderId}/status` con `{ status: "CONFIRMED" }`.
   - Rechazar: `PATCH /orders/{orderId}/status` con `{ status: "CANCELLED" }`.
3. Al pasar a cocina: `PATCH /orders/{orderId}/status` con `{ status: "IN_PREPARATION" }`.
4. Al estar listo: `PATCH /orders/{orderId}/status` con `{ status: "READY", estimatedReadyAt: "..." }`.
5. Al entregarse: `PATCH /orders/{orderId}/status` con `{ status: "COMPLETED" }`.

---

### Flujo 18 — Crear y publicar una promoción (admin)

**Actor:** Admin del restaurante

**Pasos:**

1. `GET /restaurants/{restaurantId}/menus/{menuId}` → para listar ítems y poder seleccionar a cuáles aplica la promo.
2. El admin completa el formulario: título, tipo de descuento, valor, fechas, ítems específicos (o ninguno = todo el menú).
3. Si elige notificar usuarios: el campo `notifyUsers: true` hace que el sistema envíe un email a todos los usuarios que siguen el restaurante con `receivePromotions: true`.
4. `POST /restaurants/{restaurantId}/promotions/`.
5. **Si `201`:** Mostrar la promoción activa en el panel.

#### Dar de baja una promo:
1. `PATCH /restaurants/{restaurantId}/promotions/{promotionId}/deactivate`.
2. La promo deja de aparecer en `GET /restaurants/{restaurantId}/promotions/` (solo muestra activas).

---

### Flujo 19 — Ver y gestionar los restaurantes propios (admin con múltiples restaurantes)

**Actor:** Admin con varios restaurantes

**Pasos:**

1. `GET /users/{userId}/restaurants/` → devuelve todos los restaurantes que administra el usuario.
2. Mostrar lista de tarjetas de restaurantes. Cada una con acceso a su panel de administración.
3. Al crear un nuevo restaurante adicional: flujo 10 (desde cualquier punto de la app).
4. El nuevo restaurante aparece automáticamente en `GET /users/{userId}/restaurants/` sin necesidad de hacer nada más.

---

### Flujo 20 — Ver analytics del restaurante (admin)

**Actor:** Admin del restaurante  
**Pantalla:** Dashboard de analytics

**Pasos:**

1. El admin selecciona el rango de fechas con un date range picker (`start`, `end`).
2. Al aplicar el rango, hacer 5 llamadas en paralelo:
   - `GET /restaurants/{restaurantId}/analytics/occupancy?start=...&end=...`
   - `GET /restaurants/{restaurantId}/analytics/orders?start=...&end=...`
   - `GET /restaurants/{restaurantId}/analytics/popular-items?start=...&end=...&limit=10`
   - `GET /restaurants/{restaurantId}/analytics/promotions?start=...&end=...`
   - `GET /restaurants/{restaurantId}/analytics/peak-hours?start=...&end=...`
3. Renderizar cada sección con los datos:
   - Ocupación: gráfico de barras por día con `covers` y `occupancyRate`.
   - Revenue: gráfico de líneas de `revenueByDay`.
   - Ítems populares: ranking con `quantitySold` y `revenue`.
   - Horas pico: heatmap o gráfico de barras con `reservationsByHour` y `ordersByHour`.

---

### Flujo 21 — Gestionar preferencias de notificación (cliente)

**Actor:** Usuario autenticado  
**Pantalla:** Configuración de cuenta → "Notificaciones"

**Pasos:**

1. `GET /users/{userId}/notification-preferences/` → mostrar lista de restaurantes que el usuario "sigue" y sus preferencias.
2. El usuario activa/desactiva toggles para cada preferencia de cada restaurante.
3. Al cambiar un toggle: `PUT /users/{userId}/notification-preferences/{restaurantId}` con los 3 campos (enviar todos, incluso los que no cambiaron).

> **Nota:** Una preferencia se crea automáticamente la primera vez que el usuario realiza un pedido o reserva en un restaurante. Hasta ese momento, el restaurante no aparece en la lista.

---

### Flujo 22 — Feed global de promociones (público)

**Actor:** Cualquier visitante

**Pasos:**

1. `GET /promotions/feed?page=1&per_page=20` → mostrar todas las promociones activas de la plataforma.
2. Mostrar tarjetas con restaurante, título, tipo de descuento, fechas.
3. Al hacer click en una promo: navegar al perfil del restaurante (`GET /restaurants/{restaurantId}`).
4. La paginación permite cargar más con `page=2`, `page=3`, etc.

---

## Apéndice — Resumen de Valores Posibles

### `role` de usuario
| Valor | Descripción |
|---|---|
| `CUSTOMER` | Usuario final |
| `RESTAURANT_ADMIN` | Administrador de al menos un restaurante |
| `SUPER_ADMIN` | Staff de Abricot |

### `source` de reserva
| Valor | Descripción |
|---|---|
| `ONLINE` | Reserva hecha por el cliente desde la app |
| `PHONE` | Creada por el admin para un llamado telefónico |
| `EVENT` | Creada por el admin para un evento o grupo grande |

### `status` de reserva
| Valor | Descripción |
|---|---|
| `CONFIRMED` | Activa, mesas asignadas |
| `CANCELLED` | Cancelada por cliente o admin |
| `COMPLETED` | Turno finalizado |
| `NO_SHOW` | El grupo no se presentó |

### `status` de pedido
| Valor | Descripción |
|---|---|
| `PENDING` | Recibido, esperando confirmación del restaurante |
| `CONFIRMED` | Confirmado por el restaurante |
| `IN_PREPARATION` | En cocina |
| `READY` | Listo para retirar |
| `COMPLETED` | Entregado o retirado |
| `CANCELLED` | Cancelado |

### `discountType` de promoción
| Valor | Descripción |
|---|---|
| `PERCENTAGE` | Descuento porcentual (ej: 20%) |
| `FIXED_AMOUNT` | Monto fijo de descuento (ej: $500) |
| `FREE_ITEM` | Ítem gratis con la compra |
