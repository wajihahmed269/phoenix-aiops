data "oci_identity_availability_domains" "ads" {
  compartment_id = var.compartment_ocid
}

resource "oci_core_vcn" "phoenix" {
  compartment_id = var.compartment_ocid
  cidr_block     = var.vcn_cidr
  display_name   = "phoenix-ops-vcn"
  dns_label      = "phoenixops"
  freeform_tags  = var.freeform_tags
}

resource "oci_core_internet_gateway" "phoenix" {
  compartment_id = var.compartment_ocid
  vcn_id         = oci_core_vcn.phoenix.id
  display_name   = "phoenix-ops-igw"
  enabled        = true
  freeform_tags  = var.freeform_tags
}

resource "oci_core_route_table" "public" {
  compartment_id = var.compartment_ocid
  vcn_id         = oci_core_vcn.phoenix.id
  display_name   = "phoenix-ops-public-rt"
  freeform_tags  = var.freeform_tags

  route_rules {
    destination       = "0.0.0.0/0"
    destination_type  = "CIDR_BLOCK"
    network_entity_id = oci_core_internet_gateway.phoenix.id
  }
}

resource "oci_core_subnet" "public" {
  compartment_id             = var.compartment_ocid
  vcn_id                     = oci_core_vcn.phoenix.id
  cidr_block                 = var.public_subnet_cidr
  display_name               = "phoenix-ops-public-subnet"
  dns_label                  = "public"
  route_table_id             = oci_core_route_table.public.id
  prohibit_public_ip_on_vnic = false
  freeform_tags              = var.freeform_tags
}

