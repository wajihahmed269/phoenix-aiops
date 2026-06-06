variable "region" {
  description = "OCI region for Phoenix-Ops."
  type        = string
  default     = "me-jeddah-1"
}

variable "compartment_ocid" {
  description = "OCI compartment OCID where Phoenix-Ops lab resources will be created."
  type        = string
}

variable "vcn_cidr" {
  description = "CIDR block for the Phoenix-Ops OCI VCN."
  type        = string
  default     = "10.0.0.0/16"
}

variable "public_subnet_cidr" {
  description = "CIDR block for the public SSH subnet."
  type        = string
  default     = "10.0.1.0/24"
}

variable "ssh_ingress_cidr" {
  description = "Public CIDR allowed to SSH to lab nodes, for example 203.0.113.5/32. Do not use 0.0.0.0/0."
  type        = string

  validation {
    condition     = can(cidrhost(var.ssh_ingress_cidr, 0)) && var.ssh_ingress_cidr != "0.0.0.0/0"
    error_message = "ssh_ingress_cidr must be a valid CIDR and must not be 0.0.0.0/0."
  }
}

variable "ssh_public_key" {
  description = "Public SSH key content authorized on each instance."
  type        = string
  sensitive   = true
}

variable "instance_shape" {
  description = "Default OCI compute shape for Phoenix-Ops nodes. Review cost and availability before provisioning."
  type        = string
  default     = "VM.Standard.E3.Flex"
}

variable "instance_ocpus" {
  description = "OCPUs for flexible OCI shapes."
  type        = number
  default     = 1
}

variable "instance_memory_gbs" {
  description = "Memory in GB for flexible OCI shapes."
  type        = number
  default     = 6
}

variable "boot_volume_size_gbs" {
  description = "Boot volume size in GB for each lab node."
  type        = number
  default     = 50
}

variable "ubuntu_operating_system" {
  description = "OCI image operating system filter."
  type        = string
  default     = "Canonical Ubuntu"
}

variable "ubuntu_operating_system_version" {
  description = "OCI image operating system version filter."
  type        = string
  default     = "22.04"
}

variable "instance_image_ocid" {
  description = "Optional Ubuntu image OCID. Leave null to use the latest matching OCI platform image lookup."
  type        = string
  default     = null
}

variable "freeform_tags" {
  description = "Freeform tags applied to Phoenix-Ops OCI resources."
  type        = map(string)
  default = {
    Project     = "phoenix-ops"
    Environment = "lab"
    ManagedBy   = "terraform"
  }
}

