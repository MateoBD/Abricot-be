# `lambda_function` custom module

Reusable building block for every Lambda in the Abricot TP3 stack. It owns the
two concerns that were previously duplicated per function in the root module:

1. Packaging the service source directory into a deterministic ZIP
   (`archive_file`), driving `source_code_hash` so redeploys happen only when the
   code changes.
2. Creating the `aws_lambda_function`, with optional environment variables and
   optional VPC attachment expressed through `dynamic` blocks.

## Usage

```hcl
module "lambda" {
  source   = "./modules/lambda_function"
  for_each = local.lambda_functions

  function_name = "${local.name_prefix}-${replace(each.key, "_", "-")}"
  source_dir    = each.value.source_dir
  handler       = each.value.handler
  runtime       = local.lambda_runtime
  role_arn      = local.lab_role_arn
  timeout       = each.value.timeout
  excludes      = each.value.excludes
  environment   = lookup(local.lambda_environment, each.key, {})

  vpc_config = each.value.vpc_enabled ? {
    subnet_ids         = each.value.subnet_ids
    security_group_ids = each.value.security_group_ids
  } : null
}
```

## Inputs

| Name | Type | Default | Description |
|------|------|---------|-------------|
| `function_name` | string | — | Fully qualified Lambda name. |
| `source_dir` | string | — | Directory packaged into the ZIP. |
| `handler` | string | — | Handler entrypoint. |
| `runtime` | string | — | Lambda runtime. |
| `role_arn` | string | — | Execution role ARN (LabRole). |
| `timeout` | number | `10` | Timeout in seconds (validated 1–900). |
| `excludes` | list(string) | `[]` | Paths excluded from the ZIP. |
| `environment` | map(string) | `{}` | Environment variables. |
| `vpc_config` | object/null | `null` | Optional VPC attachment. |

## Outputs

| Name | Description |
|------|-------------|
| `function_name` | Created function name. |
| `arn` | Function ARN. |
| `invoke_arn` | Invoke ARN for API Gateway integrations. |
