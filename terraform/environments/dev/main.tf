terraform {
  required_version = ">= 1.6.0"
  required_providers {
    aws = { source = "hashicorp/aws", version = "~> 6.0" }
  }
}

provider "aws" { region = var.aws_region }

module "vpc" {
  source            = "../../modules/vpc"
  name              = var.project_name
  cidr              = "10.42.0.0/16"
  availability_zone = "${var.aws_region}a"
}

resource "aws_security_group" "k3s" {
  name   = "${var.project_name}-k3s"
  vpc_id = module.vpc.vpc_id
  ingress {
    description = "HTTP"
    from_port   = 80
    to_port     = 80
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }
  ingress {
    description = "SSH"
    from_port   = 22
    to_port     = 22
    protocol    = "tcp"
    cidr_blocks = [var.ssh_cidr]
  }
  ingress {
    description = "Kubernetes API"
    from_port   = 6443
    to_port     = 6443
    protocol    = "tcp"
    cidr_blocks = [var.ssh_cidr]
  }
  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }
}

module "iam" {
  source = "../../modules/iam"
  name   = var.project_name
}
module "ec2" {
  source                = "../../modules/ec2"
  name                  = "${var.project_name}-k3s"
  subnet_id             = module.vpc.public_subnet_id
  security_group_id     = aws_security_group.k3s.id
  instance_profile_name = module.iam.instance_profile_name
  instance_type         = var.instance_type
}
