resource "oci_core_network_security_group" "phoenix_nodes" {
  compartment_id = var.compartment_ocid
  vcn_id         = oci_core_vcn.phoenix.id
  display_name   = "phoenix-ops-nodes-nsg"
  freeform_tags  = var.freeform_tags
}

resource "oci_core_network_security_group_security_rule" "ssh_from_operator" {
  network_security_group_id = oci_core_network_security_group.phoenix_nodes.id
  direction                 = "INGRESS"
  protocol                  = "6"
  source                    = var.ssh_ingress_cidr
  source_type               = "CIDR_BLOCK"
  description               = "SSH from operator public IP only"

  tcp_options {
    destination_port_range {
      min = 22
      max = 22
    }
  }
}

resource "oci_core_network_security_group_security_rule" "internal_vcn" {
  network_security_group_id = oci_core_network_security_group.phoenix_nodes.id
  direction                 = "INGRESS"
  protocol                  = "all"
  source                    = var.vcn_cidr
  source_type               = "CIDR_BLOCK"
  description               = "Internal Phoenix-Ops VCN traffic for K3s and workloads"
}

resource "oci_core_network_security_group_security_rule" "egress_all" {
  network_security_group_id = oci_core_network_security_group.phoenix_nodes.id
  direction                 = "EGRESS"
  protocol                  = "all"
  destination               = "0.0.0.0/0"
  destination_type          = "CIDR_BLOCK"
  description               = "Outbound package updates and image pulls"
}


resource "oci_core_default_security_list" "phoenix" {
  manage_default_resource_id = oci_core_vcn.phoenix.default_security_list_id
  display_name               = "phoenix-ops-default-security-list"
  freeform_tags              = var.freeform_tags

  egress_security_rules {
    protocol    = "all"
    destination = "0.0.0.0/0"
  }
}
