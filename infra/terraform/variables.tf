variable "project_id" {
  description = "Google Cloud project ID."
  type        = string
}

variable "location" {
  description = "Primary location for the buckets and BigQuery dataset."
  type        = string
  default     = "US"
}

variable "raw_bucket_name" {
  description = "Name of the raw telemetry bucket."
  type        = string
}

variable "curated_bucket_name" {
  description = "Name of the curated telemetry bucket."
  type        = string
}

variable "bigquery_dataset_id" {
  description = "BigQuery dataset for telemetry analytics."
  type        = string
  default     = "telemetry"
}

variable "service_account_id" {
  description = "Service account ID used by the FastAPI app."
  type        = string
  default     = "fleet-data-ml-ai"
}

variable "labels" {
  description = "Common labels applied to Terraform-managed resources."
  type        = map(string)
  default = {
    app     = "fleet-data-ml-ai"
    managed = "terraform"
  }
}

