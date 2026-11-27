# Raw event files and scratch space for the pipeline's jobs.
resource "google_storage_bucket" "data" {
  name     = "${var.project_id}-data"
  location = upper(var.region)

  uniform_bucket_level_access = true
  public_access_prevention    = "enforced"

  # Destroy fails while the bucket holds files, so the raw data is never wiped by accident.
  force_destroy = false

  # Jobs write scratch files under tmp/; nothing else expires.
  lifecycle_rule {
    action {
      type = "Delete"
    }
    condition {
      age            = 7
      matches_prefix = ["tmp/"]
    }
  }

  depends_on = [google_project_service.api]
}
