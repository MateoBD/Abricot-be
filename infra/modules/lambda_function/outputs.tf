output "function_name" {
  description = "Created Lambda function name."
  value       = aws_lambda_function.this.function_name
}

output "arn" {
  description = "Created Lambda function ARN."
  value       = aws_lambda_function.this.arn
}

output "invoke_arn" {
  description = "Invoke ARN used by API Gateway integrations."
  value       = aws_lambda_function.this.invoke_arn
}
