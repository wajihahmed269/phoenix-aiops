variable "aws_region" {
  description = "AWS region"
  type        = string
  default     = "eu-north-1"
}

variable "ubuntu_ami" {
  description = "Ubuntu 22.04 LTS AMI ID for eu-north-1"
  type        = string
  # Ubuntu 22.04 LTS - eu-north-1 (Stockholm)
  # Always verify at: https://cloud-images.ubuntu.com/locator/ec2/
  default = "ami-07c8c1b18ca66bb07"
}

variable "key_pair_name" {
  description = "Name of existing AWS key pair"
  type        = string
  # This is your existing key pair - matches banking-app.pem
  default = "banking-app"
}

variable "my_ip_cidr" {
  description = "Your public IP in CIDR format e.g. 203.0.113.5/32"
  type        = string
  # NEVER hardcode here - set in terraform.tfvars
}

variable "instance_type" {
  description = "EC2 instance type for Phoenix-Ops nodes"
  type        = string
  default     = "m7i-flex.large"
}

variable "root_volume_size" {
  description = "Root EBS volume size in GB"
  type        = number
  default     = 30
}
