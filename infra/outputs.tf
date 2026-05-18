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
  description = "Hosted UI login URL — paste into browser to start OAuth flow."
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
