########### Global ###########

terraform {
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "4.23.0"
    }
    google = {
      source  = "hashicorp/google"
      version = "4.30.0"
    }
  }
}

variable "project_name" {
  type    = string
  default = "Baas"
}

variable "amazon" {
  type = object({
    function_src = string
    region      = string
    functions   = list(
      object({
        function_name = string,
        memory        = number,
        handler       = string,
        timeout       = number
      }))
  })
} 

########### Lambda ###########

resource "aws_iam_role" "iam_for_lambda"{
  name = "iam_for_lambda_${var.project_name}"
  assume_role_policy = <<EOF
  {
 "Version": "2012-10-17",
 "Statement": [
   {
     "Action": "sts:AssumeRole",
     "Principal": {
       "Service": "lambda.amazonaws.com"
     },
     "Effect": "Allow",
     "Sid": ""
   }
 ]
}
EOF
}
  

resource "aws_lambda_function" "test_lambda" {
  for_each = {for func in var.amazon.functions : func.function_name => func}

  filename         = var.amazon.function_src
  function_name    = each.value.function_name
  role             = aws_iam_role.iam_for_lambda.arn
  handler          = each.value.handler
  memory_size      = each.value.memory
  timeout          = each.value.timeout
  source_code_hash = filebase64sha256(var.amazon.function_src)

  runtime = "java11"
}

#TODO source from tfvars
resource "aws_lambda_function" "no_op_function"{
  function_name = "testOps_no_op_function"
  role          = aws_iam_role.iam_for_lambda.arn
  handler       = "lambda_function.lambda_handler"
  memory_size   = 256
  timeout = 3
  filename = "../Baas/templates/testOps_no_op.zip"
  source_code_hash = filebase64sha256("../Baas/templates/testOps_no_op.zip")
  runtime       = "python3.9"
}

output "lambda_arns" {
  value = {for func in var.amazon.functions : func.function_name => aws_lambda_function.test_lambda[func.function_name].arn}
}

########### GCP ###########

variable "gcp" {
  type = object({
    function_src = string,
    project      = string,
    region       = string,
    functions    = list(
      object({
        function_name = string,
        memory        = number,
        handler       = string,
        timeout       = number
      })
    )
  })
  default = {
    function_src = ""
    project      = ""
    region       = "us-east1"
    functions    = []
  }
}

provider "google" {
  project = var.gcp.project
  region  = "us-central1"
}

#TODO including the project name in the bucket name would be good
resource "google_storage_bucket" "gcp_bucket" {
  name     = "baas-jfops-bucket"
  location = var.gcp.region
}

resource "google_storage_bucket_object" "jar" {
  name   = "output.zip"
  bucket = google_storage_bucket.gcp_bucket.name
  source = var.gcp.function_src
}

#TODO source also from tfvars
resource "google_storage_bucket_object" "no_op" {
  name   = "testOps_no_op.zip "
  bucket = google_storage_bucket.gcp_bucket.name
  source = "../Baas/templates/testOps_no_op.zip"
}

resource "google_cloudfunctions_function" "function" {
  for_each = {for func in var.gcp.functions : func.function_name => func}

  name        = each.value.function_name
  description = "jfOps Function"
  runtime     = "java11"

  available_memory_mb   = each.value.memory
  timeout               = each.value.timeout
  source_archive_bucket = google_storage_bucket.gcp_bucket.name
  source_archive_object = google_storage_bucket_object.jar.name
  trigger_http          = true
  entry_point           = each.value.handler
  max_instances         = 1
}

resource "google_cloudfunctions_function" "no_op_function" {
  name        = "testOps_no_op_function"
  runtime     = "python39"

  available_memory_mb   = 256
  timeout               = 3
  source_archive_bucket = google_storage_bucket.gcp_bucket.name
  source_archive_object = google_storage_bucket_object.no_op.name
  trigger_http          = true
  entry_point           = "entry_handler"
  max_instances         = 1
}

resource "google_cloudfunctions_function_iam_member" "invoker" {
  for_each = {for func in var.gcp.functions : func.function_name => func}

  project        = google_cloudfunctions_function.function[each.key].project
  region         = google_cloudfunctions_function.function[each.key].region
  cloud_function = google_cloudfunctions_function.function[each.key].name

  role   = "roles/cloudfunctions.invoker"
  member = "allUsers"
}

output "gcp_uris" {
  value = {for func in var.gcp.functions : func.function_name => google_cloudfunctions_function.function[func.function_name].https_trigger_url}
}
