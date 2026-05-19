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

variable "lambda_role_arn" {
  description = "AWS Academy LabRole ARN used by Lambda. Terraform does not create or read IAM roles."
  type        = string

  validation {
    condition     = can(regex("^arn:aws:iam::[0-9]{12}:role/LabRole$", var.lambda_role_arn))
    error_message = "lambda_role_arn must be the AWS LabRole ARN, for example arn:aws:iam::<account-id>:role/LabRole."
  }
}

variable "rds_proxy_role_arn" {
  description = "AWS Academy LabRole ARN used by RDS Proxy to read the DB secret. Terraform does not create or read IAM roles."
  type        = string

  validation {
    condition     = can(regex("^arn:aws:iam::[0-9]{12}:role/LabRole$", var.rds_proxy_role_arn))
    error_message = "rds_proxy_role_arn must be the AWS LabRole ARN, for example arn:aws:iam::<account-id>:role/LabRole."
  }
}

variable "frontend_callback_url" {
  description = "Frontend SPA callback URL that receives Cognito tokens in the hash fragment."
  type        = string
  default     = "http://localhost:5173/auth/callback"
}

variable "postgres_db" {
  description = "PostgreSQL database name."
  type        = string
  default     = "abricot"
}

variable "postgres_user" {
  description = "PostgreSQL admin username."
  type        = string
  default     = "abricot_app"

  validation {
    condition     = length(trimspace(var.postgres_user)) > 0
    error_message = "postgres_user cannot be empty."
  }
}

variable "postgres_password" {
  description = "PostgreSQL admin password. Must be changed in terraform.tfvars before planning/apply."
  type        = string
  sensitive   = true

  validation {
    condition     = length(trimspace(nonsensitive(var.postgres_password))) >= 12 && nonsensitive(var.postgres_password) != "CHANGE_ME_STRONG_PASSWORD"
    error_message = "postgres_password must be at least 12 characters and cannot be CHANGE_ME_STRONG_PASSWORD."
  }
}

variable "enable_full_private_stack" {
  description = "Create the final TP3 private architecture: VPC, NAT, private RDS, RDS Proxy, Lambda VPC attachment, and protected /users routes."
  type        = bool
  default     = true
}

variable "recovery_skip_lambda_private_attachment" {
  description = "Emergency two-phase toggle only. Keep false for normal delivery; set true only if AWS provider fails when adding Lambda vpc_config in the same apply."
  type        = bool
  default     = false
}

variable "users_service_layer_arns" {
  description = "Optional Lambda Layer ARNs for users-service dependencies such as psycopg2. Leave empty if dependencies are packaged into the Lambda source."
  type        = list(string)
  default     = []
}
