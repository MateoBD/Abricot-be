provider "aws" {
  region = var.aws_region
  # AWS Academy Lab (voc-cancel-cred policy) blocks tagging on API Gateway and
  # CloudWatch resources. default_tags removed to avoid AccessDeniedException on apply.
}
