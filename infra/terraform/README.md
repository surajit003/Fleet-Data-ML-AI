# GCP Terraform

This directory provisions the minimum GCP resources for the telemetry pipeline:

- a service account for the FastAPI app
- a raw Cloud Storage bucket
- a curated Cloud Storage bucket
- a BigQuery dataset
- IAM bindings for storage and analytics

## Files

- `versions.tf` pins the Google provider
- `variables.tf` defines the environment-specific inputs
- `main.tf` creates the resources and IAM bindings
- `outputs.tf` exposes the values the app will need

## Usage

```bash
cd infra/terraform
terraform init
terraform plan -var-file=terraform.tfvars
terraform apply -var-file=terraform.tfvars
```

Copy `terraform.tfvars.example` to `terraform.tfvars` and fill in your project ID first.

## Notes

- The buckets have uniform bucket-level access enabled.
- Public access prevention is enforced.
- The service account gets bucket object admin access and BigQuery job/dataset permissions.
- This is enough for the first production-like GCP slice. You can add BigLake/Iceberg later.

