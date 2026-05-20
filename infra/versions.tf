terraform {
  required_version = ">= 1.6.0"

  backend "s3" {
    bucket         = "abricot-terraform-state"
    key            = "abricot-be/terraform.tfstate"
    region         = "us-east-1"
    dynamodb_table = "abricot-terraform-lock"
    encrypt        = true
  }

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
