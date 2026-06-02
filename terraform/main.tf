terraform {
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
}

provider "aws" {
  region = var.aws_region
}

# ─────────────────────────────────────────
# NETWORKING
# ─────────────────────────────────────────

resource "aws_vpc" "phoenix_vpc" {
  cidr_block           = "10.0.0.0/16"
  enable_dns_hostnames = true
  enable_dns_support   = true

  tags = {
    Name    = "phoenix-vpc"
    Project = "phoenix-aiops"
  }
}

resource "aws_subnet" "phoenix_subnet" {
  vpc_id                  = aws_vpc.phoenix_vpc.id
  cidr_block              = "10.0.1.0/24"
  map_public_ip_on_launch = true
  availability_zone       = "${var.aws_region}a"

  tags = {
    Name    = "phoenix-subnet"
    Project = "phoenix-aiops"
  }
}

resource "aws_internet_gateway" "phoenix_igw" {
  vpc_id = aws_vpc.phoenix_vpc.id

  tags = {
    Name    = "phoenix-igw"
    Project = "phoenix-aiops"
  }
}

resource "aws_route_table" "phoenix_rt" {
  vpc_id = aws_vpc.phoenix_vpc.id

  route {
    cidr_block = "0.0.0.0/0"
    gateway_id = aws_internet_gateway.phoenix_igw.id
  }

  tags = {
    Name    = "phoenix-rt"
    Project = "phoenix-aiops"
  }
}

resource "aws_route_table_association" "phoenix_rta" {
  subnet_id      = aws_subnet.phoenix_subnet.id
  route_table_id = aws_route_table.phoenix_rt.id
}

# ─────────────────────────────────────────
# SECURITY GROUP
# ─────────────────────────────────────────

resource "aws_security_group" "phoenix_sg" {
  name        = "phoenix-sg"
  description = "Phoenix AIOps security group"
  vpc_id      = aws_vpc.phoenix_vpc.id

  # SSH from your IP only
  ingress {
    description = "SSH from my IP"
    from_port   = 22
    to_port     = 22
    protocol    = "tcp"
    cidr_blocks = [var.my_ip_cidr]
  }

  # All internal traffic between nodes
  ingress {
    description = "Internal cluster traffic"
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["10.0.0.0/16"]
  }

  # K3s API server - your IP only
  ingress {
    description = "K3s API"
    from_port   = 6443
    to_port     = 6443
    protocol    = "tcp"
    cidr_blocks = [var.my_ip_cidr]
  }

  # K3s API server - Phoenix nodes only
  ingress {
    description = "K3s API between Phoenix nodes"
    from_port   = 6443
    to_port     = 6443
    protocol    = "tcp"
    self        = true
  }

  # Grafana - your IP only
  ingress {
    description = "Grafana"
    from_port   = 30300
    to_port     = 30300
    protocol    = "tcp"
    cidr_blocks = [var.my_ip_cidr]
  }

  # BankApp - your IP only
  ingress {
    description = "BankApp NodePort"
    from_port   = 30080
    to_port     = 30080
    protocol    = "tcp"
    cidr_blocks = [var.my_ip_cidr]
  }

  # Streamlit - your IP only
  ingress {
    description = "Streamlit Dashboard"
    from_port   = 30090
    to_port     = 30090
    protocol    = "tcp"
    cidr_blocks = [var.my_ip_cidr]
  }

  # Outbound - allow all
  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = {
    Name    = "phoenix-sg"
    Project = "phoenix-aiops"
  }
}

# ─────────────────────────────────────────
# KEY PAIR (reuse your existing one)
# ─────────────────────────────────────────

data "aws_key_pair" "phoenix_key" {
  key_name = var.key_pair_name
}

# ─────────────────────────────────────────
# EC2 INSTANCES (5 nodes)
# ─────────────────────────────────────────

locals {
  node_roles = [
    "control-plane",
    "observatory",
    "app",
    "ollama",
    "ai-ops"
  ]
}

resource "aws_instance" "phoenix_nodes" {
  count = 5

  ami                    = var.ubuntu_ami
  instance_type          = var.instance_type
  subnet_id              = aws_subnet.phoenix_subnet.id
  vpc_security_group_ids = [aws_security_group.phoenix_sg.id]
  key_name               = data.aws_key_pair.phoenix_key.key_name

  dynamic "instance_market_options" {
    for_each = var.use_spot_instances ? [1] : []

    content {
      market_type = "spot"

      spot_options {
        instance_interruption_behavior = "stop"
        spot_instance_type             = "persistent"
      }
    }
  }

  root_block_device {
    volume_size = var.root_volume_size
    volume_type = "gp3"
  }

  tags = {
    Name    = "phoenix-node-${local.node_roles[count.index]}"
    Role    = local.node_roles[count.index]
    Project = "phoenix-aiops"
  }
}
