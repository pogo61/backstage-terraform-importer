provider "aws" {
  region = var.aws_region
}

terraform {
  backend "s3" {
    region         = "eu-west-2"
    bucket         = "japara-terraform-state"
    key            = "platform/test-terraform.tfstate"
    dynamodb_table = "platform-terraform-locks"
    encrypt        = true
  }
}

module "eks_example_fargate_profile" {
  source  = "terraform-aws-modules/eks/aws//examples/fargate_profile"
  version = "20.2.1"
}

resource "aws_ssm_parameter" "validated_image" {
  name  = "/core_infrastructure/latest_ecs_ami"
  type  = "String"
  value = data.aws_ssm_parameter.ecs_ami.value
}
