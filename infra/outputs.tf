output "cognito_user_pool_id" {
  description = "Cognito User Pool ID."
  value       = aws_cognito_user_pool.main.id
}

output "cognito_user_pool_client_id" {
  description = "Cognito App Client ID."
  value       = aws_cognito_user_pool_client.spa.id
}

output "cognito_domain" {
  description = "Cognito Hosted UI base domain."
  value       = local.cognito_domain
}

output "cognito_login_url" {
  description = "Hosted UI login URL - paste into browser to start OAuth flow."
  value       = "${local.cognito_domain}/login?client_id=${aws_cognito_user_pool_client.spa.id}&response_type=code&scope=${join("+", local.cognito_scopes)}&redirect_uri=${urlencode(local.api_gateway_callback_url)}"
}

output "api_gateway_url" {
  description = "HTTP API Gateway base URL."
  value       = local.api_gateway_url
}

output "api_gateway_callback_url" {
  description = "OAuth callback URL registered in Cognito (API Gateway /callback)."
  value       = local.api_gateway_callback_url
}

output "callback_url" {
  description = "Alias for api_gateway_callback_url."
  value       = local.api_gateway_callback_url
}

output "frontend_callback_url" {
  description = "Frontend URL that receives tokens in the hash fragment."
  value       = local.frontend_callback_url
}

output "frontend_bucket_name" {
  description = "S3 bucket used to host the frontend SPA."
  value       = aws_s3_bucket.frontend.bucket
}

output "frontend_website_url" {
  description = "S3 website URL for the frontend SPA."
  value       = local.frontend_website_url
}

output "lambda_artifacts_bucket_name" {
  description = "S3 bucket used to store Lambda ZIP artifacts (external module)."
  value       = module.lambda_artifacts_bucket.s3_bucket_id
}

output "health_url" {
  description = "Public health endpoint."
  value       = "${local.api_gateway_url}/health"
}

output "auth_test_url" {
  description = "Protected auth-test endpoint (requires Bearer token)."
  value       = "${local.api_gateway_url}/auth-test"
}

output "users_url" {
  description = "Protected users collection endpoint."
  value       = local.users_routes_enabled ? "${local.api_gateway_url}/users" : null
}

output "user_url_template" {
  description = "Protected user profile endpoint template."
  value       = local.users_routes_enabled ? "${local.api_gateway_url}/users/{userId}" : null
}

output "private_database_infra_enabled" {
  description = "Whether the full private stack is enabled."
  value       = local.full_private_stack_enabled
}

output "users_service_private_attachment_enabled" {
  description = "Whether users-service-lambda is attached to private app subnets."
  value       = local.lambda_private_attachment_enabled
}

output "users_routes_enabled" {
  description = "Whether DB-backed /users API Gateway routes are enabled."
  value       = local.users_routes_enabled
}

output "catalog_routes_enabled" {
  description = "Whether public catalog API Gateway routes are enabled."
  value       = local.catalog_routes_enabled
}

output "catalog_lookups_url" {
  description = "Public cuisine/price lookup endpoint."
  value       = local.catalog_routes_enabled ? "${local.api_gateway_url}/lookups?type=cuisine-type" : null
}

output "catalog_restaurants_url" {
  description = "Public paginated restaurants list endpoint."
  value       = local.catalog_routes_enabled ? "${local.api_gateway_url}/restaurants?page=1&perPage=12" : null
}

output "private_app_subnet_ids" {
  description = "Private app subnet IDs for DB-backed Lambdas when PASO 2.2B is enabled."
  value       = local.private_app_subnet_ids
}

output "private_db_subnet_ids" {
  description = "Private DB subnet IDs across two AZs for Multi-AZ private RDS and RDS Proxy."
  value       = local.private_db_subnet_ids
}

output "rds_multi_az_enabled" {
  description = "Whether private PostgreSQL RDS is configured as Multi-AZ primary/standby."
  value       = local.full_private_stack_enabled ? true : false
}

output "lambda_security_group_ids" {
  description = "Security group IDs attached to DB-backed Lambdas when PASO 2.2B is enabled."
  value       = local.lambda_security_group_ids
}

output "rds_proxy_endpoint" {
  description = "RDS Proxy endpoint used as POSTGRES_HOST when PASO 2.2B creates a proxy."
  value       = local.rds_proxy_endpoint
}

output "vpc_endpoints_summary" {
  description = "Final VPC egress state: 2 interface endpoints (SNS, Secrets Manager) over PrivateLink + 1 S3 gateway endpoint + retained NAT for the Cognito Hosted-UI /oauth2/token call."
  value = local.full_private_stack_enabled ? {
    interface_secretsmanager = aws_vpc_endpoint.secretsmanager[0].id
    interface_sns            = aws_vpc_endpoint.sns[0].id
    gateway_s3               = aws_vpc_endpoint.s3[0].id
    nat_retained_for         = "cognito-hosted-ui-oauth2-token"
  } : null
}

output "db_migration_lambda_name" {
  description = "Internal Lambda used to run Flask-Migrate/Alembic migrations inside the private VPC."
  value = local.lambda_private_attachment_enabled ? lookup({
    for name, instance in module.lambda : name => instance.function_name
  }, "db_migrate", null) : null
}

output "lambda_function_names" {
  description = "Lambda function names keyed by local service key."
  value = {
    for name, instance in module.lambda : name => instance.function_name
  }
}

output "domain_events_topic_arn" {
  description = "SNS topic ARN used by orders-service for internal domain event fanout."
  value       = aws_sns_topic.domain_events.arn
}

output "email_topic_arn" {
  description = "Shared SNS notification topic ARN (all user emails; filter-policy targeted)."
  value       = aws_sns_topic.email_topic.arn
}

output "notification_topic_arn" {
  description = "Shared notification topic ARN passed to Lambdas as EMAIL_NOTIFICATIONS_TOPIC_ARN."
  value       = aws_sns_topic.email_topic.arn
}

output "email_events_queue_url" {
  description = "SQS queue URL subscribed to domain events for email processing."
  value       = aws_sqs_queue.email_events.url
}

output "analytics_events_queue_url" {
  description = "SQS queue URL subscribed to domain events for analytics processing."
  value       = aws_sqs_queue.analytics_events.url
}

output "email_worker_lambda_name" {
  description = "Lambda function name for the SQS email worker."
  value       = lookup({ for name, instance in module.lambda : name => instance.function_name }, "email_worker", null)
}

output "analytics_worker_lambda_name" {
  description = "Lambda function name for the SQS analytics worker."
  value       = lookup({ for name, instance in module.lambda : name => instance.function_name }, "analytics_worker", null)
}

output "notification_subscription_note" {
  description = "How users get subscribed to the shared notification topic."
  value       = "Users are subscribed to the shared notification topic on signup with a per-user FilterPolicy {\"userId\":[<id>]}. Each must confirm the SNS email before delivery."
}
