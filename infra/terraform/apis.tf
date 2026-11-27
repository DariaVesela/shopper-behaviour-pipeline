resource "google_project_service" "api" {
  for_each = toset([
    "bigquery.googleapis.com",
    "pubsub.googleapis.com",
    "storage.googleapis.com",
    "dataflow.googleapis.com",
    "iam.googleapis.com",
    "billingbudgets.googleapis.com",
    # Needed to look up the project number for the budget.
    "cloudresourcemanager.googleapis.com",
  ])

  service = each.key

  # Destroy leaves the APIs on: turning one off can break resources outside this config,
  # and several of these were on before Terraform managed them.
  disable_on_destroy = false
}
