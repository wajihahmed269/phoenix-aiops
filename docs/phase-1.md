# Phoenix AIOps — Phase 1: Infrastructure

## Before You Start

1. Find your public IP:
   ```bash
   curl ifconfig.me
   ```

2. Open `terraform/terraform.tfvars` and replace `YOUR_PUBLIC_IP/32` with your actual IP.

3. Verify your PEM key is in place:
   ```bash
   ls ~/.ssh/banking-app.pem
   chmod 400 ~/.ssh/banking-app.pem
   ```

---

## Step 1: Terraform — Provision 5 Nodes

```bash
cd terraform/

# Install providers
terraform init

# Preview what will be created
terraform plan

# Create the 5 nodes
terraform apply
```

After apply, you will see output like:
```
node_public_ips = {
  "ai-ops"         = "X.X.X.X"
  "app"            = "X.X.X.X"
  "control-plane"  = "X.X.X.X"
  "observatory"    = "X.X.X.X"
  "ollama"         = "X.X.X.X"
}
```

Copy these IPs into `ansible/inventory.ini` before running Ansible.

---

## Step 2: Update Ansible Inventory

Open `ansible/inventory.ini` and replace each `*_PUBLIC_IP` placeholder with the actual IP from Terraform output.

---

## Step 3: Ansible — Configure All Nodes

```bash
cd ../ansible/

# Test connectivity first
ansible all_nodes -i inventory.ini -m ping

# Run full setup
ansible-playbook -i inventory.ini playbook.yml
```

This will:
- Update all nodes
- Install Docker
- Setup ZRAM on all nodes
- Install K3s server on Node 1
- Join Nodes 2-5 as agents with correct role labels
- Distribute SSH keys so Node 5 can control all others

---

## Step 4: Verify Everything Works

SSH into Node 1:
```bash
ssh -i ~/.ssh/banking-app.pem ubuntu@CONTROL_PLANE_IP
```

Run these checks:
```bash
# All 5 nodes should show Ready
kubectl get nodes

# Node labels should be visible
kubectl get nodes --show-labels

# ZRAM should be active
zramctl

# Node 5 SSH to Node 3 (no password prompt)
ssh ubuntu@NODE3_PRIVATE_IP
```

---

## ⚠️ Important Notes

- **Spot instances**: AWS can terminate these with 2 min notice. Fine for dev. For demo day, switch Node 1 and Node 4 to on-demand.
- **terraform.tfvars**: Never commit this file. It is in .gitignore.
- **terraform.tfstate**: Never delete this file. Back it up locally.
- **AMI ID**: `ami-07c8c1b18ca66bb07` is Ubuntu 22.04 for eu-north-1. Verify it is still current at https://cloud-images.ubuntu.com/locator/ec2/ if you get AMI errors.
