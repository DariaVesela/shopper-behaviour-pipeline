# Plan-only tests against a mocked Google provider: no credentials or network needed.

mock_provider "google" {}

variables {
  project_id      = "test-project"
  billing_account = "000000-000000-000000"
}

run "enables_the_apis_the_pipeline_needs" {
  command = plan

  assert {
    condition = toset(keys(google_project_service.api)) == toset([
      "bigquery.googleapis.com",
      "pubsub.googleapis.com",
      "storage.googleapis.com",
      "dataflow.googleapis.com",
      "iam.googleapis.com",
      "billingbudgets.googleapis.com",
      "cloudresourcemanager.googleapis.com",
    ])
    error_message = "The enabled APIs are not the ones the pipeline needs."
  }
}

run "data_bucket_is_private_and_regional" {
  command = plan

  assert {
    condition     = google_storage_bucket.data.name == "test-project-data"
    error_message = "The data bucket should be named after the project."
  }
  assert {
    condition     = google_storage_bucket.data.location == "US-CENTRAL1"
    error_message = "The data bucket should be in the pipeline's region."
  }
  assert {
    condition     = google_storage_bucket.data.uniform_bucket_level_access
    error_message = "The data bucket should use uniform bucket-level access."
  }
  assert {
    condition     = google_storage_bucket.data.public_access_prevention == "enforced"
    error_message = "The data bucket should never be public."
  }
  assert {
    condition     = !google_storage_bucket.data.force_destroy
    error_message = "Destroy should refuse to delete a bucket that still holds data."
  }
}

run "data_bucket_expires_only_tmp_objects_after_7_days" {
  command = plan

  assert {
    condition     = length(google_storage_bucket.data.lifecycle_rule) == 1
    error_message = "The data bucket should have exactly one lifecycle rule."
  }
  assert {
    condition     = one(google_storage_bucket.data.lifecycle_rule[0].action).type == "Delete"
    error_message = "The lifecycle rule should delete objects."
  }
  assert {
    condition     = one(google_storage_bucket.data.lifecycle_rule[0].condition).age == 7
    error_message = "Objects should be deleted after 7 days."
  }
  assert {
    condition     = one(google_storage_bucket.data.lifecycle_rule[0].condition).matches_prefix == tolist(["tmp/"])
    error_message = "Only objects under tmp/ should expire."
  }
}

run "budget_alerts_at_50_90_and_100_percent_of_10_a_month" {
  # apply, against the mock: the project number is only known once the APIs are on.
  command = apply

  override_data {
    target = data.google_project.this
    values = {
      number = "123456789"
    }
  }

  assert {
    condition     = google_billing_budget.monthly.billing_account == "000000-000000-000000"
    error_message = "The budget should watch the configured billing account."
  }
  assert {
    condition     = one(google_billing_budget.monthly.budget_filter).projects == toset(["projects/123456789"])
    error_message = "The budget should count only this project's spend."
  }
  assert {
    condition     = one(one(google_billing_budget.monthly.amount).specified_amount).units == "10"
    error_message = "The budget should be 10 a month."
  }
  assert {
    condition = toset([
      for rule in google_billing_budget.monthly.threshold_rules : rule.threshold_percent
    ]) == toset([0.5, 0.9, 1.0])
    error_message = "The budget should alert at 50%, 90% and 100%."
  }
}
