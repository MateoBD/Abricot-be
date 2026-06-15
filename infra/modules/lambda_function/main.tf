terraform {
  required_version = ">= 1.6.0"

  required_providers {
    archive = {
      source  = "hashicorp/archive"
      version = "~> 2.4"
    }

    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
}

# Package the service source directory into a deterministic ZIP. The
# output_base64sha256 drives source_code_hash so Lambda redeploys only when the
# packaged code actually changes.
data "archive_file" "this" {
  type        = "zip"
  source_dir  = var.source_dir
  excludes    = var.excludes
  output_path = "${path.module}/.artifacts/${var.function_name}.zip"
}

resource "aws_lambda_function" "this" {
  function_name    = var.function_name
  filename         = data.archive_file.this.output_path
  handler          = var.handler
  role             = var.role_arn
  runtime          = var.runtime
  source_code_hash = data.archive_file.this.output_base64sha256
  timeout          = var.timeout
  memory_size      = var.memory_size

  dynamic "environment" {
    for_each = length(var.environment) > 0 ? [1] : []
    content {
      variables = var.environment
    }
  }

  dynamic "vpc_config" {
    for_each = var.vpc_config != null ? [var.vpc_config] : []
    content {
      subnet_ids         = vpc_config.value.subnet_ids
      security_group_ids = vpc_config.value.security_group_ids
    }
  }
}
