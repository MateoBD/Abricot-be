variable "project_name" {
  description = "Short project name used in AWS resource names."
  type        = string
  default     = "abricot-tp3"
}

variable "aws_region" {
  description = "AWS region."
  type        = string
  default     = "us-east-1"
}

variable "frontend_base_url" {
  description = "Frontend base URL. For local smoke tests use http://localhost:5173; for S3 deploy use the S3 website HTTP URL."
  type        = string
  default     = "http://localhost:5173"
}

variable "frontend_callback_path" {
  description = "SPA route that receives tokens in the URL hash."
  type        = string
  default     = "/auth/callback"
}

variable "local_dev_callback_url" {
  description = "Optional local frontend callback URL registered in Cognito for development."
  type        = string
  default     = "http://localhost:5173/auth/callback"
}

variable "cognito_domain_prefix" {
  description = "Cognito Hosted UI domain prefix. Must be globally unique. Defaults to project name plus AWS account ID."
  type        = string
  default     = null
}

variable "cognito_scopes" {
  description = "OAuth scopes for Cognito Hosted UI."
  type        = list(string)
  default     = ["openid", "email", "profile"]
}

variable "lambda_runtime" {
  description = "Python runtime for Lambdas."
  type        = string
  default     = "python3.12"
}

variable "lambda_role_arn" {
  description = "Existing AWS Lab role ARN used by Lambda. Pass LabRole here to avoid iam:GetRole and IAM role creation."
  type        = string

  validation {
    condition     = can(regex("^arn:aws:iam::[0-9]{12}:role/.+", var.lambda_role_arn))
    error_message = "lambda_role_arn must be an IAM role ARN, for example arn:aws:iam::<account-id>:role/LabRole."
  }
}
