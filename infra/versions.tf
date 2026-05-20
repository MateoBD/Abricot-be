terraform {
  required_version = ">= 1.6.0"

  # ---------------------------------------------------------------------------
  # LOCAL ONLY - DO NOT PUSH / DO NOT MERGE
  # Temporarily disabled by Fede to use local terraform.tfstate while testing
  # reservation availability hotfixes in AWS Academy.
  #
  # To rollback this local-only change:
  # 1. Uncomment the backend "s3" block below.
  # 2. Run: terraform init -reconfigure
  #
  # The dev/main branch must keep the S3 backend/pipeline work.
  # ---------------------------------------------------------------------------
  # backend "s3" {
  #   key     = "abricot-be/terraform.tfstate"
  #   region  = "us-east-1"
  #   encrypt = true
  # }

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
