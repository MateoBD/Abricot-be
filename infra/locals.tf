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

  private_database_enabled = var.enable_private_database_infra
  dedicated_vpc_enabled    = local.private_database_enabled && var.network_strategy == "dedicated_vpc"
  default_vpc_enabled      = local.private_database_enabled && var.network_strategy == "default_vpc_private_subnets"

  private_vpc_id              = local.dedicated_vpc_enabled ? aws_vpc.private[0].id : var.vpc_id
  nat_subnet_id               = local.dedicated_vpc_enabled ? aws_subnet.public[0].id : var.nat_public_subnet_id
  private_app_subnet_ids      = local.private_database_enabled ? aws_subnet.private_app[*].id : []
  private_db_subnet_ids       = local.private_database_enabled ? aws_subnet.private_db[*].id : []
  lambda_security_group_ids   = local.private_database_enabled ? [aws_security_group.lambda[0].id] : []
  db_secret_arn             = local.private_database_enabled && var.create_db_secret ? aws_secretsmanager_secret.db[0].arn : var.db_secret_arn
  rds_proxy_enabled         = local.private_database_enabled && var.create_rds_proxy
  rds_proxy_endpoint        = local.rds_proxy_enabled ? aws_db_proxy.users[0].endpoint : null

  users_service_base_environment = {
    API_GATEWAY_CALLBACK_URL = local.api_gateway_callback_url
    COGNITO_CLIENT_ID        = aws_cognito_user_pool_client.spa.id
    COGNITO_DOMAIN           = local.cognito_domain
    FRONTEND_CALLBACK_URL    = local.frontend_callback_url
  }

  users_service_db_environment = local.rds_proxy_enabled ? {
    DB_TARGET         = "RDS_PROXY"
    POSTGRES_HOST     = local.rds_proxy_endpoint
    POSTGRES_PORT     = tostring(var.postgres_port)
    POSTGRES_DB       = var.postgres_db
    POSTGRES_USER     = var.postgres_user
    POSTGRES_PASSWORD = var.postgres_password
    POSTGRES_SSLMODE  = var.postgres_sslmode
  } : {}

  lambda_environment = {
    health = {}
    users_service = merge(local.users_service_base_environment, local.users_service_db_environment)
  }

  lambda_functions = {
    health = {
      handler            = "handler.handler"
      source_dir         = "${path.module}/../lambdas/health"
      layers             = []
      timeout            = 5
      vpc_enabled        = false
      subnet_ids         = []
      security_group_ids = []
    }
    users_service = {
      handler            = "handler.handler"
      source_dir         = "${path.module}/../lambdas/users_service"
      layers             = var.users_service_layer_arns
      timeout            = 10
      vpc_enabled        = local.private_database_enabled
      subnet_ids         = local.private_app_subnet_ids
      security_group_ids = local.lambda_security_group_ids
    }
  }
}
