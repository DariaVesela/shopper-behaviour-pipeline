terraform {
  required_version = ">= 1.14"

  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "~> 8.12"
    }
  }

  # The bucket is private, so it comes from the gitignored backend.hcl:
  # terraform init -backend-config=backend.hcl (make tf-init does this).
  backend "gcs" {
    prefix = "foundation"
  }
}
