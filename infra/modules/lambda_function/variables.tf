variable "function_name" {
  description = "Fully qualified Lambda function name."
  type        = string
}

variable "source_dir" {
  description = "Directory packaged into the Lambda deployment ZIP."
  type        = string
}

variable "handler" {
  description = "Lambda handler entrypoint (module.function)."
  type        = string
}

variable "runtime" {
  description = "Lambda runtime identifier."
  type        = string
}

variable "role_arn" {
  description = "IAM role ARN assumed by the Lambda function."
  type        = string
}

variable "timeout" {
  description = "Lambda timeout in seconds."
  type        = number
  default     = 10

  validation {
    condition     = var.timeout >= 1 && var.timeout <= 900
    error_message = "timeout must be between 1 and 900 seconds."
  }
}

variable "memory_size" {
  description = "Lambda memory in MB. Also scales CPU; 128 (AWS floor) gives minimal CPU."
  type        = number
  default     = 128

  validation {
    condition     = var.memory_size >= 128 && var.memory_size <= 10240
    error_message = "memory_size must be between 128 and 10240 MB."
  }
}

variable "excludes" {
  description = "Paths excluded from the deployment ZIP."
  type        = list(string)
  default     = []
}

variable "environment" {
  description = "Environment variables injected into the Lambda."
  type        = map(string)
  default     = {}
}

variable "vpc_config" {
  description = "Optional VPC attachment. Set to null to run the Lambda outside the VPC."
  type = object({
    subnet_ids         = list(string)
    security_group_ids = list(string)
  })
  default = null
}
