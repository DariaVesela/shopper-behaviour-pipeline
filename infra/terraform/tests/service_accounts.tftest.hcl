# Tests against a mocked Google provider: no credentials or network needed.

mock_provider "google" {
  source = "./tests/mocks"
}

variables {
  project_id      = "test-project"
  billing_account = "000000-000000-000000"
}

run "creates_one_service_account_per_component" {
  command = plan

  assert {
    condition = { for name, account in google_service_account.component : name => account.account_id } == {
      kafka-connect = "kafka-connect-sa"
      grafana       = "grafana-sa"
      beam          = "beam-sa"
    }
    error_message = "There should be one service account each for kafka-connect, grafana and beam."
  }
}

run "only_grafana_and_beam_can_run_bigquery_jobs" {
  command = plan

  assert {
    condition = { for name, binding in google_project_iam_member.bigquery_job_user : name => binding.role } == {
      grafana = "roles/bigquery.jobUser"
      beam    = "roles/bigquery.jobUser"
    }
    error_message = "Only grafana and beam should get the project-wide BigQuery Job User role."
  }
}

run "outputs_each_component_service_account_email" {
  # apply, against the mock: emails are only known once the accounts exist.
  command = apply

  override_resource {
    target = google_service_account.component["beam"]
    values = {
      email  = "beam-sa@test-project.iam.gserviceaccount.com"
      member = "serviceAccount:beam-sa@test-project.iam.gserviceaccount.com"
    }
  }

  assert {
    condition     = toset(keys(output.service_account_emails)) == toset(["kafka-connect", "grafana", "beam"])
    error_message = "The emails output should be keyed by component."
  }
  assert {
    condition     = output.service_account_emails["beam"] == "beam-sa@test-project.iam.gserviceaccount.com"
    error_message = "The emails output should give each account's email."
  }
}
