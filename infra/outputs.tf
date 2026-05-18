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
  value       = "${local.cognito_domain}/login?client_id=${aws_cognito_user_pool_client.spa.id}&response_type=code&scope=${join("+", var.cognito_scopes)}&redirect_uri=${urlencode(local.api_gateway_callback_url)}"
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
  value       = local.rds_proxy_enabled ? "${local.api_gateway_url}/users" : null
}

output "user_url_template" {
  description = "Protected user profile endpoint template."
  value       = local.rds_proxy_enabled ? "${local.api_gateway_url}/users/{userId}" : null
}

output "private_database_infra_enabled" {
  description = "Whether PASO 2.2B private database infrastructure is enabled."
  value       = var.enable_private_database_infra
}

output "private_app_subnet_ids" {
  description = "Private app subnet IDs for DB-backed Lambdas when PASO 2.2B is enabled."
  value       = local.private_app_subnet_ids
}

output "private_db_subnet_ids" {
  description = "Private DB subnet IDs for private RDS/RDS Proxy when PASO 2.2B is enabled."
  value       = local.private_db_subnet_ids
}

output "lambda_security_group_ids" {
  description = "Security group IDs attached to DB-backed Lambdas when PASO 2.2B is enabled."
  value       = local.lambda_security_group_ids
}

output "rds_proxy_endpoint" {
  description = "RDS Proxy endpoint used as POSTGRES_HOST when PASO 2.2B creates a proxy."
  value       = local.rds_proxy_endpoint
}
