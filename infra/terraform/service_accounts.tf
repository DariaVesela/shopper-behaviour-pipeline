# One identity per component. Resource roles are granted by the ticket that creates each
# resource, scoped to that resource. Keys are made by `make keys`, never here, so no private
# key ever lands in Terraform state. Account IDs need 6+ characters, hence the -sa suffix.
resource "google_service_account" "component" {
  for_each = toset(["kafka-connect", "grafana", "beam"])

  account_id   = "${each.key}-sa"
  display_name = "${each.key} (shopper pipeline)"

  depends_on = [google_project_service.api]
}

# Project-wide only because BigQuery has no narrower way to let an identity run query jobs.
resource "google_project_iam_member" "bigquery_job_user" {
  for_each = toset(["grafana", "beam"])

  project = var.project_id
  role    = "roles/bigquery.jobUser"
  member  = google_service_account.component[each.key].member
}

output "service_account_emails" {
  description = "Each component's service account email, keyed by component; read by make keys."
  value       = { for name, account in google_service_account.component : name => account.email }
}
