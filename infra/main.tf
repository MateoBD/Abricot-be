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

  lifecycle {
    prevent_destroy = true
  }
}

resource "aws_cognito_user_pool_client" "spa" {
  name         = "${local.name_prefix}-spa-client"
  user_pool_id = aws_cognito_user_pool.main.id

  generate_secret                      = false
  prevent_user_existence_errors        = "ENABLED"
  allowed_oauth_flows_user_pool_client = true
  allowed_oauth_flows                  = ["code"]
  allowed_oauth_scopes                 = var.cognito_scopes
  callback_urls                        = local.callback_urls
  logout_urls                          = distinct([local.frontend_base_url, local.frontend_callback_url])
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
    allow_methods = ["GET", "POST", "PUT", "OPTIONS"]
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
  output_path = "${path.module}/${each.key}.zip"
}

resource "aws_lambda_function" "this" {
  for_each = local.lambda_functions

  function_name    = "${local.name_prefix}-${replace(each.key, "_", "-")}"
  filename         = data.archive_file.lambda[each.key].output_path
  handler          = each.value.handler
  role             = var.lambda_role_arn
  runtime          = var.lambda_runtime
  source_code_hash = data.archive_file.lambda[each.key].output_base64sha256
  layers           = each.value.layers
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
  for_each = local.lambda_functions

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
  count = local.rds_proxy_enabled ? 1 : 0

  api_id             = aws_apigatewayv2_api.http.id
  route_key          = "POST /users"
  target             = "integrations/${aws_apigatewayv2_integration.lambda["users_service"].id}"
  authorization_type = "JWT"
  authorizer_id      = aws_apigatewayv2_authorizer.cognito.id
}

resource "aws_apigatewayv2_route" "users_get" {
  count = local.rds_proxy_enabled ? 1 : 0

  api_id             = aws_apigatewayv2_api.http.id
  route_key          = "GET /users/{userId}"
  target             = "integrations/${aws_apigatewayv2_integration.lambda["users_service"].id}"
  authorization_type = "JWT"
  authorizer_id      = aws_apigatewayv2_authorizer.cognito.id
}

resource "aws_apigatewayv2_route" "users_put" {
  count = local.rds_proxy_enabled ? 1 : 0

  api_id             = aws_apigatewayv2_api.http.id
  route_key          = "PUT /users/{userId}"
  target             = "integrations/${aws_apigatewayv2_integration.lambda["users_service"].id}"
  authorization_type = "JWT"
  authorizer_id      = aws_apigatewayv2_authorizer.cognito.id
}

resource "aws_lambda_permission" "api_gateway" {
  for_each = local.lambda_functions

  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.this[each.key].function_name
  principal     = "apigateway.amazonaws.com"
  source_arn    = "${aws_apigatewayv2_api.http.execution_arn}/*/*"
}
