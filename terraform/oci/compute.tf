locals {
  nodes = {
    control-plane = {
      display_name = "phoenix-node-control-plane"
      role         = "control-plane"
    }
    app = {
      display_name = "phoenix-node-app"
      role         = "app"
    }
    observatory = {
      display_name = "phoenix-node-observatory"
      role         = "observability"
    }
    ai-ops = {
      display_name = "phoenix-node-ai-ops"
      role         = "ai-ops"
    }
    ollama = {
      display_name = "phoenix-node-ollama"
      role         = "ollama"
    }
  }
}

data "oci_core_images" "ubuntu" {
  count = var.instance_image_ocid == null ? 1 : 0

  compartment_id           = var.compartment_ocid
  operating_system         = var.ubuntu_operating_system
  operating_system_version = var.ubuntu_operating_system_version
  shape                    = var.instance_shape
  sort_by                  = "TIMECREATED"
  sort_order               = "DESC"
}

resource "oci_core_instance" "phoenix_nodes" {
  for_each = local.nodes

  availability_domain = data.oci_identity_availability_domains.ads.availability_domains[0].name
  compartment_id      = var.compartment_ocid
  display_name        = each.value.display_name
  shape               = var.instance_shape
  freeform_tags = merge(var.freeform_tags, {
    Name = each.value.display_name
    Role = each.value.role
  })

  shape_config {
    ocpus         = var.instance_ocpus
    memory_in_gbs = var.instance_memory_gbs
  }

  create_vnic_details {
    subnet_id        = oci_core_subnet.public.id
    assign_public_ip = true
    hostname_label   = replace(each.key, "-", "")
    nsg_ids          = [oci_core_network_security_group.phoenix_nodes.id]
    freeform_tags = merge(var.freeform_tags, {
      Name = each.value.display_name
      Role = each.value.role
    })
  }

  metadata = {
    ssh_authorized_keys = var.ssh_public_key
  }

  source_details {
    source_type             = "image"
    source_id               = var.instance_image_ocid != null ? var.instance_image_ocid : data.oci_core_images.ubuntu[0].images[0].id
    boot_volume_size_in_gbs = var.boot_volume_size_gbs
  }
}

