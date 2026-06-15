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

# Custom reusable module: one call per Lambda, driven by for_each over the
# merged local.lambda_functions map. Replaces the previous duplicated
# archive_file + aws_lambda_function pair.
module "lambda" {
  source   = "./modules/lambda_function"
  for_each = local.lambda_functions

  function_name = "${local.name_prefix}-${replace(each.key, "_", "-")}"
  source_dir    = each.value.source_dir
  handler       = each.value.handler
  runtime       = local.lambda_runtime
  role_arn      = local.lab_role_arn
  timeout       = each.value.timeout
  memory_size   = each.value.memory_size
  excludes      = each.value.excludes
  environment   = lookup(local.lambda_environment, each.key, {})

  vpc_config = each.value.vpc_enabled ? {
    subnet_ids         = each.value.subnet_ids
    security_group_ids = each.value.security_group_ids
  } : null
}

resource "aws_apigatewayv2_integration" "lambda" {
  for_each = local.api_lambda_functions

  api_id                 = aws_apigatewayv2_api.http.id
  integration_type       = "AWS_PROXY"
  integration_uri        = module.lambda[each.key].invoke_arn
  payload_format_version = "2.0"
}

# All HTTP API routes collapsed into a single for_each over local.api_routes.
# The conditional `enabled` flag per route replaces ~50 near-identical resources
# and their individual `count` guards. JWT-protected routes attach the Cognito
# authorizer; public routes leave authorization_type null (NONE).
resource "aws_apigatewayv2_route" "this" {
  for_each = { for key, route in local.api_routes : key => route if route.enabled }

  api_id    = aws_apigatewayv2_api.http.id
  route_key = each.value.route_key
  target    = "integrations/${aws_apigatewayv2_integration.lambda[each.value.service].id}"

  authorization_type = each.value.jwt ? "JWT" : null
  authorizer_id      = each.value.jwt ? aws_apigatewayv2_authorizer.cognito.id : null
}

resource "aws_lambda_permission" "api_gateway" {
  for_each = local.api_lambda_functions

  action        = "lambda:InvokeFunction"
  function_name = module.lambda[each.key].function_name
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
  function_name           = module.lambda["email_worker"].arn
  batch_size              = 10
  function_response_types = ["ReportBatchItemFailures"]
}

resource "aws_lambda_event_source_mapping" "analytics_worker" {
  event_source_arn        = aws_sqs_queue.analytics_events.arn
  function_name           = module.lambda["analytics_worker"].arn
  batch_size              = 10
  function_response_types = ["ReportBatchItemFailures"]
}
