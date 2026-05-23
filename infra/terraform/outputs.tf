output "service_account_email" {
  description = "Service account email for the app."
  value       = google_service_account.app.email
}

output "raw_bucket_name" {
  description = "Raw telemetry bucket name."
  value       = google_storage_bucket.raw.name
}

output "curated_bucket_name" {
  description = "Curated telemetry bucket name."
  value       = google_storage_bucket.curated.name
}

output "bigquery_dataset_id" {
  description = "BigQuery telemetry dataset ID."
  value       = google_bigquery_dataset.telemetry.dataset_id
}

