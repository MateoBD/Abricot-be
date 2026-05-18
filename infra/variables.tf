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

variable "enable_private_database_infra" {
  description = "Feature flag for PASO 2.2B private app subnets, NAT, private RDS and RDS Proxy. Keep false for PASO 1-only plans."
  type        = bool
  default     = false
}

variable "network_strategy" {
  description = "Private network strategy for PASO 2.2B: dedicated_vpc or default_vpc_private_subnets."
  type        = string
  default     = "dedicated_vpc"

  validation {
    condition     = contains(["dedicated_vpc", "default_vpc_private_subnets"], var.network_strategy)
    error_message = "network_strategy must be dedicated_vpc or default_vpc_private_subnets."
  }
}

variable "vpc_id" {
  description = "Existing VPC ID when network_strategy is default_vpc_private_subnets. Ignored when enable_private_database_infra=false."
  type        = string
  default     = null
}

variable "vpc_cidr" {
  description = "CIDR for a dedicated VPC when network_strategy is dedicated_vpc."
  type        = string
  default     = "10.42.0.0/16"
}

variable "availability_zones" {
  description = "Two AZs for public, private app, and private DB subnets."
  type        = list(string)
  default     = ["us-east-1a", "us-east-1b"]
}

variable "public_subnet_cidrs" {
  description = "Public subnet CIDRs for dedicated VPC strategy."
  type        = list(string)
  default     = ["10.42.0.0/24", "10.42.1.0/24"]
}

variable "private_app_subnet_cidrs" {
  description = "Private app subnet CIDRs for users-service-lambda."
  type        = list(string)
  default     = ["10.42.10.0/24", "10.42.11.0/24"]
}

variable "private_db_subnet_cidrs" {
  description = "Private DB subnet CIDRs for RDS and RDS Proxy."
  type        = list(string)
  default     = ["10.42.20.0/24", "10.42.21.0/24"]
}

variable "nat_public_subnet_id" {
  description = "Existing public subnet for NAT Gateway when reusing default VPC. Ignored for dedicated VPC."
  type        = string
  default     = null
}

variable "postgres_port" {
  description = "PostgreSQL port exposed by RDS Proxy."
  type        = number
  default     = 5432
}

variable "postgres_db" {
  description = "PostgreSQL database name for private RDS. Ignored when enable_private_database_infra=false."
  type        = string
  default     = null
}

variable "postgres_user" {
  description = "PostgreSQL username for private RDS. Ignored when enable_private_database_infra=false."
  type        = string
  default     = null
}

variable "postgres_password" {
  description = "PostgreSQL password for private RDS and optional DB secret. Ignored when enable_private_database_infra=false."
  type        = string
  default     = null
  sensitive   = true
}

variable "postgres_sslmode" {
  description = "PostgreSQL sslmode for RDS Proxy connections."
  type        = string
  default     = "require"
}

variable "rds_instance_class" {
  description = "Lab-friendly RDS PostgreSQL instance class."
  type        = string
  default     = "db.t3.micro"
}

variable "rds_allocated_storage" {
  description = "Allocated storage in GB for lab RDS PostgreSQL."
  type        = number
  default     = 20
}

variable "create_db_secret" {
  description = "Create a Secrets Manager secret for RDS Proxy auth. May be blocked in AWS Lab."
  type        = bool
  default     = true
}

variable "db_secret_arn" {
  description = "Existing Secrets Manager secret ARN for RDS Proxy auth. Required if create_db_secret=false and private database infra is enabled."
  type        = string
  default     = null
}

variable "rds_proxy_role_arn" {
  description = "Existing IAM role ARN for RDS Proxy to read the DB secret. Codex must not use data.aws_iam_role; Fede must provide this if needed."
  type        = string
  default     = null
}

variable "create_rds_proxy" {
  description = "Whether to create RDS Proxy when private database infra is enabled. Requires rds_proxy_role_arn and either create_db_secret=true or db_secret_arn."
  type        = bool
  default     = true
}

variable "users_service_layer_arns" {
  description = "Optional Lambda Layer ARNs for users-service dependencies such as psycopg2-binary. No layer is created by this Terraform."
  type        = list(string)
  default     = []
}
