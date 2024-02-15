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

module "ecs-cluster-terraform" {
  source  = "git::https://github.com/pogo61/terraform-ecs-cluster-module.git"
}

module "iam" {
  source  = "terraform-aws-modules/iam/aws"
}

module "alb" {
  source  = "terraform-aws-modules/alb/aws"
  version = "9.7.0"
}

#module "ecs" {
#  source  = "terraform-aws-modules/ecs/aws"
#  version = "5.9.0"
#}



resource "aws_ssm_parameter" "validated_image" {
  name  = "/core_infrastructure/latest_ecs_ami"
  type  = "String"
  value = data.aws_ssm_parameter.ecs_ami.value
}
