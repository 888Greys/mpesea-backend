# Docker Deployment Guide for M-Pesa Tracker Backend

Complete guide to deploy the backend using Docker on your VM.

---

## Prerequisites

### 1. Install Docker on VM
```bash
# Update system
sudo apt update && sudo apt upgrade -y

# Install Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh

# Add your user to docker group (no sudo needed)
sudo usermod -aG docker $USER
newgrp docker

# Verify installation
docker --version
docker compose version
```

---

## Quick Start (5 Minutes)

### 1. Clone Repository
```bash
cd ~
git clone https://github.com/YOUR_USERNAME/mpesa-backend.git
cd mpesa-backend
```

### 2. Configure Environment
```bash
# Copy example env
cp .env.example .env

# Edit configuration
nano .env
```

**Set these values:**
```bash
DATABASE_URL=sqlite:///./data/mpesa_tracker.db
SLACK_WEBHOOK_URL=https://hooks.slack.com/services/YOUR/WEBHOOK/URL
DAILY_LIMIT=2000
WARNING_THRESHOLD=0.7
ENVIRONMENT=production
```

### 3. Create Data Directories
```bash
mkdir -p data logs
```

### 4. Build and Run
```bash
# Build the Docker image
docker compose build

# Start the container
docker compose up -d

# Check logs
docker compose logs -f
```

**That's it!** Backend is running on `http://YOUR_VM_IP:8000`

---

## Docker Commands

### Container Management
```bash
# Start containers
docker compose up -d

# Stop containers
docker compose down

# Restart containers
docker compose restart

# View logs
docker compose logs -f

# View logs for last 100 lines
docker compose logs --tail=100 -f

# Check container status
docker compose ps

# Execute command in container
docker compose exec mpesa-backend bash
```

### Rebuild After Code Changes
```bash
# Pull latest code
git pull

# Rebuild and restart
docker compose down
docker compose build --no-cache
docker compose up -d
```

### View Real-time Stats
```bash
docker stats mpesa-tracker
```

---

## Testing

### 1. Health Check
```bash
curl http://localhost:8000/health
```

Expected response:
```json
{
  "status": "running",
  "database": "healthy",
  "slack_configured": true,
  "daily_limit": 2000.0,
  "environment": "production"
}
```

### 2. Test Webhook
```bash
curl -X POST http://localhost:8000/webhook/sms \
  -H "Content-Type: application/json" \
  -d '{
    "sender": "MPESA",
    "message": "RK12AB34CD confirmed. You have sent Ksh500.00 to JOHN DOE. New balance is Ksh1,234.56.",
    "timestamp": 1699000000000
  }'
```

### 3. Test Slack
```bash
curl -X POST http://localhost:8000/test/slack
```

Check Slack for test message!

---

## Using PostgreSQL Instead of SQLite

### 1. Uncomment PostgreSQL in docker-compose.yml
```bash
nano docker-compose.yml

# Uncomment the postgres service and postgres_data volume
```

### 2. Update .env
```bash
DATABASE_URL=postgresql://mpesa_user:mpesa_password@postgres:5432/mpesa_tracker
```

### 3. Restart
```bash
docker compose down
docker compose up -d
```

---

## Nginx Reverse Proxy (Optional - for HTTPS)

### 1. Install Nginx
```bash
sudo apt install nginx -y
```

### 2. Create Nginx Config
```bash
sudo nano /etc/nginx/sites-available/mpesa-tracker
```

```nginx
server {
    listen 80;
    server_name yourdomain.com;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

```bash
# Enable site
sudo ln -s /etc/nginx/sites-available/mpesa-tracker /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl restart nginx
```

### 3. Setup SSL with Certbot
```bash
sudo apt install certbot python3-certbot-nginx -y
sudo certbot --nginx -d yourdomain.com
```

---

## Backup and Restore

### Backup Database
```bash
# SQLite
docker compose exec mpesa-backend cp /app/data/mpesa_tracker.db /app/data/backup_$(date +%Y%m%d).db

# Copy to host
docker cp mpesa-tracker:/app/data/backup_$(date +%Y%m%d).db ./backups/

# PostgreSQL
docker compose exec postgres pg_dump -U mpesa_user mpesa_tracker > backup_$(date +%Y%m%d).sql
```

### Restore Database
```bash
# SQLite
docker cp ./backups/backup_20251103.db mpesa-tracker:/app/data/mpesa_tracker.db
docker compose restart

# PostgreSQL
cat backup_20251103.sql | docker compose exec -T postgres psql -U mpesa_user mpesa_tracker
```

---

## Monitoring

### View Logs
```bash
# All logs
docker compose logs -f

# Only last hour
docker compose logs --since 1h

# Only errors
docker compose logs | grep ERROR
```

### Resource Usage
```bash
docker stats mpesa-tracker
```

### Database Size
```bash
# SQLite
docker compose exec mpesa-backend ls -lh /app/data/mpesa_tracker.db

# PostgreSQL
docker compose exec postgres psql -U mpesa_user -d mpesa_tracker -c "SELECT pg_size_pretty(pg_database_size('mpesa_tracker'));"
```

---

## Troubleshooting

### Container Won't Start
```bash
# Check logs
docker compose logs

# Check if port is in use
sudo lsof -i :8000

# Rebuild from scratch
docker compose down -v
docker compose build --no-cache
docker compose up -d
```

### Can't Connect from Phone
```bash
# Check container is running
docker compose ps

# Check firewall
sudo ufw allow 8000/tcp
sudo ufw status

# Test locally first
curl http://localhost:8000/health

# Test from external
curl http://YOUR_VM_IP:8000/health
```

### Database Issues
```bash
# Reset database (SQLite)
docker compose down
rm data/mpesa_tracker.db
docker compose up -d

# PostgreSQL
docker compose down -v
docker compose up -d
```

### Update to Latest Code
```bash
cd ~/mpesa-backend
git pull
docker compose down
docker compose build
docker compose up -d
```

---

## Auto-start on Boot

Docker containers with `restart: unless-stopped` will automatically start on VM reboot.

Verify:
```bash
# Check restart policy
docker inspect mpesa-tracker | grep RestartPolicy -A 3

# Test by rebooting VM
sudo reboot

# After reboot, check container
docker compose ps
```

---

## Uninstall

```bash
# Stop and remove containers
docker compose down -v

# Remove images
docker rmi mpesa-backend-mpesa-backend

# Remove all data
rm -rf ~/mpesa-backend
```

---

## Architecture

```
┌─────────────────────────────────────────┐
│           Docker Host (VM)              │
│                                         │
│  ┌───────────────────────────────────┐ │
│  │  mpesa-tracker Container          │ │
│  │                                   │ │
│  │  ┌─────────────────────────────┐ │ │
│  │  │  FastAPI Application        │ │ │
│  │  │  - Webhook Endpoint         │ │ │
│  │  │  - SMS Parser               │ │ │
│  │  │  - Spending Agent           │ │ │
│  │  │  - Slack Integration        │ │ │
│  │  └─────────────────────────────┘ │ │
│  │                                   │ │
│  │  ┌─────────────────────────────┐ │ │
│  │  │  SQLite Database (Volume)   │ │ │
│  │  └─────────────────────────────┘ │ │
│  │                                   │ │
│  │  Port: 8000 → Host: 8000         │ │
│  └───────────────────────────────────┘ │
│                                         │
│  Optional:                              │
│  ┌───────────────────────────────────┐ │
│  │  PostgreSQL Container             │ │
│  │  - Port: 5432 (internal)          │ │
│  └───────────────────────────────────┘ │
└─────────────────────────────────────────┘
         │
         │ HTTP :8000
         ▼
   ┌─────────────┐
   │ Android App │
   └─────────────┘
```

---

## Production Checklist

- ✅ Docker and Docker Compose installed
- ✅ `.env` configured with correct values
- ✅ Slack webhook URL set
- ✅ Firewall allows port 8000
- ✅ Container starts automatically (restart policy)
- ✅ Logs are monitored
- ✅ Backups scheduled
- ✅ SSL/HTTPS configured (optional but recommended)

---

**Need help? Check logs:** `docker compose logs -f`
