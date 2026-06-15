data "aws_caller_identity" "current" {}

locals {
  name_prefix  = lower(var.project_name)
  lab_role_arn = "arn:aws:iam::${data.aws_caller_identity.current.account_id}:role/LabRole"

  frontend_bucket_name         = "${local.name_prefix}-${data.aws_caller_identity.current.account_id}-frontend"
  lambda_artifacts_bucket_name = "${local.name_prefix}-${data.aws_caller_identity.current.account_id}-lambda-artifacts"
  images_bucket_name           = "${local.name_prefix}-${data.aws_caller_identity.current.account_id}-images"
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

  vpc_cidr                 = "10.0.0.0/16"
  availability_zones       = ["us-east-1a", "us-east-1b"]
  public_subnet_cidrs      = ["10.0.1.0/24", "10.0.11.0/24"]
  private_app_subnet_cidrs = ["10.0.2.0/24", "10.0.12.0/24"]
  private_db_subnet_cidrs  = ["10.0.3.0/24", "10.0.13.0/24"]

  postgres_port        = 5432
  postgres_tls_enabled = false
  postgres_sslmode     = local.postgres_tls_enabled ? "require" : "disable"

  rds_instance_class    = "db.t3.micro"
  rds_allocated_storage = 20

  users_service_base_environment = {
    API_GATEWAY_CALLBACK_URL = local.api_gateway_callback_url
    COGNITO_CLIENT_ID        = aws_cognito_user_pool_client.spa.id
    COGNITO_DOMAIN           = local.cognito_domain
    FRONTEND_CALLBACK_URL    = local.frontend_callback_url
    SNS_USER_TOPIC_PREFIX    = "${local.name_prefix}-user"
  }

  users_service_db_environment = local.lambda_private_attachment_enabled ? {
    DB_TARGET         = "RDS_PROXY"
    POSTGRES_HOST     = local.rds_proxy_endpoint
    POSTGRES_PORT     = tostring(local.postgres_port)
    POSTGRES_DB       = var.postgres_db
    POSTGRES_USER     = var.postgres_user
    POSTGRES_PASSWORD = var.postgres_password
    POSTGRES_SSLMODE  = local.postgres_sslmode
    DB_SSL_MODE       = local.postgres_sslmode
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
    catalog_service      = local.catalog_routes_enabled ? merge(local.users_service_db_environment, { AWS_S3_BUCKET = local.images_bucket_name }) : {}
    orders_service       = local.orders_routes_enabled ? merge(local.users_service_db_environment, { DOMAIN_EVENTS_TOPIC_ARN = aws_sns_topic.domain_events.arn }) : {}
    restaurants_service  = local.restaurants_routes_enabled ? merge(local.users_service_db_environment, { AWS_S3_BUCKET = local.images_bucket_name }) : {}
    reservations_service = local.reservations_routes_enabled ? merge(local.users_service_db_environment, { SNS_USER_TOPIC_PREFIX = "${local.name_prefix}-user" }) : {}
    promotions_service   = local.promotions_routes_enabled ? merge(local.users_service_db_environment, { DOMAIN_EVENTS_TOPIC_ARN = aws_sns_topic.domain_events.arn }) : {}
    analytics_service    = local.analytics_routes_enabled ? local.users_service_db_environment : {}
    email_worker         = { EMAIL_TOPIC_ARN = aws_sns_topic.email_topic.arn }
    analytics_worker     = local.users_service_db_environment
    db_migrate           = local.db_migration_environment
  }

  api_lambda_functions = {
    health = {
      handler            = "handler.handler"
      source_dir         = "${path.module}/../build/lambdas/health"
      excludes           = []
      timeout            = 5
      memory_size        = 128
      vpc_enabled        = false
      subnet_ids         = []
      security_group_ids = []
    }
    users_service = {
      handler            = "handler.handler"
      source_dir         = "${path.module}/../build/lambdas/users_service"
      excludes           = []
      timeout            = 30
      memory_size        = 512
      vpc_enabled        = local.lambda_private_attachment_enabled
      subnet_ids         = local.private_app_subnet_ids
      security_group_ids = local.lambda_security_group_ids
    }
    catalog_service = {
      handler            = "handler.handler"
      source_dir         = "${path.module}/../build/lambdas/catalog_service"
      excludes           = []
      timeout            = 30
      memory_size        = 512
      vpc_enabled        = local.lambda_private_attachment_enabled
      subnet_ids         = local.private_app_subnet_ids
      security_group_ids = local.lambda_security_group_ids
    }
    orders_service = {
      handler            = "handler.handler"
      source_dir         = "${path.module}/../build/lambdas/orders_service"
      excludes           = []
      timeout            = 30
      memory_size        = 512
      vpc_enabled        = local.lambda_private_attachment_enabled
      subnet_ids         = local.private_app_subnet_ids
      security_group_ids = local.lambda_security_group_ids
    }
    restaurants_service = {
      handler            = "handler.handler"
      source_dir         = "${path.module}/../build/lambdas/restaurants_service"
      excludes           = []
      timeout            = 30
      memory_size        = 512
      vpc_enabled        = local.lambda_private_attachment_enabled
      subnet_ids         = local.private_app_subnet_ids
      security_group_ids = local.lambda_security_group_ids
    }
    reservations_service = {
      handler            = "handler.handler"
      source_dir         = "${path.module}/../build/lambdas/reservations_service"
      excludes           = []
      timeout            = 30
      memory_size        = 512
      vpc_enabled        = local.lambda_private_attachment_enabled
      subnet_ids         = local.private_app_subnet_ids
      security_group_ids = local.lambda_security_group_ids
    }
    promotions_service = {
      handler            = "handler.handler"
      source_dir         = "${path.module}/../build/lambdas/promotions_service"
      excludes           = []
      timeout            = 30
      memory_size        = 512
      vpc_enabled        = local.lambda_private_attachment_enabled
      subnet_ids         = local.private_app_subnet_ids
      security_group_ids = local.lambda_security_group_ids
    }
    analytics_service = {
      handler            = "handler.handler"
      source_dir         = "${path.module}/../build/lambdas/analytics_service"
      excludes           = []
      timeout            = 30
      memory_size        = 512
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
      memory_size        = 128
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
      memory_size        = 128
      vpc_enabled        = false
      subnet_ids         = []
      security_group_ids = []
    }
    analytics_worker = {
      handler            = "handler.handler"
      source_dir         = "${path.module}/../build/lambdas/analytics_worker"
      excludes           = []
      timeout            = 30
      memory_size        = 128
      vpc_enabled        = local.lambda_private_attachment_enabled
      subnet_ids         = local.private_app_subnet_ids
      security_group_ids = local.lambda_security_group_ids
    }
  }

  lambda_functions = merge(local.api_lambda_functions, local.private_lambda_functions, local.event_worker_lambda_functions)

  # API Gateway HTTP routes. enabled gates creation per service stack toggle;
  # jwt selects whether the Cognito JWT authorizer is attached.
  api_routes = {
    health                           = { route_key = "GET /health", service = "health", jwt = false, enabled = true }
    callback                         = { route_key = "GET /callback", service = "users_service", jwt = false, enabled = true }
    auth_test                        = { route_key = "GET /auth-test", service = "users_service", jwt = true, enabled = true }
    users_post                       = { route_key = "POST /users", service = "users_service", jwt = true, enabled = local.users_routes_enabled }
    users_get                        = { route_key = "GET /users/{userId}", service = "users_service", jwt = true, enabled = local.users_routes_enabled }
    users_put                        = { route_key = "PUT /users/{userId}", service = "users_service", jwt = true, enabled = local.users_routes_enabled }
    users_restaurants_list           = { route_key = "GET /users/{userId}/restaurants", service = "users_service", jwt = true, enabled = local.users_routes_enabled }
    restaurants_post                 = { route_key = "POST /restaurants", service = "restaurants_service", jwt = true, enabled = local.restaurants_routes_enabled }
    catalog_lookups                  = { route_key = "GET /lookups", service = "catalog_service", jwt = false, enabled = local.catalog_routes_enabled }
    catalog_restaurants_list         = { route_key = "GET /restaurants", service = "catalog_service", jwt = false, enabled = local.catalog_routes_enabled }
    catalog_restaurant_detail        = { route_key = "GET /restaurants/{restaurantId}", service = "catalog_service", jwt = false, enabled = local.catalog_routes_enabled }
    catalog_restaurant_menus         = { route_key = "GET /restaurants/{restaurantId}/menus", service = "catalog_service", jwt = false, enabled = local.catalog_routes_enabled }
    orders_create                    = { route_key = "POST /restaurants/{restaurantId}/orders", service = "orders_service", jwt = true, enabled = local.orders_routes_enabled }
    orders_user_list                 = { route_key = "GET /users/{userId}/orders", service = "orders_service", jwt = true, enabled = local.orders_routes_enabled }
    orders_restaurant_list           = { route_key = "GET /restaurants/{restaurantId}/orders", service = "orders_service", jwt = true, enabled = local.orders_routes_enabled }
    orders_restaurant_detail         = { route_key = "GET /restaurants/{restaurantId}/orders/{orderId}", service = "orders_service", jwt = true, enabled = local.orders_routes_enabled }
    orders_restaurant_patch          = { route_key = "PATCH /restaurants/{restaurantId}/orders/{orderId}", service = "orders_service", jwt = true, enabled = local.orders_routes_enabled }
    restaurants_put                  = { route_key = "PUT /restaurants/{restaurantId}", service = "restaurants_service", jwt = true, enabled = local.restaurants_routes_enabled }
    restaurants_delete               = { route_key = "DELETE /restaurants/{restaurantId}", service = "restaurants_service", jwt = true, enabled = local.restaurants_routes_enabled }
    restaurants_review_put           = { route_key = "PUT /restaurants/{restaurantId}/reviews/{userId}", service = "restaurants_service", jwt = true, enabled = local.restaurants_routes_enabled }
    restaurants_admins_list          = { route_key = "GET /restaurants/{restaurantId}/admins", service = "restaurants_service", jwt = true, enabled = local.restaurants_routes_enabled }
    restaurants_admins_post          = { route_key = "POST /restaurants/{restaurantId}/admins", service = "restaurants_service", jwt = true, enabled = local.restaurants_routes_enabled }
    restaurants_admins_delete        = { route_key = "DELETE /restaurants/{restaurantId}/admins/{userId}", service = "restaurants_service", jwt = true, enabled = local.restaurants_routes_enabled }
    restaurants_admin_menus_list     = { route_key = "GET /restaurants/{restaurantId}/admin/menus", service = "restaurants_service", jwt = true, enabled = local.restaurants_routes_enabled }
    restaurants_admin_menus_post     = { route_key = "POST /restaurants/{restaurantId}/admin/menus", service = "restaurants_service", jwt = true, enabled = local.restaurants_routes_enabled }
    restaurants_menus_post           = { route_key = "POST /restaurants/{restaurantId}/menus", service = "restaurants_service", jwt = true, enabled = local.restaurants_routes_enabled }
    restaurants_admin_menu_get       = { route_key = "GET /restaurants/{restaurantId}/admin/menus/{menuId}", service = "restaurants_service", jwt = true, enabled = local.restaurants_routes_enabled }
    restaurants_menu_get             = { route_key = "GET /restaurants/{restaurantId}/menus/{menuId}", service = "restaurants_service", jwt = true, enabled = local.restaurants_routes_enabled }
    restaurants_admin_menu_put       = { route_key = "PUT /restaurants/{restaurantId}/admin/menus/{menuId}", service = "restaurants_service", jwt = true, enabled = local.restaurants_routes_enabled }
    restaurants_menu_put             = { route_key = "PUT /restaurants/{restaurantId}/menus/{menuId}", service = "restaurants_service", jwt = true, enabled = local.restaurants_routes_enabled }
    restaurants_admin_menu_patch     = { route_key = "PATCH /restaurants/{restaurantId}/admin/menus/{menuId}", service = "restaurants_service", jwt = true, enabled = local.restaurants_routes_enabled }
    restaurants_menu_patch           = { route_key = "PATCH /restaurants/{restaurantId}/menus/{menuId}", service = "restaurants_service", jwt = true, enabled = local.restaurants_routes_enabled }
    restaurants_admin_menu_delete    = { route_key = "DELETE /restaurants/{restaurantId}/admin/menus/{menuId}", service = "restaurants_service", jwt = true, enabled = local.restaurants_routes_enabled }
    restaurants_menu_delete          = { route_key = "DELETE /restaurants/{restaurantId}/menus/{menuId}", service = "restaurants_service", jwt = true, enabled = local.restaurants_routes_enabled }
    restaurants_menu_categories_list = { route_key = "GET /restaurants/{restaurantId}/menus/{menuId}/categories", service = "restaurants_service", jwt = true, enabled = local.restaurants_routes_enabled }
    restaurants_menu_categories_post = { route_key = "POST /restaurants/{restaurantId}/menus/{menuId}/categories", service = "restaurants_service", jwt = true, enabled = local.restaurants_routes_enabled }
    restaurants_menu_category_get    = { route_key = "GET /restaurants/{restaurantId}/menus/{menuId}/categories/{categoryId}", service = "restaurants_service", jwt = true, enabled = local.restaurants_routes_enabled }
    restaurants_menu_category_put    = { route_key = "PUT /restaurants/{restaurantId}/menus/{menuId}/categories/{categoryId}", service = "restaurants_service", jwt = true, enabled = local.restaurants_routes_enabled }
    restaurants_menu_category_delete = { route_key = "DELETE /restaurants/{restaurantId}/menus/{menuId}/categories/{categoryId}", service = "restaurants_service", jwt = true, enabled = local.restaurants_routes_enabled }
    restaurants_menu_items_list      = { route_key = "GET /restaurants/{restaurantId}/menus/{menuId}/categories/{categoryId}/items", service = "restaurants_service", jwt = true, enabled = local.restaurants_routes_enabled }
    restaurants_menu_items_post      = { route_key = "POST /restaurants/{restaurantId}/menus/{menuId}/categories/{categoryId}/items", service = "restaurants_service", jwt = true, enabled = local.restaurants_routes_enabled }
    restaurants_menu_item_get        = { route_key = "GET /restaurants/{restaurantId}/menus/{menuId}/categories/{categoryId}/items/{itemId}", service = "restaurants_service", jwt = true, enabled = local.restaurants_routes_enabled }
    restaurants_menu_item_put        = { route_key = "PUT /restaurants/{restaurantId}/menus/{menuId}/categories/{categoryId}/items/{itemId}", service = "restaurants_service", jwt = true, enabled = local.restaurants_routes_enabled }
    restaurants_menu_item_delete     = { route_key = "DELETE /restaurants/{restaurantId}/menus/{menuId}/categories/{categoryId}/items/{itemId}", service = "restaurants_service", jwt = true, enabled = local.restaurants_routes_enabled }
    restaurants_tables_list          = { route_key = "GET /restaurants/{restaurantId}/tables", service = "restaurants_service", jwt = true, enabled = local.restaurants_routes_enabled }
    restaurants_tables_post          = { route_key = "POST /restaurants/{restaurantId}/tables", service = "restaurants_service", jwt = true, enabled = local.restaurants_routes_enabled }
    restaurants_table_get            = { route_key = "GET /restaurants/{restaurantId}/tables/{tableId}", service = "restaurants_service", jwt = true, enabled = local.restaurants_routes_enabled }
    restaurants_table_put            = { route_key = "PUT /restaurants/{restaurantId}/tables/{tableId}", service = "restaurants_service", jwt = true, enabled = local.restaurants_routes_enabled }
    restaurants_table_delete         = { route_key = "DELETE /restaurants/{restaurantId}/tables/{tableId}", service = "restaurants_service", jwt = true, enabled = local.restaurants_routes_enabled }
    restaurants_business_hours_get   = { route_key = "GET /restaurants/{restaurantId}/business-hours", service = "restaurants_service", jwt = true, enabled = local.restaurants_routes_enabled }
    restaurants_business_hours_put   = { route_key = "PUT /restaurants/{restaurantId}/business-hours", service = "restaurants_service", jwt = true, enabled = local.restaurants_routes_enabled }
    restaurants_availability         = { route_key = "GET /restaurants/{restaurantId}/availability", service = "restaurants_service", jwt = true, enabled = local.restaurants_routes_enabled }
    restaurants_public_availability  = { route_key = "GET /restaurants/{restaurantId}/public-availability", service = "restaurants_service", jwt = false, enabled = local.restaurants_routes_enabled }
    restaurants_photo                = { route_key = "POST /restaurants/{restaurantId}/photo", service = "restaurants_service", jwt = true, enabled = local.restaurants_routes_enabled }
    reservations_create              = { route_key = "POST /restaurants/{restaurantId}/reservations", service = "reservations_service", jwt = true, enabled = local.reservations_routes_enabled }
    reservations_create_public       = { route_key = "POST /restaurants/{restaurantId}/public-reservations", service = "reservations_service", jwt = false, enabled = local.reservations_routes_enabled }
    reservations_restaurant_list     = { route_key = "GET /restaurants/{restaurantId}/reservations", service = "reservations_service", jwt = true, enabled = local.reservations_routes_enabled }
    reservations_get                 = { route_key = "GET /reservations/{reservationId}", service = "reservations_service", jwt = true, enabled = local.reservations_routes_enabled }
    reservations_patch               = { route_key = "PATCH /reservations/{reservationId}", service = "reservations_service", jwt = true, enabled = local.reservations_routes_enabled }
    reservations_user_list           = { route_key = "GET /users/{userId}/reservations", service = "reservations_service", jwt = true, enabled = local.reservations_routes_enabled }
    promotions_list                  = { route_key = "GET /restaurants/{restaurantId}/promotions", service = "promotions_service", jwt = true, enabled = local.promotions_routes_enabled }
    promotions_create                = { route_key = "POST /restaurants/{restaurantId}/promotions", service = "promotions_service", jwt = true, enabled = local.promotions_routes_enabled }
    promotions_get                   = { route_key = "GET /restaurants/{restaurantId}/promotions/{promotionId}", service = "promotions_service", jwt = true, enabled = local.promotions_routes_enabled }
    promotions_delete                = { route_key = "DELETE /restaurants/{restaurantId}/promotions/{promotionId}", service = "promotions_service", jwt = true, enabled = local.promotions_routes_enabled }
    analytics_get                    = { route_key = "GET /restaurants/{restaurantId}/analytics", service = "analytics_service", jwt = true, enabled = local.analytics_routes_enabled }
  }
}
