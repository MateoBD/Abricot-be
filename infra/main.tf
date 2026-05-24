resource "aws_cognito_user_pool" "main" {
  name = "${local.name_prefix}-user-pool"

  username_attributes      = ["email"]
  auto_verified_attributes = ["email"]

  password_policy {
    minimum_length    = 8
    require_lowercase = true
    require_numbers   = true
    require_symbols   = false
    require_uppercase = true
  }
}

resource "aws_cognito_user_pool_client" "spa" {
  name         = "${local.name_prefix}-spa-client"
  user_pool_id = aws_cognito_user_pool.main.id

  prevent_user_existence_errors        = "ENABLED"
  allowed_oauth_flows_user_pool_client = true
  allowed_oauth_flows                  = ["code"]
  allowed_oauth_scopes                 = local.cognito_scopes
  callback_urls                        = local.callback_urls
  logout_urls                          = local.logout_urls
  supported_identity_providers         = ["COGNITO"]

  explicit_auth_flows = [
    "ALLOW_REFRESH_TOKEN_AUTH",
    "ALLOW_USER_SRP_AUTH",
  ]
}

resource "aws_cognito_user_pool_domain" "main" {
  domain       = local.cognito_domain_prefix
  user_pool_id = aws_cognito_user_pool.main.id
}

resource "aws_apigatewayv2_api" "http" {
  name          = "${local.name_prefix}-http-api"
  protocol_type = "HTTP"

  cors_configuration {
    allow_headers = ["Authorization", "Content-Type"]
    allow_methods = ["GET", "POST", "PUT", "PATCH", "OPTIONS"]
    allow_origins = distinct([local.frontend_base_url, "http://localhost:5173"])
    max_age       = 300
  }
}

resource "aws_apigatewayv2_stage" "default" {
  api_id      = aws_apigatewayv2_api.http.id
  name        = "$default"
  auto_deploy = true
}

resource "aws_apigatewayv2_authorizer" "cognito" {
  api_id           = aws_apigatewayv2_api.http.id
  authorizer_type  = "JWT"
  identity_sources = ["$request.header.Authorization"]
  name             = "${local.name_prefix}-cognito-authorizer"

  jwt_configuration {
    audience = [aws_cognito_user_pool_client.spa.id]
    issuer   = "https://cognito-idp.${var.aws_region}.amazonaws.com/${aws_cognito_user_pool.main.id}"
  }
}

data "archive_file" "lambda" {
  for_each = local.lambda_functions

  type        = "zip"
  source_dir  = each.value.source_dir
  excludes    = each.value.excludes
  output_path = "${path.module}/${each.key}.zip"
}

resource "aws_lambda_function" "this" {
  for_each = local.lambda_functions

  function_name    = "${local.name_prefix}-${replace(each.key, "_", "-")}"
  filename         = data.archive_file.lambda[each.key].output_path
  handler          = each.value.handler
  role             = local.lab_role_arn
  runtime          = local.lambda_runtime
  source_code_hash = data.archive_file.lambda[each.key].output_base64sha256
  timeout          = each.value.timeout

  dynamic "environment" {
    for_each = length(lookup(local.lambda_environment, each.key, {})) > 0 ? [1] : []
    content {
      variables = local.lambda_environment[each.key]
    }
  }

  dynamic "vpc_config" {
    for_each = each.value.vpc_enabled ? [1] : []
    content {
      subnet_ids         = each.value.subnet_ids
      security_group_ids = each.value.security_group_ids
    }
  }
}

resource "aws_apigatewayv2_integration" "lambda" {
  for_each = local.api_lambda_functions

  api_id                 = aws_apigatewayv2_api.http.id
  integration_type       = "AWS_PROXY"
  integration_uri        = aws_lambda_function.this[each.key].invoke_arn
  payload_format_version = "2.0"
}

resource "aws_apigatewayv2_route" "health" {
  api_id    = aws_apigatewayv2_api.http.id
  route_key = "GET /health"
  target    = "integrations/${aws_apigatewayv2_integration.lambda["health"].id}"
}

resource "aws_apigatewayv2_route" "callback" {
  api_id    = aws_apigatewayv2_api.http.id
  route_key = "GET /callback"
  target    = "integrations/${aws_apigatewayv2_integration.lambda["users_service"].id}"
}

resource "aws_apigatewayv2_route" "auth_test" {
  api_id             = aws_apigatewayv2_api.http.id
  route_key          = "GET /auth-test"
  target             = "integrations/${aws_apigatewayv2_integration.lambda["users_service"].id}"
  authorization_type = "JWT"
  authorizer_id      = aws_apigatewayv2_authorizer.cognito.id
}

resource "aws_apigatewayv2_route" "users_post" {
  count = local.users_routes_enabled ? 1 : 0

  api_id             = aws_apigatewayv2_api.http.id
  route_key          = "POST /users"
  target             = "integrations/${aws_apigatewayv2_integration.lambda["users_service"].id}"
  authorization_type = "JWT"
  authorizer_id      = aws_apigatewayv2_authorizer.cognito.id
}

resource "aws_apigatewayv2_route" "users_get" {
  count = local.users_routes_enabled ? 1 : 0

  api_id             = aws_apigatewayv2_api.http.id
  route_key          = "GET /users/{userId}"
  target             = "integrations/${aws_apigatewayv2_integration.lambda["users_service"].id}"
  authorization_type = "JWT"
  authorizer_id      = aws_apigatewayv2_authorizer.cognito.id
}

resource "aws_apigatewayv2_route" "users_put" {
  count = local.users_routes_enabled ? 1 : 0

  api_id             = aws_apigatewayv2_api.http.id
  route_key          = "PUT /users/{userId}"
  target             = "integrations/${aws_apigatewayv2_integration.lambda["users_service"].id}"
  authorization_type = "JWT"
  authorizer_id      = aws_apigatewayv2_authorizer.cognito.id
}

resource "aws_apigatewayv2_route" "users_restaurants_list" {
  count = local.users_routes_enabled ? 1 : 0

  api_id             = aws_apigatewayv2_api.http.id
  route_key          = "GET /users/{userId}/restaurants"
  target             = "integrations/${aws_apigatewayv2_integration.lambda["users_service"].id}"
  authorization_type = "JWT"
  authorizer_id      = aws_apigatewayv2_authorizer.cognito.id
}

resource "aws_apigatewayv2_route" "restaurants_post" {
  count = local.restaurants_routes_enabled ? 1 : 0

  api_id             = aws_apigatewayv2_api.http.id
  route_key          = "POST /restaurants"
  target             = "integrations/${aws_apigatewayv2_integration.lambda["restaurants_service"].id}"
  authorization_type = "JWT"
  authorizer_id      = aws_apigatewayv2_authorizer.cognito.id
}

resource "aws_apigatewayv2_route" "catalog_lookups" {
  count = local.catalog_routes_enabled ? 1 : 0

  api_id    = aws_apigatewayv2_api.http.id
  route_key = "GET /lookups"
  target    = "integrations/${aws_apigatewayv2_integration.lambda["catalog_service"].id}"
}

resource "aws_apigatewayv2_route" "catalog_restaurants_list" {
  count = local.catalog_routes_enabled ? 1 : 0

  api_id    = aws_apigatewayv2_api.http.id
  route_key = "GET /restaurants"
  target    = "integrations/${aws_apigatewayv2_integration.lambda["catalog_service"].id}"
}

resource "aws_apigatewayv2_route" "catalog_restaurant_detail" {
  count = local.catalog_routes_enabled ? 1 : 0

  api_id    = aws_apigatewayv2_api.http.id
  route_key = "GET /restaurants/{restaurantId}"
  target    = "integrations/${aws_apigatewayv2_integration.lambda["catalog_service"].id}"
}

resource "aws_apigatewayv2_route" "catalog_restaurant_menus" {
  count = local.catalog_routes_enabled ? 1 : 0

  api_id    = aws_apigatewayv2_api.http.id
  route_key = "GET /restaurants/{restaurantId}/menus"
  target    = "integrations/${aws_apigatewayv2_integration.lambda["catalog_service"].id}"
}

resource "aws_apigatewayv2_route" "orders_create" {
  count = local.orders_routes_enabled ? 1 : 0

  api_id             = aws_apigatewayv2_api.http.id
  route_key          = "POST /restaurants/{restaurantId}/orders"
  target             = "integrations/${aws_apigatewayv2_integration.lambda["orders_service"].id}"
  authorization_type = "JWT"
  authorizer_id      = aws_apigatewayv2_authorizer.cognito.id
}

resource "aws_apigatewayv2_route" "orders_user_list" {
  count = local.orders_routes_enabled ? 1 : 0

  api_id             = aws_apigatewayv2_api.http.id
  route_key          = "GET /users/{userId}/orders"
  target             = "integrations/${aws_apigatewayv2_integration.lambda["orders_service"].id}"
  authorization_type = "JWT"
  authorizer_id      = aws_apigatewayv2_authorizer.cognito.id
}

resource "aws_apigatewayv2_route" "orders_restaurant_list" {
  count = local.orders_routes_enabled ? 1 : 0

  api_id             = aws_apigatewayv2_api.http.id
  route_key          = "GET /restaurants/{restaurantId}/orders"
  target             = "integrations/${aws_apigatewayv2_integration.lambda["orders_service"].id}"
  authorization_type = "JWT"
  authorizer_id      = aws_apigatewayv2_authorizer.cognito.id
}

resource "aws_apigatewayv2_route" "orders_restaurant_detail" {
  count = local.orders_routes_enabled ? 1 : 0

  api_id             = aws_apigatewayv2_api.http.id
  route_key          = "GET /restaurants/{restaurantId}/orders/{orderId}"
  target             = "integrations/${aws_apigatewayv2_integration.lambda["orders_service"].id}"
  authorization_type = "JWT"
  authorizer_id      = aws_apigatewayv2_authorizer.cognito.id
}

resource "aws_apigatewayv2_route" "orders_restaurant_patch" {
  count = local.orders_routes_enabled ? 1 : 0

  api_id             = aws_apigatewayv2_api.http.id
  route_key          = "PATCH /restaurants/{restaurantId}/orders/{orderId}"
  target             = "integrations/${aws_apigatewayv2_integration.lambda["orders_service"].id}"
  authorization_type = "JWT"
  authorizer_id      = aws_apigatewayv2_authorizer.cognito.id
}

resource "aws_apigatewayv2_route" "restaurants_put" {
  count = local.restaurants_routes_enabled ? 1 : 0

  api_id             = aws_apigatewayv2_api.http.id
  route_key          = "PUT /restaurants/{restaurantId}"
  target             = "integrations/${aws_apigatewayv2_integration.lambda["restaurants_service"].id}"
  authorization_type = "JWT"
  authorizer_id      = aws_apigatewayv2_authorizer.cognito.id
}

resource "aws_apigatewayv2_route" "restaurants_delete" {
  count = local.restaurants_routes_enabled ? 1 : 0

  api_id             = aws_apigatewayv2_api.http.id
  route_key          = "DELETE /restaurants/{restaurantId}"
  target             = "integrations/${aws_apigatewayv2_integration.lambda["restaurants_service"].id}"
  authorization_type = "JWT"
  authorizer_id      = aws_apigatewayv2_authorizer.cognito.id
}

resource "aws_apigatewayv2_route" "restaurants_review_put" {
  count = local.restaurants_routes_enabled ? 1 : 0

  api_id             = aws_apigatewayv2_api.http.id
  route_key          = "PUT /restaurants/{restaurantId}/reviews/{userId}"
  target             = "integrations/${aws_apigatewayv2_integration.lambda["restaurants_service"].id}"
  authorization_type = "JWT"
  authorizer_id      = aws_apigatewayv2_authorizer.cognito.id
}

resource "aws_apigatewayv2_route" "restaurants_admins_list" {
  count = local.restaurants_routes_enabled ? 1 : 0

  api_id             = aws_apigatewayv2_api.http.id
  route_key          = "GET /restaurants/{restaurantId}/admins"
  target             = "integrations/${aws_apigatewayv2_integration.lambda["restaurants_service"].id}"
  authorization_type = "JWT"
  authorizer_id      = aws_apigatewayv2_authorizer.cognito.id
}

resource "aws_apigatewayv2_route" "restaurants_admins_post" {
  count = local.restaurants_routes_enabled ? 1 : 0

  api_id             = aws_apigatewayv2_api.http.id
  route_key          = "POST /restaurants/{restaurantId}/admins"
  target             = "integrations/${aws_apigatewayv2_integration.lambda["restaurants_service"].id}"
  authorization_type = "JWT"
  authorizer_id      = aws_apigatewayv2_authorizer.cognito.id
}

resource "aws_apigatewayv2_route" "restaurants_admins_delete" {
  count = local.restaurants_routes_enabled ? 1 : 0

  api_id             = aws_apigatewayv2_api.http.id
  route_key          = "DELETE /restaurants/{restaurantId}/admins/{userId}"
  target             = "integrations/${aws_apigatewayv2_integration.lambda["restaurants_service"].id}"
  authorization_type = "JWT"
  authorizer_id      = aws_apigatewayv2_authorizer.cognito.id
}

resource "aws_apigatewayv2_route" "restaurants_admin_menus_list" {
  count = local.restaurants_routes_enabled ? 1 : 0

  api_id             = aws_apigatewayv2_api.http.id
  route_key          = "GET /restaurants/{restaurantId}/admin/menus"
  target             = "integrations/${aws_apigatewayv2_integration.lambda["restaurants_service"].id}"
  authorization_type = "JWT"
  authorizer_id      = aws_apigatewayv2_authorizer.cognito.id
}

resource "aws_apigatewayv2_route" "restaurants_admin_menus_post" {
  count = local.restaurants_routes_enabled ? 1 : 0

  api_id             = aws_apigatewayv2_api.http.id
  route_key          = "POST /restaurants/{restaurantId}/admin/menus"
  target             = "integrations/${aws_apigatewayv2_integration.lambda["restaurants_service"].id}"
  authorization_type = "JWT"
  authorizer_id      = aws_apigatewayv2_authorizer.cognito.id
}

resource "aws_apigatewayv2_route" "restaurants_menus_post" {
  count = local.restaurants_routes_enabled ? 1 : 0

  api_id             = aws_apigatewayv2_api.http.id
  route_key          = "POST /restaurants/{restaurantId}/menus"
  target             = "integrations/${aws_apigatewayv2_integration.lambda["restaurants_service"].id}"
  authorization_type = "JWT"
  authorizer_id      = aws_apigatewayv2_authorizer.cognito.id
}

resource "aws_apigatewayv2_route" "restaurants_admin_menu_get" {
  count = local.restaurants_routes_enabled ? 1 : 0

  api_id             = aws_apigatewayv2_api.http.id
  route_key          = "GET /restaurants/{restaurantId}/admin/menus/{menuId}"
  target             = "integrations/${aws_apigatewayv2_integration.lambda["restaurants_service"].id}"
  authorization_type = "JWT"
  authorizer_id      = aws_apigatewayv2_authorizer.cognito.id
}

resource "aws_apigatewayv2_route" "restaurants_admin_menu_put" {
  count = local.restaurants_routes_enabled ? 1 : 0

  api_id             = aws_apigatewayv2_api.http.id
  route_key          = "PUT /restaurants/{restaurantId}/admin/menus/{menuId}"
  target             = "integrations/${aws_apigatewayv2_integration.lambda["restaurants_service"].id}"
  authorization_type = "JWT"
  authorizer_id      = aws_apigatewayv2_authorizer.cognito.id
}

resource "aws_apigatewayv2_route" "restaurants_admin_menu_patch" {
  count = local.restaurants_routes_enabled ? 1 : 0

  api_id             = aws_apigatewayv2_api.http.id
  route_key          = "PATCH /restaurants/{restaurantId}/admin/menus/{menuId}"
  target             = "integrations/${aws_apigatewayv2_integration.lambda["restaurants_service"].id}"
  authorization_type = "JWT"
  authorizer_id      = aws_apigatewayv2_authorizer.cognito.id
}

resource "aws_apigatewayv2_route" "restaurants_admin_menu_delete" {
  count = local.restaurants_routes_enabled ? 1 : 0

  api_id             = aws_apigatewayv2_api.http.id
  route_key          = "DELETE /restaurants/{restaurantId}/admin/menus/{menuId}"
  target             = "integrations/${aws_apigatewayv2_integration.lambda["restaurants_service"].id}"
  authorization_type = "JWT"
  authorizer_id      = aws_apigatewayv2_authorizer.cognito.id
}

resource "aws_apigatewayv2_route" "restaurants_menu_categories_list" {
  count = local.restaurants_routes_enabled ? 1 : 0

  api_id             = aws_apigatewayv2_api.http.id
  route_key          = "GET /restaurants/{restaurantId}/menus/{menuId}/categories"
  target             = "integrations/${aws_apigatewayv2_integration.lambda["restaurants_service"].id}"
  authorization_type = "JWT"
  authorizer_id      = aws_apigatewayv2_authorizer.cognito.id
}

resource "aws_apigatewayv2_route" "restaurants_menu_categories_post" {
  count = local.restaurants_routes_enabled ? 1 : 0

  api_id             = aws_apigatewayv2_api.http.id
  route_key          = "POST /restaurants/{restaurantId}/menus/{menuId}/categories"
  target             = "integrations/${aws_apigatewayv2_integration.lambda["restaurants_service"].id}"
  authorization_type = "JWT"
  authorizer_id      = aws_apigatewayv2_authorizer.cognito.id
}

resource "aws_apigatewayv2_route" "restaurants_menu_category_get" {
  count = local.restaurants_routes_enabled ? 1 : 0

  api_id             = aws_apigatewayv2_api.http.id
  route_key          = "GET /restaurants/{restaurantId}/menus/{menuId}/categories/{categoryId}"
  target             = "integrations/${aws_apigatewayv2_integration.lambda["restaurants_service"].id}"
  authorization_type = "JWT"
  authorizer_id      = aws_apigatewayv2_authorizer.cognito.id
}

resource "aws_apigatewayv2_route" "restaurants_menu_category_put" {
  count = local.restaurants_routes_enabled ? 1 : 0

  api_id             = aws_apigatewayv2_api.http.id
  route_key          = "PUT /restaurants/{restaurantId}/menus/{menuId}/categories/{categoryId}"
  target             = "integrations/${aws_apigatewayv2_integration.lambda["restaurants_service"].id}"
  authorization_type = "JWT"
  authorizer_id      = aws_apigatewayv2_authorizer.cognito.id
}

resource "aws_apigatewayv2_route" "restaurants_menu_category_delete" {
  count = local.restaurants_routes_enabled ? 1 : 0

  api_id             = aws_apigatewayv2_api.http.id
  route_key          = "DELETE /restaurants/{restaurantId}/menus/{menuId}/categories/{categoryId}"
  target             = "integrations/${aws_apigatewayv2_integration.lambda["restaurants_service"].id}"
  authorization_type = "JWT"
  authorizer_id      = aws_apigatewayv2_authorizer.cognito.id
}

resource "aws_apigatewayv2_route" "restaurants_menu_items_list" {
  count = local.restaurants_routes_enabled ? 1 : 0

  api_id             = aws_apigatewayv2_api.http.id
  route_key          = "GET /restaurants/{restaurantId}/menus/{menuId}/categories/{categoryId}/items"
  target             = "integrations/${aws_apigatewayv2_integration.lambda["restaurants_service"].id}"
  authorization_type = "JWT"
  authorizer_id      = aws_apigatewayv2_authorizer.cognito.id
}

resource "aws_apigatewayv2_route" "restaurants_menu_items_post" {
  count = local.restaurants_routes_enabled ? 1 : 0

  api_id             = aws_apigatewayv2_api.http.id
  route_key          = "POST /restaurants/{restaurantId}/menus/{menuId}/categories/{categoryId}/items"
  target             = "integrations/${aws_apigatewayv2_integration.lambda["restaurants_service"].id}"
  authorization_type = "JWT"
  authorizer_id      = aws_apigatewayv2_authorizer.cognito.id
}

resource "aws_apigatewayv2_route" "restaurants_menu_item_get" {
  count = local.restaurants_routes_enabled ? 1 : 0

  api_id             = aws_apigatewayv2_api.http.id
  route_key          = "GET /restaurants/{restaurantId}/menus/{menuId}/categories/{categoryId}/items/{itemId}"
  target             = "integrations/${aws_apigatewayv2_integration.lambda["restaurants_service"].id}"
  authorization_type = "JWT"
  authorizer_id      = aws_apigatewayv2_authorizer.cognito.id
}

resource "aws_apigatewayv2_route" "restaurants_menu_item_put" {
  count = local.restaurants_routes_enabled ? 1 : 0

  api_id             = aws_apigatewayv2_api.http.id
  route_key          = "PUT /restaurants/{restaurantId}/menus/{menuId}/categories/{categoryId}/items/{itemId}"
  target             = "integrations/${aws_apigatewayv2_integration.lambda["restaurants_service"].id}"
  authorization_type = "JWT"
  authorizer_id      = aws_apigatewayv2_authorizer.cognito.id
}

resource "aws_apigatewayv2_route" "restaurants_menu_item_delete" {
  count = local.restaurants_routes_enabled ? 1 : 0

  api_id             = aws_apigatewayv2_api.http.id
  route_key          = "DELETE /restaurants/{restaurantId}/menus/{menuId}/categories/{categoryId}/items/{itemId}"
  target             = "integrations/${aws_apigatewayv2_integration.lambda["restaurants_service"].id}"
  authorization_type = "JWT"
  authorizer_id      = aws_apigatewayv2_authorizer.cognito.id
}

resource "aws_apigatewayv2_route" "restaurants_tables_list" {
  count = local.restaurants_routes_enabled ? 1 : 0

  api_id             = aws_apigatewayv2_api.http.id
  route_key          = "GET /restaurants/{restaurantId}/tables"
  target             = "integrations/${aws_apigatewayv2_integration.lambda["restaurants_service"].id}"
  authorization_type = "JWT"
  authorizer_id      = aws_apigatewayv2_authorizer.cognito.id
}

resource "aws_apigatewayv2_route" "restaurants_tables_post" {
  count = local.restaurants_routes_enabled ? 1 : 0

  api_id             = aws_apigatewayv2_api.http.id
  route_key          = "POST /restaurants/{restaurantId}/tables"
  target             = "integrations/${aws_apigatewayv2_integration.lambda["restaurants_service"].id}"
  authorization_type = "JWT"
  authorizer_id      = aws_apigatewayv2_authorizer.cognito.id
}

resource "aws_apigatewayv2_route" "restaurants_table_get" {
  count = local.restaurants_routes_enabled ? 1 : 0

  api_id             = aws_apigatewayv2_api.http.id
  route_key          = "GET /restaurants/{restaurantId}/tables/{tableId}"
  target             = "integrations/${aws_apigatewayv2_integration.lambda["restaurants_service"].id}"
  authorization_type = "JWT"
  authorizer_id      = aws_apigatewayv2_authorizer.cognito.id
}

resource "aws_apigatewayv2_route" "restaurants_table_put" {
  count = local.restaurants_routes_enabled ? 1 : 0

  api_id             = aws_apigatewayv2_api.http.id
  route_key          = "PUT /restaurants/{restaurantId}/tables/{tableId}"
  target             = "integrations/${aws_apigatewayv2_integration.lambda["restaurants_service"].id}"
  authorization_type = "JWT"
  authorizer_id      = aws_apigatewayv2_authorizer.cognito.id
}

resource "aws_apigatewayv2_route" "restaurants_table_delete" {
  count = local.restaurants_routes_enabled ? 1 : 0

  api_id             = aws_apigatewayv2_api.http.id
  route_key          = "DELETE /restaurants/{restaurantId}/tables/{tableId}"
  target             = "integrations/${aws_apigatewayv2_integration.lambda["restaurants_service"].id}"
  authorization_type = "JWT"
  authorizer_id      = aws_apigatewayv2_authorizer.cognito.id
}

resource "aws_apigatewayv2_route" "restaurants_business_hours_get" {
  count = local.restaurants_routes_enabled ? 1 : 0

  api_id             = aws_apigatewayv2_api.http.id
  route_key          = "GET /restaurants/{restaurantId}/business-hours"
  target             = "integrations/${aws_apigatewayv2_integration.lambda["restaurants_service"].id}"
  authorization_type = "JWT"
  authorizer_id      = aws_apigatewayv2_authorizer.cognito.id
}

resource "aws_apigatewayv2_route" "restaurants_business_hours_put" {
  count = local.restaurants_routes_enabled ? 1 : 0

  api_id             = aws_apigatewayv2_api.http.id
  route_key          = "PUT /restaurants/{restaurantId}/business-hours"
  target             = "integrations/${aws_apigatewayv2_integration.lambda["restaurants_service"].id}"
  authorization_type = "JWT"
  authorizer_id      = aws_apigatewayv2_authorizer.cognito.id
}

resource "aws_apigatewayv2_route" "restaurants_availability" {
  count = local.restaurants_routes_enabled ? 1 : 0

  api_id             = aws_apigatewayv2_api.http.id
  route_key          = "GET /restaurants/{restaurantId}/availability"
  target             = "integrations/${aws_apigatewayv2_integration.lambda["restaurants_service"].id}"
  authorization_type = "JWT"
  authorizer_id      = aws_apigatewayv2_authorizer.cognito.id
}

resource "aws_apigatewayv2_route" "restaurants_public_availability" {
  count = local.restaurants_routes_enabled ? 1 : 0

  api_id    = aws_apigatewayv2_api.http.id
  route_key = "GET /restaurants/{restaurantId}/public-availability"
  target    = "integrations/${aws_apigatewayv2_integration.lambda["restaurants_service"].id}"
}

resource "aws_apigatewayv2_route" "reservations_create" {
  count = local.reservations_routes_enabled ? 1 : 0

  api_id             = aws_apigatewayv2_api.http.id
  route_key          = "POST /restaurants/{restaurantId}/reservations"
  target             = "integrations/${aws_apigatewayv2_integration.lambda["reservations_service"].id}"
  authorization_type = "JWT"
  authorizer_id      = aws_apigatewayv2_authorizer.cognito.id
}

resource "aws_apigatewayv2_route" "reservations_create_public" {
  count = local.reservations_routes_enabled ? 1 : 0

  api_id    = aws_apigatewayv2_api.http.id
  route_key = "POST /restaurants/{restaurantId}/public-reservations"
  target    = "integrations/${aws_apigatewayv2_integration.lambda["reservations_service"].id}"
}

resource "aws_apigatewayv2_route" "reservations_restaurant_list" {
  count = local.reservations_routes_enabled ? 1 : 0

  api_id             = aws_apigatewayv2_api.http.id
  route_key          = "GET /restaurants/{restaurantId}/reservations"
  target             = "integrations/${aws_apigatewayv2_integration.lambda["reservations_service"].id}"
  authorization_type = "JWT"
  authorizer_id      = aws_apigatewayv2_authorizer.cognito.id
}

resource "aws_apigatewayv2_route" "reservations_get" {
  count = local.reservations_routes_enabled ? 1 : 0

  api_id             = aws_apigatewayv2_api.http.id
  route_key          = "GET /reservations/{reservationId}"
  target             = "integrations/${aws_apigatewayv2_integration.lambda["reservations_service"].id}"
  authorization_type = "JWT"
  authorizer_id      = aws_apigatewayv2_authorizer.cognito.id
}

resource "aws_apigatewayv2_route" "reservations_patch" {
  count = local.reservations_routes_enabled ? 1 : 0

  api_id             = aws_apigatewayv2_api.http.id
  route_key          = "PATCH /reservations/{reservationId}"
  target             = "integrations/${aws_apigatewayv2_integration.lambda["reservations_service"].id}"
  authorization_type = "JWT"
  authorizer_id      = aws_apigatewayv2_authorizer.cognito.id
}

resource "aws_apigatewayv2_route" "reservations_user_list" {
  count = local.reservations_routes_enabled ? 1 : 0

  api_id             = aws_apigatewayv2_api.http.id
  route_key          = "GET /users/{userId}/reservations"
  target             = "integrations/${aws_apigatewayv2_integration.lambda["reservations_service"].id}"
  authorization_type = "JWT"
  authorizer_id      = aws_apigatewayv2_authorizer.cognito.id
}

resource "aws_apigatewayv2_route" "promotions_list" {
  count = local.promotions_routes_enabled ? 1 : 0

  api_id             = aws_apigatewayv2_api.http.id
  route_key          = "GET /restaurants/{restaurantId}/promotions"
  target             = "integrations/${aws_apigatewayv2_integration.lambda["promotions_service"].id}"
  authorization_type = "JWT"
  authorizer_id      = aws_apigatewayv2_authorizer.cognito.id
}

resource "aws_apigatewayv2_route" "promotions_create" {
  count = local.promotions_routes_enabled ? 1 : 0

  api_id             = aws_apigatewayv2_api.http.id
  route_key          = "POST /restaurants/{restaurantId}/promotions"
  target             = "integrations/${aws_apigatewayv2_integration.lambda["promotions_service"].id}"
  authorization_type = "JWT"
  authorizer_id      = aws_apigatewayv2_authorizer.cognito.id
}

resource "aws_apigatewayv2_route" "promotions_get" {
  count = local.promotions_routes_enabled ? 1 : 0

  api_id             = aws_apigatewayv2_api.http.id
  route_key          = "GET /restaurants/{restaurantId}/promotions/{promotionId}"
  target             = "integrations/${aws_apigatewayv2_integration.lambda["promotions_service"].id}"
  authorization_type = "JWT"
  authorizer_id      = aws_apigatewayv2_authorizer.cognito.id
}

resource "aws_apigatewayv2_route" "promotions_delete" {
  count = local.promotions_routes_enabled ? 1 : 0

  api_id             = aws_apigatewayv2_api.http.id
  route_key          = "DELETE /restaurants/{restaurantId}/promotions/{promotionId}"
  target             = "integrations/${aws_apigatewayv2_integration.lambda["promotions_service"].id}"
  authorization_type = "JWT"
  authorizer_id      = aws_apigatewayv2_authorizer.cognito.id
}

resource "aws_apigatewayv2_route" "analytics_get" {
  count = local.analytics_routes_enabled ? 1 : 0

  api_id             = aws_apigatewayv2_api.http.id
  route_key          = "GET /restaurants/{restaurantId}/analytics"
  target             = "integrations/${aws_apigatewayv2_integration.lambda["analytics_service"].id}"
  authorization_type = "JWT"
  authorizer_id      = aws_apigatewayv2_authorizer.cognito.id
}

resource "aws_lambda_permission" "api_gateway" {
  for_each = local.api_lambda_functions

  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.this[each.key].function_name
  principal     = "apigateway.amazonaws.com"
  source_arn    = "${aws_apigatewayv2_api.http.execution_arn}/*/*"
}

resource "aws_sns_topic" "domain_events" {
  name = "${local.name_prefix}-domain-events"
}

resource "aws_sns_topic" "email_topic" {
  name = "${local.name_prefix}-email-notifications"
}

resource "aws_sns_topic_subscription" "email_notification" {
  count = trimspace(var.notification_email) != "" ? 1 : 0

  topic_arn = aws_sns_topic.email_topic.arn
  protocol  = "email"
  endpoint  = var.notification_email
}

resource "aws_sqs_queue" "email_events_dlq" {
  name                      = "${local.name_prefix}-email-events-dlq"
  message_retention_seconds = 1209600
}

resource "aws_sqs_queue" "email_events" {
  name                       = "${local.name_prefix}-email-events"
  message_retention_seconds  = 345600
  visibility_timeout_seconds = 45

  redrive_policy = jsonencode({
    deadLetterTargetArn = aws_sqs_queue.email_events_dlq.arn
    maxReceiveCount     = 3
  })
}

resource "aws_sqs_queue" "analytics_events_dlq" {
  name                      = "${local.name_prefix}-analytics-events-dlq"
  message_retention_seconds = 1209600
}

resource "aws_sqs_queue" "analytics_events" {
  name                       = "${local.name_prefix}-analytics-events"
  message_retention_seconds  = 345600
  visibility_timeout_seconds = 45

  redrive_policy = jsonencode({
    deadLetterTargetArn = aws_sqs_queue.analytics_events_dlq.arn
    maxReceiveCount     = 3
  })
}

resource "aws_sqs_queue_policy" "email_events" {
  queue_url = aws_sqs_queue.email_events.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid       = "AllowDomainEventsTopic"
        Effect    = "Allow"
        Principal = { Service = "sns.amazonaws.com" }
        Action    = "sqs:SendMessage"
        Resource  = aws_sqs_queue.email_events.arn
        Condition = {
          ArnEquals = {
            "aws:SourceArn" = aws_sns_topic.domain_events.arn
          }
        }
      }
    ]
  })
}

resource "aws_sqs_queue_policy" "analytics_events" {
  queue_url = aws_sqs_queue.analytics_events.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid       = "AllowDomainEventsTopic"
        Effect    = "Allow"
        Principal = { Service = "sns.amazonaws.com" }
        Action    = "sqs:SendMessage"
        Resource  = aws_sqs_queue.analytics_events.arn
        Condition = {
          ArnEquals = {
            "aws:SourceArn" = aws_sns_topic.domain_events.arn
          }
        }
      }
    ]
  })
}

resource "aws_sns_topic_subscription" "email_events_sqs" {
  topic_arn = aws_sns_topic.domain_events.arn
  protocol  = "sqs"
  endpoint  = aws_sqs_queue.email_events.arn

  depends_on = [aws_sqs_queue_policy.email_events]
}

resource "aws_sns_topic_subscription" "analytics_events_sqs" {
  topic_arn = aws_sns_topic.domain_events.arn
  protocol  = "sqs"
  endpoint  = aws_sqs_queue.analytics_events.arn

  depends_on = [aws_sqs_queue_policy.analytics_events]
}

resource "aws_lambda_event_source_mapping" "email_worker" {
  event_source_arn        = aws_sqs_queue.email_events.arn
  function_name           = aws_lambda_function.this["email_worker"].arn
  batch_size              = 10
  function_response_types = ["ReportBatchItemFailures"]
}

resource "aws_lambda_event_source_mapping" "analytics_worker" {
  event_source_arn        = aws_sqs_queue.analytics_events.arn
  function_name           = aws_lambda_function.this["analytics_worker"].arn
  batch_size              = 10
  function_response_types = ["ReportBatchItemFailures"]
}
