provider "google" {
  project = var.project_id
}

locals {
  service_account_email = "${var.service_account_id}@${var.project_id}.iam.gserviceaccount.com"
}

resource "google_project_service" "bigquery" {
  project = var.project_id
  service = "bigquery.googleapis.com"
}

resource "google_project_service" "storage" {
  project = var.project_id
  service = "storage.googleapis.com"
}

resource "google_project_service" "iam" {
  project = var.project_id
  service = "iam.googleapis.com"
}

resource "google_project_service" "cloudresourcemanager" {
  project = var.project_id
  service = "cloudresourcemanager.googleapis.com"
}

resource "google_service_account" "app" {
  project      = var.project_id
  account_id   = var.service_account_id
  display_name = "Fleet Data ML AI app service account"
}

resource "google_storage_bucket" "raw" {
  name                        = var.raw_bucket_name
  location                    = var.location
  uniform_bucket_level_access = true
  public_access_prevention    = "enforced"
  force_destroy               = false
  labels                      = var.labels

  versioning {
    enabled = true
  }

  lifecycle_rule {
    action {
      type = "Delete"
    }
    condition {
      age = 30
    }
  }

  depends_on = [
    google_project_service.storage,
  ]
}

resource "google_storage_bucket" "curated" {
  name                        = var.curated_bucket_name
  location                    = var.location
  uniform_bucket_level_access = true
  public_access_prevention    = "enforced"
  force_destroy               = false
  labels                      = var.labels

  versioning {
    enabled = true
  }

  depends_on = [
    google_project_service.storage,
  ]
}

resource "google_bigquery_dataset" "telemetry" {
  dataset_id                 = var.bigquery_dataset_id
  project                    = var.project_id
  location                   = var.location
  delete_contents_on_destroy = false
  labels                     = var.labels

  depends_on = [
    google_project_service.bigquery,
  ]
}

resource "google_storage_bucket_iam_member" "raw_object_admin" {
  bucket = google_storage_bucket.raw.name
  role   = "roles/storage.objectAdmin"
  member = "serviceAccount:${local.service_account_email}"
}

resource "google_storage_bucket_iam_member" "curated_object_admin" {
  bucket = google_storage_bucket.curated.name
  role   = "roles/storage.objectAdmin"
  member = "serviceAccount:${local.service_account_email}"
}

resource "google_project_iam_member" "bigquery_job_user" {
  project = var.project_id
  role    = "roles/bigquery.jobUser"
  member  = "serviceAccount:${local.service_account_email}"
}

resource "google_bigquery_dataset_iam_member" "bigquery_data_editor" {
  dataset_id = google_bigquery_dataset.telemetry.dataset_id
  project    = var.project_id
  role       = "roles/bigquery.dataEditor"
  member     = "serviceAccount:${local.service_account_email}"
}

