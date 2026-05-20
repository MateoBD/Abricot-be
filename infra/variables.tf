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

variable "frontend_callback_url" {
  description = "Optional frontend SPA callback URL. Leave empty to use the Terraform-managed S3 website endpoint."
  type        = string
  default     = ""
}

variable "notification_email" {
  description = "Optional email address subscribed to SNS email notifications. Recipient must confirm SNS subscription email."
  type        = string
  default     = ""
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
    condition     = length(trimspace(var.postgres_password)) >= 12 && var.postgres_password != "CHANGE_ME_STRONG_PASSWORD"
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
