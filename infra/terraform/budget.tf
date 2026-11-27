data "google_project" "this" {
  depends_on = [google_project_service.api]
}

# Alerts go to the billing account's admins and users (GCP's default recipients).
resource "google_billing_budget" "monthly" {
  billing_account = var.billing_account
  display_name    = "${var.project_id} monthly"

  budget_filter {
    projects = ["projects/${data.google_project.this.number}"]
  }

  amount {
    # No currency_code: the API requires the billing account's own currency.
    specified_amount {
      units = "10"
    }
  }

  threshold_rules {
    threshold_percent = 0.5
  }
  threshold_rules {
    threshold_percent = 0.9
  }
  threshold_rules {
    threshold_percent = 1.0
  }
}
