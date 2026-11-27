variable "project_id" {
  description = "The GCP project every resource is created in."
  type        = string
}

variable "region" {
  description = "The region for regional resources."
  type        = string
  default     = "us-central1"
}

variable "billing_account" {
  description = "The billing account ID the budget watches, e.g. 012345-6789AB-CDEF01."
  type        = string
}
