output "node_public_ips" {
  description = "Public IPs of all 5 nodes - paste directly into Ansible inventory"
  value = {
    for i, node in aws_instance.phoenix_nodes :
    local.node_roles[i] => node.public_ip
  }
}

output "node_private_ips" {
  description = "Private IPs - used for internal cluster communication"
  value = {
    for i, node in aws_instance.phoenix_nodes :
    local.node_roles[i] => node.private_ip
  }
}

output "control_plane_public_ip" {
  description = "Node 1 public IP - for kubectl access"
  value       = aws_instance.phoenix_nodes[0].public_ip
}

output "ollama_private_ip" {
  description = "Node 4 private IP - used in Python bridge config"
  value       = aws_instance.phoenix_nodes[3].private_ip
}

output "ssh_commands" {
  description = "Ready-to-use SSH commands for each node"
  value = {
    for i, node in aws_instance.phoenix_nodes :
    local.node_roles[i] => "ssh -i ~/.ssh/banking-app.pem ubuntu@${node.public_ip}"
  }
}
