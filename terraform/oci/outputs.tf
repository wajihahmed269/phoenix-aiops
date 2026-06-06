output "node_instance_ids" {
  description = "OCI instance OCIDs by Phoenix-Ops node role."
  value = {
    for role, node in oci_core_instance.phoenix_nodes :
    role => node.id
  }
}

output "node_private_ips" {
  description = "Private IPs for internal K3s and workload communication."
  value = {
    for role, node in oci_core_instance.phoenix_nodes :
    role => node.private_ip
  }
}

output "node_public_ips" {
  description = "Public IPs for SSH from the operator laptop only."
  value = {
    for role, node in oci_core_instance.phoenix_nodes :
    role => node.public_ip
  }
}

output "control_plane_public_ip" {
  description = "Control-plane public IP for SSH tunnel access."
  value       = oci_core_instance.phoenix_nodes["control-plane"].public_ip
}

output "control_plane_private_ip" {
  description = "Control-plane private IP for K3s worker join configuration."
  value       = oci_core_instance.phoenix_nodes["control-plane"].private_ip
}

output "ssh_commands" {
  description = "SSH commands for OCI lab nodes. Adjust the private key path as needed."
  value = {
    for role, node in oci_core_instance.phoenix_nodes :
    role => "ssh ubuntu@${node.public_ip}"
  }
}

