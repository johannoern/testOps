########### Global ###########

terraform {
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "4.23.0"
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

output "lambda_arns" {
  value = {for func in var.amazon.functions : func.function_name => aws_lambda_function.test_lambda[func.function_name].arn}
}
