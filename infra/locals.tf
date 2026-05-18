data "aws_caller_identity" "current" {}

locals {
  name_prefix = lower(var.project_name)

  frontend_base_url        = trimsuffix(var.frontend_base_url, "/")
  frontend_callback_path   = startswith(var.frontend_callback_path, "/") ? var.frontend_callback_path : "/${var.frontend_callback_path}"
  frontend_callback_url    = "${local.frontend_base_url}${local.frontend_callback_path}"
  api_gateway_url          = trimsuffix(aws_apigatewayv2_stage.default.invoke_url, "/")
  api_gateway_callback_url = "${local.api_gateway_url}/callback"

  cognito_domain_prefix = coalesce(
    var.cognito_domain_prefix,
    "${local.name_prefix}-${data.aws_caller_identity.current.account_id}",
  )
  cognito_domain = "https://${aws_cognito_user_pool_domain.main.domain}.auth.${var.aws_region}.amazoncognito.com"

  callback_urls = distinct(compact([
    local.api_gateway_callback_url,
    var.local_dev_callback_url,
  ]))

  lambda_environment = {
    health = {}
    users_service = {
      API_GATEWAY_CALLBACK_URL = local.api_gateway_callback_url
      COGNITO_CLIENT_ID        = aws_cognito_user_pool_client.spa.id
      COGNITO_DOMAIN           = local.cognito_domain
      FRONTEND_CALLBACK_URL    = local.frontend_callback_url
    }
  }

  lambda_functions = {
    health = {
      handler    = "handler.handler"
      source_dir = "${path.module}/../lambdas/health"
      timeout    = 5
    }
    users_service = {
      handler    = "handler.handler"
      source_dir = "${path.module}/../lambdas/users_service"
      timeout    = 10
    }
  }
}
