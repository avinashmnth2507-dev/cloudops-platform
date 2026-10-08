# Deployment

## Local

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
pytest -q
uvicorn app.main:app --reload
```

## Docker

```bash
docker compose up --build
curl http://localhost:8000/health
```

## AWS

```bash
cd terraform/environments/dev
cp terraform.tfvars.example terraform.tfvars
# Replace YOUR_PUBLIC_IP with your actual public IPv4 /32.
terraform init
terraform validate
terraform plan
terraform apply
```

After the EC2 host is ready, install/configure k3s and deploy the application.

## Cleanup

```bash
terraform destroy
```
