data "aws_caller_identity" "current" {}

locals {
  name_prefix  = lower(var.project_name)
  lab_role_arn = "arn:aws:iam::${data.aws_caller_identity.current.account_id}:role/LabRole"

  frontend_bucket_name         = "${local.name_prefix}-${data.aws_caller_identity.current.account_id}-frontend"
  lambda_artifacts_bucket_name = "${local.name_prefix}-${data.aws_caller_identity.current.account_id}-lambda-artifacts"
  frontend_website_url         = "http://${aws_s3_bucket_website_configuration.frontend.website_endpoint}"
  frontend_callback_url        = trimspace(var.frontend_callback_url) != "" ? trimsuffix(var.frontend_callback_url, "/") : "${local.frontend_website_url}/auth/callback"
  frontend_base_url            = trimsuffix(trimsuffix(local.frontend_callback_url, "/auth/callback"), "/")

  api_gateway_url          = trimsuffix(aws_apigatewayv2_stage.default.invoke_url, "/")
  api_gateway_callback_url = "${local.api_gateway_url}/callback"

  cognito_domain_prefix = "${local.name_prefix}-${data.aws_caller_identity.current.account_id}"
  cognito_domain        = "https://${aws_cognito_user_pool_domain.main.domain}.auth.${var.aws_region}.amazoncognito.com"
  cognito_scopes        = ["openid", "email", "profile"]
  callback_urls         = [local.api_gateway_callback_url]
  logout_urls           = [local.api_gateway_url]

  lambda_runtime = "python3.12"

  full_private_stack_enabled        = var.enable_full_private_stack
  lambda_private_attachment_enabled = local.full_private_stack_enabled && !var.recovery_skip_lambda_private_attachment
  users_routes_enabled              = local.lambda_private_attachment_enabled
  private_vpc_id                    = local.full_private_stack_enabled ? aws_vpc.private[0].id : null
  private_app_subnet_ids            = local.full_private_stack_enabled ? aws_subnet.private_app[*].id : []
  private_db_subnet_ids             = local.full_private_stack_enabled ? aws_subnet.private_db[*].id : []
  lambda_security_group_ids         = local.full_private_stack_enabled ? [aws_security_group.lambda[0].id] : []
  rds_proxy_endpoint                = local.full_private_stack_enabled ? aws_db_proxy.users[0].endpoint : null

  vpc_cidr                 = "10.42.0.0/16"
  availability_zones       = ["us-east-1a", "us-east-1b"]
  public_subnet_cidrs      = ["10.42.0.0/24", "10.42.1.0/24"]
  private_app_subnet_cidrs = ["10.42.10.0/24", "10.42.11.0/24"]
  private_db_subnet_cidrs  = ["10.42.20.0/24", "10.42.21.0/24"]

  postgres_port         = 5432
  postgres_sslmode      = "require"
  rds_instance_class    = "db.t3.micro"
  rds_allocated_storage = 20

  users_service_base_environment = {
    API_GATEWAY_CALLBACK_URL = local.api_gateway_callback_url
    COGNITO_CLIENT_ID        = aws_cognito_user_pool_client.spa.id
    COGNITO_DOMAIN           = local.cognito_domain
    FRONTEND_CALLBACK_URL    = local.frontend_callback_url
  }

  users_service_db_environment = local.lambda_private_attachment_enabled ? {
    DB_TARGET         = "RDS_PROXY"
    POSTGRES_HOST     = local.rds_proxy_endpoint
    POSTGRES_PORT     = tostring(local.postgres_port)
    POSTGRES_DB       = var.postgres_db
    POSTGRES_USER     = var.postgres_user
    POSTGRES_PASSWORD = var.postgres_password
    POSTGRES_SSLMODE  = local.postgres_sslmode
  } : {}

  db_migration_environment = merge(local.users_service_db_environment, {
    DB_MIGRATION_REVISION = "head"
    MIGRATIONS_DIR        = "migrations"
  })

  catalog_routes_enabled      = local.lambda_private_attachment_enabled
  orders_routes_enabled       = local.lambda_private_attachment_enabled
  restaurants_routes_enabled  = local.lambda_private_attachment_enabled
  reservations_routes_enabled = local.lambda_private_attachment_enabled
  promotions_routes_enabled   = local.lambda_private_attachment_enabled
  analytics_routes_enabled    = local.lambda_private_attachment_enabled

  lambda_environment = {
    health               = {}
    users_service        = merge(local.users_service_base_environment, local.users_service_db_environment)
    catalog_service      = local.catalog_routes_enabled ? local.users_service_db_environment : {}
    orders_service       = local.orders_routes_enabled ? merge(local.users_service_db_environment, { DOMAIN_EVENTS_TOPIC_ARN = aws_sns_topic.domain_events.arn }) : {}
    restaurants_service  = local.restaurants_routes_enabled ? local.users_service_db_environment : {}
    reservations_service = local.reservations_routes_enabled ? local.users_service_db_environment : {}
    promotions_service   = local.promotions_routes_enabled ? local.users_service_db_environment : {}
    analytics_service    = local.analytics_routes_enabled ? local.users_service_db_environment : {}
    email_worker         = { EMAIL_TOPIC_ARN = aws_sns_topic.email_topic.arn }
    analytics_worker     = {}
    db_migrate           = local.db_migration_environment
  }

  api_lambda_functions = {
    health = {
      handler            = "handler.handler"
      source_dir         = "${path.module}/../build/lambdas/health"
      excludes           = []
      timeout            = 5
      vpc_enabled        = false
      subnet_ids         = []
      security_group_ids = []
    }
    users_service = {
      handler            = "handler.handler"
      source_dir         = "${path.module}/../build/lambdas/users_service"
      excludes           = []
      timeout            = 10
      vpc_enabled        = local.lambda_private_attachment_enabled
      subnet_ids         = local.private_app_subnet_ids
      security_group_ids = local.lambda_security_group_ids
    }
    catalog_service = {
      handler            = "handler.handler"
      source_dir         = "${path.module}/../build/lambdas/catalog_service"
      excludes           = []
      timeout            = 15
      vpc_enabled        = local.lambda_private_attachment_enabled
      subnet_ids         = local.private_app_subnet_ids
      security_group_ids = local.lambda_security_group_ids
    }
    orders_service = {
      handler            = "handler.handler"
      source_dir         = "${path.module}/../build/lambdas/orders_service"
      excludes           = []
      timeout            = 15
      vpc_enabled        = local.lambda_private_attachment_enabled
      subnet_ids         = local.private_app_subnet_ids
      security_group_ids = local.lambda_security_group_ids
    }
    restaurants_service = {
      handler            = "handler.handler"
      source_dir         = "${path.module}/../build/lambdas/restaurants_service"
      excludes           = []
      timeout            = 30
      vpc_enabled        = local.lambda_private_attachment_enabled
      subnet_ids         = local.private_app_subnet_ids
      security_group_ids = local.lambda_security_group_ids
    }
    reservations_service = {
      handler            = "handler.handler"
      source_dir         = "${path.module}/../build/lambdas/reservations_service"
      excludes           = []
      timeout            = 15
      vpc_enabled        = local.lambda_private_attachment_enabled
      subnet_ids         = local.private_app_subnet_ids
      security_group_ids = local.lambda_security_group_ids
    }
    promotions_service = {
      handler            = "handler.handler"
      source_dir         = "${path.module}/../build/lambdas/promotions_service"
      excludes           = []
      timeout            = 15
      vpc_enabled        = local.lambda_private_attachment_enabled
      subnet_ids         = local.private_app_subnet_ids
      security_group_ids = local.lambda_security_group_ids
    }
    analytics_service = {
      handler            = "handler.handler"
      source_dir         = "${path.module}/../build/lambdas/analytics_service"
      excludes           = []
      timeout            = 15
      vpc_enabled        = local.lambda_private_attachment_enabled
      subnet_ids         = local.private_app_subnet_ids
      security_group_ids = local.lambda_security_group_ids
    }
  }

  private_lambda_functions = local.lambda_private_attachment_enabled ? {
    db_migrate = {
      handler            = "handler.handler"
      source_dir         = "${path.module}/../build/lambdas/db_migrate"
      excludes           = []
      timeout            = 120
      vpc_enabled        = true
      subnet_ids         = local.private_app_subnet_ids
      security_group_ids = local.lambda_security_group_ids
    }
  } : {}

  event_worker_lambda_functions = {
    email_worker = {
      handler            = "handler.handler"
      source_dir         = "${path.module}/../build/lambdas/email_worker"
      excludes           = []
      timeout            = 10
      vpc_enabled        = false
      subnet_ids         = []
      security_group_ids = []
    }
    analytics_worker = {
      handler            = "handler.handler"
      source_dir         = "${path.module}/../build/lambdas/analytics_worker"
      excludes           = []
      timeout            = 10
      vpc_enabled        = false
      subnet_ids         = []
      security_group_ids = []
    }
  }

  lambda_functions = merge(local.api_lambda_functions, local.private_lambda_functions, local.event_worker_lambda_functions)
}
