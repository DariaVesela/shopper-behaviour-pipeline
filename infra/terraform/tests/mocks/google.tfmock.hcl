# Defaults for the mocked Google provider shared by every test file.

# IAM bindings reject the mock's random strings, so give every account a well-formed member.
mock_resource "google_service_account" {
  defaults = {
    member = "serviceAccount:mock-sa@test-project.iam.gserviceaccount.com"
  }
}
