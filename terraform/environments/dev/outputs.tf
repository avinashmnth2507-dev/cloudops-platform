output "instance_id" { value = module.ec2.instance_id }
output "public_ip" { value = module.ec2.public_ip }
output "kube_api" { value = "https://${module.ec2.public_ip}:6443" }
