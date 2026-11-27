provider "google" {
  project = var.project_id
  region  = var.region

  # Every resource that supports labels gets these.
  default_labels = {
    project = "capstone"
  }

  # The Billing Budgets API needs a quota project when called with user credentials.
  user_project_override = true
  billing_project       = var.project_id
}
